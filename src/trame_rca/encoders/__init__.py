import logging

from .image_encoder import RcaImageEncoder

try:
    from .video_encoder import RcaVideoEncoder, VideoEncoderType
except ModuleNotFoundError:
    RcaVideoEncoder = object
    VideoEncoderType = object
    logger = logging.getLogger(__name__)
    logger.warning(
        "VTKStreaming Video encoding is NOT AVAILABLE (missing Python package)"
    )


__all__ = ["RcaVideoEncoder", "RcaImageEncoder", "VideoEncoderType"]
