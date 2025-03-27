"""RCA Widgets support both vue2 and vue3."""

from trame_client.widgets.core import AbstractElement
from trame_rca.utils import RcaViewAdapter, RcaRenderScheduler
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
    def __init__(self, **kwargs):
        super().__init__(
            "remote-controlled-area",
            **kwargs,
        )
        self._attr_names += [
            "name",
            "origin",
            "display",
            ("send_mouse_move", "sendMouseMove"),
        ]
        self._handlers = []
        self.ctrl.on_server_ready.add(self._on_ready)

    def create_vtk_handler(
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
        self._handlers.append(view_handler)
        return view_handler

    def _on_ready(self, **_):
        for handler in self._handlers:
            self.server.controller.rc_area_register(handler)


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
        self._attr_names += ["name", "origin", ("pool_size", "poolSize")]


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
        ]
