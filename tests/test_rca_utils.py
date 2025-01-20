import asyncio
import os
import sys
from multiprocessing import Pool
from pathlib import Path
from unittest.mock import MagicMock

from selenium.webdriver import ActionChains
from seleniumbase import SB

import pytest
from PIL import Image
from trame_rca.utils import (
    RcaEncoder,
    RcaRenderScheduler,
    encode_np_img_to_bytes,
    encode_np_img_to_format_with_meta,
    render_to_image,
    time_now_ms,
    vtk_img_to_numpy_array,
)

from vtkmodules.vtkFiltersSources import vtkConeSource
from vtkmodules.vtkRenderingCore import (
    vtkRenderer,
    vtkRenderWindow,
    vtkPolyDataMapper,
    vtkActor,
)


if os.environ.get("CI") is not None and sys.platform != "linux":
    pytest.skip(
        "Rendering tests are disabled on CI for non Linux platforms.",
        allow_module_level=True,
    )


@pytest.fixture()
def a_threed_view():
    renderer = vtkRenderer()
    render_window = vtkRenderWindow()
    render_window.AddRenderer(renderer)

    cone_source = vtkConeSource()
    mapper = vtkPolyDataMapper()
    mapper.SetInputConnection(cone_source.GetOutputPort())
    actor = vtkActor()
    actor.SetMapper(mapper)

    renderer.AddActor(actor)
    renderer.ResetCamera()
    yield render_window


@pytest.mark.parametrize("img_format", ["jpeg", "png", "avif", "webp"])
def test_a_view_can_be_encoded_to_format(a_threed_view, tmpdir, img_format):
    img = encode_np_img_to_bytes(
        *vtk_img_to_numpy_array(render_to_image(a_threed_view)),
        img_format,
        100,
    )
    dest_file = Path(tmpdir).joinpath(f"test_img.{img_format}")
    with open(dest_file, "wb") as f:
        f.write(img)

    assert dest_file.is_file()
    im = Image.open(dest_file)
    assert im


@pytest.mark.parametrize("img_format", ["jpeg", "png", "avif", "webp"])
def test_np_encode_can_be_done_using_multiprocess(a_threed_view, img_format):
    array, cols, rows = vtk_img_to_numpy_array(render_to_image(a_threed_view))
    now_ms = time_now_ms()

    with Pool(1) as p:
        encoded, meta, ret_now_ms = p.apply(
            encode_np_img_to_format_with_meta,
            args=(array, img_format, cols, rows, 100, now_ms),
        )
        assert meta
        assert meta["st"] == now_ms
        assert ret_now_ms == now_ms
        assert encoded


@pytest.mark.asyncio
@pytest.mark.parametrize("encoder", list(RcaEncoder))
async def test_after_request_render_pushes_render_followed_by_still_render(
    encoder,
    a_threed_view,
):
    a_mock_push = MagicMock()
    scheduler = RcaRenderScheduler(
        a_threed_view,
        push_callback=a_mock_push,
        target_fps=20,
        interactive_quality=0,
        still_quality=100,
        rca_encoder=encoder,
    )

    try:
        await scheduler.async_schedule_render()
        await asyncio.sleep(2)
        assert a_mock_push.call_count == 2
        assert a_mock_push.call_args_list[0].args[1]["quality"] == 0
        assert a_mock_push.call_args_list[1].args[1]["quality"] == 100
    finally:
        await scheduler.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("encoder", list(RcaEncoder))
async def test_when_schedule_render_called_before_still_render_keeps_animating(
    encoder,
    a_threed_view,
):
    a_mock_push = MagicMock()
    scheduler = RcaRenderScheduler(
        a_threed_view,
        push_callback=a_mock_push,
        target_fps=20,
        interactive_quality=0,
        rca_encoder=encoder,
    )

    try:
        await scheduler.async_schedule_render()
        await asyncio.sleep(0.1)
        await scheduler.async_schedule_render()
        await asyncio.sleep(0.1)
        await scheduler.async_schedule_render()
        await asyncio.sleep(2)
        assert a_mock_push.call_count == 4
    finally:
        await scheduler.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("encoder", list(RcaEncoder))
async def test_if_no_render_is_scheduled_doesnt_push(
    encoder,
    a_threed_view,
):
    a_mock_push = MagicMock()
    scheduler = RcaRenderScheduler(
        a_threed_view,
        push_callback=a_mock_push,
        target_fps=20,
        interactive_quality=0,
        rca_encoder=encoder,
    )

    try:
        await asyncio.sleep(2)
        assert a_mock_push.call_count == 0
    finally:
        await scheduler.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("encoder", list(RcaEncoder))
async def test_groups_close_request_render_together(
    encoder,
    a_threed_view,
):
    a_mock_push = MagicMock()
    scheduler = RcaRenderScheduler(
        a_threed_view,
        push_callback=a_mock_push,
        target_fps=20,
        interactive_quality=0,
        rca_encoder=encoder,
    )

    try:
        for _ in range(30):
            await scheduler.async_schedule_render()
        await asyncio.sleep(2)
        assert a_mock_push.call_count == 2
    finally:
        await scheduler.close()


@pytest.mark.parametrize("server_path", ["examples/00_cone/app.py"])
def test_rca_view_is_interactive(server):
    with SB() as sb:
        assert server.port

        url = f"http://127.0.0.1:{server.port}/"
        sb.open(url)

        element = sb.find_element("img")
        initial_img_url = element.get_attribute("src")

        ActionChains(sb.driver).move_to_element(element).perform()
        ActionChains(sb.driver).click_and_hold(element).move_by_offset(
            100, 0
        ).release().perform()

        # Expect image to have been updated following user action
        new_img_url = element.get_attribute("src")
        assert initial_img_url != new_img_url
