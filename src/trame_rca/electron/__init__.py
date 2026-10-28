"""Render VTK into a texture shared with an Electron app, instead of streaming images.

The Electron side lives in the trame-rca-electron npm package: it spawns the trame
server with ``--emp-port`` and shows the shared texture in the page.

Call ``trame_rca.widgets.init_vtk_for_shared_textures()`` before creating any VTK render
window, then use
``RemoteControlledArea(display="shared-texture").create_electron_handler(...)``.
"""

import argparse

from .comm import PROTOCOL_VERSION

__all__ = [
    "EMP_PORT_ARG",
    "PROTOCOL_VERSION",
    "emp_port",
    "server_url",
]

# The CLI argument that trame-rca-electron passes the port of its `texture` channel.
EMP_PORT_ARG = "--emp-port"


def emp_port(server):
    """The port of the Electron main process's `texture` channel, from the CLI.

    Raises RuntimeError when the server wasn't started by trame-rca-electron.
    """
    try:
        server.cli.add_argument(
            EMP_PORT_ARG,
            type=int,
            help="Port of the Electron main process's texture channel",
        )
    except argparse.ArgumentError:
        pass  # Another view added it already.
    args, _ = server.cli.parse_known_args()
    if args.emp_port is None:
        raise RuntimeError(
            f"{EMP_PORT_ARG} is missing: shared-texture views only work when "
            "the trame server is started by trame-rca-electron"
        )
    return args.emp_port


def server_url(server):
    """The URL of the page trame serves, once the server is ready."""
    return f"http://{server.server_options.host}:{server.port}/"
