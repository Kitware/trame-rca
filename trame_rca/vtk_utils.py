import json
from packaging.version import Version
import vtkmodules.vtkRenderingOpenGL2  # noqa
from vtkmodules.util.numpy_support import vtk_to_numpy
from vtkmodules.vtkCommonCore import vtkCommand, vtkVersion
from vtkmodules.vtkRenderingCore import vtkRenderWindow, vtkWindowToImageFilter
from vtkmodules.vtkWebCore import vtkRemoteInteractionAdapter


class VtkWindow:
    def __init__(self, vtk_render_window: vtkRenderWindow):
        self._vtk_render_window = vtk_render_window
        self._window_to_image = vtkWindowToImageFilter()
        self._window_to_image.SetInput(vtk_render_window)
        self._window_to_image.SetScale(1)
        self._window_to_image.ReadFrontBufferOff()
        self._window_to_image.ShouldRerenderOff()
        self._window_to_image.FixBoundaryOn()
        self._iren = self._vtk_render_window.GetInteractor()
        self._iren.EnableRenderOff()
        self._vtk_render_window.ShowWindowOff()

    @property
    def img_cols_rows(self):
        self._vtk_render_window.Render()
        self._window_to_image.Modified()
        self._window_to_image.Update()

        image_data = self._window_to_image.GetOutput()
        rows, cols, _ = image_data.GetDimensions()
        scalars = image_data.GetPointData().GetScalars()
        np_image = vtk_to_numpy(scalars)
        np_image = np_image.reshape((cols, rows, -1))
        np_image[:] = np_image[::-1, :, :]
        return np_image, cols, rows

    def process_resize_event(self, width, height):
        self._iren.UpdateSize(width, height)
        if Version(vtkVersion().vtk_version) < Version("9.5"):
            self._iren.InvokeEvent(vtkCommand.WindowResizeEvent)

    def process_interaction_event(self, event):
        event_type = event["type"]
        if event_type in ["StartInteractionEvent", "EndInteractionEvent"]:
            return

        vtkRemoteInteractionAdapter.ProcessEvent(self._iren, json.dumps(event))
