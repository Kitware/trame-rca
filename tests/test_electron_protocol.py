import pytest

from trame_rca.electron import EMP_PORT_ARG, PROTOCOL_VERSION
import asyncio
import json

from trame_rca.electron.comm import (
    TOKEN_ENV,
    EmpClient,
    ProtocolMismatchError,
    check_protocol,
)
from trame_rca.electron.passports import texture_passport_class


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


def test_protocol_version_matches_npm_package():
    """trame-rca and @kitware/trame-rca-electron must speak the same protocol."""
    import re
    from pathlib import Path

    js = (
        Path(__file__).parent.parent / "js-electron-lib/src/main/protocol.js"
    ).read_text()
    match = re.search(r"PROTOCOL_VERSION = (\d+)", js)
    assert match and int(match.group(1)) == PROTOCOL_VERSION
    assert f"TOKEN_ENV = '{TOKEN_ENV}'" in js


def test_port_arg_matches_npm_package():
    """@kitware/trame-rca-electron spawns the server with this argument."""
    from pathlib import Path

    js = (
        Path(__file__).parent.parent / "js-electron-lib/src/main/index.js"
    ).read_text()
    assert EMP_PORT_ARG == "--trame-electron-port"
    assert f"'{EMP_PORT_ARG}'" in js


@pytest.mark.asyncio
async def test_client_authenticates_before_the_hello(monkeypatch):
    received = []

    async def on_connect(reader, writer):
        received.append(json.loads(await reader.readline()))
        hello = {"type": "hello", "protocol": PROTOCOL_VERSION, "passport": "nope"}
        writer.write((json.dumps(hello) + "\n").encode())
        await writer.drain()

    server = await asyncio.start_server(on_connect, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    monkeypatch.setenv(TOKEN_ENV, "secret")
    client = EmpClient(port)
    try:
        assert await asyncio.wait_for(client.connect(), 10) == "nope"
    finally:
        client.close()
        server.close()
    assert received == [{"type": "auth", "token": "secret"}]


@pytest.mark.asyncio
async def test_client_needs_a_token(monkeypatch):
    monkeypatch.delenv(TOKEN_ENV, raising=False)
    with pytest.raises(RuntimeError, match=TOKEN_ENV):
        await EmpClient(1).connect()
