"""RCA Widgets support both vue2 and vue3."""

from trame_client.widgets.core import AbstractElement
from trame_rca.utils import RcaViewAdapter, RcaRenderScheduler
import warnings
from .. import module

__all__ = [
    "RemoteControlledArea",
    "DisplayArea",
    "StatisticsDisplay",
    "ImageDisplayArea",
    "MediaSourceDisplayArea",
    "VideoDecoderDisplayArea",
    "RawImageDisplayArea",
]


class HtmlElement(AbstractElement):
    def __init__(self, _elem_name, children=None, **kwargs):
        super().__init__(_elem_name, children, **kwargs)
        if self.server:
            self.server.enable_module(module)


# Expose your vue component(s)
class RemoteControlledArea(HtmlElement):
    _next_id = 0

    def __init__(self, **kwargs):
        super().__init__(
            "remote-controlled-area",
            **kwargs,
        )
        RemoteControlledArea._next_id += 1
        self._attr_names += [
            "name",
            "origin",
            "display",
            ("image_style", "imageStyle"),
            ("send_mouse_move", "sendMouseMove"),
            ("event_throttle_ms", "eventThrottleMs"),
        ]

        self.name = kwargs.get("name") or f"trame_rca_{RemoteControlledArea._next_id}"
        self._handlers = []
        self.ctrl.on_server_ready.add(self._on_ready)

    def add_view_handler(self, view_handler):
        if view_handler in self._handlers:
            return

        if self.server.running:
            self.server.root_server.controller.rc_area_register(view_handler)
        else:
            self._handlers.append(view_handler)

    def create_view_handler(
        self,
        render_window,
        encoder=None,
        target_fps=30,
        interactive_quality=60,
        still_quality=90,
    ):
        scheduler = None
        if encoder:
            scheduler = RcaRenderScheduler(
                render_window,
                target_fps=target_fps,
                interactive_quality=interactive_quality,
                still_quality=still_quality,
                rca_encoder=encoder,
            )
        view_handler = RcaViewAdapter(render_window, self.name, scheduler=scheduler)
        self.add_view_handler(view_handler)
        return view_handler

    def create_vtk_handler(
        self,
        render_window,
        encoder=None,
        target_fps=30,
        interactive_quality=60,
        still_quality=90,
    ):
        warnings.warn(
            "'create_vtk_handler' will be deprecated in a future version. "
            "Please use 'create_view_handler' instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.create_view_handler(
            render_window, encoder, target_fps, interactive_quality, still_quality
        )

    def _on_ready(self, **_):
        while self._handlers:
            handler = self._handlers.pop()
            self.server.root_server.controller.rc_area_register(handler)


class DisplayArea(HtmlElement):
    def __init__(self, **kwargs):
        super().__init__(
            "display-area",
            **kwargs,
        )
        self._attr_names += [
            "name",
            "origin",
            "display",
            ("image_style", "imageStyle"),
        ]


class StatisticsDisplay(HtmlElement):
    def __init__(self, **kwargs):
        super().__init__(
            "statistics-display",
            **kwargs,
        )
        self._attr_names += [
            "name",
            ("fps_delta", "fpsDelta"),
            ("stat_window_size", "statWindowSize"),
            ("history_window_size", "historyWindowSize"),
            ("reset_ms_threshold", "resetMsThreshold"),
            ("ws_topic", "wsLinkTopic"),
            ("packet_decorator", "packetDecorator"),
        ]


class ImageDisplayArea(HtmlElement):
    def __init__(self, **kwargs):
        super().__init__(
            "image-display-area",
            **kwargs,
        )
        self._attr_names += [
            "name",
            "origin",
            ("pool_size", "poolSize"),
            ("image_style", "imageStyle"),
        ]


class MediaSourceDisplayArea(HtmlElement):
    def __init__(self, **kwargs):
        super().__init__(
            "media-source-display-area",
            **kwargs,
        )
        self._attr_names += [
            "name",
            "origin",
        ]


class VideoDecoderDisplayArea(HtmlElement):
    def __init__(self, **kwargs):
        super().__init__(
            "video-decoder-display-area",
            **kwargs,
        )
        self._attr_names += [
            "name",
            "origin",
        ]


class RawImageDisplayArea(HtmlElement):
    def __init__(self, **kwargs):
        super().__init__(
            "raw-image-display-area",
            **kwargs,
        )
        self._attr_names += [
            "name",
            "origin",
            ("image_style", "imageStyle"),
        ]
