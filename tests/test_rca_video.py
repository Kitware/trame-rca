import asyncio
import os
import sys
import time
from unittest.mock import MagicMock


import pytest
from trame_rca.encoders import RcaVideoEncoder
from trame_rca.schedulers import RcaVideoRenderScheduler


if os.environ.get("CI") is not None and sys.platform != "linux":
    pytest.skip(
        "Rendering tests are disabled on CI for non Linux platforms.",
        allow_module_level=True,
    )


def test_a_view_can_be_encoded_to_format(a_render_window, tmpdir):
    rca_encoder = RcaVideoEncoder(a_render_window)
    a_mock_push = MagicMock()

    rca_encoder.set_push_callback(a_mock_push)
    rca_encoder.encode(a_render_window)

    time.sleep(1)
    a_mock_push.assert_called_once()

    args, _ = a_mock_push.call_args
    img_bytes = args[0]
    assert isinstance(img_bytes, (bytes, bytearray))
    assert len(img_bytes) > 0


@pytest.mark.asyncio
async def test_if_no_render_is_scheduled_doesnt_push(a_render_window):
    a_mock_push = MagicMock()
    scheduler = RcaVideoRenderScheduler(
        a_render_window,
        push_callback=a_mock_push,
        target_fps=20,
    )

    try:
        await asyncio.sleep(1)
        assert a_mock_push.call_count == 0
    finally:
        await scheduler.close()


@pytest.mark.asyncio
async def test_groups_close_request_render_together(a_render_window):
    a_mock_push = MagicMock()
    scheduler = RcaVideoRenderScheduler(
        a_render_window,
        push_callback=a_mock_push,
        target_fps=30,
    )

    try:
        for _ in range(30):
            scheduler.schedule_render()
        await asyncio.sleep(1)
        assert a_mock_push.call_count == 1
    finally:
        await scheduler.close()
