from __future__ import annotations

import os
from asyncio import Queue, sleep, wrap_future
from typing import TYPE_CHECKING, Callable
from time import time_ns

from concurrent.futures import Executor
from concurrent.futures.thread import ThreadPoolExecutor
from trame.app import asynchronous

if TYPE_CHECKING:
    from vtkmodules.vtkRenderingCore import vtkRenderWindow

from trame_rca.encoders import RcaImageEncoder
from trame_rca.rca import RemoteControlledAreaProtocol, window_wrapper


ENCODING_POOL = ThreadPoolExecutor(max(4, os.cpu_count()))


class RcaImageRenderScheduler:
    """
    Image-based implementation of :class:`RcaRenderSchedulerProtocol`.

    Captures rendered frames, encodes them to an image format (:class:`RcaImageEncoder`) asynchronously, and forwards
    the encoded images and metadata to a callback. Frames are initially encoded using interactive quality settings
    and may be re-encoded at higher quality shortly afterwards.

    Supports multiple rendering backends, including VTK.

    Call :meth:`close` before discarding the scheduler to release resources and stop background tasks.
    """

    def __init__(
        self,
        window: RemoteControlledAreaProtocol | vtkRenderWindow,
        *,
        push_callback: Callable[[bytes, dict], None] | None = None,
        encode_pool: Executor = None,
        target_fps: float = 30.0,
        interactive_quality: int = 50,
        still_quality: int = 90,
        rca_encoder: RcaImageEncoder | str = "jpeg",
        **_,
    ):
        self._rca = window_wrapper(window)
        self._rca_encoder = RcaImageEncoder(rca_encoder)

        self._push_callback = push_callback

        self._target_fps = target_fps
        self._interactive_quality = interactive_quality
        self._still_quality = still_quality

        self._n_period_until_still_render = 5
        self._last_push_time_ms = int(time_ns() / 1000000)
        self._request_render_queue = Queue()
        self._render_quality_queue = Queue()
        self._push_queue = Queue()

        self._is_closing = False
        self._encode_pool: Executor = encode_pool or ENCODING_POOL
        self._render_quality_task = asynchronous.create_task(self._render_quality())
        self._render_task = asynchronous.create_task(self._render())
        self._push_task = asynchronous.create_task(self._push())

    def update_quality(self, interactive, still):
        self._interactive_quality = interactive
        self._still_quality = still

    def set_push_callback(self, callback: Callable[[bytes, dict], None]):
        self._push_callback = callback

    @property
    def rca(self):
        return self._rca

    @property
    def target_fps(self):
        return self._target_fps

    @target_fps.setter
    def target_fps(self, v):
        self._target_fps = v

    @property
    def _target_period_s(self):
        return 1.0 / self._target_fps

    async def close(self):
        # Set closing flag to true and push one final render to make sure every task will have a chance to be canceled.
        if self._is_closing:
            return

        self._is_closing = True
        await self.async_schedule_render()
        await sleep(1)
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
            await sleep(self._target_period_s)
            if not self._request_render_queue.empty():
                return
        await self._render_quality_queue.put(self._still_quality)

    async def _empty_request_render_queue(self):
        while not self._request_render_queue.empty():
            await self._request_render_queue.get()

    async def _render(self):
        while not self._is_closing:
            quality = await self._render_quality_queue.get()
            np_img, cols, rows = self._rca.img_cols_rows
            await self._push_queue.put(
                wrap_future(
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
