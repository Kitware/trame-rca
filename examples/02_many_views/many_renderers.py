import math

import vtk
from trame.app import TrameApp, TrameComponent
from trame.decorators import change
from trame.ui.vuetify3 import SinglePageLayout
from vtkmodules.vtkRenderingCore import vtkRenderer, vtkRenderWindow

from trame.widgets import html, rca
from trame.widgets import vuetify3 as v3


class ManyViewManager:
    def __init__(self):
        self._view_size = [300, 300]  # assume uniform
        self._render_window = vtkRenderWindow()
        self._render_window.OffScreenRenderingOn()
        # self._camera = vtkCamera()
        self._renderers = {}
        self._visibility = {}
        self._layout = {}

        renderWindowInteractor = vtk.vtkRenderWindowInteractor()
        renderWindowInteractor.SetRenderWindow(self._render_window)
        renderWindowInteractor.GetInteractorStyle().SetCurrentStyleToTrackballCamera()

    def create_renderer(self, name):
        if name not in self._renderers:
            renderer = vtkRenderer()  # active_camera=self._camera
            self._renderers[name] = renderer
            self._visibility[name] = True

        self.refresh_layout()

        return self._renderers[name]

    def delete_renderer(self, name):
        self._visibility[name] = False
        renderer = self._renderers.pop(name, None)
        if renderer:
            # do something with render window
            self._render_window.RemoveRenderer(renderer)

        self.refresh_layout()

    def update_visibility(self, name, visibility):
        self._visibility[name] = visibility
        self.refresh_layout()

    def refresh_layout(self):
        renderers_in_layout = {}
        for name, visible in self._visibility.items():
            renderer = self._renderers.get(name)
            if renderer is None:
                continue
            if visible:
                self._render_window.AddRenderer(renderer)
                renderers_in_layout[name] = renderer
            else:
                self._render_window.RemoveRenderer(renderer)

        size = len(renderers_in_layout)
        width_count = math.ceil(math.sqrt(size))
        height_count = math.ceil(size / width_count)
        full_size = [
            self._view_size[0] * width_count,
            self._view_size[1] * height_count,
        ]
        self._render_window.SetSize(*full_size)
        dx = 1.0 / width_count
        dy = 1.0 / height_count
        self._layout = {}
        for idx, (name, renderer) in enumerate(renderers_in_layout.items()):
            i = idx % width_count
            j = int(idx / width_count)
            bounds = (i * dx, j * dy, (i + 1) * dx, (j + 1) * dy)
            renderer.SetViewport(*bounds)
            self._layout[name] = bounds

    @property
    def layout(self):
        return self._layout


class Cone(TrameComponent):
    COUNT = 1

    def __init__(self, server):
        super().__init__(server)
        self.name = f"Cone {Cone.COUNT}"
        Cone.COUNT += 1

        self.cone = vtk.vtkConeSource()
        self.mapper = vtk.vtkPolyDataMapper()
        self.actor = vtk.vtkActor(mapper=self.mapper)
        self.cone >> self.mapper

    @property
    def resolution(self):
        return self.cone.resolution

    @resolution.setter
    def resolution(self, v):
        self.cone.resolution = v


class ManyViewTest(TrameApp):
    def __init__(self, server=None):
        super().__init__(server)
        self.cones = {}
        self.state.views = {}
        self.view_manager = ManyViewManager()
        self._build_ui()

    def add_view(self):
        cone = Cone(self.server)
        self.cones[cone.name] = cone
        renderer = self.view_manager.create_renderer(cone.name)
        renderer.AddActor(cone.actor)
        renderer.ResetCamera()
        self.state.names = list(self.cones.keys())
        self.state.views = self.view_manager.layout
        self.ctx.handler.update()

    def remove_view(self):
        name_to_remove = self.state.active_renderer
        self.view_manager.delete_renderer(name_to_remove)
        self.state.active_renderer = None
        self.cones.pop(name_to_remove, None)
        self.state.names = list(self.cones.keys())
        self.state.views = self.view_manager.layout
        self.ctx.handler.update()

    @change("resolution")
    def _on_resolution(self, resolution, active_renderer, **_):
        cone = self.cones.get(active_renderer)
        if cone:
            cone.resolution = resolution
            self.ctx.handler.update()

    @change("active_renderer")
    def _on_active_renderer(self, active_renderer, **_):
        cone = self.cones.get(active_renderer)
        if cone:
            self.state.resolution = cone.resolution

    def update_size(self, name, size):
        print("Size update for", name, size)
        self.view_manager._view_size = [
            round(size["w"] * size["p"]),
            round(size["h"] * size["p"]),
        ]
        self.view_manager.refresh_layout()
        self.ctx.handler.update()

    def _build_ui(self):
        with SinglePageLayout(self.server) as self.ui:
            with self.ui.toolbar.clear() as toolbar:
                toolbar.classes = "px-4"
                v3.VSelect(
                    v_model=("active_renderer", None),
                    items=("names", []),
                    density="compact",
                    hide_details=True,
                    style="max-width: 300px;",
                )
                v3.VBtn(icon="mdi-plus", click=self.add_view)
                v3.VBtn(icon="mdi-minus", click=self.remove_view)
                v3.VSlider(
                    v_model=("resolution", 6),
                    min=3,
                    max=24,
                    step=1,
                    hide_details=True,
                    density="compact",
                )
                v3.VSwitch(
                    v_model=("enable_interaction", True),
                    density="compact",
                    hide_details=True,
                    classes="mx-2",
                )
            with self.ui.content:
                # with rca.RemoteControlledArea(display="image") as view:
                #     self.ctx.handler = view.create_view_handler(
                #         self.view_manager._render_window,
                #         encoder="turbo-jpeg",
                #     )

                # Expected
                with rca.ImageStream(
                    self.view_manager._render_window,
                    encoder="turbo-jpeg",
                    ctx_name="handler",
                ):
                    with v3.VRow(classes="ma-0 pa-2"):
                        html.Img(src=["image?.src"], height="200px")
                    with v3.VRow(classes="mx-4"):
                        with v3.VCol(cols=3, v_for="bounds, name in views", key="name"):
                            with v3.VCard():
                                v3.VCardTitle("{{ name }}")
                                with html.Div(
                                    classes="position-relative w-100",
                                    style="aspect-ratio:16/9;",
                                ):
                                    rca.ImageRegion(
                                        enable_interaction=(
                                            "enable_interaction",
                                            True,
                                        ),
                                        bounds=("bounds",),
                                        size=(self.update_size, "[name, $event]"),
                                    )


def main():
    app = ManyViewTest()
    app.server.start()


if __name__ == "__main__":
    main()
