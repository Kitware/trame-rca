import pytest
from pathlib import Path
from trame_client.utils.testing import FixtureHelper

from vtkmodules.vtkFiltersSources import vtkConeSource
from vtkmodules.vtkRenderingCore import (
    vtkRenderer,
    vtkRenderWindow,
    vtkPolyDataMapper,
    vtkActor,
    vtkRenderWindowInteractor,
)

ROOT_PATH = Path(__file__).parent.parent.absolute()
HELPER = FixtureHelper(ROOT_PATH)


@pytest.fixture
def server(xprocess, server_path):
    name, Starter, Monitor = HELPER.get_xprocess_args(server_path)

    # ensure process is running and return its logfile
    logfile = xprocess.ensure(name, Starter)
    try:
        yield Monitor(logfile[1])
    finally:
        # clean up whole process tree afterwards
        xprocess.getinfo(name).terminate()


@pytest.fixture()
def a_render_window():
    renderer = vtkRenderer()
    render_window = vtkRenderWindow()
    render_window.AddRenderer(renderer)
    render_window.SetSize(300, 300)
    render_window.ShowWindowOff()

    render_window_interactor = vtkRenderWindowInteractor()
    render_window_interactor.SetRenderWindow(render_window)

    cone_source = vtkConeSource()
    mapper = vtkPolyDataMapper()
    mapper.SetInputConnection(cone_source.GetOutputPort())
    actor = vtkActor()
    actor.SetMapper(mapper)

    renderer.AddActor(actor)
    renderer.ResetCamera()
    yield render_window
