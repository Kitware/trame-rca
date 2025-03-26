# Required for rendering initialization, not necessary for
# local rendering, but doesn't hurt to include it
import asyncio
import vtkmodules.vtkRenderingOpenGL2  # noqa
from trame.app.testing import enable_testing
from trame_rca.utils import RcaViewAdapter, RcaRenderScheduler
from trame.app import get_server
from trame.ui.vuetify import SinglePageLayout
from trame.widgets import rca, vuetify
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

server = get_server(client_type="vue2")
state, ctrl = server.state, server.controller

state.img_size = (0, 0)

server.cli.add_argument("--encoder", default="jpeg")
args, _ = server.cli.parse_known_args()

STATS_STYLES = """
    position: absolute;
    top: 1rem;
    left: 1rem;
    height: 150px;
    width: 300px;
    background: white;
    z-index: 100;
"""

DEFAULT_RESOLUTION = 6


@ctrl.add("on_server_ready")
def init_rca(**kwargs):
    renderer = vtkRenderer()
    renderWindow = vtkRenderWindow()
    renderWindow.AddRenderer(renderer)

    renderWindowInteractor = vtkRenderWindowInteractor()
    renderWindowInteractor.SetRenderWindow(renderWindow)
    renderWindowInteractor.GetInteractorStyle().SetCurrentStyleToTrackballCamera()

    # RemoteControllerArea
    scheduler = RcaRenderScheduler(
        renderWindow, target_fps=30, rca_encoder=args.encoder
    )
    view_handler = RcaViewAdapter(renderWindow, scheduler, "view")
    server.controller.rc_area_register(view_handler)

    cone_source = vtkConeSource()
    mapper = vtkPolyDataMapper()
    mapper.SetInputConnection(cone_source.GetOutputPort())
    actor = vtkActor()
    actor.SetMapper(mapper)

    renderer.AddActor(actor)
    renderer.ResetCamera()

    @server.state.change("resolution")
    def update_cone(resolution=DEFAULT_RESOLUTION, **kwargs):
        cone_source.SetResolution(resolution)
        view_handler.schedule_render()

    @server.state.change("scale")
    def update_scale(scale, **kwargs):
        view_handler.scale = scale
        state.img_size = view_handler.image_size

    @server.state.change("quality")
    def update_quality(quality, **kwargs):
        view_handler.update_quality(*quality)

    @ctrl.add_task("on_client_connected")
    async def on_client_connected(**_):
        await asyncio.sleep(0.5)
        print("connected", view_handler.image_size)
        with state:
            state.img_size = view_handler.image_size


def update_reset_resolution():
    server.state.resolution = DEFAULT_RESOLUTION


# -----------------------------------------------------------------------------
# Trame
# -----------------------------------------------------------------------------


with SinglePageLayout(server) as layout:
    layout.title.set_text(
        "RCA rendering {{ img_size.join('x') }}"
        " - Scale({{scale}})"
        " - Quality(interactive={{quality[0]}}, still={{quality[1]}})"
    )

    with layout.toolbar:
        vuetify.VSpacer()
        vuetify.VRangeSlider(
            label="Quality",
            v_model=("quality", [50, 90]),
            min=10,
            max=100,
            step=5,
            hide_details=True,
            dense=True,
            style="max-width: 300px",
        )
        vuetify.VSlider(
            label="Scale",
            v_model=("scale", 1),
            min=0.5,
            max=3,
            step=0.1,
            hide_details=True,
            dense=True,
            style="max-width: 300px",
        )
        vuetify.VSlider(
            v_model=("resolution", DEFAULT_RESOLUTION),
            min=3,
            max=60,
            step=1,
            hide_details=True,
            dense=True,
            style="max-width: 300px",
        )

        with vuetify.VBtn(icon=True, click=update_reset_resolution):
            vuetify.VIcon("mdi-undo-variant")

    with layout.content:
        with vuetify.VContainer(
            fluid=True,
            classes="pa-0 fill-height",
        ):
            view = rca.RemoteControlledArea(
                name="view",
                display="image",
            )
            with vuetify.VCard(classes="pa-4 ma-0", style=STATS_STYLES):
                rca.StatisticsDisplay(
                    name="view",
                    fps_delta=1.5,
                    stat_window_size=10,
                    history_window_size=30,
                    reset_ms_threshold=100,
                )

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    enable_testing(server)
    server.start()
