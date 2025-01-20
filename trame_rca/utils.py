from __future__ import annotations

import asyncio
import time
from asyncio import Queue
from concurrent.futures.process import ProcessPoolExecutor
from enum import Enum
from multiprocessing import Pool
from typing import Callable, Optional

from numpy.typing import NDArray
from trame.app import asynchronous
from trame.app.singleton import Singleton
from vtkmodules.util.numpy_support import vtk_to_numpy
from vtkmodules.vtkCommonDataModel import vtkImageData
from vtkmodules.vtkRenderingCore import vtkRenderWindow, vtkWindowToImageFilter
import json

from vtkmodules.vtkWebCore import vtkRemoteInteractionAdapter


class RcaEncoder(str, Enum):
    AVIF = "avif"
    JPEG = "jpeg"
    PNG = "png"
    WEBP = "webp"


def encode_np_img_to_bytes(
    image: NDArray,
    cols: int,
    rows: int,
    img_format: str,
    quality: int,
) -> bytes:
    """
    Numpy implementation of JPEG conversion of the input image.
    Input image should be a numpy array as extracted from the render to image function.
    This method uses numpy arrays as input for compatibility with Python's multiprocessing.
    """
    from io import BytesIO

    import pillow_avif  # noqa
    from PIL import Image

    if not (cols and rows):
        return b""

    image = image.reshape((cols, rows, -1))
    image = image[::-1, :, :]
    fake_file = BytesIO()
    image = Image.fromarray(image)
    image.save(fake_file, img_format, quality=quality)

    return fake_file.getvalue()


def time_now_ms() -> int:
    return int(time.time_ns() / 1000000)


def encode_np_img_to_format_with_meta(
    np_image: NDArray,
    img_format: str,
    cols: int,
    rows: int,
    quality: int,
    now_ms: int,
) -> tuple[bytes, dict, int]:
    meta = dict(
        type=f"image/{img_format}",
        codec="",
        w=cols,
        h=rows,
        st=now_ms,
        key="key",
        quality=quality,
    )

    return (
        encode_np_img_to_bytes(np_image, cols, rows, img_format, quality),
        meta,
        now_ms,
    )


def render_to_image(view) -> vtkImageData:
    """
    Renders the input vtkRenderWindow to a vtkImageData
    """
    view.Render()
    window_to_image = vtkWindowToImageFilter()
    window_to_image.SetInput(view)
    window_to_image.SetScale(1)
    window_to_image.ReadFrontBufferOff()
    window_to_image.ShouldRerenderOff()
    window_to_image.FixBoundaryOn()
    window_to_image.Update()
    return window_to_image.GetOutput()


def vtk_img_to_numpy_array(image_data: vtkImageData) -> tuple[NDArray, int, int]:
    """
    Converts the input vtkImageData to numpy format.
    """
    rows, cols, _ = image_data.GetDimensions()
    scalars = image_data.GetPointData().GetScalars()
    return vtk_to_numpy(scalars), cols, rows


@Singleton
class RcaRenderingPool:
    def __init__(self):
        self.pool = ProcessPoolExecutor()


class RcaRenderScheduler:
    """
    Render scheduler which renders to image and pushes the rendered encoded image to given input callback.
    JPEG image metadata are pushed along the encoded image.

    Renders synchronously to a vtkImageData, encodes to JPEG in a subprocesses and pushes asynchronously.
    Limits the rendering speed given the target FPS.
    Encodes using interactive quality first and then using 100 quality after a few ticks pass.

    Call the close method to properly stop the scheduler before deleting the object.
    """

    def __init__(
        self,
        window: vtkRenderWindow,
        *,
        push_callback: Optional[Callable[[bytes, dict], None]] = None,
        encode_pool: ProcessPoolExecutor = None,
        target_fps: Optional[float] = None,
        interactive_quality: Optional[int] = None,
        still_quality: Optional[int] = None,
        rca_encoder: Optional[RcaEncoder | str] = None,
    ):
        super().__init__()

        if not isinstance(window, vtkRenderWindow):
            raise RuntimeError(
                "Invalid input window. "
                "RcaRenderScheduler is only compatible with VTK RenderWindows."
            )

        self._rca_encoder = rca_encoder or RcaEncoder.JPEG
        self._push_callback = push_callback
        self._window = window
        self._target_fps = target_fps or 30.0
        self._interactive_quality = interactive_quality
        if self._interactive_quality is None:
            self._interactive_quality = 50

        self._still_quality = still_quality
        if self._still_quality is None:
            self._still_quality = 90

        self._n_period_until_still_render = 5

        self._last_push_time_ms = time_now_ms()
        self._request_render_queue = Queue()
        self._render_quality_queue = Queue()
        self._push_queue = Queue()

        self._is_closing = False
        self._encode_pool: Pool = encode_pool or RcaRenderingPool().pool
        self._render_quality_task = asynchronous.create_task(self._render_quality())
        self._render_task = asynchronous.create_task(self._render())
        self._push_task = asynchronous.create_task(self._push())

    def set_push_callback(self, callback: Callable[[bytes, dict], None]):
        self._push_callback = callback

    @property
    def _target_period_s(self):
        return 1.0 / self._target_fps

    async def close(self):
        # Set closing flag to true and push one final render to make sure every task will have a chance to be canceled.
        if self._is_closing:
            return

        self._is_closing = True
        await self.async_schedule_render()
        await asyncio.sleep(1)
        for task in [self._render_task, self._render_quality_task, self._push_task]:
            await task

    def schedule_render(self):
        asynchronous.create_task(self.async_schedule_render())

    async def async_schedule_render(self):
        await self._request_render_queue.put(True)

    async def _render_quality(self):
        while not self._is_closing:
            await self._request_render_queue.get()
            await self._render_quality_queue.put(self._interactive_quality)
            await self._schedule_still_render()

    async def _schedule_still_render(self):
        await self._empty_request_render_queue()
        for _ in range(self._n_period_until_still_render):
            await asyncio.sleep(self._target_period_s)
            if not self._request_render_queue.empty():
                return
        await self._render_quality_queue.put(self._still_quality)

    async def _empty_request_render_queue(self):
        while not self._request_render_queue.empty():
            await self._request_render_queue.get()

    async def _render(self):
        while not self._is_closing:
            quality = await self._render_quality_queue.get()
            now_ms = time_now_ms()
            np_img, cols, rows = vtk_img_to_numpy_array(render_to_image(self._window))
            await self._push_queue.put(
                asyncio.wrap_future(
                    self._encode_pool.submit(
                        encode_np_img_to_format_with_meta,
                        np_img,
                        self._rca_encoder,
                        cols,
                        rows,
                        quality,
                        now_ms,
                    )
                )
            )

    async def _push(self):
        while not self._is_closing:
            result = await self._push_queue.get()
            img, meta, m_time = await result
            if m_time >= self._last_push_time_ms and self._push_callback is not None:
                self._last_push_time_ms = m_time
                self._push_callback(img, meta)


class RcaViewAdapter:
    """
    Adapter for Remote Control Area.
    Uses an RCA render scheduler to serialize vtk RenderWindow to the RCA.
    """

    def __init__(
        self,
        window: vtkRenderWindow,
        scheduler: RcaRenderScheduler,
        name: str,
        *,
        do_schedule_render_on_interaction=True,
    ):
        self._scheduler = scheduler
        self._scheduler.set_push_callback(self.push)
        self._window = window
        self.area_name = name
        self.streamer = None
        self._prev_data_m_time = None

        self._iren = self._window.GetInteractor()
        self._iren.EnableRenderOff()
        self._window.ShowWindowOff()
        self._press_set = set()
        self._do_render_on_interaction = do_schedule_render_on_interaction

    def set_streamer(self, stream_manager):
        self.streamer = stream_manager

    def update_size(self, origin, size):
        # Resize to one pixel min to avoid rendering problems in VTK
        width = max(1, int(size.get("w", 300)))
        height = max(1, int(size.get("h", 300)))
        self._iren.UpdateSize(width, height)
        self._scheduler.schedule_render()

    def push(self, content, meta: dict):
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
        event_type = event["type"]
        if event_type in ["StartInteractionEvent", "EndInteractionEvent"]:
            return

        if self.do_discard_extra_release_event(event):
            return

        vtkRemoteInteractionAdapter.ProcessEvent(self._iren, json.dumps(event))
        if self._do_render_on_interaction:
            self._scheduler.schedule_render()
