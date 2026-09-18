from __future__ import annotations

import asyncio
import os
from asyncio import Event, Queue, sleep
from time import monotonic
from concurrent.futures import Executor
from concurrent.futures.thread import ThreadPoolExecutor
from time import time_ns
from typing import TYPE_CHECKING, Callable

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
        self._interactive_quality = max(1, min(interactive_quality, 100))
        self._still_quality = max(1, min(still_quality, 100))

        self._n_period_until_still_render = 5
        self._last_push_time_ms = int(time_ns() / 1000000)

        self._is_closing = False
        self._encode_pool: Executor = encode_pool or ENCODING_POOL

        self._request_event = Event()
        self._push_queue = Queue()

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
        self._request_event.set()
        self._render_task.cancel()
        self._push_task.cancel()
        await asyncio.gather(self._render_task, self._push_task, return_exceptions=True)

    def schedule_render(self):
        self._request_event.set()

    async def async_schedule_render(self):
        self.schedule_render()

    async def _render(self):
        while not self._is_closing:
            await self._request_event.wait()
            if self._is_closing:
                break

            self._request_event.clear()

            interactive = self._interactive_quality
            still = self._still_quality
            started = monotonic()
            self._render_frame(interactive)

            if interactive == still:
                # Sleep only for what is left of the _target_period_s.
                await sleep(max(0.0, self._target_period_s - (monotonic() - started)))
                continue

            if await self._wait_for_still(started):
                self._render_frame(still)

    async def _wait_for_still(self, timer_started_at):
        self._request_event.clear()

        for i in range(1, self._n_period_until_still_render + 1):
            # Sleep only for what is left of the i-th _target_period_s since the timer started, so that the time
            # spent rendering the interactive frame (and any loop overhead) is not added on top of the wait.
            deadline = timer_started_at + i * self._target_period_s
            await sleep(max(0.0, deadline - monotonic()))
            if self._request_event.is_set():
                return False

        return True

    def _render_frame(self, quality):
        np_img, cols, rows = self._rca.img_cols_rows

        loop = asyncio.get_running_loop()
        future = loop.run_in_executor(
            self._encode_pool,
            self._rca_encoder.encode,
            np_img,
            cols,
            rows,
            quality,
        )
        self._push_queue.put_nowait(future)

    async def _push(self):
        while not self._is_closing:
            result = await self._push_queue.get()
            img, meta, m_time = await result
            if m_time >= self._last_push_time_ms and self._push_callback is not None:
                self._last_push_time_ms = m_time
                self._push_callback(img, meta)

    def reset(self):
        """Nothing to do with images"""
