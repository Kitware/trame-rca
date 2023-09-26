import asyncio
import json
import time

# Required for rendering initialization, not necessary for
# local rendering, but doesn't hurt to include it
import vtkmodules.vtkRenderingOpenGL2  # noqa
from trame.app import asynchronous, get_server
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
from vtkmodules.vtkWebCore import vtkRemoteInteractionAdapter, vtkWebApplication

# This should be unique
HELPER = vtkWebApplication()
HELPER.SetImageEncoding(vtkWebApplication.ENCODING_NONE)
HELPER.SetNumberOfEncoderThreads(4)


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

    def _get_metadata(self):
        return dict(
            type="image/jpeg",  # mime time
            codec="",  # video codec, not relevant here
            w=self._view.GetSize()[0],
            h=self._view.GetSize()[1],
            st=int(time.time_ns() / 1000000),
            key=("key"),  # jpegs are always keyframes
        )

    async def _animate(self):
        mtime = 0
        while self.animating:
            data = HELPER.InteractiveRender(self._view)
            if data is not None and mtime != data.GetMTime():
                mtime = data.GetMTime()
                self.push(memoryview(data), self._get_metadata())
                await asyncio.sleep(1.0 / self.target_fps)
            await asyncio.sleep(0)

        HELPER.InvalidateCache(self._view)
        content = memoryview(HELPER.StillRender(self._view))
        self.push(content, self._get_metadata())

    def set_streamer(self, stream_manager):
        self.streamer = stream_manager

    def update_size(self, origin, size):
        width = int(size.get("w", 300))
        height = int(size.get("h", 300))
        self._view.SetSize(width, height)
        content = memoryview(HELPER.StillRender(self._view))
        self.push(content, self._get_metadata())

    def push(self, content, meta=None):
        if meta is not None:
            self.last_meta = meta
        if content is None:
            return
        self.streamer.push_content(self.area_name, self.last_meta, content)

    def on_interaction(self, origin, event):
        event_type = event["type"]
        if event_type == "StartInteractionEvent":
            if not self.animating:
                self.animating = True
                asynchronous.create_task(self._animate())
        elif event_type == "EndInteractionEvent":
            self.animating = False
        else:
            event_str = json.dumps(event)
            status = vtkRemoteInteractionAdapter.ProcessEvent(self._iren, event_str)

            # Force Render next time InteractiveRender is called
            if status:
                HELPER.InvalidateCache(self._view)


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
    view_handler = ViewAdapter(renderWindow, "view", target_fps=30)
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
    server.start()
