# Required for rendering initialization, not necessary for
# local rendering, but doesn't hurt to include it
import asyncio

from trame.app import get_server, asynchronous
from trame.app.testing import enable_testing
from trame.decorators import TrameApp, change, life_cycle
from trame.ui.vuetify3 import SinglePageLayout
from trame.widgets import vuetify3 as v3

# use this import path to allow -e install for dev
from trame_rca.widgets import rca

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


@TrameApp()
class ConeApp:
    def __init__(self, server=None):
        self.server = get_server(server, client_type="vue3")

        self.server.cli.add_argument("--encoder", default="jpeg")
        args, _ = self.server.cli.parse_known_args()
        self.state.encoder = args.encoder

        self.view_handler = None
        self.render_window, self.cone_source = self.setup_vtk()
        self.build_ui()

    @property
    def state(self):
        return self.server.state

    @property
    def ctrl(self):
        return self.server.controller

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
        actor.GetProperty().SetColor(1, 0.8, 0.8)

        renderer.AddActor(actor)
        renderer.ResetCamera()

        return renderWindow, cone_source

    def build_ui(self):
        self.state.img_size = (0, 0)
        with SinglePageLayout(self.server, full_height=True) as layout:
            layout.title.set_text("RCA rendering")

            with layout.footer.clear() as footer:
                footer.classes = "text-caption"
                footer.add_child("Image Size ({{ img_size.join('x') }})")
                v3.VSpacer()
                footer.add_child("Scale ({{ scale }})")
                v3.VSpacer()
                footer.add_child("Quality ({{quality[0]}}/{{quality[1]}})")
                v3.VSpacer()
                footer.add_child("Encoder ({{encoder}})")

            with layout.toolbar:
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
                    label="Scale",
                    v_model=("scale", 1),
                    min=0.5,
                    max=3,
                    step=0.1,
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
                        name="view",
                        display="image",
                    )
                    self.view_handler = view.create_vtk_handler(
                        self.render_window,
                        encoder=self.state.encoder,
                    )
                    with v3.VCard(classes="pa-4 ma-0", style=STATS_STYLES):
                        rca.StatisticsDisplay(
                            name="view",
                            fps_delta=1.5,
                            stat_window_size=10,
                            history_window_size=30,
                            reset_ms_threshold=100,
                        )

    @change("resolution")
    def update_cone(self, resolution, **kwargs):
        self.cone_source.SetResolution(resolution)
        self.view_handler.update()

    @change("scale")
    def update_scale(self, scale, **_):
        self.view_handler.scale = scale
        self.state.img_size = self.view_handler.image_size

    @change("quality")
    def update_quality(self, quality, **_):
        self.view_handler.update_quality(*quality)

    @life_cycle.client_connected
    def on_client_connected(self, **_):
        asynchronous.create_task(self.update_resolution_info())

    async def update_resolution_info(self):
        await asyncio.sleep(0.5)
        with self.state as state:
            state.img_size = self.view_handler.image_size

    def update_reset_resolution(self):
        self.state.resolution = DEFAULT_RESOLUTION


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    app = ConeApp()
    enable_testing(app.server)
    app.server.start()
