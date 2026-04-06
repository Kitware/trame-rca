#!/usr/bin/env -S uv run --script
#
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "trame>=3.10",
#     "trame-rca[turbo]",
#     "trame-vuetify",
#     "vtk>=9.6",
# ]
# ///
import asyncio
import time

import vtkmodules.vtkRenderingOpenGL2  # noqa
from vtkmodules.vtkFiltersSources import vtkConeSource

# Required for interactor initialization
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleSwitch  # noqa
from vtkmodules.vtkRenderingCore import (
    vtkActor,
    vtkPolyDataMapper,
    vtkRenderer,
    vtkRenderWindow,
    vtkRenderWindowInteractor,
)

from trame.app import TrameApp
from trame.decorators import change
from trame.ui.vuetify3 import SinglePageLayout
from trame.widgets import vuetify3 as v3

# use this import path to allow -e install for dev
from trame_rca.widgets import rca

v3.enable_lab()

DEFAULT_RESOLUTION = 6
STATS_STYLES = """
    position: absolute;
    top: 1rem;
    left: 1rem;
    height: 150px;
    width: 300px;
    background: white;
    z-index: 100;
"""


def time_now_ms() -> int:
    return int(time.time_ns() / 1000000)


class ConeApp(TrameApp):
    def __init__(self, server=None):
        super().__init__(server)

        self.server.cli.add_argument("--encoder", default="turbo-jpeg")  # jpeg
        args, _ = self.server.cli.parse_known_args()
        self.state.encoder = args.encoder
        self.state.stats = None
        self.state.stats_display = ""
        self.max_dt = 0

        self.render_window, self.cone_source = self.setup_vtk()
        self.build_ui()

    def setup_vtk(self):
        renderer = vtkRenderer()
        renderWindow = vtkRenderWindow()
        renderWindow.AddRenderer(renderer)

        renderWindowInteractor = vtkRenderWindowInteractor()
        renderWindowInteractor.SetRenderWindow(renderWindow)
        renderWindowInteractor.GetInteractorStyle().SetCurrentStyleToTrackballCamera()

        cone_source = vtkConeSource()
        mapper = vtkPolyDataMapper()
        mapper.SetInputConnection(cone_source.GetOutputPort())
        actor = vtkActor()
        actor.SetMapper(mapper)

        renderer.AddActor(actor)
        renderer.ResetCamera()

        return renderWindow, cone_source

    async def _animate(self):
        resolution = 3
        delta = 1
        while self.state.playing:
            resolution += delta
            if resolution > 100 or resolution < 4:
                delta *= -1
            self.cone_source.SetResolution(resolution)
            self.view_handler.update()
            await asyncio.sleep(1 / int(self.state.target_fps))

    @change("stats")
    def on_stats(self, stats, **_):
        if stats is None:
            self.state.stats_display = ""
            return

        now = time_now_ms()
        ds = now - stats.get("st")
        self.max_dt = max(self.max_dt, ds)
        fps = stats.get("fps")
        self.state.stats_display = (
            f"round-trip: {int(ds)} [{self.max_dt}] ms - fps: {fps}"
        )

    @change("playing")
    def on_playing(self, playing, **_):
        if playing:
            asyncio.create_task(self._animate())

    @change("target_fps")
    def on_target_fps(self, target_fps, **_):
        self.view_handler.target_fps = target_fps
        self.max_dt = 0

    def build_ui(self):
        with SinglePageLayout(self.server, full_height=True) as layout:
            with layout.footer.clear() as footer:
                footer.classes = "text-caption"
                v3.VSpacer()
                footer.add_child("Quality ({{quality[0]}}/{{quality[1]}})")
                v3.VSpacer()
                footer.add_child("Encoder ({{encoder}})")
                v3.VSpacer()
                footer.add_child("{{ stats_display }}")

            with layout.toolbar.clear():
                v3.VBtn(
                    icon="mdi-stop",
                    v_if=("playing", False),
                    click="playing = !playing",
                )
                v3.VBtn(icon="mdi-play", v_else=True, click="playing = !playing")
                v3.VNumberInput(
                    label="target FPS",
                    v_model=("target_fps", 30),
                    min=[1],
                    max=[200],
                    step=[1],
                    hide_details=True,
                    density="compact",
                    control_variant="hidden",
                    variant="outlined",
                    style="max-width: 100px",
                )
                v3.VSpacer()

                v3.VRangeSlider(
                    label="Quality",
                    v_model=("quality", [50, 90]),
                    min=10,
                    max=100,
                    step=5,
                    hide_details=True,
                    density="compact",
                    style="max-width: 300px",
                )
                v3.VSlider(
                    v_model=("resolution", DEFAULT_RESOLUTION),
                    min=3,
                    max=60,
                    step=1,
                    hide_details=True,
                    density="compact",
                    style="max-width: 300px",
                )

                v3.VBtn(icon="mdi-undo-variant", click=self.update_reset_resolution)

            with layout.content:
                with v3.VContainer(
                    fluid=True,
                    classes="pa-0 fill-height position-relative",
                ):
                    view = rca.RemoteControlledArea(
                        display="image",
                        monitor="10",
                        stats="stats = $event",
                        event_throttle_ms=("500/target_fps",),
                    )
                    self.view_handler = view.create_view_handler(
                        self.render_window,
                        encoder=self.state.encoder,
                    )
                    with v3.VCard(classes="pa-4 ma-0", style=STATS_STYLES):
                        rca.StatisticsDisplay(
                            name=view.name,
                            fps_delta=1.5,
                            stat_window_size=10,
                            history_window_size=30,
                            reset_ms_threshold=100,
                        )

    @change("resolution")
    def update_cone(self, resolution, **kwargs):
        self.cone_source.SetResolution(resolution)
        self.view_handler.update()

    @change("quality")
    def update_quality(self, quality, **_):
        self.view_handler.update_quality(*quality)

    def update_reset_resolution(self):
        self.state.resolution = DEFAULT_RESOLUTION


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    app = ConeApp()
    app.server.start()
