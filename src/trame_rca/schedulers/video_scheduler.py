from __future__ import annotations

import asyncio
from asyncio import Event, sleep
from typing import TYPE_CHECKING, Callable

from trame.app import asynchronous

if TYPE_CHECKING:
    from vtkmodules.vtkRenderingCore import vtkRenderWindow

    from trame_rca.rca import VtkRemoteControlledArea

from trame_rca.encoders import RcaVideoEncoder
from trame_rca.rca import window_wrapper


class RcaVideoRenderScheduler:
    """
    Video-based implementation of :class:`RcaRenderSchedulerProtocol`.

    This scheduler encodes rendered frames using an :class:`RcaVideoEncoder` and forwards the encoded video
    data to a callback. Render requests are coalesced and processed by a background task running at the
    configured target frame rate, preventing the encoder from producing frames faster than the desired FPS.

    Supports only VTK rendering backend (:class:`vtkRenderWindow` or :class:`VtkRemoteControlledArea`).

    Call :meth:`close` before discarding the scheduler to stop the background task and release encoder resources.
    """

    def __init__(
        self,
        window: VtkRemoteControlledArea | vtkRenderWindow,
        *,
        push_callback: Callable[[bytes, dict]] | None = None,
        target_fps: float = 30.0,
    ):
        self._rca: VtkRemoteControlledArea = window_wrapper(window)
        self._push_callback = push_callback
        self._rca_encoder = RcaVideoEncoder(
            self._rca.render_window, push_callback=self._push
        )
        self._is_closing = False
        self._request_event = Event()

        self._target_fps = target_fps
        self._render_task = asynchronous.create_task(self._render())

    @property
    def rca(self) -> VtkRemoteControlledArea:
        return self._rca

    def set_push_callback(self, callback: Callable[[bytes, dict], bool]):
        self._push_callback = callback

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
        if self._is_closing:
            return

        self._is_closing = True
        self._request_event.set()
        self._render_task.cancel()
        await asyncio.gather(self._render_task, return_exceptions=True)
        self._rca_encoder.release()

    def schedule_render(self):
        self._request_event.set()

    async def _render(self):
        while not self._is_closing:
            await self._request_event.wait()
            if self._is_closing:
                break

            self._request_event.clear()
            self._rca_encoder.encode(self._rca.render_window)
            await sleep(self._target_period_s)

    def _push(self, content: bytes, meta: dict, _m_time: int):
        if self._push_callback is not None:
            self._push_callback(content, meta)

    def reset(self):
        self._rca_encoder.reset(self._rca.render_window)
