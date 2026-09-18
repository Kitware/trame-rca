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

# PLEASE DO NOT ALTER!
# Video stream tuning for low-latency CBR (Constant Bit Rate) setup
# - low-delay mode: P1 preset + ultra-low-latency tuning, infinite GOP (Group Of Pictures),
#   0 B-frames, lookahead=False produces a packet per frame, nothing gets buffered;
# - CBR at the chosen bitrate, with the frame rate told to the rate control
#   so its per-frame budget is right (the default in vtk_streaming assumes 30 fps);
# - QP (Quantization Parameter) floor so a static scene doesn't burn the budget on
#   invisible detail.
VIDEO_MAXIMUM_B_FRAMES = 0
VIDEO_TARGET_FPS_DEFAULT = 30
VIDEO_BITRATE_MBPS_DEFAULT = 8
VIDEO_BITRATE_MBPS_MIN = 1
VIDEO_BITRATE_MBPS_MAX = 100
VIDEO_QP_FLOOR = 5  # H.264/HEVC QP scale; 5 is visually lossless


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

    def configure(
        self,
        codecs: Optional[list[str]],
        target_fps: int = VIDEO_TARGET_FPS_DEFAULT,
        target_bitrate_mbps: float = VIDEO_BITRATE_MBPS_DEFAULT,
    ) -> dict:
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
            self._tune(target_fps, target_bitrate_mbps)
            self._initialize(self._render_window)
        return self.describe()

    def describe(self) -> dict:
        return describe_encoder(self.encoder)

    def _set_size(self, render_window_size: tuple[int]):
        self._window_size = render_window_size
        self.frame.SetWidth(self._window_size[0])
        self.frame.SetHeight(self._window_size[1])
        self.frame.AllocateDataStore()

    def _tune(self, target_fps: int, target_bitrate_mbps: float):
        if self.encoder is None:
            raise RuntimeError(
                "Tune called but no encoder exists. Did you forget to call RcaVideoEncoder.configure(codecs)?"
            )
        bitrate = int(float(target_bitrate_mbps) * 1_000_000)
        self.encoder.low_delay_mode = True
        self.encoder.maximum_b_frames = VIDEO_MAXIMUM_B_FRAMES
        self.encoder.time_base_start = 1
        self.encoder.time_base_end = max(1, int(target_fps))
        self.encoder.bit_rate_control_mode = vtkVideoEncoder.BRCType.CBR
        self.encoder.quantization_parameter = VIDEO_QP_FLOOR
        self.encoder.bit_rate = bitrate
        self.encoder.min_bit_rate = bitrate
        self.encoder.max_bit_rate = bitrate
        # one IDR (Instantaneous Decoder Refresh) to start the (re)built context, then delta frames only.
        self.encoder.force_i_frame = True  # we will turn this off in _on_encoded_chunk

    def _initialize(self, render_window: vtkRenderWindow):
        self.encoder.SetGraphicsContext(render_window)
        self.encoder.SetInputPixelFormat(VTKPF_IYUV)

        self.frame = vtkOpenGLVideoFrame()
        self.frame.SetContext(render_window)
        self.frame.SetPixelFormat(VTKPF_IYUV)

        self._set_size(render_window.GetSize())
        self.encoder.Initialize()

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
        if video_packet.is_key_frame and _encoder.force_i_frame:
            _encoder.force_i_frame = False
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
