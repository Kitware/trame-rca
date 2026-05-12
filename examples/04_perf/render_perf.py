#!/usr/bin/env -S uv run --script
#
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "trame>=3.12.1",
#     "trame-rca[turbo]",
#     "trame-vuetify",
#     "vtk>=9.6",
# ]
# ///
import asyncio

import vtkmodules.vtkRenderingOpenGL2  # noqa
from trame_common.utils import profiler
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
profiler.enable()

DEFAULT_RESOLUTION = 6
RESOLUTIONS = [
    (300, 300),
    (7680, 4320),
    (3840, 2160),
    (2560, 1440),
    (1920, 1080),
    (1280, 720),
]


class ConeApp(TrameApp):
    def __init__(self, server=None):
        super().__init__(server)

        self.server.cli.add_argument("--encoder", default="turbo-jpeg")
        self.server.cli.add_argument("--target-fps", default=30, type=int)
        self.server.cli.add_argument("--auto", action="store_true")
        self.server.cli.add_argument("--auto-client", action="store_true")
        args, _ = self.server.cli.parse_known_args()
        self.target_fps = args.target_fps
        self.state.encoder = args.encoder
        self.render_window, self.cone_source = self.setup_vtk()
        self.build_ui()

        if args.auto:
            self.ctrl.on_server_ready.add_task(self.auto)

        if args.auto_client:
            self.ctrl.on_client_connected.add_task(self.auto)

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

    async def auto(self, **_):
        self.view_handler.target_fps = 120
        await asyncio.sleep(0.1)
        for w, h in RESOLUTIONS:
            self.view_handler.update_size("", {"w": w, "h": h, "p": 1})
            self.cone_source.SetResolution(3)
            self.view_handler.update()
            await asyncio.sleep(0.25)
            with profiler.timer(f"render-round-{w}x{h}"):
                for i in range(60):
                    self.cone_source.SetResolution(i + 3)
                    self.view_handler.update()
                    await asyncio.sleep(0.01)

        await asyncio.sleep(1)
        await self.server.stop()

    def build_ui(self):
        with SinglePageLayout(self.server, full_height=True) as layout:
            with layout.toolbar.clear():
                v3.VSpacer()
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
                    )
                    self.view_handler = view.create_view_handler(
                        self.render_window,
                        encoder=self.state.encoder,
                    )
                    self.view_handler.target_fps = self.target_fps

    @change("resolution")
    def update_cone(self, resolution, **kwargs):
        self.cone_source.SetResolution(resolution)
        self.view_handler.update()

    def update_reset_resolution(self):
        self.state.resolution = DEFAULT_RESOLUTION


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    app = ConeApp()
    app.server.start()
