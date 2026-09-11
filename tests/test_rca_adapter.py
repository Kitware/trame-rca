import copy
import pytest
from unittest.mock import MagicMock
from trame_rca.view_adapter import RcaViewAdapter


@pytest.fixture
def adapter():
    window_mock = MagicMock()
    scheduler_mock = MagicMock()
    scheduler_mock.rca = window_mock

    adapter_inst = RcaViewAdapter(
        window=window_mock, name="test_area", scheduler=scheduler_mock
    )
    adapter_inst.update_size("test", {"w": 1000, "h": 800, "p": 2})
    return adapter_inst


def test_update_size(adapter: RcaViewAdapter):
    adapter.update_size("origin", {"w": 500, "h": 400, "p": 1})

    assert adapter._current_size == (500, 400, 1)
    assert adapter.image_size == (500, 400)
    assert adapter.scale_factor == 1.0
    adapter._rca.process_resize_event.assert_called_with(500, 400)


def test_update_size_enforce_minimum(adapter: RcaViewAdapter):
    adapter.update_size("origin", {"w": 2, "h": 5, "p": 1})

    assert adapter._current_size == (10, 10, 1)
    assert adapter.image_size == (10, 10)
    adapter._rca.process_resize_event.assert_called_with(10, 10)


def test_update_size_pixel_ratio_and_scale(adapter: RcaViewAdapter):
    adapter.update_size("origin", {"w": 500, "h": 400, "p": 2})

    assert adapter.scale_factor == 2.0
    assert adapter.image_size == (1000, 800)
    adapter._rca.process_resize_event.assert_called_with(1000, 800)

    adapter.scale = 0.5

    assert adapter.scale_factor == 1.0
    assert adapter.image_size == (500, 400)
    adapter._rca.process_resize_event.assert_called_with(500, 400)


def test_update_size_max_pixel_count_capping(adapter: RcaViewAdapter):
    adapter.update_size("origin", {"w": 1000, "h": 1000, "p": 2})
    adapter._rca.process_resize_event.assert_called_with(2000, 2000)

    adapter.max_pixel_count = 1_000_000

    assert adapter.scale_factor == 1.0
    assert adapter.image_size == (1000, 1000)
    adapter._rca.process_resize_event.assert_called_with(1000, 1000)


def test_update_size_max_pixel_count_no_op_when_under_cap(adapter: RcaViewAdapter):
    adapter.max_pixel_count = 5_000_000
    adapter.update_size("origin", {"w": 500, "h": 400, "p": 2})

    assert adapter.scale_factor == 2.0
    assert adapter.image_size == (1000, 800)
    adapter._rca.process_resize_event.assert_called_with(1000, 800)


def test_update_size_schedules_render(adapter: RcaViewAdapter):
    adapter.update_size("origin", {"w": 400, "h": 300, "p": 1})
    adapter._scheduler.schedule_render.assert_called()


def test_scale_event_mouse_move(adapter: RcaViewAdapter):
    event = {
        "type": "MouseMove",
        "x": 100,
        "y": 200,
        "w": 1000,
        "h": 800,
    }

    scaled = adapter._scale_event(dict(event))
    scale_factor = adapter.scale_factor

    assert scale_factor == 2
    assert scaled["x"] == event["x"] * scale_factor
    assert scaled["y"] == event["y"] * scale_factor
    assert scaled["w"] == event["w"] * scale_factor
    assert scaled["h"] == event["h"] * scale_factor


def test_scale_event_custom_scale(adapter: RcaViewAdapter):
    adapter.scale = 0.5
    event = {
        "type": "MouseMove",
        "x": 100,
        "y": 200,
        "w": 1000,
        "h": 800,
    }

    scaled = adapter._scale_event(dict(event))
    scale_factor = adapter.scale_factor

    assert scale_factor == 1
    assert scaled["x"] == event["x"]
    assert scaled["y"] == event["y"]
    assert scaled["w"] == event["w"]
    assert scaled["h"] == event["h"]


def test_scale_event_multi_touch(adapter: RcaViewAdapter):
    event = {
        "type": "Pinch",
        "w": 1000,
        "h": 800,
        "positions": {
            "0": {"x": 100, "y": 150},
            "1": {"x": 200, "y": 250},
        },
    }

    scaled = adapter._scale_event(copy.deepcopy(event))
    scale_factor = adapter.scale_factor

    assert scale_factor == 2
    assert scaled["positions"]["0"]["x"] == event["positions"]["0"]["x"] * scale_factor
    assert scaled["positions"]["0"]["y"] == event["positions"]["0"]["y"] * scale_factor
    assert scaled["positions"]["1"]["x"] == event["positions"]["1"]["x"] * scale_factor
    assert scaled["positions"]["1"]["y"] == event["positions"]["1"]["y"] * scale_factor
    assert scaled["w"] == event["w"] * scale_factor
    assert scaled["h"] == event["h"] * scale_factor


def test_scale_event_translation(adapter: RcaViewAdapter):
    event = {
        "type": "Pan",
        "translation": [-10.5, 20.2],
    }

    scaled = adapter._scale_event(dict(event))
    scale_factor = adapter.scale_factor

    assert scale_factor == 2
    assert scaled["translation"] == [-21.0, 40.0]


def test_scale_event_max_pixel_count_capping(adapter: RcaViewAdapter):
    adapter.max_pixel_count = 800_000

    event = {
        "type": "MouseMove",
        "x": 100,
        "y": 200,
        "w": 1000,
        "h": 800,
    }

    scaled = adapter._scale_event(dict(event))
    scale_factor = adapter.scale_factor

    assert scale_factor == 1
    assert scaled["x"] == event["x"]
    assert scaled["y"] == event["y"]
    assert scaled["w"] == event["w"]
    assert scaled["h"] == event["h"]
