# Required for rendering initialization, not necessary for
# local rendering, but doesn't hurt to include it
import vtkmodules.vtkRenderingOpenGL2  # noqa
from trame.app.testing import enable_testing
from trame_rca.utils import RcaViewAdapter, RcaRenderScheduler, RcaEncoder
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

server = get_server()
server.client_type = "vue2"
ctrl = server.controller


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
        renderWindow, target_fps=30, rca_encoder=RcaEncoder.JPEG
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


# -----------------------------------------------------------------------------
# Trame
# -----------------------------------------------------------------------------


with SinglePageLayout(server) as layout:
    layout.title.set_text("Hello trame")

    with layout.content:
        with vuetify.VContainer(
            fluid=True,
            classes="pa-0 fill-height",
        ):
            view = rca.RemoteControlledArea(
                name="view",
                display="image",
            )
        with vuetify.VCardText(style="height: 150px; background: white"):
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
