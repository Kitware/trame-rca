import os
import sys

import pytest
from vtkmodules.vtkFiltersCore import vtkElevationFilter
from vtkmodules.vtkFiltersSources import vtkSphereSource
from vtkmodules.vtkRenderingCore import (
    vtkActor,
    vtkPolyDataMapper,
    vtkRenderer,
    vtkRenderWindow,
    vtkRenderWindowInteractor,
)

from trame_rca.encoders import RcaImageEncoder
from trame_rca.rca import VtkRemoteControlledArea


if os.environ.get("CI") is not None and sys.platform != "linux":
    pytest.skip(
        "Rendering tests are disabled on CI for non Linux platforms.",
        allow_module_level=True,
    )


@pytest.fixture(scope="module")
def full_hd_scene():
    # A colored mesh filling most of the frame over a gradient, so encoding
    # sees detail rather than mostly flat background
    sphere = vtkSphereSource()
    sphere.SetThetaResolution(120)
    sphere.SetPhiResolution(120)
    elevation = vtkElevationFilter()
    elevation.SetInputConnection(sphere.GetOutputPort())
    elevation.SetLowPoint(0, 0, -0.5)
    elevation.SetHighPoint(0, 0, 0.5)
    mapper = vtkPolyDataMapper()
    mapper.SetInputConnection(elevation.GetOutputPort())
    actor = vtkActor()
    actor.SetMapper(mapper)
    actor.GetProperty().EdgeVisibilityOn()
    renderer = vtkRenderer()
    renderer.AddActor(actor)
    renderer.GradientBackgroundOn()
    renderer.SetBackground(0.1, 0.2, 0.3)
    renderer.SetBackground2(0.8, 0.8, 0.9)
    renderer.ResetCamera()
    renderer.GetActiveCamera().Zoom(2.4)
    render_window = vtkRenderWindow()
    render_window.SetOffScreenRendering(1)
    render_window.AddRenderer(renderer)
    render_window.SetSize(1920, 1080)
    interactor = vtkRenderWindowInteractor()
    interactor.SetRenderWindow(render_window)

    rca = VtkRemoteControlledArea(render_window)
    rca_render = rca._render

    def render():
        rca_render()
        # Render() only queues GPU work; finish it so capture doesn't time it
        render_window.WaitForCompletion()

    # img_cols_rows renders first; render in the untimed setup instead
    rendered = []

    def recording_render():
        rendered.append(True)
        render()

    rca._render = recording_render
    rca.img_cols_rows
    assert rendered, "img_cols_rows no longer renders through _render"
    rca._render = lambda: None
    yield rca, render, renderer.GetActiveCamera()
    render_window.Finalize()


def test_benchmark_capture(benchmark, full_hd_scene):
    rca, render, camera = full_hd_scene

    def next_frame():
        camera.Azimuth(1)
        render()

    benchmark.pedantic(
        lambda: rca.img_cols_rows, setup=next_frame, rounds=50, warmup_rounds=5
    )


@pytest.mark.parametrize("encoder", list(RcaImageEncoder))
def test_benchmark_encode(benchmark, full_hd_scene, encoder):
    rca, render, _ = full_hd_scene
    render()
    image, cols, rows = rca.img_cols_rows

    encoded, *_ = benchmark.pedantic(
        encoder.encode,
        args=(image, cols, rows, 80),
        # JPEG encodes in milliseconds and needs more rounds for a stable median;
        # the other formats are 20-150x slower, so fewer rounds keep this short
        rounds=50 if "JPEG" in encoder.name else 10,
        warmup_rounds=2,
    )
    benchmark.extra_info["frame_bytes"] = len(encoded)
