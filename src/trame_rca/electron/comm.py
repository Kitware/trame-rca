"""
Talks newline-delimited JSON to the Electron main process (EMP) on 127.0.0.1:<port>.

-> means python to EMP
<- means EMP to Python

    <- {"type":"hello", "protocol": N, "passport": name}    at start, the texture passport to use
    -> {"type":"server_ready", "protocol": N, "url": url}   once, when trame serves its page
    -> {"type":"texture", "view": v, "slot": i, "slots": k, ...}
                                                            at start, after every resize and
                                                            change of texture count, one per slot
    -> {"type":"frame", "view": v, "seq": n, "slot": i, "timestamp_us": t}
                                                            after every render into slot i
                                                            (finished on the GPU)
    <- {"type":"frame_done", "view": v, "seq": n}           when Electron released the texture
    <- {"type":"frame_done", "view": v, "seq": n, "dropped": true}
                                                            when the frame didn't reach the ERP

Every shared-texture view of the server talks over the same connection: `view` is the name of
its RemoteControlledArea, and `seq` and `slot` count per view.
The k textures of a view form a ring: several frames can be in flight, one per slot. Slots past
k are gone.

Everything else (size, input, app state) goes from the renderer process to trame over its websocket.

PROTOCOL_VERSION must match the one of the trame-rca-electron npm package.
"""

import asyncio
import json
import logging
import socket
from typing import Callable

logger = logging.getLogger(__name__)

PROTOCOL_VERSION = 1


class ProtocolMismatchError(RuntimeError):
    pass


def check_protocol(msg):
    """Raise ProtocolMismatchError unless the EMP's hello speaks PROTOCOL_VERSION."""
    version = msg.get("protocol")
    if version != PROTOCOL_VERSION:
        raise ProtocolMismatchError(
            f"Electron speaks shared texture protocol {version}, trame-rca speaks "
            f"{PROTOCOL_VERSION}: update trame-rca or trame-rca-electron so they match"
        )


class LineConnection:
    def __init__(self, reader, writer):
        self.reader = reader
        self.writer = writer
        # Several views send on the same connection.
        self._send_lock = asyncio.Lock()

    @classmethod
    async def open(cls, port, host="127.0.0.1"):
        reader, writer = await asyncio.open_connection(host, port)
        # Small request/response messages: don't let Nagle wait for delayed ACKs.
        writer.get_extra_info("socket").setsockopt(
            socket.IPPROTO_TCP, socket.TCP_NODELAY, 1
        )
        return cls(reader, writer)

    async def send(self, msg):
        async with self._send_lock:
            self.writer.write((json.dumps(msg) + "\n").encode())
            await self.writer.drain()

    async def recv(self):
        """Return the next message. Raises EOFError on close."""
        line = await self.reader.readline()
        if not line:
            raise EOFError
        return json.loads(line)

    def close(self):
        self.writer.close()


class EmpClient:
    """The connection to the EMP, shared by all the shared-texture views of the server.

    The EMP takes a single connection per window, so views register here by name and get
    the frame_done messages of their own frames.
    """

    # The open clients, by EMP port.
    _clients: dict[int, "EmpClient"] = {}

    @classmethod
    def for_port(cls, port: int) -> "EmpClient":
        """The client connected (or connecting) to the EMP on ``port``."""
        client = cls._clients.get(port)
        if client is None:
            client = cls._clients[port] = cls(port)
        return client

    def __init__(self, port: int):
        self.port = port
        self._conn: LineConnection | None = None
        self._connect_task: asyncio.Task | None = None
        self._read_task: asyncio.Task | None = None
        # view name: (on_frame_done(msg), on_disconnect())
        self._views: dict[str, tuple[Callable[[dict], None], Callable[[], None]]] = {}
        self._server_ready_sent = False
        self._closed = False

    def add_view(
        self,
        view: str,
        on_frame_done: Callable[[dict], None],
        on_disconnect: Callable[[], None],
    ):
        if view in self._views:
            raise ValueError(f"a shared-texture view named {view!r} already exists")
        self._views[view] = (on_frame_done, on_disconnect)

    def remove_view(self, view: str):
        """Forget ``view``. The connection closes with the last view."""
        self._views.pop(view, None)
        if not self._views:
            self.close()

    async def connect(self) -> str:
        """Connect to the EMP once, and return the texture passport name of its hello."""
        if self._connect_task is None:
            self._connect_task = asyncio.ensure_future(self._connect())
        # shield: one view giving up must not cancel the connection of the others.
        return await asyncio.shield(self._connect_task)

    async def _connect(self):
        try:
            self._conn = await LineConnection.open(self.port)
            logger.info("connected to the Electron main process on port %d", self.port)
            try:
                msg = await self._conn.recv()
            except EOFError:
                raise ConnectionError("disconnected before the hello message") from None
            if msg.get("type") != "hello":
                raise ConnectionError(f"expected a hello message, got {msg!r}")
            check_protocol(msg)
        except Exception:
            self.close()
            raise
        self._read_task = asyncio.ensure_future(self._read())
        return msg["passport"]

    async def server_ready(self, url: str | None):
        """Tell the EMP which page to load. Only the first call sends it."""
        if self._server_ready_sent:
            return
        self._server_ready_sent = True
        await self.send(
            {"type": "server_ready", "protocol": PROTOCOL_VERSION, "url": url}
        )

    async def send(self, msg):
        assert self._conn is not None, "Connection to EMP is uninitialized!"
        await self._conn.send(msg)

    async def _read(self):
        assert self._conn is not None, "Connection to EMP is uninitialized!"
        try:
            while True:
                msg = await self._conn.recv()
                if msg["type"] == "frame_done":
                    callbacks = self._views.get(msg.get("view"))
                    if callbacks:
                        callbacks[0](msg)
        except (EOFError, ConnectionError):
            logger.info("the Electron main process disconnected")
        self.close()

    def close(self):
        """Close the connection and tell every view it is gone."""
        if self._closed:
            return
        self._closed = True
        if EmpClient._clients.get(self.port) is self:
            del EmpClient._clients[self.port]
        current = asyncio.current_task()
        for task in (self._read_task, self._connect_task):
            if task and task is not current:
                task.cancel()
        if self._conn:
            self._conn.close()
        views, self._views = self._views, {}
        for _, on_disconnect in views.values():
            on_disconnect()
