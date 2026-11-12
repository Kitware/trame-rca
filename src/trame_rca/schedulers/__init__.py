import logging

from .image_scheduler import RcaImageRenderScheduler
from .protocol import RcaRenderSchedulerProtocol

logger = logging.getLogger(__name__)
try:
    from .video_scheduler import RcaVideoRenderScheduler
except (ModuleNotFoundError, ImportError) as e:
    logger.info(e.msg)
    RcaVideoRenderScheduler = None
try:
    from .shared_texture_scheduler import RcaSharedTextureRenderScheduler
except (ModuleNotFoundError, ImportError) as e:
    logger.info(e.msg)
    RcaSharedTextureRenderScheduler = None


__all__ = [
    "RcaImageRenderScheduler",
    "RcaRenderSchedulerProtocol",
    "RcaSharedTextureRenderScheduler",
    "RcaVideoRenderScheduler",
]
