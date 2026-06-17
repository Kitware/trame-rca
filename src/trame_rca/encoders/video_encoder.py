from time import time_ns
from typing import Callable
import logging

from vtkmodules.vtkCommonCore import vtkUnsignedCharArray
from vtkmodules.vtkRenderingCore import vtkRenderWindow
from vtkmodules.util.misc import calldata_type
from vtkmodules.util.vtkConstants import VTK_OBJECT

from vtk_streaming.vtkStreamingCore import (
    VTKPF_IYUV,
    VTKVC_H264,
    VTKVC_VP9,
    vtkCompressedVideoPacket,
)
from vtk_streaming.vtkStreamingEncode import vtkVideoEncoder
from vtk_streaming.vtkStreamingNvEncode import vtkNvEncoderGL
from vtk_streaming.vtkStreamingOpenGL2 import vtkOpenGLVideoFrame
from vtk_streaming.vtkStreamingVpxEncode import vtkVpxEncoder

logger = logging.getLogger(__name__)


def create_vpx_encoder() -> vtkVpxEncoder:
    encoder = vtkVpxEncoder()
    encoder.SetCodec(VTKVC_VP9)
    encoder.SetTargetCPUUsage(9)
    encoder.SetRowBasedMultiThreading(False)  # crashes if True
    return encoder


def create_nvenc_encoder() -> vtkNvEncoderGL:
    encoder = vtkNvEncoderGL()
    encoder.SetCodec(VTKVC_H264)
    return encoder


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
        self.encoder = None
        self.frame = None
        self._push_callback = push_callback
        self._window_size = None

        if vtkNvEncoderGL.CheckAvailability():
            logger.info("Using H264 through NVENC")
            self._create_encoder = create_nvenc_encoder
        else:
            logger.info("Using VP9 through libvpx")
            self._create_encoder = create_vpx_encoder

        self._initialize(render_window)

    def _set_size(self, render_window_size: tuple[int]):
        self._window_size = render_window_size
        width = self._window_size[0] + self._window_size[0] % 4
        height = self._window_size[1] + self._window_size[1] % 4

        self.encoder.SetWidth(width)
        self.encoder.SetHeight(height)
        self.frame.SetWidth(width)
        self.frame.SetHeight(height)
        self.frame.AllocateDataStore()

    def _initialize(self, render_window: vtkRenderWindow):
        self.encoder = self._create_encoder()
        self.encoder.SetGraphicsContext(render_window)
        self.encoder.SetInputPixelFormat(VTKPF_IYUV)
        self.encoder.SetBitRateControlMode(3)  # Constant quantization
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
        _encoder: vtkNvEncoderGL | vtkVpxEncoder,
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
            # Ideally we would just call _set_size here
            self._reset(render_window)
        self.frame.Capture(render_window)
        self.encoder.Encode(self.frame)

    def release(self):
        self.encoder = None
        self.frame = None
