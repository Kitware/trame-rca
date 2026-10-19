"""A render scheduler that renders into a texture shared with the Electron main process (EMP).

OS handles do not go through trame's websocket because that is wired to the Electron renderer
process (ERP), which does not have access to the OS API needed to import a texture.

Instead the scheduler tells the EMP about the shared texture and each finished frame over
trame_rca.electron.comm, and the EMP hands them to the renderer process. Size and input still
come from the RemoteControlledArea through the RcaViewAdapter.

Renders run on trame's event loop.
"""

from __future__ import annotations
from asyncio.futures import Future

import asyncio
import logging
import time
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from vtkmodules.vtkRenderingCore import vtkRenderWindow

from trame.app import asynchronous

from trame_rca.electron.comm import (
    PROTOCOL_VERSION,
    LineConnection,
    check_protocol,
)
from trame_rca.electron.passports import texture_passport_class, TexturePassport
from trame_rca.rca import (
    RemoteControlledAreaProtocol,
    VtkRemoteControlledArea,
    window_wrapper,
)

logger = logging.getLogger(__name__)

FRAME_DONE_TIMEOUT_S = 1.0


def _report_failure(task):
    # Otherwise asyncio only reports it once the task is garbage collected.
    if not task.cancelled() and task.exception():
        logger.error("render task failed", exc_info=task.exception())


class RcaSharedTextureRenderScheduler:
    """Implements RcaRenderSchedulerProtocol by sharing the render window's texture with Electron."""

    def __init__(
        self,
        window: RemoteControlledAreaProtocol | vtkRenderWindow,
        emp_port: int,
        *,
        target_fps: float = 60.0,
        on_disconnect: Callable[[], None] | None = None,
        before_render: Callable[[], None] | None = None,
    ):
        self._rca = window_wrapper(window)
        assert isinstance(self._rca, VtkRemoteControlledArea), (
            "SharedTexture scheduler only works with VTK render windows!"
        )
        self._emp_port = emp_port
        self._target_fps = target_fps
        self._on_disconnect = on_disconnect
        # Called before every frame, e.g. to animate the scene. It may schedule_render() again.
        self._before_render = before_render
        self._push_callback = None

        self._conn = None
        self._passport = None
        self._passport_name_future = None
        self._seq = 0
        self._frame_done = None
        # Renders asked for before start() wait in here.
        self._request_event = asyncio.Event()
        self._tasks = []
        self._is_closing = False

        # Render into the FBOs only: Frame() then stops after resolving into the DisplayFramebuffer.
        self._rca.render_window.SetUseOffScreenBuffers(True)
        self._rca.render_window.SetDoubleBuffer(False)
        self._rca.render_window.SetShowWindow(False)
        self._rca.render_window.GetInteractor().Initialize()

        # Wait for the client to report it's canvas size before rendering to avoid
        # sending a not-so-useful 300x300 default sized frame.
        self._sized = False
        process_resize_event = self._rca.process_resize_event

        def on_resize(width, height):
            process_resize_event(width, height)
            self._sized = True
            self.schedule_render()  # to ensure self._request_event is set

        self._rca.process_resize_event = on_resize

    @property
    def rca(self):
        return self._rca

    @property
    def target_fps(self):
        return self._target_fps

    @target_fps.setter
    def target_fps(self, value):
        self._target_fps = value

    def set_push_callback(self, callback):
        # Frames go to the EMP, never through the push callback.
        self._push_callback = callback

    def reset(self):
        """Nothing to re-initialize."""

    def schedule_render(self):
        self._request_event.set()

    def start(self, url: str | None = None, **_):
        """Connect to the EMP and start rendering. Call once trame's event loop runs.

        ``url`` is the page the EMP should load: the one trame serves.
        """
        self._start_task(self._run(url))

    def _start_task(self, coro):
        task = asynchronous.create_task(coro)
        task.add_done_callback(_report_failure)
        self._tasks.append(task)

    async def close(self):
        if self._is_closing:
            return
        self._is_closing = True
        for task in self._tasks:
            task.cancel()
        if self._conn:
            self._conn.close()
        if self._passport:
            self._passport.release()
            self._passport = None

    async def _run(self, url):
        assert isinstance(self._rca, VtkRemoteControlledArea), (
            "SharedTexture scheduler only works with VTK render windows!"
        )
        self._passport_name_future = asyncio.get_running_loop().create_future()
        self._conn = await LineConnection.open(self._emp_port)
        logger.info("connected to the Electron main process on port %d", self._emp_port)
        self._start_task(self._read())
        try:
            passport_name = await self._passport_name_future
        except Exception:
            await self._disconnect()
            raise
        await self._conn.send(
            {"type": "server_ready", "protocol": PROTOCOL_VERSION, "url": url}
        )
        next_frame = 0
        period = 1.0 / self._target_fps

        while not self._is_closing:
            await self._request_event.wait()
            self._request_event.clear()
            # Only render when the ERP has booted up (<canvas> is sized)
            if not self._sized:
                continue

            await self._update_texture(passport_name)
            assert isinstance(self._passport, TexturePassport), "Passport unavailable!"
            if self._before_render:
                self._before_render()
            self._rca.render_window.Render()
            self._rca.render_window.MakeCurrent()
            await self._passport.flush_graphics_commands()

            # Backpressure: don't touch the texture until Electron is done reading it.
            # Input keeps setting the request event meanwhile, so it renders once afterwards.
            seq = self._seq
            self._seq += 1
            self._frame_done = asyncio.get_running_loop().create_future()
            await self._conn.send(
                {"type": "frame", "seq": seq, "timestamp_us": int(time.time() * 1e6)}
            )
            try:
                await asyncio.wait_for(self._frame_done, FRAME_DONE_TIMEOUT_S)
            except asyncio.TimeoutError:
                logger.warning(
                    "frame %d: no frame_done within %ss, continuing",
                    seq,
                    FRAME_DONE_TIMEOUT_S,
                )
            self._frame_done = None
            # Pace against fixed frame clock held in `next_frame`
            next_frame = max(next_frame + period, time.monotonic())
            await asyncio.sleep(max(0.0, next_frame - time.monotonic()))

    async def _update_texture(self, passport_name):
        """(Re)allocate the shared texture when the render window's size changed."""
        assert isinstance(self._rca, VtkRemoteControlledArea), (
            "SharedTexture scheduler only works with VTK render windows!"
        )
        assert isinstance(self._conn, LineConnection), (
            "Connection to EMP is uninitialized!"
        )
        width, height = self._rca.render_window.GetSize()
        if self._passport and (self._passport.width, self._passport.height) == (
            width,
            height,
        ):
            return
        if self._passport is None:
            # The first render creates the context and the framebuffers the passport patches.
            self._rca.render_window.Render()
            self._rca.render_window.MakeCurrent()
        passport_class = texture_passport_class(passport_name)
        old, self._passport = (
            self._passport,
            passport_class(self._rca.render_window, width, height),
        )
        if old:
            # Frames still in flight hold their own imports in Electron.
            old.release()
        await self._conn.send(self._passport.to_json())

    async def _read(self):
        assert isinstance(self._conn, LineConnection), (
            "Connection to EMP is uninitialized!"
        )
        assert isinstance(self._passport_name_future, Future), (
            "Passport name future was not created!"
        )
        try:
            while True:
                msg = await self._conn.recv()
                if msg["type"] == "hello":
                    try:
                        check_protocol(msg)
                    except Exception as e:
                        self._passport_name_future.set_exception(e)
                        return
                    self._passport_name_future.set_result(msg["passport"])
                elif msg["type"] == "frame_done":
                    if (
                        msg["seq"] == self._seq - 1
                        and self._frame_done
                        and not self._frame_done.done()
                    ):
                        self._frame_done.set_result(None)
                    if msg.get("dropped"):
                        # The page never processed it: e.g. it was still loading or busy..
                        logger.info("frame %d dropped, rendering again", msg["seq"])
                        self.schedule_render()
        except (EOFError, ConnectionError):
            logger.info("the Electron main process disconnected")
            if not self._passport_name_future.done():
                self._passport_name_future.set_exception(
                    ConnectionError("disconnected before the hello message")
                )
                return
            await self._disconnect()

    async def _disconnect(self):
        await self.close()
        if self._on_disconnect:
            self._on_disconnect()
