"""A dynamic point cloud whose VTK view is shared with Electron as a texture, not streamed.

Every frame the server moves each point randomly, assigns new random colors and renders
into the texture Electron shows. The frames are computed ahead, on resize, so that the
app work is ~0: --frames 0 computes each one live instead. The next frame starts once Electron is done with the
previous one, so the measured updates/s is the maximum rate at which new data goes
through the full pipeline:

    numpy -> vtk arrays -> render (upload to the GPU + draw) -> shared texture
          -> Electron composites the frame -> "frame_done" back to Python

--second-view adds a second shared-texture view of the same cloud next to the first, and
spins the camera of both views, in opposite directions.

Started by the Electron app in ./electron, see the README. app_native.py renders the
same scene in a desktop window, as a baseline.
"""

import asyncio
import time

import numpy as np

from trame.app import TrameApp
from trame.decorators import change
from trame.ui.html import DivLayout
from trame.widgets import client, html
from trame_common.utils import profiler
from trame_rca.widgets import init_vtk_for_shared_textures, rca

# Before creating any VTK render window: VTK must render on the GPU Electron uses.
init_vtk_for_shared_textures()

from vtkmodules.util.numpy_support import numpy_to_vtk, numpy_to_vtkIdTypeArray  # noqa: E402
from vtkmodules.vtkCommonCore import vtkPoints  # noqa: E402
from vtkmodules.vtkCommonDataModel import vtkCellArray, vtkPolyData  # noqa: E402
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleTrackballCamera  # noqa: E402
from vtkmodules.vtkRenderingCore import (  # noqa: E402
    vtkActor,
    vtkPolyDataMapper,
    vtkRenderer,
    vtkRenderWindow,
)
from vtkmodules.vtkRenderingUI import vtkGenericRenderWindowInteractor  # noqa: E402

# Required for vtk factory
import vtkmodules.vtkRenderingOpenGL2  # noqa: E402, F401

WARMUP_FRAMES = 5  # frames skipped after a resize (topology + first upload)
ROLLING_FRAMES = 30  # frames averaged in the live panel
UI_REFRESH_S = 0.25
BYTES_PER_POINT = 3 * 4 + 3 * 1  # float32 xyz + uint8 rgb
DISABLE_SHIFT_SCALE = 0  # vtkOpenGLVertexBufferObject::ShiftScaleMethod
RADII = (2.0, 1.0, 0.5)  # standard deviation of the cloud along x, y and z
SPIN_DEG_PER_S = 30.0  # camera spin with --second-view

STAGES = [
    ("generate", "app work: swap in the next precomputed frame, or compute it"),
    ("render", "Render + WaitForCompletion: upload to the GPU + draw, until done"),
    (
        "electron",
        "until the next texture is free: import, IPC, canvas draw, frame_done, pacing",
    ),
]

PANEL_STYLE = """
position:absolute; top:1rem; left:1rem; z-index:10; width:38rem;
max-height:calc(100vh - 2rem); overflow:auto;
background:rgba(20,22,28,0.85); color:#e8e8e8; border-radius:8px;
padding:0.75rem 1rem; font:12px/1.4 ui-monospace,Menlo,monospace;
"""

CSS = """
body { margin: 0; }
.bench table { width:100%; border-collapse:collapse; margin:0.25rem 0 0.75rem; }
.bench td, .bench th { padding:1px 4px; text-align:right; white-space:nowrap; }
.bench td:first-child, .bench th:first-child { text-align:left; }
.bench td.stage { white-space:normal; }
.bench th { color:#9aa; font-weight:normal; border-bottom:1px solid #444; }
.bench .bar { height:8px; background:#4c9be8; border-radius:2px; }
.bench .big { font-size:20px; font-weight:bold; }
.bench button { font:inherit; padding:4px 10px; margin-right:6px; cursor:pointer; }
.bench .muted { color:#9aa; }
"""


# -----------------------------------------------------------------------------
# Data
# -----------------------------------------------------------------------------


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
    # The texture's alpha reaches Electron, so keep the background opaque.
    renderer.SetBackgroundAlpha(1.0)
    renderer.ResetCamera()

    render_window = vtkRenderWindow()
    render_window.AddRenderer(renderer)
    # MSAA costs more than drawing the points themselves, ~6 ms per frame at 1080p.
    render_window.SetMultiSamples(0)
    # trame-rca replays the canvas's input on the interactor.
    vtkGenericRenderWindowInteractor(
        render_window=render_window,
        interactor_style=vtkInteractorStyleTrackballCamera(),
    )
    return render_window


class CameraSpinner:
    """Turns the camera of a render window around its view up at a steady rate.

    The angle follows the elapsed time, so views rendering at different rates spin alike.
    """

    def __init__(self, render_window, deg_per_s):
        renderer = render_window.GetRenderers().GetFirstRenderer()
        self.camera = renderer.GetActiveCamera()
        self.deg_per_s = deg_per_s
        self._t_last = None

    def step(self):
        t = time.perf_counter()
        if self._t_last is not None:
            self.camera.Azimuth(self.deg_per_s * (t - self._t_last))
        self._t_last = t

    def pause(self):
        # Resume from where it stopped, without catching up on the pause.
        self._t_last = None


# -----------------------------------------------------------------------------
# Frame bookkeeping
# -----------------------------------------------------------------------------


class Frame:
    __slots__ = ["n_points", "t_start", "stages", "total_ms"]

    def __init__(self, n_points):
        self.n_points = n_points
        self.t_start = time.perf_counter()
        self.stages = {}
        self.total_ms = 0.0

    def finalize(self, t_end):
        """The frame ends when the next one starts: whatever is left is Electron's"""
        self.total_ms = (t_end - self.t_start) * 1000
        self.stages["electron"] = max(
            0.0,
            self.total_ms - self.stages["generate"] - self.stages["render"],
        )


class LevelStats:
    """Aggregated frames recorded at one point count and number of shared textures"""

    def __init__(self, n_points, textures):
        self.n_points = n_points
        self.textures = textures
        self.seen = 0
        self.count = 0
        self.total_ms = 0.0
        self.work_ms = 0.0

    def add(self, frame):
        self.seen += 1
        if self.seen <= WARMUP_FRAMES:
            return
        self.count += 1
        self.total_ms += frame.total_ms
        self.work_ms += frame.stages["generate"]

    @property
    def mean_ms(self):
        return self.total_ms / self.count if self.count else 0.0

    def row(self):
        mean = self.mean_ms
        mb = self.n_points * BYTES_PER_POINT / 1e6
        overhead = mean - self.work_ms / self.count
        return {
            "points": f"{self.n_points:,}",
            "textures": self.textures,
            "frames": self.count,
            "ms": f"{mean:.1f}",
            "ups": f"{1000 / mean:.1f}" if mean else "-",
            "mbs": f"{mb / (overhead / 1000):.0f}" if overhead > 0 else "-",
        }


def fit_capacity(levels):
    """Least squares fit total_ms = a + b * n_points over the measured levels"""
    pts = [(lv.n_points, lv.mean_ms) for lv in levels if lv.count >= 10]
    if len(pts) < 2:
        return None
    n = np.array([p[0] for p in pts], dtype=float)
    t = np.array([p[1] for p in pts], dtype=float)
    b, a = np.polyfit(n, t, 1)
    if b <= 0:
        return None

    def capacity(ups):
        return max(0, int((1000.0 / ups - a) / b))

    return {
        "fixed_ms": f"{a:.2f}",
        "ns_per_point": f"{b * 1e6:.1f}",
        "at30": f"{capacity(30):,}",
        "at60": f"{capacity(60):,}",
    }


# -----------------------------------------------------------------------------
# Application
# -----------------------------------------------------------------------------


class PointCloudBenchmark(TrameApp):
    def __init__(self, server=None):
        super().__init__(server)

        cli = self.server.cli
        cli.add_argument("--points", type=int, default=100_000, help="Initial points")
        cli.add_argument(
            "--step", type=int, default=100_000, help="Points per +N click"
        )
        cli.add_argument(
            "--frames",
            type=int,
            default=8,
            help="Frames computed ahead on resize, 0 to compute each one live",
        )
        cli.add_argument(
            "--target-fps", type=float, default=60.0, help="Cap on the frame rate"
        )
        cli.add_argument(
            "--textures",
            type=int,
            default=2,
            help="Shared textures VTK renders into in turn, also changeable in the panel",
        )
        cli.add_argument(
            "--radii",
            type=float,
            nargs=3,
            default=RADII,
            metavar=("X", "Y", "Z"),
            help="Spread of the ellipsoidal cloud along x, y and z",
        )
        cli.add_argument(
            "--second-view",
            action="store_true",
            help="Add a second view of the cloud and spin both cameras",
        )
        args, _ = cli.parse_known_args()

        self.step_size = args.step
        self.target_fps = args.target_fps
        self.texture_count = args.textures
        self.cloud = PointCloud(args.points, args.frames, radii=args.radii)
        self.pending_points = None
        self.running = True
        self.frame = None
        self.recent = []
        self.levels = []

        self._timer_generate = profiler.Timer("rca.bench.generate")
        self._render_start = 0.0

        self.render_window = create_vtk_pipeline(self.cloud.polydata)
        self.render_window.AddObserver("StartEvent", self._on_render_start)
        self.render_window.AddObserver("EndEvent", self._on_render_end)

        # The second view shares the cloud: the first view's frames move its points.
        self.second_render_window = None
        self.spinners = []
        if args.second_view:
            self.second_render_window = create_vtk_pipeline(self.cloud.polydata)
            self.spinners = [
                CameraSpinner(self.render_window, SPIN_DEG_PER_S),
                CameraSpinner(self.second_render_window, -SPIN_DEG_PER_S),
            ]
        self.second_view_handler = None

        self._build_ui()
        self._new_level()
        self.server.controller.on_server_ready.add(self._on_server_ready)

    # Frame loop -----------------------------------------------------------------

    def _on_server_ready(self, **_):
        asyncio.get_running_loop().create_task(self._publish_stats())

    def before_render(self):
        # Called by the scheduler before every frame: each frame asks for the next one.
        t_now = time.perf_counter()
        if self.frame is not None:
            self.frame.finalize(t_now)
            self.recent.append(self.frame)
            del self.recent[:-ROLLING_FRAMES]
            self.levels[-1].add(self.frame)
            self.frame = None

        if not self.running:
            return

        if self.pending_points is not None:
            if self.pending_points != self.cloud.n_points:
                self.cloud.resize(self.pending_points)
                self._new_level()
            self.pending_points = None

        if self.spinners:
            self.spinners[0].step()

        frame = Frame(self.cloud.n_points)
        with self._timer_generate:
            self.cloud.animate()
        frame.stages["generate"] = self._timer_generate.dt
        self.frame = frame
        self.view_handler.update()

    def before_render_second(self):
        # The second view only spins: it picks up the cloud's latest points on its own.
        if not self.running:
            return
        self.spinners[1].step()
        self.second_view_handler.update()

    def _on_render_start(self, *_):
        self._render_start = time.perf_counter()

    def _on_render_end(self, *_):
        if self.frame is None:
            return
        # GL only queues the work: wait for the GPU here so that it counts as rendering.
        # The scheduler's flush waits for the same thing right after, for free.
        self.render_window.WaitForCompletion()
        self.frame.stages["render"] = (time.perf_counter() - self._render_start) * 1000

    # Controls -------------------------------------------------------------------

    def add_points(self):
        self._change_points(+self.step_size)

    def remove_points(self):
        self._change_points(-self.step_size)

    def _change_points(self, delta):
        base = self.pending_points or self.cloud.n_points
        self.pending_points = max(1, base + delta)
        self.state.n_points_pending = self.pending_points

    @change("textures")
    def on_textures_change(self, textures, **_):
        textures = int(textures)
        if textures == self.texture_count:
            return
        # The scheduler rebuilds its ring of textures before the next frame.
        self.texture_count = textures
        self.view_handler.texture_count = textures
        if self.second_view_handler:
            self.second_view_handler.texture_count = textures
        self._new_level()

    def toggle_running(self):
        self.running = not self.running
        self.state.running = self.running
        if self.running:
            self.view_handler.update()
            if self.second_view_handler:
                self.second_view_handler.update()
        else:
            for spinner in self.spinners:
                spinner.pause()

    def _new_level(self):
        if self.levels and self.levels[-1].count:
            row = self.levels[-1].row()
            print(
                f"[bench] points={row['points']:>12} textures={row['textures']} "
                f"updates={row['frames']:>5} "
                f"update={row['ms']:>8} ms updates/s={row['ups']:>7} overhead MB/s={row['mbs']:>6}",
                flush=True,
            )
        if self.levels and not self.levels[-1].count:
            self.levels.pop()

        # Coming back to a measured point count keeps adding to its row so the
        # fit sees each count once. Warmup is skipped again after the resize.
        key = (self.cloud.n_points, self.texture_count)
        level = next(
            (lv for lv in self.levels if (lv.n_points, lv.textures) == key), None
        )
        if level is None:
            level = LevelStats(*key)
        else:
            self.levels.remove(level)
            level.seen = 0
        self.levels.append(level)
        self.recent.clear()

    # Stats ------------------------------------------------------------------------

    async def _publish_stats(self):
        t_print = time.perf_counter()
        while True:
            await asyncio.sleep(UI_REFRESH_S)
            if not self.recent:
                continue
            stats = self._stats()
            with self.state:
                self.state.update(stats)
            # Also once a second on the console, to compare with app_native.py.
            if time.perf_counter() - t_print >= 1.0:
                t_print = time.perf_counter()
                stages = " ".join(
                    f"{s['name']}={s['ms']:>7} ms" for s in stats["stages"]
                )
                print(
                    f"points={stats['n_points']:>12} updates/s={stats['ups']:>7} "
                    f"update={stats['frame_ms']:>7} ms {stages}",
                    flush=True,
                )

    def _stats(self):
        frames = self.recent
        k = len(frames)
        total = sum(f.total_ms for f in frames) / k
        stage_ms = {
            name: sum(f.stages.get(name, 0) for f in frames) / k for name, _ in STAGES
        }
        overhead = total - stage_ms["generate"]
        payload_mb = self.cloud.payload_bytes / 1e6

        return {
            "n_points": f"{self.cloud.n_points:,}",
            "n_points_pending": self.pending_points,
            "payload_mb": f"{payload_mb:.1f}",
            "ups": f"{1000 / total:.1f}",
            "frame_ms": f"{total:.1f}",
            "overhead_ms": f"{overhead:.1f}",
            "overhead_mbs": f"{payload_mb / (overhead / 1000):.0f}"
            if overhead > 0
            else "-",
            "stages": [
                {
                    "name": name,
                    "help": help,
                    "ms": f"{stage_ms[name]:.2f}",
                    "pct": f"{100 * stage_ms[name] / total:.0f}",
                }
                for name, help in STAGES
            ],
            "levels": [
                lv.row()
                for lv in sorted(self.levels, key=lambda lv: (lv.textures, lv.n_points))
                if lv.count
            ],
            "fit": fit_capacity(
                [lv for lv in self.levels if lv.textures == self.texture_count]
            ),
        }

    # UI -----------------------------------------------------------------------------

    def _build_ui(self):
        self.state.update(
            {
                "running": True,
                "n_points": f"{self.cloud.n_points:,}",
                "n_points_pending": None,
                "payload_mb": "-",
                "ups": "-",
                "frame_ms": "-",
                "overhead_ms": "-",
                "overhead_mbs": "-",
                "stages": [],
                "levels": [],
                "textures": self.texture_count,
                "fit": None,
            }
        )
        # Frame stats from the canvas, once a second: only the panel needs them, not the server.
        self.state.client_only("stats")
        self.state.stats = {"fps": 0, "frames": 0, "info": ""}

        with DivLayout(self.server) as self.ui:
            self.ui.root.style = "height:100vh;position:relative;"
            client.Style(CSS)

            with html.Div(style="position:absolute;inset:0;display:flex;"):
                with html.Div(style="flex:1;min-width:0;position:relative;"):
                    view = rca.RemoteControlledArea(
                        display="shared-texture",
                        event_throttle_ms=10,
                        stats="stats = $event",
                    )
                    self.view_handler = view.create_electron_handler(
                        self.render_window,
                        target_fps=self.target_fps,
                        texture_count=self.texture_count,
                        before_render=self.before_render,
                    )
                if self.second_render_window:
                    with html.Div(
                        style="flex:1;min-width:0;position:relative;border-left:1px solid #333;"
                    ):
                        second_view = rca.RemoteControlledArea(
                            display="shared-texture",
                            event_throttle_ms=10,
                        )
                        self.second_view_handler = second_view.create_electron_handler(
                            self.second_render_window,
                            target_fps=self.target_fps,
                            texture_count=self.texture_count,
                            before_render=self.before_render_second,
                        )

            with html.Div(classes="bench", style=PANEL_STYLE):
                with html.Div(style="margin-bottom:0.5rem;"):
                    html.Button(
                        "{{ running ? 'Pause' : 'Resume' }}",
                        click=self.toggle_running,
                    )
                    html.Button(f"−{self.step_size:,}", click=self.remove_points)
                    html.Button(f"+{self.step_size:,}", click=self.add_points)
                    html.Span("textures:", classes="muted", style="margin:0 6px;")
                    for n in range(1, 5):
                        html.Button(
                            str(n),
                            click=f"textures = {n}",
                            style=(
                                "{ fontWeight: textures === %d ? 'bold' : 'normal' }"
                                % n,
                            ),
                        )
                    html.Span(
                        "→ {{ n_points_pending.toLocaleString() }} on next update",
                        v_if="n_points_pending",
                        classes="muted",
                    )

                with html.Div(style="display:flex;gap:1.5rem;margin-bottom:0.5rem;"):
                    with html.Div():
                        html.Div("{{ stats.fps }} fps", classes="big")
                        html.Div("client render rate", classes="muted")
                    with html.Div():
                        html.Div("{{ ups }} updates/s", classes="big")
                        html.Div("{{ frame_ms }} ms / update", classes="muted")
                    with html.Div():
                        html.Div("{{ n_points }} pts", classes="big")
                        html.Div("{{ payload_mb }} MB / update", classes="muted")

                html.Div(
                    "Overhead (update − app work): {{ overhead_ms }} ms "
                    "→ {{ overhead_mbs }} MB/s"
                    f", capped at {self.target_fps:g} updates/s"
                )

                with html.Table():
                    with html.Tr():
                        html.Th("stage")
                        html.Th("ms")
                        html.Th("%")
                        html.Th("", style="width:35%;")
                    with html.Tr(v_for="s in stages", key="s.name"):
                        with html.Td(classes="stage"):
                            html.Span("{{ s.name }} ")
                            html.Span("({{ s.help }})", classes="muted")
                        html.Td("{{ s.ms }}")
                        html.Td("{{ s.pct }}")
                        with html.Td():
                            html.Div(classes="bar", style=("{ width: s.pct + '%' }",))

                html.Div(
                    f"Per point count (first {WARMUP_FRAMES} updates skipped)",
                    classes="muted",
                )
                with html.Table():
                    with html.Tr():
                        html.Th("points")
                        html.Th("textures")
                        html.Th("updates")
                        html.Th("ms")
                        html.Th("updates/s")
                        html.Th("MB/s")
                    with html.Tr(
                        v_for="l in levels", key="l.points + '/' + l.textures"
                    ):
                        html.Td("{{ l.points }}")
                        html.Td("{{ l.textures }}")
                        html.Td("{{ l.frames }}")
                        html.Td("{{ l.ms }}")
                        html.Td("{{ l.ups }}")
                        html.Td("{{ l.mbs }}")

                with html.Div(v_if="fit"):
                    html.Div(
                        "Fit with {{ textures }} textures: {{ fit.fixed_ms }} ms fixed "
                        "+ {{ fit.ns_per_point }} ns/point"
                    )
                    html.Div(
                        "Realtime capacity: {{ fit.at30 }} pts @ 30 updates/s, "
                        "{{ fit.at60 }} pts @ 60 updates/s",
                        classes="big",
                        style="font-size:14px;",
                    )
                html.Div(
                    "Add points at least twice to fit the per-point cost",
                    v_else=True,
                    classes="muted",
                )


if __name__ == "__main__":
    PointCloudBenchmark().server.start()
