from asyncio import Queue, sleep, QueueEmpty
import numpy as np
from trame.app.testing import enable_testing
from trame.decorators import TrameApp
from trame.app import get_server, asynchronous
from trame_rca.utils import AbstractWindow, RcaViewAdapter
from trame.ui.vuetify3 import SinglePageLayout
from trame.widgets import vuetify3 as v3
from trame_rca.widgets import rca
from vizdoom import DoomGame, ScreenResolution, Button, Mode


@TrameApp()
class DoomWindow(AbstractWindow):
    def __init__(self, server, **kwargs):
        self.server = server
        self._event_queue = Queue()
        self._key_to_action = {
            "z": Button.MOVE_FORWARD,
            "s": Button.MOVE_BACKWARD,
            "q": Button.MOVE_LEFT,
            "d": Button.MOVE_RIGHT,
            " ": Button.ATTACK,
            "e": Button.USE,
            "a": Button.JUMP,
            "Control": Button.CROUCH,
            "1": Button.SELECT_WEAPON1,
            "2": Button.SELECT_WEAPON2,
            "3": Button.SELECT_WEAPON3,
            "ArrowLeft": Button.TURN_LEFT,
            "ArrowRight": Button.TURN_RIGHT,
            "r": Button.RELOAD,
        }
        self._handler = None
        self._game = None
        self._run_task = None
        self._event_task = None

    @property
    def state(self):
        return self.server.state

    @property
    def ctrl(self):
        return self.server.controller

    def set_handler(self, handler: RcaViewAdapter):
        self._handler = handler

    def init_game(self, config):
        self._game = DoomGame()
        if config is not None:
            self._game.load_config(config)
        self._game.set_episode_timeout(0)
        self._game.set_window_visible(False)
        self._game.set_screen_resolution(ScreenResolution.RES_800X600)
        self._game.set_available_buttons(list(self._key_to_action.values()))
        self._game.set_mode(Mode.PLAYER)
        self._game.init()

        self._run_task = asynchronous.create_task(self._run_game())
        self._event_task = asynchronous.create_task(self._push_events())

        self.state.running_config = config

    async def stop_game(self):
        self._is_closing = True
        for task in [self._run_task, self._event_task]:
            if task is not None:
                await task
        self._empty_event_queue()
        self._is_closing = False

    def _empty_event_queue(self):
        while not self._event_queue.empty():
            self._event_queue.get_nowait()
            self._event_queue.task_done()

    def _get_action(self, pressed_key):
        action = [0] * len(
            self._game.get_available_buttons()
        )  # Start with all buttons as 0
        for key, button in self._key_to_action.items():
            if key == pressed_key:
                # Set the corresponding button index to 1
                action[self._game.get_available_buttons().index(button)] = 1
        return action

    @property
    def img_cols_rows(self):
        state = self._game.get_state()
        if state is not None:
            image = np.transpose(state.screen_buffer, (1, 2, 0))
            return (
                image,
                image.shape[0],
                image.shape[1],
            )
        return (np.ones((1, 1, 3)) * 255, 1, 1)

    def process_resize_event(self, width, height):
        # TODO
        return

    def process_interaction_event(self, event):
        asynchronous.create_task(self._event_queue.put(event))

    async def _push_events(self):
        while self._game.is_running():
            try:
                event = self._event_queue.get_nowait()
                if event["type"] == "KeyDown":
                    pressed_key = event.get("key", "")
                    action = self._get_action(pressed_key)
                    self._game.set_action(action)
            except QueueEmpty:
                empty_action = self._get_action(None)
                self._game.set_action(empty_action)

            await sleep(0.05)

    async def _run_game(self):
        print("Doom game start...")
        self._is_closing = False
        self.state.is_game_running = True
        self.state.flush()
        while not self._is_closing:
            if not self._game.is_episode_finished():
                self._game.advance_action()  # Default game progression
                if self._handler is not None:
                    self._handler.schedule_render()
                await sleep(0.02)  # Run at ~20 FPS
            else:
                self._is_closing = True

        self._game.close()
        self.state.is_game_running = False
        self.state.flush()
        print("Doom game finished.")


@TrameApp()
class DoomApp:
    def __init__(self, server=None, start_game=True):
        self.server = get_server(server, client_type="vue3")
        self._window = DoomWindow(server=self.server)
        self.state.scenarii = [
            {
                "title": "Demo",
                "subtitle": "Very simple environment. One enemy, one room",
                "value": "basic.cfg",
            },
            {
                "title": "Classic",
                "subtitle": "Run DOOM game",
                "value": None,
            },
            {
                "title": "Deadly corridor",
                "subtitle": "Long hallway with enemies and obstacles",
                "value": "deadly_corridor.cfg",
            },
            {
                "title": "Deathmatch",
                "subtitle": "Full deathmatch-like environment",
                "value": "deathmatch.cfg",
            },
            {
                "title": "Take cover",
                "subtitle": "Take cover behind objects while enemies shoot",
                "value": "take_cover.cfg",
            },
            {
                "title": "Maze",
                "subtitle": "Find your way home through a maze",
                "value": "my_way_home.cfg",
            },
        ]
        self.state.config = "basic.cfg"
        if start_game:
            self._window.init_game(config=self.state.config)
        self._build_ui()

    @property
    def state(self):
        return self.server.state

    @property
    def ctrl(self):
        return self.server.controller

    async def start(self):
        if self.state.is_game_running:
            await self._window.stop_game()
        self._window.init_game(config=self.state.config)

    async def stop(self):
        await self._window.stop_game()

    def _build_ui(self):
        with SinglePageLayout(self.server, full_height=True) as layout:
            layout.title.set_text("DOOM")
            layout.toolbar.height = 80
            with layout.toolbar, v3.VRow(align="center", style="margin: 0px"):
                v3.VSpacer()
                v3.VSelect(
                    v_model=("config",),
                    messages=(
                        "!is_game_running || running_config===config"
                        "? '' : 'Restart game to apply changes'",
                    ),
                    items=("scenarii",),
                    item_props=True,
                    style="max-width: 500px; margin: 20px",
                )
                v3.VBtn(
                    icon="mdi-play-circle-outline", click=self.start, size="x-large"
                )
                v3.VBtn(
                    icon="mdi-stop-circle-outline",
                    click=self.stop,
                    size="x-large",
                    disabled=("!is_game_running",),
                )

            with layout.content:
                with v3.VContainer(
                    fluid=True,
                    classes="pa-0 fill-height position-relative",
                ):
                    view = rca.RemoteControlledArea(
                        v_if=("is_game_running",),
                        name="doom",
                        display="image",
                        image_style=(
                            {
                                "max-width": "100%",
                                "max-height": "100%",
                                "object-fit": "contain",
                            },
                        ),
                    )
                    view_handler = view.create_view_handler(self._window)
                    self._window.set_handler(view_handler)


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    app = DoomApp()
    enable_testing(app.server)
    app.server.start()
