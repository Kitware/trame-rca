#!/usr/bin/env -S uv run --script
#
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "trame>=3.10",
#     "trame-rca[turbo,vtkstreaming]",
#     "trame-vuetify",
#     "vtk>=9.6",
# ]
# ///
import asyncio
import time

import vtkmodules.vtkRenderingOpenGL2  # noqa
from trame.app import TrameApp
from trame.decorators import change
from trame.ui.vuetify3 import SinglePageLayout
from trame_common.utils import profiler
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

from trame.widgets import html, vuetify3 as v3

# use this import path to allow -e install for dev
from trame_rca.widgets import rca

v3.enable_lab()
profiler.enable()

DEFAULT_RESOLUTION = 6
DEFAULT_QUANTIZATION = 5  # 0 (high quality) - 63 (low quality)
STATS_STYLES = """
    position: absolute;
    top: 1rem;
    left: 1rem;
    height: 150px;
    width: 300px;
    background: white;
    z-index: 100;
"""

IMAGE = "image"
VIDEO = "video-decoder"


def time_now_ms() -> int:
    return int(time.time_ns() / 1000000)


class ConeApp(TrameApp):
    def __init__(self, server=None):
        super().__init__(server)

        self.server.cli.add_argument("--encoder", default="turbo-jpeg")  # jpeg
        args, _ = self.server.cli.parse_known_args()
        self.encoder = args.encoder
        self.state.video_codec = "unavailable"
        self.state.display_mode = IMAGE
        self.state.stats = None
        self.state.stats_display = ""
        self.max_dt = 0

        self.render_window, self.cone_source = self.setup_vtk()
        self.build_ui()
        # Label the codec from the encoder actually selected by the video scheduler
        # (codec selection is automatic; see RcaVideoEncoder / vtkEncoderFactory).
        self._update_video_codec_label()

    @property
    def view_handler(self):
        if self.state.display_mode == VIDEO:
            return self.video_view_handler
        return self.image_view_handler

    def _update_video_codec_label(self):
        # Reflect the encoder the video scheduler actually selected,
        try:
            from trame_rca.encoders.video_encoder import describe_encoder
        except ImportError:
            self.state.video_codec = "unavailable"
            return
        scheduler = getattr(self.video_view_handler, "_scheduler", None)
        rca_encoder = getattr(scheduler, "_rca_encoder", None)
        self.state.video_codec = describe_encoder(getattr(rca_encoder, "encoder", None))

    def setup_vtk(self):
        renderer = vtkRenderer()
        renderWindow = vtkRenderWindow()
        renderWindow.AddRenderer(renderer)
        renderWindow.OffScreenRenderingOn()

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
        renderWindow.Render()

        return renderWindow, cone_source

    async def _animate(self):
        resolution = 3
        delta = 1
        while self.state.playing:
            resolution += delta
            if resolution > 100 or resolution < 4:
                delta *= -1
            self.cone_source.SetResolution(resolution)
            self.view_handler.update()
            await asyncio.sleep(1 / int(self.state.target_fps))

    @change("stats")
    def on_stats(self, stats, **_):
        if stats is None:
            self.state.stats_display = ""
            return

        now = time_now_ms()
        ds = now - stats.get("st")
        self.max_dt = max(self.max_dt, ds)
        fps = stats.get("fps")
        self.state.stats_display = (
            f"round-trip: {int(ds)} [{self.max_dt}] ms - fps: {fps}"
        )

    @change("playing")
    def on_playing(self, playing, **_):
        if playing:
            asyncio.create_task(self._animate())

    @change("target_fps")
    def on_target_fps(self, target_fps, **_):
        self.image_view_handler.target_fps = target_fps
        self.video_view_handler.target_fps = target_fps
        self.max_dt = 0

    @change("display_mode")
    def on_display_mode(self, **_):
        self.max_dt = 0
        self.state.stats = None
        self.view_handler.update()

    def build_ui(self):
        with SinglePageLayout(self.server, full_height=True) as layout:
            with layout.footer.clear() as footer:
                footer.classes = "text-caption"
                v3.VSpacer()
                html.Span(
                    "Quality ({{quality[0]}}/{{quality[1]}}) - Encoder ({{encoder}})",
                    v_if="display_mode === 'image'",
                )
                html.Span(
                    "Quantization ({{quantization}}/63) - Codec ({{video_codec}})",
                    v_else=True,
                )
                v3.VSpacer()
                footer.add_child("{{ stats_display }}")

            with layout.toolbar.clear():
                v3.VBtn(
                    icon="mdi-stop",
                    v_if=("playing", False),
                    click="playing = !playing",
                )
                v3.VBtn(icon="mdi-play", v_else=True, click="playing = !playing")
                v3.VNumberInput(
                    label="target FPS",
                    v_model=("target_fps", 30),
                    min=[1],
                    max=[200],
                    step=[1],
                    hide_details=True,
                    density="compact",
                    control_variant="hidden",
                    variant="outlined",
                    style="max-width: 100px",
                )
                with v3.VBtnToggle(
                    v_model=("display_mode", IMAGE),
                    mandatory=True,
                    density="compact",
                    classes="mx-2",
                ):
                    v3.VBtn(text="JPEG", value=IMAGE)
                    v3.VBtn(text="Video", value=VIDEO)
                v3.VSpacer()

                v3.VRangeSlider(
                    v_if=(f"display_mode === '{IMAGE}'",),
                    label="Quality",
                    v_model=("quality", [50, 90]),
                    min=10,
                    max=100,
                    step=5,
                    hide_details=True,
                    density="compact",
                    style="max-width: 300px",
                )
                v3.VSlider(
                    v_else=True,
                    label="Quantization",
                    v_model=("quantization", DEFAULT_QUANTIZATION),
                    min=0,  # high quality
                    max=63,  # low quality
                    step=1,
                    hide_details=True,
                    density="compact",
                    style="max-width: 300px",
                )
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
                    image_view = rca.RemoteControlledArea(
                        v_if=(f"display_mode === '{IMAGE}'",),
                        display=IMAGE,
                        monitor="10",
                        stats="stats = $event",
                        event_throttle_ms=("500/target_fps",),
                    )
                    # prevent network backup
                    # => seems to only trigger with fps > 140
                    image_view.set_drop_frames_pending_network_limit(5)
                    self.image_view_handler = image_view.create_view_handler(
                        self.render_window,
                        encoder=self.encoder,
                    )

                    video_view = rca.RemoteControlledArea(
                        v_else=True,
                        display=VIDEO,
                        monitor="10",
                        stats="stats = $event",
                        event_throttle_ms=("500/target_fps",),
                    )
                    self.video_view_handler = video_view.create_view_handler(
                        self.render_window,
                    )

                    with v3.VCard(classes="pa-4 ma-0", style=STATS_STYLES):
                        rca.StatisticsDisplay(
                            v_if=(f"display_mode === '{IMAGE}'",),
                            name=image_view.name,
                            fps_delta=1.5,
                            stat_window_size=10,
                            history_window_size=30,
                            reset_ms_threshold=100,
                        )
                        rca.StatisticsDisplay(
                            v_else=True,
                            name=video_view.name,
                            fps_delta=1.5,
                            stat_window_size=10,
                            history_window_size=30,
                            reset_ms_threshold=100,
                        )

    @change("resolution")
    def update_cone(self, resolution, **kwargs):
        self.cone_source.SetResolution(resolution)
        self.view_handler.update()

    @change("quality")
    def update_quality(self, quality, **_):
        self.image_view_handler.update_quality(*quality)

    @change("quantization")
    def update_quantization(self, quantization, **_):
        # No public API yet: reach into the video scheduler's encoder.
        video_encoder = self.video_view_handler._scheduler._rca_encoder.encoder
        video_encoder.SetQuantizationParameter(int(quantization))
        self.video_view_handler.update()

    def update_reset_resolution(self):
        self.state.resolution = DEFAULT_RESOLUTION


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    app = ConeApp()
    app.server.start()
