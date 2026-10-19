"""Render VTK into a texture shared with an Electron app, instead of streaming images.

The Electron side lives in the trame-rca-electron npm package: it spawns the trame
server with ``--emp-port`` and shows the shared texture in the page.

Call :func:`init_vtk` before creating any VTK render window, then use
``RemoteControlledArea(display="shared-texture").create_electron_handler(...)``.
"""

import argparse
import logging
import os
import sys

from .comm import PROTOCOL_VERSION

logger = logging.getLogger(__name__)

__all__ = [
    "EMP_PORT_ARG",
    "PROTOCOL_VERSION",
    "emp_port",
    "init_vtk",
    "server_url",
]

# The CLI argument that trame-rca-electron passes the port of its `texture` channel.
EMP_PORT_ARG = "--emp-port"

_initialized = False


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


def init_vtk():
    """Make VTK render on the GPU Electron composites with.

    The shared texture can only be imported on the GPU Chromium uses, and VTK reads
    some of these settings when its render window is constructed: call this before
    creating any. It can be called more than once.

    Linux: ``RENDER_NODE`` overrides the render node (default: the GPU driving the
    display).
    Windows: ``D3D_ADAPTER`` overrides the DXGI adapter index (default 0).
    MacOS: Calling this method is unnecessary.
    """
    global _initialized
    if _initialized:
        return
    _initialized = True

    if sys.platform == "linux":
        from .passports import wayland_dmabuf

        if os.environ.get("RENDER_NODE"):
            render_node, reason = os.environ["RENDER_NODE"], "env"
        else:
            render_node, reason = wayland_dmabuf.default_render_node()
        logger.info("using render node %s (%s)", render_node, reason)
        # vtkEGLRenderWindow::SetDeviceIndex doesn't reach the EGL display setup; the
        # constructor only reads the device from this variable.
        os.environ["VTK_EGL_DEVICE_INDEX"] = str(
            wayland_dmabuf.device_index(render_node)
        )
        os.environ["VTK_DEFAULT_OPENGL_WINDOW"] = "vtkEGLRenderWindow"
    elif sys.platform == "win32":
        from .passports import nthandle

        # The shared texture must live on the GPU Chromium uses, which is DXGI adapter 0
        # unless told otherwise. VTK's WGL context has to be on that GPU too.
        nthandle.init_device(int(os.environ.get("D3D_ADAPTER", "0")))
