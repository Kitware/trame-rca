"""A render scheduler that renders into a texture shared with the Electron main process (EMP).

OS handles do not go through trame's websocket because that is wired to the Electron renderer
process (ERP), which does not have access to the OS API needed to import a texture.

Instead the scheduler tells the EMP about the shared textures and each finished frame over
trame_rca.electron.comm, and the EMP hands them to the renderer process. Size and input still
come from the RemoteControlledArea through the RcaViewAdapter.

The textures form a ring: VTK renders the next frame into the next texture while Electron
still shows the previous ones, and only waits when the texture it's about to reuse is still
held by Electron.

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
from trame_common.utils import profiler

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


def _check_texture_count(value):
    if int(value) != value or value < 1:
        raise ValueError(f"texture_count must be a positive integer, not {value!r}")
    return int(value)


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
        texture_count: int = 2,
    ):
        self._timer_render = profiler.Timer("rca.shared_texture.render")
        self._timer_flush = profiler.Timer("rca.shared_texture.flush")
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
        self._texture_count = _check_texture_count(texture_count)
        # The ring of shared textures
        self._passports = []
        # the frame_done of the last frame per shared texture.
        self._slot_frames = []
        self._next_slot = 0
        # `seq`:`frame_done` future map valid until Electron fulfils with the "type":"frame_done" message.
        self._frames_in_flight = {}
        self._passport_name_future = None
        self._seq = 0
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

    @property
    def texture_count(self):
        """How many shared textures VTK renders into in turn. 1 waits for Electron after every frame."""
        return self._texture_count

    @texture_count.setter
    def texture_count(self, value):
        value = _check_texture_count(value)
        if value != self._texture_count:
            self._texture_count = value
            # The ring is rebuilt before the next frame.
            self.schedule_render()

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
        for passport in self._passports:
            passport.release()
        self._passports = []

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

            # Do not touch a texture in the ring until Electron is done reading it.
            # Wait until a slot frees up in the ring.
            await self._wait_for_slot(self._next_slot)
            await self._update_textures(passport_name)
            slot = self._next_slot
            passport = self._passports[slot]
            if (passport.width, passport.height) != tuple(
                self._rca.render_window.GetSize()
            ):
                # Resized while waiting: rendering now would reallocate the shared texture.
                self.schedule_render()
                continue
            self._next_slot = (slot + 1) % len(self._passports)

            passport.attach()
            if self._before_render:
                self._before_render()
            with self._timer_render:
                self._rca.render_window.Render()
            with self._timer_flush:
                self._rca.render_window.MakeCurrent()
                await passport.flush_graphics_commands()

            seq = self._seq
            self._seq += 1
            frame_done = asyncio.get_running_loop().create_future()
            self._slot_frames[slot] = frame_done
            self._frames_in_flight[seq] = frame_done
            await self._conn.send(
                {
                    "type": "frame",
                    "seq": seq,
                    "slot": slot,
                    "timestamp_us": int(time.time() * 1e6),
                }
            )
            # Pace against fixed frame clock held in `next_frame`
            next_frame = max(next_frame + period, time.monotonic())
            await asyncio.sleep(max(0.0, next_frame - time.monotonic()))

    async def _wait_for_slot(self, slot):
        """Wait until Electron released the last frame rendered into the texture at ``slot``."""
        frame_done = self._slot_frames[slot] if slot < len(self._slot_frames) else None
        if frame_done is None or frame_done.done():
            return
        try:
            # shield: a frame_done arriving late must still find its future.
            await asyncio.wait_for(asyncio.shield(frame_done), FRAME_DONE_TIMEOUT_S)
        except asyncio.TimeoutError:
            logger.warning(
                "texture %d: no frame_done within %ss, continuing",
                slot,
                FRAME_DONE_TIMEOUT_S,
            )

    async def _update_textures(self, passport_name):
        """(Re)allocate the shared textures when the render window's size or their count changed."""
        assert isinstance(self._rca, VtkRemoteControlledArea), (
            "SharedTexture scheduler only works with VTK render windows!"
        )
        assert isinstance(self._conn, LineConnection), (
            "Connection to EMP is uninitialized!"
        )
        width, height = self._rca.render_window.GetSize()
        count = self._texture_count
        if len(self._passports) == count and all(
            (p.width, p.height) == (width, height) for p in self._passports
        ):
            return
        if not self._passports:
            # The first render will create the context and the framebuffers.
            self._rca.render_window.Render()
            self._rca.render_window.MakeCurrent()
        passport_class = texture_passport_class(passport_name)
        old, self._passports = (
            self._passports,
            [
                passport_class(self._rca.render_window, width, height)
                for _ in range(count)
            ],
        )
        for passport in old:
            passport.release()
        self._slot_frames = [None] * count
        self._next_slot = 0
        for slot, passport in enumerate(self._passports):
            assert isinstance(passport, TexturePassport)
            await self._conn.send({**passport.to_json(), "slot": slot, "slots": count})

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
                    frame_done = self._frames_in_flight.pop(msg["seq"], None)
                    if frame_done and not frame_done.done():
                        frame_done.set_result(None)
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
