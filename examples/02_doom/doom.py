# Required for rendering initialization, not necessary for
# local rendering, but doesn't hurt to include it
from asyncio import Queue, sleep, wrap_future, QueueEmpty
from enum import Enum
from PIL import Image
import numpy as np
from trame.app.testing import enable_testing
from trame.decorators import TrameApp, life_cycle
from trame.app import get_server, asynchronous
from trame_rca.utils import time_now_ms, Executor, ENCODING_POOL
from trame.ui.vuetify3 import SinglePageLayout
from trame.widgets import vuetify3 as v3
from trame.widgets import rca
from typing import Callable, Optional
from .doom_encoder import encode as encode_doom_screen
from vizdoom import DoomGame, ScreenResolution, Button, Mode


class DoomEncoder(Enum):
    AVIF = "avif"
    JPEG = "jpeg"
    TURBO_JPEG = "turbo-jpeg"
    PNG = "png"
    WEBP = "webp"

    def encode(
        self,
        image: Image,
        cols: int,
        rows: int,
        quality: int,
    ) -> tuple[bytes, dict, int]:
        now_ms = time_now_ms()
        return encode_doom_screen(image, self.value, cols, rows, quality, now_ms)


class DoomWindow:
    def __init__(self, config="basic.cfg", window_visible=False, **kwargs):
        self.event_queue = Queue()
        self._events = ["KeyDown"]
        self._keys_to_action = {
            "z": Button.MOVE_FORWARD,
            "s": Button.MOVE_BACKWARD,
            "q": Button.TURN_LEFT,
            "d": Button.TURN_RIGHT,
            " ": Button.ATTACK,
            "e": Button.USE,
            "a": Button.JUMP,
            "Control": Button.CROUCH,
            "1": Button.SELECT_WEAPON1,
            "2": Button.SELECT_WEAPON2,
            "3": Button.SELECT_WEAPON3,
            "ArrowLeft": Button.MOVE_LEFT,
            "ArrowRight": Button.MOVE_RIGHT,
            "r": Button.RELOAD,
        }
        self._game = self._init_game(config, window_visible)
        self._is_game_finished = False
        self._scheduler = None
        self._run_doom_task = asynchronous.create_task(self._run_doom())
        self._process_event_task = asynchronous.create_task(self._process_events())

    def _init_game(self, config, window_visible):
        game = DoomGame()
        game.load_config(config)
        game.set_episode_timeout(0)
        game.set_window_visible(window_visible)
        game.set_screen_resolution(ScreenResolution.RES_800X600)
        game.set_available_buttons(list(self._keys_to_action.values()))
        game.set_mode(Mode.PLAYER)
        game.init()

        return game

    async def _run_doom(self):
        print("ViZDoom started...")

        while not self._game.is_episode_finished():
            self._game.advance_action()
            # Default game progression
            if self._scheduler is not None:
                self._scheduler.schedule_render()
            await sleep(0.02)  # Run at ~20 FPS

        self._game.close()
        self._is_game_finished = True
        print("ViZDoom closed.")

    def _get_action(self, pressed_key):
        action = [0] * len(
            self._game.get_available_buttons()
        )  # Start with all buttons as 0
        for key, button in self._keys_to_action.items():
            if key == pressed_key:
                # Set the corresponding button index to 1
                action[self._game.get_available_buttons().index(button)] = 1
        return action

    async def _process_events(self):
        while not self._is_game_finished:
            try:
                event = self.event_queue.get_nowait()
                event_type = event["type"]
                if event_type in self._events:
                    pressed_key = event.get("key", "")
                    if pressed_key in self._keys_to_action.keys():
                        action = self._get_action(pressed_key)
                        self._game.set_action(action)
            except QueueEmpty:
                empty_action = self._get_action(None)
                self._game.set_action(empty_action)

            await sleep(0.1)

    def resize(self, target_width, target_height):
        # TODO fetch vanilla resize
        return

    def set_scheduler(self, scheduler):
        self._scheduler = scheduler

    def update(self):
        state = self._game.get_state()
        if state:
            image = Image.fromarray(np.transpose(state.screen_buffer, (1, 2, 0)))
            return (
                image,
                image.size[0],
                image.size[1],
            )
        return None


class RenderScheduler:
    """
    Render scheduler which renders to image and pushes the rendered encoded image to given input callback.
    JPEG image metadata are pushed along the encoded image.

    Renders synchronously to a PIL Image, encodes to JPEG in a subprocesses and pushes asynchronously.
    Limits the rendering speed given the target FPS.
    Encodes using interactive quality first and then using 100 quality after a few ticks pass.

    Call the close method to properly stop the scheduler before deleting the object.
    """

    def __init__(
        self,
        window: DoomWindow,
        *,
        push_callback: Optional[Callable[[bytes, dict], None]] = None,
        target_fps: Optional[float] = None,
        interactive_quality: Optional[int] = None,
        still_quality: Optional[int] = None,
        encoder: Optional[DoomEncoder] = None,
        encode_pool: Executor = None,
    ):
        if not isinstance(window, DoomWindow):
            raise RuntimeError(
                "Invalid input window. "
                "RenderScheduler is only compatible with DoomWindow."
            )

        self._window = window
        self._encoder = encoder
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

    def set_encoder(self, encoder: DoomEncoder):
        self._encoder = encoder

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

    def schedule_event(self, event):
        asynchronous.create_task(self.async_schedule_event(event))

    async def async_schedule_render(self):
        await self._request_render_queue.put(True)

    async def async_schedule_event(self, event):
        await self._window.event_queue.put(event)

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
            window_to_render = self._window.update()
            if window_to_render is not None:
                image, cols, rows = window_to_render
                await self._push_queue.put(
                    wrap_future(
                        self._encode_pool.submit(
                            self._encoder.encode,
                            image,
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


class DoomViewAdapter:
    """
    Adapter for Generic Remote Controlled Area.
    """

    def __init__(
        self,
        window: DoomWindow,
        name: str,
        scheduler: RenderScheduler,
        encoder: Optional[str] = None,
        **kwargs,
    ):
        self._window = window
        self.area_name = name
        self._scheduler = scheduler
        self._encoder = DoomEncoder(encoder or DoomEncoder.PNG)
        self._scheduler.set_push_callback(self.push)
        self._scheduler.set_encoder(self._encoder)
        self._window.set_scheduler(scheduler)
        self._streamer = None

    def push(self, content: bytes, meta: dict):
        if not self._streamer:
            return
        if content is None:
            return
        self._streamer.push_content(self.area_name, meta, content)

    def set_streamer(self, stream_manager):
        self._streamer = stream_manager

    def update_size(self, _, size):
        width = max(1, int(size.get("w", 300)))
        height = max(1, int(size.get("h", 300)))
        self._window.resize(width, height)
        self._scheduler.schedule_render()

    def on_interaction(self, _, event):
        self._scheduler.schedule_event(event)


@TrameApp()
class DoomApp:
    def __init__(self, server=None):
        self.server = get_server(server, client_type="vue3")

        # Run EEG Viz Remote
        window = DoomWindow()
        self.name = "doom"
        self.window_handler = self.create_doom_handler(
            window,
        )
        self._build_ui()

    def create_doom_handler(
        self,
        window: DoomWindow,
        encoder: str = "jpeg",
        target_fps: int = 30,
        interactive_quality: int = 60,
        still_quality: int = 90,
    ):
        scheduler = RenderScheduler(
            window,
            target_fps=target_fps,
            interactive_quality=interactive_quality,
            still_quality=still_quality,
        )
        window_handler = DoomViewAdapter(window, self.name, scheduler, encoder)

        return window_handler

    @property
    def state(self):
        return self.server.state

    @property
    def ctrl(self):
        return self.server.controller

    @life_cycle.server_ready
    def on_server_ready(self, **_):
        # can only be called when server is ready
        self.ctrl.rc_area_register(self.window_handler)

    def _build_ui(self):
        with SinglePageLayout(self.server, full_height=True) as layout:
            layout.title.set_text("DOOM")

            with layout.content:
                with v3.VContainer(
                    fluid=True,
                    classes="pa-0 fill-height position-relative",
                ):
                    rca.RemoteControlledArea(
                        name=self.name,
                        display="image",
                    )


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    app = DoomApp()
    enable_testing(app.server)
    app.server.start()
