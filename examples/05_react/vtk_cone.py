#!/usr/bin/env -S uv run --script
# /// script
#
# requires-python = ">=3.10"
#
# dependencies = [
#   "trame>=4",
#   "trame-rca>=2.10",
#   "vtk-streaming>=0.4.0",
# ]
#
# [[tool.uv.index]]
# url = "https://wheels.vtk.org"
#
# ///

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
from trame.ui.html import DivLayout
from trame.widgets import html, react, rca, client

DEFAULT_RESOLUTION = 6


class ConeApp(TrameApp):
    def __init__(self, server=None):
        super().__init__(server, client_type="react")

        self.server.cli.add_argument("--encoder", default="turbo-jpeg")  # jpeg
        args, _ = self.server.cli.parse_known_args()
        self.state.encoder = args.encoder
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

    def build_ui(self):
        with DivLayout(self.server, full_height=True) as self.ui:
            self.ui.root.style = {"height": "100vh"}
            client.Style("body { margin: 0; }")

            # 3D view
            view = rca.RemoteControlledArea(display="image")
            self.view_handler = view.create_view_handler(
                self.render_window,
                encoder=self.state.encoder,
            )

            # Toolbar
            with html.Div(
                style={
                    "position": "absolute",
                    "top": "1rem",
                    "left": "1rem",
                    "right": "1rem",
                    "zIndex": 10,
                    "padding": "1rem",
                    "borderRadius": "1rem",
                },
            ):
                html.Input(
                    type="range",
                    value=react.Bind("resolution", resolution=6),
                    on_change=react.Callback(
                        "resolution = Number($event.target.value)"
                    ),
                    min=3,
                    max=60,
                    step=1,
                )
                html.Button(
                    "Reset Resolution",
                    on_click=react.Callback(self.update_reset_resolution),
                )

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
