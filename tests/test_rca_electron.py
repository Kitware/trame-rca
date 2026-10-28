import asyncio
import json

import pytest

from trame_rca.electron import PROTOCOL_VERSION
from trame_rca.electron.comm import ProtocolMismatchError, check_protocol
from trame_rca.electron.passports import TexturePassport, texture_passport_class
from trame_rca.schedulers import RcaSharedTextureRenderScheduler

TIMEOUT_S = 10


class FakePassport(TexturePassport):
    released = []

    def to_json(self):
        return {"type": "texture", "width": self.width, "height": self.height}

    def release(self):
        FakePassport.released.append((self.width, self.height))


class FakeEmp:
    """The Electron main process's end of the texture channel."""

    def __init__(self, hello):
        self.hello = hello
        self.connected = asyncio.Event()
        self.reader = self.writer = None

    async def start(self):
        self.server = await asyncio.start_server(self._on_connect, "127.0.0.1", 0)
        return self.server.sockets[0].getsockname()[1]

    async def _on_connect(self, reader, writer):
        self.reader, self.writer = reader, writer
        await self.send(self.hello)
        self.connected.set()

    async def send(self, msg):
        self.writer.write((json.dumps(msg) + "\n").encode())
        await self.writer.drain()

    async def recv(self):
        await asyncio.wait_for(self.connected.wait(), TIMEOUT_S)
        line = await asyncio.wait_for(self.reader.readline(), TIMEOUT_S)
        return json.loads(line)

    def close(self):
        if self.writer:
            self.writer.close()
        self.server.close()


@pytest.fixture
def fake_passport(monkeypatch):
    FakePassport.released = []
    monkeypatch.setattr(
        "trame_rca.schedulers.shared_texture_scheduler.texture_passport_class",
        lambda name: FakePassport,
    )


def test_texture_passport_class():
    with pytest.raises(TypeError):
        texture_passport_class(1)
    with pytest.raises(NotImplementedError):
        texture_passport_class("x11-dmabuf")
    with pytest.raises(ValueError):
        texture_passport_class("nope")


def test_check_protocol():
    check_protocol({"protocol": PROTOCOL_VERSION})
    with pytest.raises(ProtocolMismatchError):
        check_protocol({"protocol": PROTOCOL_VERSION + 1})
    with pytest.raises(ProtocolMismatchError):
        check_protocol({})


@pytest.mark.asyncio
async def test_scheduler_shares_frames(a_render_window, fake_passport):
    emp = FakeEmp({"type": "hello", "protocol": PROTOCOL_VERSION, "passport": "fake"})
    port = await emp.start()
    disconnected = asyncio.Event()
    scheduler = RcaSharedTextureRenderScheduler(
        a_render_window, port, on_disconnect=disconnected.set
    )
    try:
        scheduler.start(url="http://127.0.0.1:1234/")
        assert await emp.recv() == {
            "type": "server_ready",
            "protocol": PROTOCOL_VERSION,
            "url": "http://127.0.0.1:1234/",
        }

        # Nothing to render into until the page reported its size.
        scheduler.schedule_render()
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(emp.reader.readline(), 0.2)

        # As the RcaViewAdapter does when the canvas reports its size.
        scheduler.rca.process_resize_event(300, 300)
        scheduler.schedule_render()
        # One texture per slot of the ring, two by default.
        for slot in range(2):
            assert await emp.recv() == {
                "type": "texture",
                "width": 300,
                "height": 300,
                "view": "default",
                "slot": slot,
                "slots": 2,
            }
        frame = await emp.recv()
        assert frame["type"] == "frame" and frame["seq"] == 0 and frame["slot"] == 0
        assert frame["view"] == "default"
        await emp.send({"type": "frame_done", "view": "default", "seq": 0})

        # A resize makes new textures and releases the old ones.
        scheduler.rca.process_resize_event(200, 100)
        scheduler.schedule_render()
        for slot in range(2):
            assert (await emp.recv())["width"] == 200
        assert FakePassport.released == [(300, 300)] * 2
        frame = await emp.recv()
        assert frame["seq"] == 1 and frame["slot"] == 0

        # Electron going away closes the scheduler.
        emp.close()
        await asyncio.wait_for(disconnected.wait(), TIMEOUT_S)
        assert FakePassport.released == [(300, 300)] * 2 + [(200, 100)] * 2
    finally:
        await scheduler.close()
        emp.close()


@pytest.mark.asyncio
async def test_scheduler_rejects_other_protocol(a_render_window, fake_passport):
    emp = FakeEmp({"type": "hello", "protocol": PROTOCOL_VERSION + 1, "passport": "x"})
    port = await emp.start()
    disconnected = asyncio.Event()
    scheduler = RcaSharedTextureRenderScheduler(
        a_render_window, port, on_disconnect=disconnected.set
    )
    try:
        scheduler.start(url="http://127.0.0.1:1234/")
        await asyncio.wait_for(disconnected.wait(), TIMEOUT_S)
        # Never told Electron the page is ready.
        await asyncio.wait_for(emp.connected.wait(), TIMEOUT_S)
        assert await emp.reader.readline() == b""
    finally:
        await scheduler.close()
        emp.close()


@pytest.mark.asyncio
async def test_scheduler_renders_dropped_frames_again(a_render_window, fake_passport):
    emp = FakeEmp({"type": "hello", "protocol": PROTOCOL_VERSION, "passport": "fake"})
    port = await emp.start()
    scheduler = RcaSharedTextureRenderScheduler(a_render_window, port)
    try:
        scheduler.start(url="http://127.0.0.1:1234/")
        assert (await emp.recv())["type"] == "server_ready"
        scheduler.rca.process_resize_event(300, 300)
        scheduler.schedule_render()
        assert (await emp.recv())["type"] == "texture"
        assert (await emp.recv())["type"] == "texture"
        assert (await emp.recv())["seq"] == 0

        # e.g. sendSharedTexture timed out while the page was loading.
        await emp.send(
            {"type": "frame_done", "view": "default", "seq": 0, "dropped": True}
        )
        frame = await emp.recv()
        assert frame["type"] == "frame" and frame["seq"] == 1
    finally:
        await scheduler.close()
        emp.close()


@pytest.mark.asyncio
async def test_scheduler_texture_ring(a_render_window, fake_passport):
    emp = FakeEmp({"type": "hello", "protocol": PROTOCOL_VERSION, "passport": "fake"})
    port = await emp.start()
    scheduler = RcaSharedTextureRenderScheduler(a_render_window, port, texture_count=3)
    try:
        scheduler.start(url="http://127.0.0.1:1234/")
        assert (await emp.recv())["type"] == "server_ready"
        scheduler.rca.process_resize_event(300, 300)
        for _ in range(3):
            assert (await emp.recv())["slots"] == 3

        # Up to one frame in flight per texture, without waiting for frame_done.
        for seq in range(3):
            scheduler.schedule_render()
            frame = await emp.recv()
            assert (frame["seq"], frame["slot"]) == (seq, seq)

        # Back to slot 0: waits until Electron released its frame.
        scheduler.schedule_render()
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(emp.reader.readline(), 0.2)
        await emp.send({"type": "frame_done", "view": "default", "seq": 0})
        frame = await emp.recv()
        assert (frame["seq"], frame["slot"]) == (3, 0)
        for seq in range(1, 4):
            await emp.send({"type": "frame_done", "view": "default", "seq": seq})

        # Changing the count at runtime rebuilds the ring before the next frame.
        scheduler.texture_count = 1
        assert await emp.recv() == {
            "type": "texture",
            "width": 300,
            "height": 300,
            "view": "default",
            "slot": 0,
            "slots": 1,
        }
        assert len(FakePassport.released) == 3
        frame = await emp.recv()
        assert (frame["seq"], frame["slot"]) == (4, 0)

        with pytest.raises(ValueError):
            scheduler.texture_count = 0
    finally:
        await scheduler.close()
        emp.close()


@pytest.fixture
def two_render_windows():
    from vtkmodules.vtkRenderingCore import (
        vtkRenderer,
        vtkRenderWindow,
        vtkRenderWindowInteractor,
    )

    windows = []
    for _ in range(2):
        window = vtkRenderWindow()
        window.AddRenderer(vtkRenderer())
        window.ShowWindowOff()
        vtkRenderWindowInteractor().SetRenderWindow(window)
        windows.append(window)
    yield windows
    for window in windows:
        window.Finalize()


@pytest.mark.asyncio
async def test_schedulers_share_the_connection(two_render_windows, fake_passport):
    emp = FakeEmp({"type": "hello", "protocol": PROTOCOL_VERSION, "passport": "fake"})
    connections = []
    on_connect = emp._on_connect

    async def count_connections(reader, writer):
        connections.append(writer)
        if len(connections) == 1:
            await on_connect(reader, writer)

    emp._on_connect = count_connections
    port = await emp.start()
    disconnected = {"a": asyncio.Event(), "b": asyncio.Event()}
    schedulers = {
        view: RcaSharedTextureRenderScheduler(
            window, port, view=view, on_disconnect=disconnected[view].set
        )
        for view, window in zip(("a", "b"), two_render_windows)
    }
    try:
        for scheduler in schedulers.values():
            scheduler.start(url="http://127.0.0.1:1234/")
        # The page is loaded once, for both views.
        assert (await emp.recv())["type"] == "server_ready"

        schedulers["a"].rca.process_resize_event(300, 300)
        schedulers["b"].rca.process_resize_event(200, 100)
        textures = {}
        frames = {}
        while len(frames) < 2:
            msg = await emp.recv()
            assert msg["type"] in ("texture", "frame")
            if msg["type"] == "texture":
                textures.setdefault(msg["view"], []).append(msg)
            else:
                frames[msg["view"]] = msg
        assert len(connections) == 1
        assert [t["width"] for t in textures["a"]] == [300, 300]
        assert [t["width"] for t in textures["b"]] == [200, 200]
        # seq counts per view.
        assert frames["a"]["seq"] == frames["b"]["seq"] == 0

        # A frame_done only reaches its own view.
        await emp.send({"type": "frame_done", "view": "b", "seq": 0, "dropped": True})
        frame = await emp.recv()
        assert (frame["view"], frame["seq"]) == ("b", 1)
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(emp.reader.readline(), 0.2)

        # Two views can't share a name.
        with pytest.raises(ValueError):
            RcaSharedTextureRenderScheduler(
                two_render_windows[0], port, view="a"
            ).start()

        # Closing one view keeps the connection of the other.
        await schedulers["a"].close()
        schedulers["b"].schedule_render()
        frame = await emp.recv()
        assert frame["view"] == "b"
        assert not disconnected["b"].is_set()

        # Electron going away disconnects the remaining views.
        emp.close()
        await asyncio.wait_for(disconnected["b"].wait(), TIMEOUT_S)
        assert not disconnected["a"].is_set()
    finally:
        for scheduler in schedulers.values():
            await scheduler.close()
        emp.close()
