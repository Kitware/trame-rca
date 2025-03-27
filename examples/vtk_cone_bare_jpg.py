# Required for rendering initialization, not necessary for
# local rendering, but doesn't hurt to include it
import time
import json
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
from vtkmodules.vtkWebCore import vtkRemoteInteractionAdapter
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleSwitch  # noqa
from vtkmodules.vtkRenderingCore import (
    vtkActor,
    vtkPolyDataMapper,
    vtkRenderer,
    vtkRenderWindow,
    vtkRenderWindowInteractor,
    vtkWindowToImageFilter,
)
from vtkmodules.vtkIOImage import vtkJPEGWriter


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


class VtkToImage:
    """
    This class just aim to illustrate how it can be done,
    but its implementation is not performant at all.
    Proper implementation should use a pool of threads for doing the encoding.
    """

    def __init__(self, render_window):
        self.render_window = render_window
        self.window_to_image = vtkWindowToImageFilter()
        self.window_to_image.SetInput(render_window)
        self.window_to_image.SetScale(1)
        self.window_to_image.ReadFrontBufferOff()
        self.window_to_image.ShouldRerenderOff()
        self.window_to_image.FixBoundaryOn()
        self.encoder = vtkJPEGWriter()
        self.encoder.SetWriteToMemory(1)
        self.encoder.SetInputConnection(self.window_to_image.GetOutputPort())

    @property
    def rgb_interact(self):
        self.render_window.Render()
        self.window_to_image.Modified()
        self.encoder.Modified()
        self.encoder.SetQuality(60)
        self.encoder.Write()

        return self.encoder.GetResult()

    @property
    def rgb_still(self):
        self.render_window.Render()
        self.window_to_image.Modified()
        self.encoder.Modified()
        self.encoder.SetQuality(90)
        self.encoder.Write()

        return self.encoder.GetResult()


class ViewAdapter:
    def __init__(self, window, name, target_fps=30):
        self._view = window
        self.area_name = name
        self.streamer = None
        self.last_meta = None
        self.animating = False
        self.target_fps = target_fps

        self._iren = window.GetInteractor()
        self._iren.EnableRenderOff()
        self._view.ShowWindowOff()
        self._vtk_helper = VtkToImage(window)

    def _get_metadata(self):
        return dict(
            type="image/jpeg",  # supported mime/type
            codec="",  # video codec, not relevant here
            w=self._view.GetSize()[0],
            h=self._view.GetSize()[1],
            st=int(time.time_ns() / 1000000),
            key=("key"),  # jpegs are always keyframes
        )

    async def _animate(self):
        while self.animating:
            self.push(memoryview(self._vtk_helper.rgb_interact), self._get_metadata())
            await asyncio.sleep(1.0 / self.target_fps)

        content = memoryview(self._vtk_helper.rgb_still)
        self.push(content, self._get_metadata())

    def set_streamer(self, stream_manager):
        """Need to implement"""
        self.streamer = stream_manager

    def update_size(self, origin, size):
        """Need to implement"""
        width = int(size.get("w", 300))
        height = int(size.get("h", 300))
        pixel_ratio = size.get("p", 1)
        self._view.SetSize(int(width * pixel_ratio), int(height * pixel_ratio))
        content = memoryview(self._vtk_helper.rgb_still)
        self.push(content, self._get_metadata())

    def push(self, content, meta=None):
        if meta is not None:
            self.last_meta = meta
        if content is None:
            return
        if self.streamer is None:
            return

        self.streamer.push_content(self.area_name, self.last_meta, content)

    def render(self):
        content = memoryview(self._vtk_helper.rgb_still)
        self.push(content, self._get_metadata())

    def on_interaction(self, origin, event):
        """Need to implement"""
        event_type = event["type"]
        if event_type == "StartInteractionEvent":
            if not self.animating:
                self.animating = True
                asynchronous.create_task(self._animate())
        elif event_type == "EndInteractionEvent":
            self.animating = False
        else:
            event_str = json.dumps(event)
            vtkRemoteInteractionAdapter.ProcessEvent(self._iren, event_str)


@TrameApp()
class ConeApp:
    def __init__(self, server=None):
        self.server = get_server(server, client_type="vue3")

        self.render_window, self.cone_source = self.setup_vtk()
        self.view_handler = ViewAdapter(self.render_window, "view")
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

        renderer.AddActor(actor)
        renderer.ResetCamera()

        return renderWindow, cone_source

    def build_ui(self):
        with SinglePageLayout(self.server, full_height=True) as layout:
            layout.title.set_text("RCA rendering")

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
                with v3.VContainer(
                    fluid=True,
                    classes="pa-0 fill-height position-relative",
                ):
                    rca.RemoteControlledArea(
                        name="view",
                        display="image",
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
        self.view_handler.render()

    @life_cycle.server_ready
    def on_server_ready(self, **_):
        # can only be called when server is ready
        self.ctrl.rc_area_register(self.view_handler)

    def update_reset_resolution(self):
        self.state.resolution = DEFAULT_RESOLUTION


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    app = ConeApp()
    enable_testing(app.server)
    app.server.start()
