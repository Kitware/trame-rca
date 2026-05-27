from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from vtkmodules.vtkRenderingCore import vtkRenderWindow

from .protocol import RemoteControlledAreaProtocol

logger = logging.getLogger(__name__)
try:
    from .vtk_rca import VtkRemoteControlledArea
except ModuleNotFoundError as e:
    logger.info(e.msg)

__all__ = [
    "RemoteControlledAreaProtocol",
    "VtkRemoteControlledArea",
    "window_wrapper",
]


def window_wrapper(
    window: RemoteControlledAreaProtocol | vtkRenderWindow,
) -> RemoteControlledAreaProtocol:
    if isinstance(window, RemoteControlledAreaProtocol):
        return window

    from vtkmodules.vtkRenderingCore import vtkRenderWindow

    if isinstance(window, vtkRenderWindow):
        return VtkRemoteControlledArea(window)

    raise RuntimeError(
        "Invalid window object provided: expected an instance of RemoteControlledAreaProtocol"
    )
