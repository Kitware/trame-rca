"""Four shared-texture views in a 2x2 grid, each with its own VTK render window.

Started by the Electron app in ./electron, see the README.
"""

# Before creating any VTK render window: VTK must render on the GPU Electron uses.
import trame_rca.electron.vtk  # noqa: F401

from trame.app import TrameApp
from trame.ui.html import DivLayout
from trame.widgets import client, html, rca

from vtkmodules.vtkCommonComputationalGeometry import vtkParametricKlein  # noqa: E402
from vtkmodules.vtkFiltersSources import vtkParametricFunctionSource  # noqa: E402
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleTrackballCamera  # noqa: E402
from vtkmodules.vtkRenderingCore import (  # noqa: E402
    vtkActor,
    vtkPolyDataMapper,
    vtkRenderer,
    vtkRenderWindow,
)
from vtkmodules.vtkRenderingUI import vtkGenericRenderWindowInteractor  # noqa: E402

# Required for vtk factory
import vtkmodules.vtkRenderingOpenGL2  # noqa: E402, F401

# (actor color, background) of each view
STYLES = [
    ((1.0, 0.5, 0.3), (0.10, 0.10, 0.15)),
    ((0.3, 0.8, 0.4), (0.15, 0.10, 0.10)),
    ((0.4, 0.6, 1.0), (0.10, 0.15, 0.10)),
    ((0.9, 0.8, 0.3), (0.12, 0.10, 0.18)),
]

DEFAULT_RESOLUTION = 50  # vtkParametricFunctionSource's default


def create_render_window(color, background):
    source = vtkParametricFunctionSource(parametric_function=vtkParametricKlein())
    mapper = vtkPolyDataMapper()
    mapper.SetInputConnection(source.output_port)
    actor = vtkActor(mapper=mapper)
    actor.property.color = color
    actor.property.edge_visibility = True
    actor.property.edge_color = (1, 1, 1)
    actor.property.edge_opacity = 0.5
    renderer = vtkRenderer(background=background)
    renderer.AddActor(actor)
    # The texture's alpha reaches Electron, so keep the background opaque.
    renderer.SetBackgroundAlpha(1.0)
    renderer.ResetCamera()

    render_window = vtkRenderWindow()
    render_window.AddRenderer(renderer)
    # trame-rca replays the canvas's input on the interactor.
    vtkGenericRenderWindowInteractor(
        render_window=render_window,
        interactor_style=vtkInteractorStyleTrackballCamera(),
    )
    return render_window, source


class MultiViewApp(TrameApp):
    def __init__(self, server=None):
        super().__init__(server)
        self.render_windows = []
        self.sources = []
        self.view_handlers = []
        for style in STYLES:
            render_window, source = create_render_window(*style)
            self.render_windows.append(render_window)
            self.sources.append(source)
        for i in range(len(STYLES)):
            self.state[f"resolution_{i}"] = DEFAULT_RESOLUTION
        self.state.change(*[f"resolution_{i}" for i in range(len(STYLES))])(
            self._on_resolution_change
        )
        self._build_ui()

    def _on_resolution_change(self, **_):
        for i, (source, view_handler) in enumerate(
            zip(self.sources, self.view_handlers)
        ):
            resolution = int(self.state[f"resolution_{i}"])
            if source.u_resolution != resolution:
                source.u_resolution = resolution
                source.v_resolution = resolution
                view_handler.update()

    def _build_ui(self):
        with DivLayout(self.server) as self.ui:
            client.Style("html, body { margin: 0; overflow: hidden; }")
            self.ui.root.style = "height: 100vh;"
            with html.Div(
                style="display: grid; grid-template-columns: 1fr 1fr; "
                "grid-template-rows: 1fr 1fr; gap: 2px; height: 100%;"
            ):
                for i, render_window in enumerate(self.render_windows):
                    with html.Div(
                        style="position: relative; min-width: 0; min-height: 0;"
                    ):
                        view = rca.RemoteControlledArea(display="shared-texture")
                        self.view_handlers.append(
                            view.create_electron_handler(render_window)
                        )
                        # Floating slider: this view's u/v resolution
                        html.Label(
                            "Resolution",
                            style="position: absolute; left: 12px; right: 12px; "
                            "bottom: 12px; z-index: 1; color: white;",
                        )
                        html.Input(
                            type="range",
                            min=5,
                            max=150,
                            step=1,
                            v_model_number=(f"resolution_{i}",),
                            style="position: absolute; left: 90px; right: 12px; "
                            "bottom: 12px; z-index: 1; opacity: 0.8;",
                        )


if __name__ == "__main__":
    MultiViewApp().server.start()
