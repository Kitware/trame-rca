"""RCA Widgets support both vue2 and vue3."""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING, Callable
from weakref import WeakKeyDictionary, WeakValueDictionary

from trame_client.widgets.core import AbstractElement

if TYPE_CHECKING:
    from vtkmodules.vtkRenderingCore import vtkRenderWindow

from trame_rca.encoders import RcaImageEncoder
from trame_rca.rca import RemoteControlledAreaProtocol, window_wrapper
from trame_rca.schedulers import RcaImageRenderScheduler
from trame_rca.utils import RcaViewAdapter

from .. import module

__all__ = [
    "RemoteControlledArea",
    "DisplayArea",
    "StatisticsDisplay",
    "ImageDisplayArea",
    "MediaSourceDisplayArea",
    "VideoDecoderDisplayArea",
    "RawImageDisplayArea",
    "SharedTextureDisplayArea",
    "ImageStream",
    "ImageRegion",
]


class HtmlElement(AbstractElement):
    def __init__(self, _elem_name, children=None, **kwargs):
        super().__init__(_elem_name, children, **kwargs)
        if self.server:
            self.server.enable_module(module)


# Expose your vue component(s)
class RemoteControlledArea(HtmlElement):
    _next_id = 0

    def __init__(self, name: str | None = None, display: str = "image", **kwargs):
        self._drop_frame_limit = 9999  # no limit / aka no frame drop
        super().__init__(
            "remote-controlled-area",
            name=name or f"trame_rca_{RemoteControlledArea._next_id}",
            display=display,
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
            "monitor",
            ("resize_throttle_ms", "resizeThrottleMs"),
        ]
        self._event_names += [
            "stats",
        ]

        self._handlers = []

        if self.server.running:
            self._on_ready()
        else:
            self.ctrl.on_server_ready.add(self._on_ready)

    def set_drop_frames_pending_network_limit(self, limit: int):
        """
        To prevent network backing up, it can be good to provide
        a limit of 5 when using an encoder that can support it.
        The provided value can not be less than 1.

        Image encoder support it but video encoder may not.
        """
        limit = int(limit)
        if limit < 1:
            msg = "The limit can not be smaller than 1"
            raise ValueError(msg)
        self._drop_frame_limit = limit

        if self.server.running:
            self._on_ready()

    def add_view_handler(self, view_handler):
        if view_handler in self._handlers:
            return

        if self.server.running:
            self.server.root_server.controller.rc_area_register(view_handler)
        else:
            self._handlers.append(view_handler)

    def create_view_handler(
        self,
        window: RemoteControlledAreaProtocol | vtkRenderWindow,
        encoder: RcaImageEncoder | str | None = None,
        target_fps: float = 30.0,
        interactive_quality: int = 60,
        still_quality: int = 90,
        on_video_codec: Callable[[dict], None] | None = None,
    ):
        """
        ``on_video_codec`` is called with the negotiated encoder description
        (``codec``, ``backend``, ``hardware``, ``label``; or ``error``) for video displays.
        """
        scheduler = None
        window = window_wrapper(window)
        if self.display == "video-decoder":
            from trame_rca.rca import VtkRemoteControlledArea
            from trame_rca.schedulers import RcaVideoRenderScheduler

            if not isinstance(window, VtkRemoteControlledArea):
                raise TypeError("Only VTK backends are supported by video decoder")
            scheduler = RcaVideoRenderScheduler(
                window, target_fps=target_fps, on_codec_changed=on_video_codec
            )

        elif encoder:
            scheduler = RcaImageRenderScheduler(
                window,
                target_fps=target_fps,
                interactive_quality=interactive_quality,
                still_quality=still_quality,
                rca_encoder=encoder,
            )

        view_handler = RcaViewAdapter(window, self.name, scheduler=scheduler)
        self.add_view_handler(view_handler)
        return view_handler

    def create_electron_handler(
        self,
        window: RemoteControlledAreaProtocol | vtkRenderWindow,
        target_fps: float = 60.0,
        before_render: Callable[[], None] | None = None,
        on_disconnect: Callable[[], None] | None = None,
    ):
        """
        Render ``render_window`` into a texture shared with the Electron app that
        started this server (see @Kitware/trame-rca-electron), for ``display="shared-texture"``.

        Call ``trame_rca.electron.init_vtk()`` before creating ``render_window``.
        ``before_render`` is called before every frame and may schedule another render,
        e.g. to animate. ``on_disconnect`` is called when Electron goes away and
        defaults to stopping the server.
        """
        from trame.app import asynchronous

        from trame_rca.electron import emp_port, server_url
        from trame_rca.schedulers import RcaSharedTextureRenderScheduler

        if self.display != "shared-texture":
            raise ValueError(
                "create_electron_handler needs a RemoteControlledArea with "
                f'display="shared-texture", not "{self.display}"'
            )

        if on_disconnect is None:

            def on_disconnect():
                asynchronous.create_task(self.server.stop())

        rca_protocol = window_wrapper(window)
        scheduler = RcaSharedTextureRenderScheduler(
            rca_protocol,
            emp_port(self.server),
            target_fps=target_fps,
            on_disconnect=on_disconnect,
            before_render=before_render,
        )

        def start(**_):
            scheduler.start(url=server_url(self.server))

        if self.server.running:
            start()
        else:
            self.ctrl.on_server_ready.add(start)

        view_handler = RcaViewAdapter(scheduler.rca, self.name, scheduler=scheduler)
        self.add_view_handler(view_handler)
        return view_handler

    def create_vtk_handler(
        self,
        render_window: vtkRenderWindow,
        encoder: RcaImageEncoder | str | None = None,
        target_fps: float = 30.0,
        interactive_quality: int = 60,
        still_quality: int = 90,
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
        self.server.protocol_call("trame.rca.drop", self.name, self._drop_frame_limit)

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
            "monitor",
        ]
        self._event_names += [
            "stats",
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
            "monitor",
        ]
        self._event_names += [
            "stats",
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


class SharedTextureDisplayArea(HtmlElement):
    """The canvas trame-rca-electron draws the shared texture into, once a frame."""

    def __init__(self, **kwargs):
        super().__init__(
            "shared-texture-display-area",
            **kwargs,
        )
        self._event_names += [
            "stats",
        ]


class ImageStream(HtmlElement):
    ID = 0
    NAMES = WeakKeyDictionary()
    HANDLERS = WeakValueDictionary()

    @classmethod
    def _next_name(cls):
        cls.ID += 1
        return f"rca_image_stream_{cls.ID}"

    @classmethod
    def _get_rw_name(cls, render_window):
        if render_window in cls.NAMES:
            return cls.NAMES[render_window]
        name = cls._next_name()
        cls.NAMES[render_window] = name
        return name

    @classmethod
    def _get_rw_handler(
        cls,
        render_window,
        encoder="turbo-jpeg",
        target_fps=30,
        interactive_quality=80,
        still_quality=95,
        **kwargs,
    ):
        name = cls._get_rw_name(render_window)
        if name in cls.HANDLERS:
            return cls.HANDLERS[name]

        scheduler = RcaImageRenderScheduler(
            render_window,
            target_fps=target_fps,
            interactive_quality=interactive_quality,
            still_quality=still_quality,
            rca_encoder=encoder,
            **kwargs,
        )
        handler = RcaViewAdapter(
            scheduler.rca,
            name,
            scheduler=scheduler,
            **kwargs,
        )
        cls.HANDLERS[render_window] = handler
        return handler

    def __init__(self, render_window, image="image", encoder="turbo-jpeg", **kwargs):
        super().__init__("image-stream", **kwargs)
        self._attr_names += [
            "name",
            ("pool_size", "poolSize"),
        ]
        self.render_window = render_window
        self.name = self._get_rw_name(render_window)
        self.handler = self._get_rw_handler(render_window, encoder)

        #
        if self.server.running:
            self.server.root_server.controller.rc_area_register(self.handler)
        else:
            self.ctrl.on_server_ready.add(self._on_ready)

        self._attributes["slot"] = f'v-slot="{{ {image}: image }}"'

    def update(self):
        self.handler.update()

    def _on_ready(self, **_):
        for handler in self.HANDLERS.values():
            self.server.root_server.controller.rc_area_register(handler)


class ImageRegion(HtmlElement):
    def __init__(self, **kwargs):
        super().__init__("image-region", **kwargs)
        self._attr_names += [
            "bounds",
            ("enable_interaction", "enableInteraction"),
            ("send_mouse_move", "sendMouseMove"),
            ("send_mouse_click", "sendMouseClick"),
            ("event_throttle_ms", "eventThrottleMs"),
        ]
        # Vue emits a `size` event, React exposes `onSize`
        if "vue" in self.server.client_type:
            self._event_names += ["size"]
        else:
            self._event_names += [("size", "onSize")]
