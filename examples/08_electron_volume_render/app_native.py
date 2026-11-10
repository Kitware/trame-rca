"""The same VTK scene as app.py, rendered in a native desktop window without trame.

Starts spinning the camera and prints the fps to the console once a second,
as a baseline to compare the shared texture path against.
"""

import argparse
import time

from vtkmodules.vtkCommonDataModel import vtkPiecewiseFunction
from vtkmodules.vtkFiltersSources import vtkPartitionedDataSetCollectionSource
from vtkmodules.vtkImagingCore import vtkRTAnalyticSource
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleTrackballCamera
from vtkmodules.vtkRenderingCore import (
    vtkActor,
    vtkColorTransferFunction,
    vtkCompositePolyDataMapper,
    vtkRenderer,
    vtkRenderWindow,
    vtkRenderWindowInteractor,
    vtkVolume,
    vtkVolumeProperty,
)
from vtkmodules.vtkRenderingVolumeOpenGL2 import vtkSmartVolumeMapper

# Required for vtk factory
import vtkmodules.vtkRenderingOpenGL2  # noqa: F401


def create_vtk_pipeline():
    wavelet = vtkRTAnalyticSource()
    volume_mapper = vtkSmartVolumeMapper()
    volume_mapper.SetInputConnection(wavelet.output_port)
    color_tf = vtkColorTransferFunction()
    color_tf.AddRGBPoint(0.0, 0.0, 0.0, 1.0)
    color_tf.AddRGBPoint(255.0 / 2.0, 0.0, 1.0, 1.0)
    color_tf.AddRGBPoint(255.0, 1.0, 0.0, 1.0)
    opacity_tf = vtkPiecewiseFunction()
    opacity_tf.AddPoint(0.0, 0.0)
    opacity_tf.AddPoint(255.0, 0.1)
    volume_property = vtkVolumeProperty()
    volume_property.SetColor(color_tf)
    volume_property.SetScalarOpacity(opacity_tf)
    volume_property.ShadeOn()
    volume_property.SetInterpolationTypeToLinear()
    volume_actor = vtkVolume(mapper=volume_mapper, property=volume_property)

    shapes = vtkPartitionedDataSetCollectionSource()
    cpdm = vtkCompositePolyDataMapper()
    cpdm.SetInputConnection(shapes.output_port)
    shapes_actor = vtkActor(mapper=cpdm)

    renderer = vtkRenderer()
    renderer.AddVolume(volume_actor)
    renderer.AddActor(shapes_actor)
    renderer.ResetCamera()

    render_window = vtkRenderWindow(size=(1024, 768))
    render_window.SetWindowName("Shared texture native example")
    render_window.AddRenderer(renderer)
    interactor = vtkRenderWindowInteractor(
        render_window=render_window,
        interactor_style=vtkInteractorStyleTrackballCamera(),
    )
    return render_window, renderer, interactor


class FpsCounter:
    def __init__(self):
        self.frames = 0
        self.start = time.perf_counter()

    def tick(self):
        self.frames += 1
        elapsed = time.perf_counter() - self.start
        if elapsed >= 1.0:
            print(f"{self.frames / elapsed:.1f} fps", flush=True)
            self.frames = 0
            self.start = time.perf_counter()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--no-vsync", action="store_true", help="Don't cap the fps at the display rate"
    )
    args = parser.parse_args()

    render_window, renderer, interactor = create_vtk_pipeline()
    interactor.Initialize()
    if args.no_vsync:
        # Needs a created window, so after Initialize().
        render_window.SetSwapControl(0)
    # Match app.py while spinning: render at the interactor's interactive rate.
    render_window.desired_update_rate = interactor.desired_update_rate

    camera = renderer.GetActiveCamera()
    fps = FpsCounter()
    render_window.AddObserver("EndEvent", lambda *_: fps.tick())

    def spin(*_):
        # Spin by a degree per frame, like app.py.
        camera.Azimuth(1.0)
        renderer.ResetCameraClippingRange()
        render_window.Render()

    interactor.AddObserver("TimerEvent", spin)
    interactor.CreateRepeatingTimer(1)
    render_window.Render()
    interactor.Start()


if __name__ == "__main__":
    main()
