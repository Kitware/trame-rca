import asyncio
import os
import sys
import time
from multiprocessing import Pool
from pathlib import Path
from unittest.mock import MagicMock


import pytest
from PIL import Image
from trame_rca.encoders import RcaImageEncoder
from trame_rca.schedulers import RcaImageRenderScheduler
from trame_rca.rca import VtkRemoteControlledArea


if os.environ.get("CI") is not None and sys.platform != "linux":
    pytest.skip(
        "Rendering tests are disabled on CI for non Linux platforms.",
        allow_module_level=True,
    )


@pytest.mark.parametrize("img_format", ["jpeg", "png", "avif", "webp"])
def test_a_view_can_be_encoded_to_format(a_render_window, tmpdir, img_format):
    img, *_ = RcaImageEncoder(img_format).encode(
        *VtkRemoteControlledArea(a_render_window).img_cols_rows, 100
    )
    dest_file = Path(tmpdir) / f"test_img.{img_format}"
    dest_file.write_bytes(img)

    assert dest_file.is_file()
    im = Image.open(dest_file)
    assert im


@pytest.mark.parametrize("img_format", ["jpeg", "png", "avif", "webp"])
def test_np_encode_can_be_done_using_multiprocess(a_render_window, img_format):
    encoder = RcaImageEncoder(img_format)
    array, cols, rows = VtkRemoteControlledArea(a_render_window).img_cols_rows
    now_ms = int(time.time_ns() / 1000000)

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
@pytest.mark.parametrize("encoder", list(RcaImageEncoder))
async def test_after_request_render_pushes_render_followed_by_still_render(
    encoder,
    a_render_window,
):
    a_mock_push = MagicMock()
    scheduler = RcaImageRenderScheduler(
        a_render_window,
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
@pytest.mark.parametrize("encoder", list(RcaImageEncoder))
async def test_when_schedule_render_called_before_still_render_keeps_animating(
    encoder,
    a_render_window,
):
    a_mock_push = MagicMock()
    scheduler = RcaImageRenderScheduler(
        a_render_window,
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
@pytest.mark.parametrize("encoder", list(RcaImageEncoder))
async def test_if_no_render_is_scheduled_doesnt_push(
    encoder,
    a_render_window,
):
    a_mock_push = MagicMock()
    scheduler = RcaImageRenderScheduler(
        a_render_window,
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
@pytest.mark.parametrize("encoder", list(RcaImageEncoder))
async def test_groups_close_request_render_together(
    encoder,
    a_render_window,
):
    a_mock_push = MagicMock()
    scheduler = RcaImageRenderScheduler(
        a_render_window,
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


@pytest.mark.parametrize("encoder", list(RcaImageEncoder))
def test_scheduler_is_compatible_with_string_encoder_format(encoder, a_render_window):
    RcaImageRenderScheduler(
        a_render_window,
        push_callback=MagicMock(),
        target_fps=20,
        interactive_quality=0,
        rca_encoder=encoder,
    )
