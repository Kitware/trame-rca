from __future__ import annotations

import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from vtkmodules.vtkRenderingCore import vtkRenderWindow

from trame_rca.rca import RemoteControlledAreaProtocol
from trame_rca.schedulers import RcaImageRenderScheduler, RcaRenderSchedulerProtocol


class RcaViewAdapter:
    """
    Adapter for Remote Control Area.
    Uses an RCA render scheduler to serialize window to the RCA.
    """

    def __init__(
        self,
        window: RemoteControlledAreaProtocol | vtkRenderWindow,
        name: str,
        *,
        scheduler: RcaRenderSchedulerProtocol | None = None,
        do_schedule_render_on_interaction: bool = True,
        **_,
    ):
        if scheduler is None:
            scheduler = RcaImageRenderScheduler(window, push_callback=self.push)

        else:
            if scheduler.rca is not window:
                raise ValueError("window does not match scheduler.rca")
            scheduler.set_push_callback(self.push)

        self._scheduler = scheduler
        self._rca = scheduler.rca

        self.area_name = name
        self.streamer = None
        self._prev_data_m_time = None

        self._press_set = set()
        self._do_render_on_interaction = do_schedule_render_on_interaction
        self._scale = 1
        self._max_pixel_count = 0
        self._current_size = None

    def update_quality(self, interactive=50, still=90) -> None:
        if isinstance(self._scheduler, RcaImageRenderScheduler):
            self._scheduler.update_quality(interactive, still)

    @property
    def target_fps(self) -> float:
        return self._scheduler.target_fps

    @target_fps.setter
    def target_fps(self, value) -> None:
        self._scheduler.target_fps = value

    @property
    def max_pixel_count(self):
        """Use 0 to disable capping of pixel count"""
        return self._max_pixel_count

    @max_pixel_count.setter
    def max_pixel_count(self, value):
        if self._max_pixel_count != value:
            self._max_pixel_count = value

            if self._current_size is not None:
                self.update_size(
                    "self",
                    {
                        "w": self._current_size[0],
                        "h": self._current_size[1],
                        "p": self._current_size[2],
                    },
                )

    @property
    def image_size(self):
        if self._current_size is None:
            return (300, 300)
        size_with_scale = (
            int(self._current_size[0] * self._current_size[2] * self._scale),
            int(self._current_size[1] * self._current_size[2] * self._scale),
        )
        if self._max_pixel_count:
            total = size_with_scale[0] * size_with_scale[1]
            if total > self._max_pixel_count:
                # not perfect but close enough
                rescale = math.sqrt(self._max_pixel_count / total)
                return (
                    int(size_with_scale[0] * rescale),
                    int(size_with_scale[1] * rescale),
                )
        return size_with_scale

    @property
    def scale(self):
        return self._scale

    @scale.setter
    def scale(self, value):
        if self._scale != value:
            self._scale = value

        if self._current_size is not None:
            self.update_size(
                "self",
                {
                    "w": self._current_size[0],
                    "h": self._current_size[1],
                    "p": self._current_size[2],
                },
            )

    def set_streamer(self, stream_manager):
        self.streamer = stream_manager

    def update_size(self, origin, size):
        # Resize to ten pixel min to avoid rendering problems
        width = max(10, int(size.get("w", 300)))
        height = max(10, int(size.get("h", 300)))
        pixel_ratio = size.get("p", 1)
        self._current_size = (width, height, pixel_ratio)
        width = int(width * pixel_ratio * self._scale)
        height = int(height * pixel_ratio * self._scale)

        # Handle count cap
        if self._max_pixel_count:
            total = width * height
            if total > self._max_pixel_count:
                # not perfect but close enough
                rescale = math.sqrt(self._max_pixel_count / total)
                width = int(width * rescale)
                height = int(height * rescale)

        self._rca.process_resize_event(width, height)
        self._scheduler.schedule_render()

    def reset(self):
        """Reset encoder"""
        self._scheduler.reset()

    def push(self, content: bytes, meta: dict):
        if not self.streamer:
            return

        if content is None:
            return

        self.streamer.push_content(self.area_name, meta, content)

    def do_discard_extra_release_event(self, event):
        """
        Ignores mouse release events which have not been preceded by a previous mouse press.
        """
        event_type = event["type"]
        if "Press" in event_type:
            self._press_set.add(event_type)
            return False

        if not event_type.endswith("Release"):
            return False

        press_event = event_type.replace("Release", "Press")
        if press_event in self._press_set:
            self._press_set.remove(press_event)
            return False

        return True

    def on_interaction(self, _, event):
        if self.do_discard_extra_release_event(event):
            return
        self._rca.process_interaction_event(event)
        if self._do_render_on_interaction:
            self._scheduler.schedule_render()

    def schedule_render(self):
        """
        Schedule a render and push to the RCA view when rendering is ready.
        """
        self._scheduler.schedule_render()

    def update(self):
        self.schedule_render()

    async def close(self):
        await self._scheduler.close()
