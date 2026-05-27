import logging

from trame_rca.encoders import RcaImageEncoder as RcaEncoder
from trame_rca.schedulers import RcaImageRenderScheduler as RcaRenderScheduler
from trame_rca.view_adapter import RcaViewAdapter

logger = logging.getLogger(__name__)
try:
    from trame_rca.rca import VtkRemoteControlledArea as VtkWindow
except (ModuleNotFoundError, ImportError) as e:
    logger.info(e.msg)


__all__ = [
    "RcaEncoder",
    "RcaRenderScheduler",
    "RcaViewAdapter",
    "VtkWindow",
]
