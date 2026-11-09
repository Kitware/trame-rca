import pytest

from trame_rca.electron import EMP_PORT_ARG, PROTOCOL_VERSION
from trame_rca.electron.comm import ProtocolMismatchError, check_protocol
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


def test_port_arg_matches_npm_package():
    """@kitware/trame-rca-electron spawns the server with this argument."""
    from pathlib import Path

    js = (
        Path(__file__).parent.parent / "js-electron-lib/src/main/index.js"
    ).read_text()
    assert EMP_PORT_ARG == "--trame-electron-port"
    assert f"'{EMP_PORT_ARG}'" in js
