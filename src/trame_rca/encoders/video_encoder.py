import logging
from time import time_ns
from typing import Callable, Optional

from trame_common.utils import profiler
from vtk_streaming.vtkStreamingCore import (
    VTKPF_IYUV,
    VTKVC_AV1,
    VTKVC_H264,
    VTKVC_H265,
    VTKVC_VP9,
    vtkCompressedVideoPacket,
    vtkVideoCodecTypeUtilities,
)
from vtk_streaming.vtkStreamingEncode import vtkEncoderFactory, vtkVideoEncoder
from vtk_streaming.vtkStreamingOpenGL2 import vtkOpenGLVideoFrame
from vtkmodules.util.misc import calldata_type
from vtkmodules.util.vtkConstants import VTK_OBJECT
from vtkmodules.vtkCommonCore import vtkUnsignedCharArray
from vtkmodules.vtkRenderingCore import vtkRenderWindow

logger = logging.getLogger(__name__)

# Server-side ranking, strongest first. Each entry: (vtk codec, name, WebCodecs probe strings)
_CODECS = [
    (VTKVC_H265, "h265", ["hev1.1.6.L93.B0", "hvc1.1.6.L93.B0"]),
    (VTKVC_H264, "h264", ["avc1.42001f", "avc1.4d001f"]),
    (VTKVC_VP9, "vp9", ["vp09.00.10.08"]),
    (VTKVC_AV1, "av1", ["av01.0.04M.08"]),
]
_DEFAULT_CODECS = [name for _, name, _ in _CODECS]

_BACKEND_LABELS = {
    "vtkVideoToolboxEncoder": "VideoToolbox",
    "vtkNvEncoderGL": "nvenc",
    "vtkVpxEncoder": "libvpx",
}


def available_codecs() -> list[dict]:
    """Codecs this server can encode, server-preferred first."""
    timer = profiler.Timer("rca.video.available_codecs")
    result = []
    with timer:
        for codec, name, probes in _CODECS:
            if vtkEncoderFactory.CheckAvailability(codec):
                result.append(
                    {
                        "codec": name,
                        "probes": probes,
                    }
                )
    return result


def create_encoder(codecs: Optional[list[str]] = None) -> Optional[vtkVideoEncoder]:
    codecs = codecs or _DEFAULT_CODECS
    vtkEncoderFactory.SetPreferences(f"Hardware=true;Codec={','.join(codecs)}")
    encoder = vtkEncoderFactory.CreateEncoder()
    if encoder is None:
        return None
    if encoder.GetClassName() == "vtkVpxEncoder":
        encoder.SetTargetCPUUsage(9)
        encoder.SetRowBasedMultiThreading(False)  # crashes if True
    logger.info("Using %s", encoder.GetClassName())
    return encoder


def describe_encoder(encoder: Optional[vtkVideoEncoder]) -> dict:
    if encoder is None:
        return {
            "codec": None,
            "backend": None,
            "hardware": False,
            "label": "unavailable",
        }
    codec = vtkVideoCodecTypeUtilities.ToString(encoder.GetCodec())
    backend = _BACKEND_LABELS.get(encoder.GetClassName(), encoder.GetClassName())
    return {
        "codec": codec,
        "backend": backend,
        "hardware": bool(encoder.IsHardwareAccelerated()),
        "label": f"{codec} ({backend})",
    }


def encode(
    video_packet: vtkCompressedVideoPacket, now_ms: int
) -> tuple[bytes, dict, int]:
    frame_data: vtkUnsignedCharArray = video_packet.GetData()
    meta = {
        "type": "application/octet-stream",
        "codec": video_packet.GetCodecLongName(),
        "w": video_packet.GetDisplayWidth(),
        "h": video_packet.GetDisplayHeight(),
        "st": now_ms,
        "key": ("key" if video_packet.GetIsKeyFrame() else "delta"),
    }

    return (bytes(frame_data), meta, now_ms)


class RcaVideoEncoder:
    """
    Wraps a vtkVideoEncoder bound to a render window.

    With ``defer=True`` no encoder exists until :meth:`configure` is called with the
    negotiated codec list; :meth:`encode` is a no-op until then.
    """

    def __init__(
        self,
        render_window: vtkRenderWindow,
        push_callback: Callable[[bytes, dict, int], None],
        *,
        codecs: Optional[list[str]] = None,
        defer: bool = False,
    ) -> None:
        self._timer_encoder = profiler.Timer("rca.video.encode")
        self._timer_capture = profiler.Timer("rca.video.frame_capture")
        self._timer_configure = profiler.Timer("rca.video.configure")
        self._render_window = render_window
        self._push_callback = push_callback
        self._codecs = codecs
        self.encoder = None
        self.frame = None
        self._window_size = None
        if not defer:
            self.configure(codecs)

    @property
    def is_ready(self) -> bool:
        return self.encoder is not None

    @property
    def codecs(self) -> Optional[list[str]]:
        return self._codecs

    def configure(self, codecs: Optional[list[str]]) -> dict:
        """(Re)create the encoder for the given codec ranking. Returns :func:`describe_encoder`."""
        with self._timer_configure:
            self.release()
            self._codecs = codecs
            self.encoder = create_encoder(codecs)
            if self.encoder is None:
                raise RuntimeError(
                    "No suitable video encoder is available on this machine."
                )
            self.encoder.AddObserver(
                vtkVideoEncoder.EncodedVideoChunkEvent, self._on_encoded_chunk
            )

            self._initialize(self._render_window)
        return self.describe()

    def describe(self) -> dict:
        return describe_encoder(self.encoder)

    def _set_size(self, render_window_size: tuple[int]):
        self._window_size = render_window_size
        self.frame.SetWidth(self._window_size[0])
        self.frame.SetHeight(self._window_size[1])
        self.frame.AllocateDataStore()

    def _initialize(self, render_window: vtkRenderWindow):
        self.encoder.SetGraphicsContext(render_window)
        self.encoder.SetInputPixelFormat(VTKPF_IYUV)
        self.encoder.SetBitRateControlMode(vtkVideoEncoder.BRCType.CQP)
        self.encoder.SetQuantizationParameter(5)  # 0 (high quality) - 63 (low quality)

        self.frame = vtkOpenGLVideoFrame()
        self.frame.SetContext(render_window)
        self.frame.SetPixelFormat(VTKPF_IYUV)

        self._set_size(render_window.GetSize())
        self.encoder.Initialize()
        self.encoder.ForceIFrameOn()

    def reset(self, render_window: vtkRenderWindow) -> None:
        if not self.is_ready:
            return
        self._render_window = render_window
        self.encoder.Shutdown()
        self._initialize(render_window)

    @calldata_type(VTK_OBJECT)
    def _on_encoded_chunk(
        self,
        _encoder: vtkVideoEncoder,
        _event: str,
        video_packet: vtkCompressedVideoPacket,
    ) -> None:
        now_ms = int(time_ns() / 1000000)
        content, meta, _ = encode(video_packet, now_ms)
        if self._push_callback is not None:
            self._push_callback(content, meta, now_ms)

    def encode(self, render_window: vtkRenderWindow):
        if not self.is_ready:
            return
        if self._window_size != render_window.GetSize():
            self._set_size(render_window_size=render_window.size)
        with self._timer_capture:
            self.frame.Capture(render_window)
        with self._timer_encoder:
            self.encoder.Encode(self.frame)

    def release(self):
        if self.encoder is not None:
            self.encoder.Shutdown()
            self.encoder = None
            self.frame = None
