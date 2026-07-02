import vtkmodules.vtkRenderingOpenGL2  # noqa
from trame.app import TrameApp
from trame.decorators import change
from trame.widgets import rca
from trame.widgets import vuetify3 as v3
from trame.ui.vuetify3 import SinglePageLayout

from vtkmodules.vtkFiltersSources import vtkConeSource

from vtkmodules.vtkInteractionStyle import vtkInteractorStyleSwitch  # noqa
from vtkmodules.vtkRenderingCore import (
    vtkActor,
    vtkPolyDataMapper,
    vtkRenderer,
    vtkRenderWindow,
    vtkRenderWindowInteractor,
)

DEFAULT_RESOLUTION = 6


class ConeApp(TrameApp):
    def __init__(self, server=None):
        super().__init__(server)

        self.server.cli.add_argument("--encoder", default="auto")
        args, _ = self.server.cli.parse_known_args()

        self.encoder = args.encoder
        self.render_window = self.setup_vtk()

        self._build_ui()

    def setup_vtk(self):
        renderer = vtkRenderer()
        render_window = vtkRenderWindow()

        render_window.AddRenderer(renderer)
        render_window.ShowWindowOff()

        render_window_interactor = vtkRenderWindowInteractor()
        render_window_interactor.SetRenderWindow(render_window)
        render_window_interactor.GetInteractorStyle().SetCurrentStyleToTrackballCamera()

        self.cone_source = vtkConeSource()
        mapper = vtkPolyDataMapper()
        mapper.SetInputConnection(self.cone_source.GetOutputPort())
        actor = vtkActor()
        actor.SetMapper(mapper)

        renderer.AddActor(actor)
        renderer.ResetCamera()
        render_window.Render()

        return render_window

    @change("resolution")
    def update_cone(self, resolution, **kwargs):
        self.cone_source.SetResolution(resolution)
        self.view_handler.update()

    def update_reset_resolution(self):
        self.state.resolution = DEFAULT_RESOLUTION

    def _build_ui(self):
        with SinglePageLayout(self.server, full_height=True) as layout:
            layout.title.set_text("Video Encoding")
            with layout.toolbar:
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
                view = rca.RemoteControlledArea(display="video-decoder")
                self.view_handler = view.create_view_handler(
                    self.render_window, encoder=self.encoder
                )


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    app = ConeApp()
    app.server.start()
