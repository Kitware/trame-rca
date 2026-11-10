"""The simplest trame-rca Electron app: one VTK surface mesh, shared with Electron as a texture.

Started by the Electron app in ./electron, see the README.
"""

from trame.app import TrameApp
from trame.ui.html import DivLayout
from trame.widgets import client, rca

# Before creating any VTK render window: VTK must render on the GPU Electron uses.
rca.init_vtk_for_shared_textures()

from vtkmodules.vtkFiltersSources import vtkPartitionedDataSetCollectionSource  # noqa: E402
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleTrackballCamera  # noqa: E402
from vtkmodules.vtkRenderingCore import (  # noqa: E402
    vtkActor,
    vtkColorTransferFunction,
    vtkCompositePolyDataMapper,
    vtkRenderer,
    vtkRenderWindow,
)
from vtkmodules.vtkRenderingUI import vtkGenericRenderWindowInteractor  # noqa: E402

# Required for vtk factory
import vtkmodules.vtkRenderingOpenGL2  # noqa: E402, F401


# Evenly spaced colors, from the low to the high end of the scalar range.
COLORS = [
    "#0E0E78", "#1C2388", "#263698", "#2F49A8", "#365CB8", "#3C6FC9", "#4482D5", "#4C94DE",
    "#53A6E8", "#5AB9F1", "#6EC6F2", "#84D2F0", "#97DDED", "#A9E9EB", "#C1EEDF", "#DAF0CD",
    "#E9ECB8", "#EFE1A0", "#F3D788", "#F3C977", "#F1BB6A", "#EFAC5C", "#EC9D4F", "#E58D46",
    "#DD7E3D", "#D66E34", "#CE5E2B", "#C45027", "#B84325", "#AD3523", "#A22621", "#96141E",
]  # fmt: skip
SCALAR_RANGE = (0.0, 3.1415927)  # The "Scalars" array of the shape source


def create_color_map():
    ctf = vtkColorTransferFunction()
    for i, color in enumerate(COLORS):
        rgb = [int(color[j : j + 2], 16) / 255 for j in (1, 3, 5)]
        ctf.AddRGBPoint(
            SCALAR_RANGE[0]
            + (SCALAR_RANGE[1] - SCALAR_RANGE[0]) * i / (len(COLORS) - 1),
            *rgb,
        )
    return ctf


def create_render_window():
    source = vtkPartitionedDataSetCollectionSource(number_of_shapes=1)
    mapper = vtkCompositePolyDataMapper()
    mapper.SetInputConnection(source.output_port)
    mapper.SetLookupTable(create_color_map())
    mapper.SetScalarRange(*SCALAR_RANGE)

    renderer = vtkRenderer()
    renderer.AddActor(vtkActor(mapper=mapper))
    # Vertical gradient: #E0EAFC at the top to #CFDEF3 at the bottom.
    renderer.SetBackground2(224 / 255, 234 / 255, 252 / 255)
    renderer.SetBackground(207 / 255, 222 / 255, 243 / 255)
    renderer.GradientBackgroundOn()
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
    return render_window


class StarterApp(TrameApp):
    def __init__(self, server=None):
        super().__init__(server)
        self.render_window = create_render_window()
        self._build_ui()

    def _build_ui(self):
        with DivLayout(self.server) as self.ui:
            client.Style("html, body { margin: 0; overflow: hidden; }")
            self.ui.root.style = "height: 100vh; position: relative;"
            view = rca.RemoteControlledArea(display="shared-texture")
            self.view_handler = view.create_electron_handler(self.render_window)


if __name__ == "__main__":
    StarterApp().server.start()
