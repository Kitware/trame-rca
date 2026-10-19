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
        assert await emp.recv() == {"type": "texture", "width": 300, "height": 300}
        frame = await emp.recv()
        assert frame["type"] == "frame" and frame["seq"] == 0
        await emp.send({"type": "frame_done", "seq": 0})

        # A resize makes a new texture and releases the old one.
        scheduler.rca.process_resize_event(200, 100)
        scheduler.schedule_render()
        assert await emp.recv() == {"type": "texture", "width": 200, "height": 100}
        assert FakePassport.released == [(300, 300)]
        assert (await emp.recv())["seq"] == 1

        # Electron going away closes the scheduler.
        emp.close()
        await asyncio.wait_for(disconnected.wait(), TIMEOUT_S)
        assert FakePassport.released == [(300, 300), (200, 100)]
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
        assert (await emp.recv())["seq"] == 0

        # e.g. sendSharedTexture timed out while the page was loading.
        await emp.send({"type": "frame_done", "seq": 0, "dropped": True})
        frame = await emp.recv()
        assert frame["type"] == "frame" and frame["seq"] == 1
    finally:
        await scheduler.close()
        emp.close()
