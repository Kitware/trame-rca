"""A dynamic point cloud rendered in a native desktop window without trame.

Every frame moves each point randomly and assigns new random colors, then renders.
The frames are computed ahead, on resize: --frames 0 computes each one live instead.
Prints the updates/s and the time spent per stage to the console once a second,
as a baseline to compare the shared texture path against.

Keys: + / - add or remove --step points, space pauses or resumes the animation.
"""

import argparse
import time

import numpy as np
from vtkmodules.util.numpy_support import numpy_to_vtk, numpy_to_vtkIdTypeArray
from vtkmodules.vtkCommonCore import vtkPoints
from vtkmodules.vtkCommonDataModel import vtkCellArray, vtkPolyData
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleTrackballCamera
from vtkmodules.vtkRenderingCore import (
    vtkActor,
    vtkPolyDataMapper,
    vtkRenderer,
    vtkRenderWindow,
    vtkRenderWindowInteractor,
)

# Required for vtk factory
import vtkmodules.vtkRenderingOpenGL2  # noqa: F401

BYTES_PER_POINT = 3 * 4 + 3 * 1  # float32 xyz + uint8 rgb
DISABLE_SHIFT_SCALE = 0  # vtkOpenGLVertexBufferObject::ShiftScaleMethod
RADII = (2.0, 1.0, 0.5)  # standard deviation of the cloud along x, y and z


class PointCloud:
    """vtkPolyData whose point and color arrays change every frame

    With ``n_frames`` > 1 the frames are computed once, on resize, and each update only
    points the polydata at the next frame's arrays: the app work drops to ~0 while every
    frame still uploads new data. They play back and forth so the loop has no jump.
    With ``n_frames`` = 0 each update computes a new frame, in place.
    The points spread out along x, y and z by ``radii``: an ellipsoidal cloud.
    """

    def __init__(self, n_points, n_frames=8, seed=0, radii=RADII):
        self.rng = np.random.default_rng(seed)
        self.radii = np.asarray(radii, dtype=np.float32)
        self.polydata = vtkPolyData()
        self.n_points = 0
        self.n_frames = n_frames
        self.positions = np.zeros((0, 3), dtype=np.float32)
        self.frames = []
        self._t = 0
        self.resize(n_points)

    def resize(self, n_points):
        n_old = self.n_points
        positions = np.empty((n_points, 3), dtype=np.float32)
        positions[: min(n_old, n_points)] = self.positions[:n_points]
        if n_points > n_old:
            positions[n_old:] = self.rng.standard_normal(
                (n_points - n_old, 3), dtype=np.float32
            )
            positions[n_old:] *= self.radii
        colors = np.empty((n_points, 3), dtype=np.uint8)
        self._noise = np.empty_like(positions)
        self.n_points = n_points

        # Keep python references alive: the VTK arrays share numpy memory.
        self.frames = []
        for _ in range(max(1, self.n_frames)):
            self._walk(positions, colors)
            self.frames.append(self._to_vtk(positions, colors))
            positions, colors = positions.copy(), colors.copy()
        self.positions = self.frames[-1][0]
        self.colors = self.frames[-1][1]
        self._t = 0

        # A single polyvertex cell with every point. The mapper rebuilds its index buffer
        # whenever the points change, and that is about twice as fast as from one vertex
        # cell per point.
        verts = vtkCellArray()
        verts.SetData(
            numpy_to_vtkIdTypeArray(np.array([0, n_points], dtype=np.int64), deep=True),
            numpy_to_vtkIdTypeArray(np.arange(n_points, dtype=np.int64), deep=True),
        )

        self.polydata.SetPoints(vtkPoints())
        self.polydata.SetVerts(verts)
        self._show(self.frames[-1])
        self.polydata.Modified()

    def animate(self):
        if self.n_frames == 0:
            self._walk(self.positions, self.colors)
            self._show(self.frames[0])
            return
        # Ping-pong: 0, 1, ..., K-1, K-2, ..., 1, 0, 1, ...
        k = len(self.frames)
        period = max(1, 2 * k - 2)
        i = self._t % period
        self._t += 1
        self._show(self.frames[i if i < k else period - i])

    def _walk(self, positions, colors, step=0.02, pull=0.995):
        # Random walk with a weak pull toward the origin so the cloud stays put. The steps
        # scale with the radii too, so the walk keeps the cloud's shape.
        self.rng.standard_normal(out=self._noise, dtype=np.float32)
        self._noise *= step * self.radii
        positions *= pull
        positions += self._noise
        colors.reshape(-1)[:] = np.frombuffer(self.rng.bytes(colors.size), np.uint8)

    @staticmethod
    def _to_vtk(positions, colors):
        vtk_positions = numpy_to_vtk(positions, deep=False)
        vtk_colors = numpy_to_vtk(colors, deep=False)
        vtk_colors.SetName("colors")
        return positions, colors, vtk_positions, vtk_colors

    def _show(self, frame):
        _, _, vtk_positions, vtk_colors = frame
        # Modified() also covers a single frame, or the live mode, reusing the arrays.
        vtk_positions.Modified()
        vtk_colors.Modified()
        points = self.polydata.GetPoints()
        points.SetData(vtk_positions)
        points.Modified()
        self.polydata.point_data.SetScalars(vtk_colors)

    @property
    def payload_bytes(self):
        return self.n_points * BYTES_PER_POINT


def create_vtk_pipeline(polydata):
    mapper = vtkPolyDataMapper()
    mapper.SetInputData(polydata)
    mapper.SetColorModeToDirectScalars()
    mapper.SetScalarModeToUsePointData()
    # The cloud stays around the origin, so float32 coordinates need no shift and scale:
    # skipping it saves a pass over the points on every upload.
    mapper.SetVBOShiftScaleMethod(DISABLE_SHIFT_SCALE)

    actor = vtkActor(mapper=mapper)
    actor.property.point_size = 2

    renderer = vtkRenderer(background=(0.1, 0.1, 0.12))
    renderer.AddActor(actor)
    renderer.ResetCamera()

    render_window = vtkRenderWindow(size=(1024, 768))
    # MSAA costs more than drawing the points themselves, ~6 ms per frame at 1080p.
    render_window.SetMultiSamples(0)
    render_window.SetWindowName("Dynamic point cloud native example")
    render_window.AddRenderer(renderer)
    interactor = vtkRenderWindowInteractor(
        render_window=render_window,
        interactor_style=vtkInteractorStyleTrackballCamera(),
    )
    return render_window, interactor


class Stats:
    """Accumulates per-frame stage timings and prints their mean once a second"""

    def __init__(self):
        self.reset()

    def reset(self):
        self.frames = 0
        self.generate_ms = 0.0
        self.render_ms = 0.0
        self.start = time.perf_counter()

    def add(self, generate_ms, render_ms, cloud):
        self.frames += 1
        self.generate_ms += generate_ms
        self.render_ms += render_ms
        elapsed = time.perf_counter() - self.start
        if elapsed < 1.0:
            return
        n = self.frames
        frame_ms = 1000 * elapsed / n
        render_ms = self.render_ms / n
        payload_mb = cloud.payload_bytes / 1e6
        print(
            f"points={cloud.n_points:>12,} updates/s={n / elapsed:>7.1f} "
            f"update={frame_ms:>7.1f} ms generate={self.generate_ms / n:>7.2f} ms "
            f"render={render_ms:>7.2f} ms ({payload_mb:.1f} MB/update"
            + (f", {payload_mb / (render_ms / 1000):.0f} MB/s" if render_ms else "")
            + ")",
            flush=True,
        )
        self.reset()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--points", type=int, default=100_000, help="Initial points")
    parser.add_argument(
        "--step", type=int, default=100_000, help="Points per + or - key press"
    )
    parser.add_argument(
        "--frames",
        type=int,
        default=8,
        help="Frames computed ahead on resize, 0 to compute each one live",
    )
    parser.add_argument(
        "--radii",
        type=float,
        nargs=3,
        default=RADII,
        metavar=("X", "Y", "Z"),
        help="Spread of the ellipsoidal cloud along x, y and z",
    )
    parser.add_argument(
        "--no-vsync", action="store_true", help="Don't cap the fps at the display rate"
    )
    args = parser.parse_args()

    cloud = PointCloud(args.points, args.frames, radii=args.radii)
    render_window, interactor = create_vtk_pipeline(cloud.polydata)
    interactor.Initialize()
    if args.no_vsync:
        # Needs a created window, so after Initialize().
        render_window.SetSwapControl(0)

    stats = Stats()
    running = True

    def step(*_):
        if not running:
            return
        t0 = time.perf_counter()
        cloud.animate()
        t1 = time.perf_counter()
        render_window.Render()
        t2 = time.perf_counter()
        stats.add(1000 * (t1 - t0), 1000 * (t2 - t1), cloud)

    def on_key(obj, _):
        nonlocal running
        key = obj.GetKeySym()
        if key in ("plus", "equal", "KP_Add"):
            cloud.resize(cloud.n_points + args.step)
        elif key in ("minus", "KP_Subtract"):
            cloud.resize(max(1, cloud.n_points - args.step))
        elif key == "space":
            running = not running
        else:
            return
        stats.reset()
        render_window.Render()

    interactor.AddObserver("KeyPressEvent", on_key)
    interactor.AddObserver("TimerEvent", step)
    interactor.CreateRepeatingTimer(1)
    render_window.Render()
    interactor.Start()


if __name__ == "__main__":
    main()
