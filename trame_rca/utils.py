from __future__ import annotations

import os
import asyncio
import time
from asyncio import Queue
from concurrent.futures.thread import ThreadPoolExecutor
from concurrent.futures import Executor
from enum import Enum
from typing import Callable, Optional, TYPE_CHECKING

from numpy.typing import NDArray
from trame.app import asynchronous
from trame_rca.encoders.pil import encode as encode_pil

if TYPE_CHECKING:
    from vtkmodules.vtkRenderingCore import vtkRenderWindow

from trame_rca.protocol import AbstractWindow

try:
    from trame_rca.vtk_utils import VtkWindow
except ModuleNotFoundError as e:
    print(e.msg)

try:
    from trame_rca.encoders.turbo_jpeg import encode as encode_turbo
except RuntimeError:
    print("Turbo JPEG - NOT AVAILABLE (System Library)")
    encode_turbo = encode_pil
except ModuleNotFoundError:
    print("Turbo JPEG - NOT AVAILABLE (Python package)")
    encode_turbo = encode_pil

ENCODING_POOL = ThreadPoolExecutor(max(4, os.cpu_count()))

__all__ = [
    "AbstractWindow",
    "RcaEncoder",
    "RcaViewAdapter",
    "RcaRenderScheduler",
    "VtkWindow",
]


def time_now_ms() -> int:
    return int(time.time_ns() / 1000000)


def window_wrapper(window: AbstractWindow | vtkRenderWindow) -> AbstractWindow:
    if isinstance(window, AbstractWindow):
        return window

    from vtkmodules.vtkRenderingCore import vtkRenderWindow

    if isinstance(window, vtkRenderWindow):
        return VtkWindow(window)

    raise RuntimeError(
        "Invalid window object provided: expected an instance of AbstractWindow"
    )


class RcaEncoder(Enum):
    AVIF = "avif"
    JPEG = "jpeg"
    TURBO_JPEG = "turbo-jpeg"
    PNG = "png"
    WEBP = "webp"

    @property
    def _impl(self):
        """Return encoding method"""
        if self is RcaEncoder.TURBO_JPEG:
            return encode_turbo

        return encode_pil

    def encode(
        self,
        np_image: NDArray,
        cols: int,
        rows: int,
        quality: int,
    ) -> tuple[bytes, dict, int]:
        now_ms = time_now_ms()
        return self._impl(np_image, self.value, cols, rows, quality, now_ms)


class RcaRenderScheduler:
    """
    Render scheduler which renders images and pushing the encoded output to a given callback function.
    Image metadata is also provided alongside the encoded image.

    The scheduler supports multiple rendering backends, including VTK.
    It encodes images to JPEG asynchronously, initially using interactive quality, followed
    by a higher-quality encoding after a few ticks.

    Rendering speed is regulated according to a target FPS to balance performance and quality.

    Call the `close` method to properly stop the scheduler before deleting the object.
    """

    def __init__(
        self,
        window: AbstractWindow | vtkRenderWindow,
        *,
        push_callback: Optional[Callable[[bytes, dict], None]] = None,
        encode_pool: Executor = None,
        target_fps: Optional[float] = None,
        interactive_quality: Optional[int] = None,
        still_quality: Optional[int] = None,
        rca_encoder: Optional[RcaEncoder | str] = None,
    ):
        self._window = window_wrapper(window)
        self._rca_encoder = RcaEncoder(rca_encoder or RcaEncoder.JPEG)
        self._push_callback = push_callback
        self._target_fps = target_fps or 30.0
        self._interactive_quality = interactive_quality
        if self._interactive_quality is None:
            self._interactive_quality = 50

        self._still_quality = still_quality
        if self._still_quality is None:
            self._still_quality = 90

        self._n_period_until_still_render = 5

        self._last_push_time_ms = time_now_ms()
        self._request_render_queue = Queue()
        self._render_quality_queue = Queue()
        self._push_queue = Queue()

        self._is_closing = False
        self._encode_pool: Executor = encode_pool or ENCODING_POOL
        self._render_quality_task = asynchronous.create_task(self._render_quality())
        self._render_task = asynchronous.create_task(self._render())
        self._push_task = asynchronous.create_task(self._push())

    def set_push_callback(self, callback: Callable[[bytes, dict], None]):
        self._push_callback = callback

    @property
    def _target_period_s(self):
        return 1.0 / self._target_fps

    async def close(self):
        # Set closing flag to true and push one final render to make sure every task will have a chance to be canceled.
        if self._is_closing:
            return

        self._is_closing = True
        await self.async_schedule_render()
        await asyncio.sleep(1)
        for task in [self._render_task, self._render_quality_task, self._push_task]:
            await task

    def schedule_render(self):
        asynchronous.create_task(self.async_schedule_render())

    async def async_schedule_render(self):
        await self._request_render_queue.put(True)

    async def _render_quality(self):
        while not self._is_closing:
            await self._request_render_queue.get()
            await self._render_quality_queue.put(self._interactive_quality)
            await self._schedule_still_render()

    async def _schedule_still_render(self):
        await self._empty_request_render_queue()
        for _ in range(self._n_period_until_still_render):
            await asyncio.sleep(self._target_period_s)
            if not self._request_render_queue.empty():
                return
        await self._render_quality_queue.put(self._still_quality)

    async def _empty_request_render_queue(self):
        while not self._request_render_queue.empty():
            await self._request_render_queue.get()

    async def _render(self):
        while not self._is_closing:
            quality = await self._render_quality_queue.get()
            np_img, cols, rows = self._window.img_cols_rows
            await self._push_queue.put(
                asyncio.wrap_future(
                    self._encode_pool.submit(
                        self._rca_encoder.encode,
                        np_img,
                        cols,
                        rows,
                        quality,
                    )
                )
            )

    async def _push(self):
        while not self._is_closing:
            result = await self._push_queue.get()
            img, meta, m_time = await result
            if m_time >= self._last_push_time_ms and self._push_callback is not None:
                self._last_push_time_ms = m_time
                self._push_callback(img, meta)


class RcaViewAdapter:
    """
    Adapter for Remote Control Area.
    Uses an RCA render scheduler to serialize window to the RCA.
    """

    def __init__(
        self,
        window: AbstractWindow | vtkRenderWindow,
        name: str,
        *,
        scheduler: RcaRenderScheduler = None,
        do_schedule_render_on_interaction=True,
    ):
        self._window = window_wrapper(window)
        if scheduler is None:
            scheduler = RcaRenderScheduler(
                self._window,
                target_fps=30,
                rca_encoder="turbo-jpeg",  # will fallback to jpeg if turbo not available
                encode_pool=ENCODING_POOL,
            )

        self._scheduler = scheduler
        self._scheduler.set_push_callback(self.push)
        self.area_name = name
        self.streamer = None
        self._prev_data_m_time = None

        self._press_set = set()
        self._do_render_on_interaction = do_schedule_render_on_interaction
        self._scale = 1
        self._current_size = None

    def update_quality(self, interactive=50, still=90):
        self._scheduler._interactive_quality = interactive
        self._scheduler._still_quality = still

    @property
    def image_size(self):
        if self._current_size is None:
            return (300, 300)
        return int(self._current_size[0] * self._current_size[2] * self._scale), int(
            self._current_size[1] * self._current_size[2] * self._scale
        )

    @property
    def scale(self):
        return self._scale

    @scale.setter
    def scale(self, value):
        if self._scale != value:
            self._scale = value

        if self._current_size is not None:
            self.update_size(
                "self",
                {
                    "w": self._current_size[0],
                    "h": self._current_size[1],
                    "p": self._current_size[2],
                },
            )

    def set_streamer(self, stream_manager):
        self.streamer = stream_manager

    def update_size(self, origin, size):
        # Resize to ten pixel min to avoid rendering problems
        width = max(10, int(size.get("w", 300)))
        height = max(10, int(size.get("h", 300)))
        pixel_ratio = size.get("p", 1)
        self._current_size = (width, height, pixel_ratio)
        width = int(width * pixel_ratio * self._scale)
        height = int(height * pixel_ratio * self._scale)
        self._window.process_resize_event(width, height)
        self._scheduler.schedule_render()

    def push(self, content, meta: dict):
        if not self.streamer:
            return

        if content is None:
            return

        self.streamer.push_content(self.area_name, meta, content)

    def do_discard_extra_release_event(self, event):
        """
        Ignores mouse release events which have not been preceded by a previous mouse press.
        """
        event_type = event["type"]
        if "Press" in event_type:
            self._press_set.add(event_type)
            return False

        if not event_type.endswith("Release"):
            return False

        press_event = event_type.replace("Release", "Press")
        if press_event in self._press_set:
            self._press_set.remove(press_event)
            return False

        return True

    def on_interaction(self, _, event):
        if self.do_discard_extra_release_event(event):
            return
        self._window.process_interaction_event(event)
        if self._do_render_on_interaction:
            self._scheduler.schedule_render()

    def schedule_render(self):
        """
        Schedule a render and push to the RCA view when rendering is ready.
        """
        self._scheduler.schedule_render()

    def update(self):
        self.schedule_render()

    async def close(self):
        await self._scheduler.close()
