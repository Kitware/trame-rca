import logging
from time import time_ns
from typing import Callable, Optional

from vtk_streaming.vtkStreamingCore import (
    VTKPF_IYUV,
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

# Backend selection is delegated to vtkEncoderFactory via a single ranked preference string
# (VTK 9.7 override format): ';' separates keys strongest-to-weakest, ',' separates a key's
# values strongest-to-weakest. Here: always take hardware when available. Among hardware,
# prefer H265 > H264 > VP9
_ENCODER_PREFERENCES = "Hardware=true;Codec=H265,H264,VP9"


def _tune_encoder(encoder: vtkVideoEncoder) -> None:
    # Backend-specific knobs the base vtkVideoEncoder API does not expose. vtkEncoderFactory
    # returns the concrete (downcast) encoder, so these setters are available when matched.
    if encoder.GetClassName() == "vtkVpxEncoder":
        encoder.SetTargetCPUUsage(9)
        encoder.SetRowBasedMultiThreading(False)  # crashes if True


def create_encoder() -> Optional[vtkVideoEncoder]:
    vtkEncoderFactory.SetPreferences(_ENCODER_PREFERENCES)
    encoder = vtkEncoderFactory.CreateEncoder()
    if encoder is None:
        return None
    _tune_encoder(encoder)
    logger.info("Using %s", encoder.GetClassName())
    return encoder


# Short backend names for a human-readable label; keyed by concrete encoder class.
_BACKEND_LABELS = {
    "vtkVideoToolboxEncoder": "VideoToolbox",
    "vtkNvEncoderGL": "nvenc",
    "vtkVpxEncoder": "libvpx",
}


def describe_encoder(encoder: Optional[vtkVideoEncoder]) -> str:
    """Human-readable 'codec (backend)' label, e.g. 'h.265 (VideoToolbox)'."""
    if encoder is None:
        return "unavailable"
    codec = vtkVideoCodecTypeUtilities.ToString(encoder.GetCodec())
    backend = _BACKEND_LABELS.get(encoder.GetClassName(), encoder.GetClassName())
    return f"{codec} ({backend})"


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
    def __init__(
        self,
        render_window: vtkRenderWindow,
        push_callback: Callable[[bytes, dict, int], None],
    ) -> None:
        self._render_window = render_window
        self.frame = None
        self._push_callback = push_callback
        self._window_size = None

        self.encoder = create_encoder()
        if self.encoder is None:
            raise RuntimeError(
                "No suitable video encoder is available on this machine."
            )
        self._initialize(render_window)

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
        self.encoder.AddObserver(
            vtkVideoEncoder.EncodedVideoChunkEvent, self._on_encoded_chunk
        )
        self.encoder.ForceIFrameOn()

    def _reset(self, render_window: vtkRenderWindow) -> None:
        self.release()
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
        if self.encoder is None or self.frame is None:
            return
        if self._window_size != render_window.GetSize():
            self._set_size(render_window_size=render_window.size)
        self.frame.Capture(render_window)
        self.encoder.Encode(self.frame)

    def release(self):
        if self.encoder is not None:
            self.encoder.Shutdown()
