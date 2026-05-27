import logging
from enum import Enum
from time import time_ns

from numpy.typing import NDArray
from trame_common.utils import profiler
from .pil import encode as encode_pil


logger = logging.getLogger(__name__)
try:
    from .turbo_jpeg import encode as encode_turbo
except RuntimeError:
    logger.warning("Turbo JPEG - NOT AVAILABLE (System Library)")
    encode_turbo = encode_pil
except ModuleNotFoundError:
    logger.warning("Turbo JPEG - NOT AVAILABLE (Python package)")
    encode_turbo = encode_pil


class RcaImageEncoder(Enum):
    JPEG = "jpeg"
    TURBO_JPEG = "turbo-jpeg"
    PNG = "png"
    WEBP = "webp"
    AVIF = "avif"

    def __init__(self, value: str):
        self.__value__ = value
        self._timer_msg = f"rca.encode.{self.value}"

    @property
    def _impl(self):
        """Return encoding method"""
        if self is RcaImageEncoder.TURBO_JPEG:
            return encode_turbo

        return encode_pil

    def encode(
        self,
        np_image: NDArray,
        cols: int,
        rows: int,
        quality: int,
    ) -> tuple[bytes, dict, int]:
        now_ms = int(time_ns() / 1000000)
        with profiler.timer(self._timer_msg):
            return self._impl(np_image, self.value, cols, rows, quality, now_ms)
