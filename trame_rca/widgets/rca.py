from trame_client.widgets.core import AbstractElement
from .. import module


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
        ]


class DisplayArea(HtmlElement):
    def __init__(self, **kwargs):
        super().__init__(
            "display-area",
            **kwargs,
        )
        self._attr_names += [
            "name",
            "origin",
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
        ]


class ImageDisplayArea(HtmlElement):
    def __init__(self, **kwargs):
        super().__init__(
            "image-display-area",
            **kwargs,
        )
        self._attr_names += ["name", "origin", ("pool_size", "poolSize")]


class VideoDisplayArea(HtmlElement):
    def __init__(self, **kwargs):
        super().__init__(
            "video-display-area",
            **kwargs,
        )
        self._attr_names += [
            "name",
            "origin",
        ]
