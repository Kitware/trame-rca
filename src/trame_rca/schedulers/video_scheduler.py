from __future__ import annotations

from asyncio import sleep
from typing import Callable, TYPE_CHECKING

from trame.app import asynchronous

if TYPE_CHECKING:
    from vtkmodules.vtkRenderingCore import vtkRenderWindow
    from trame_rca.rca import VtkRemoteControlledArea

from trame_rca.rca import window_wrapper
from trame_rca.encoders import RcaVideoEncoder


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
        self._rca_encoder = RcaVideoEncoder(self._rca.render_window)
        self._is_closing = False
        self._render_requested = False

        self._target_fps = target_fps
        self._render_task = asynchronous.create_task(self._render())

        if push_callback is not None:
            self.set_push_callback(push_callback)

    @property
    def rca(self) -> VtkRemoteControlledArea:
        return self._rca

    def set_push_callback(self, callback: Callable[[bytes, dict], None]):
        self._rca_encoder.set_push_callback(callback)

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
        await sleep(1)
        await self._render_task
        self._rca_encoder.release()

    def schedule_render(self):
        self._render_requested = True

    async def _render(self):
        while not self._is_closing:
            if self._render_requested:
                self._render_requested = False
                render_window = self._rca.render_window
                self._rca_encoder.encode(render_window)

            await sleep(self._target_period_s)
