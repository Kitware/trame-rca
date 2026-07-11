import vtkmodules.vtkRenderingOpenGL2  # noqa
from trame.app import TrameApp
from trame.decorators import change
from trame.widgets import rca
from trame.widgets import html, vuetify3 as v3
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
        self.render_window = self.setup_vtk()

        self._build_ui()
        self.state.video_codec = "unavailable"
        self._update_video_codec_label()

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

    def _update_video_codec_label(self):
        # Reflect the encoder the video scheduler actually selected,
        try:
            from trame_rca.encoders.video_encoder import describe_encoder
        except ImportError:
            self.state.video_codec = "unavailable"
            return
        scheduler = getattr(self.view_handler, "_scheduler", None)
        rca_encoder = getattr(scheduler, "_rca_encoder", None)
        self.state.video_codec = describe_encoder(getattr(rca_encoder, "encoder", None))

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
            with layout.footer.clear() as footer:
                footer.classes = "text-caption"
                v3.VSpacer()
                html.Span("Codec: {{video_codec}}")
                v3.VSpacer()

            with layout.content:
                view = rca.RemoteControlledArea(display="video-decoder")
                self.view_handler = view.create_view_handler(self.render_window)


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    app = ConeApp()
    app.server.start()
