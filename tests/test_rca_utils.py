import asyncio
import os
import sys
from multiprocessing import Pool
from pathlib import Path
from unittest.mock import MagicMock

from playwright.sync_api import expect, sync_playwright

import pytest
from PIL import Image
from trame_rca.utils import (
    RcaEncoder,
    RcaRenderScheduler,
    VtkWindow,
    time_now_ms,
)

from vtkmodules.vtkFiltersSources import vtkConeSource
from vtkmodules.vtkRenderingCore import (
    vtkRenderer,
    vtkRenderWindow,
    vtkPolyDataMapper,
    vtkActor,
    vtkRenderWindowInteractor,
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

    renderWindowInteractor = vtkRenderWindowInteractor()
    renderWindowInteractor.SetRenderWindow(render_window)

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
    img, *_ = RcaEncoder(img_format).encode(
        *VtkWindow(a_threed_view).img_cols_rows, 100
    )
    dest_file = Path(tmpdir) / f"test_img.{img_format}"
    dest_file.write_bytes(img)

    assert dest_file.is_file()
    im = Image.open(dest_file)
    assert im


@pytest.mark.parametrize("img_format", ["jpeg", "png", "avif", "webp"])
def test_np_encode_can_be_done_using_multiprocess(a_threed_view, img_format):
    encoder = RcaEncoder(img_format)
    array, cols, rows = VtkWindow(a_threed_view).img_cols_rows
    now_ms = time_now_ms()

    with Pool(1) as p:
        encoded, meta, ret_now_ms = p.apply(
            encoder.encode,
            args=(array, cols, rows, 100),
        )
        assert meta
        assert meta["st"] >= now_ms
        assert ret_now_ms >= now_ms
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


@pytest.mark.parametrize("server_path", ["examples/01_vtk/vtk_cone_simple.py"])
def test_rca_view_is_interactive(server):
    with sync_playwright() as p:
        url = f"http://127.0.0.1:{server.port}/"
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url)

        element = page.locator("img")
        expect(element).to_be_visible()
        initial_img_url = element.get_attribute("src")

        box = element.bounding_box()
        assert box is not None

        page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        page.mouse.down()
        page.mouse.move(box["x"] + box["width"] / 2 + 100, box["y"] + box["height"] / 2)
        page.mouse.up()
        page.wait_for_timeout(100)
        new_img_url = element.get_attribute("src")

        assert initial_img_url != new_img_url


@pytest.mark.parametrize("encoder", [e.value for e in RcaEncoder])
def test_scheduler_is_compatible_with_string_encoder_format(encoder, a_threed_view):
    RcaRenderScheduler(
        a_threed_view,
        push_callback=MagicMock(),
        target_fps=20,
        interactive_quality=0,
        rca_encoder=encoder,
    )
