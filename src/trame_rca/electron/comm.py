"""
Talks newline-delimited JSON to the Electron main process (EMP) on 127.0.0.1:<port>.

-> means python to EMP
<- means EMP to Python

    <- {"type":"hello", "protocol": N, "passport": name}    at start, the texture passport to use
    -> {"type":"server_ready", "protocol": N, "url": url}   once trame serves its page
    -> {"type":"texture", ...}                              at start and after every resize
    -> {"type":"frame", "seq": n, "timestamp_us": t}        after every render (finished on the GPU)
    <- {"type":"frame_done", "seq": n}                      when Electron released the texture
    <- {"type":"frame_done", "seq": n, "dropped": true}     when the frame didn't reach the ERP

Everything else (size, input, app state) goes from the renderer process to trame over its websocket.

PROTOCOL_VERSION must match the one of the trame-rca-electron npm package.
"""

import asyncio
import json
import socket

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

    @classmethod
    async def open(cls, port, host="127.0.0.1"):
        reader, writer = await asyncio.open_connection(host, port)
        # Small request/response messages: don't let Nagle wait for delayed ACKs.
        writer.get_extra_info("socket").setsockopt(
            socket.IPPROTO_TCP, socket.TCP_NODELAY, 1
        )
        return cls(reader, writer)

    async def send(self, msg):
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
