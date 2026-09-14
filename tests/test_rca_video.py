import asyncio
import os
import sys
import time
from unittest.mock import MagicMock


import pytest
from trame_rca.encoders import RcaVideoEncoder
from trame_rca.encoders.video_encoder import available_codecs
from trame_rca.protocol import StreamManager
from trame_rca.schedulers import RcaVideoRenderScheduler
from trame_rca.view_adapter import RcaViewAdapter

if os.environ.get("CI") is not None and sys.platform != "linux":
    pytest.skip(
        "Rendering tests are disabled on CI for non Linux platforms.",
        allow_module_level=True,
    )


def test_a_view_can_be_encoded_to_format(a_render_window, tmpdir):
    a_mock_push = MagicMock()
    rca_encoder = RcaVideoEncoder(a_render_window, a_mock_push)

    rca_encoder.encode(a_render_window)

    time.sleep(1)
    a_mock_push.assert_called_once()

    args, _ = a_mock_push.call_args
    img_bytes = args[0]
    assert isinstance(img_bytes, (bytes, bytearray))
    assert len(img_bytes) > 0


@pytest.mark.asyncio
async def test_reset_does_not_duplicate_encoded_chunk_observer(a_render_window):
    a_mock_push = MagicMock()
    rca_encoder = RcaVideoEncoder(a_render_window, push_callback=a_mock_push)

    for _ in range(5):
        rca_encoder.reset(a_render_window)

    rca_encoder.encode(a_render_window)

    try:
        await asyncio.sleep(1)
        assert a_mock_push.call_count == 1
    finally:
        rca_encoder.release()


@pytest.mark.asyncio
async def test_if_no_render_is_scheduled_doesnt_push(a_render_window):
    a_mock_push = MagicMock()
    scheduler = RcaVideoRenderScheduler(
        a_render_window,
        push_callback=a_mock_push,
        target_fps=20,
        negotiate=False,
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
        negotiate=False,
    )

    try:
        for _ in range(30):
            scheduler.schedule_render()
        await asyncio.sleep(1)
        assert a_mock_push.call_count == 1
    finally:
        await scheduler.close()


@pytest.mark.asyncio
async def test_deferred_scheduler_pushes_nothing_until_negotiated(a_render_window):
    a_mock_push = MagicMock()
    scheduler = RcaVideoRenderScheduler(a_render_window, push_callback=a_mock_push)

    try:
        scheduler.schedule_render()
        await asyncio.sleep(0.5)
        assert a_mock_push.call_count == 0

        server = [c["codec"] for c in scheduler.video_codecs()]
        assert server == [c["codec"] for c in available_codecs()]
        info = scheduler.negotiate_video(server)
        assert info["codec"] and "error" not in info

        await asyncio.sleep(1)
        assert a_mock_push.call_count == 1
    finally:
        await scheduler.close()


@pytest.mark.asyncio
async def test_negotiate_without_common_codec_stays_dark(a_render_window):
    a_mock_push = MagicMock()
    on_codec = MagicMock()
    scheduler = RcaVideoRenderScheduler(
        a_render_window, push_callback=a_mock_push, on_codec_changed=on_codec
    )

    try:
        info = scheduler.negotiate_video(["bogus"])
        assert info["error"] == "no-common-codec"
        on_codec.assert_called_once_with(info)

        scheduler.schedule_render()
        await asyncio.sleep(0.5)
        assert a_mock_push.call_count == 0
    finally:
        await scheduler.close()


@pytest.mark.asyncio
async def test_negotiation_rpc_dispatches_to_area(a_render_window):
    scheduler = RcaVideoRenderScheduler(a_render_window)
    adapter = RcaViewAdapter(scheduler.rca, "area", scheduler=scheduler)
    manager = StreamManager()
    manager.register_area(adapter)

    try:
        codecs = manager.video_codecs("area")
        assert codecs == available_codecs()
        assert manager.video_codecs("missing") == []
        assert manager.negotiate_video("missing", [])["error"] == "unknown-area"

        info = manager.negotiate_video("area", [c["codec"] for c in codecs])
        assert info["codec"] == scheduler._rca_encoder.describe()["codec"]
    finally:
        await scheduler.close()
