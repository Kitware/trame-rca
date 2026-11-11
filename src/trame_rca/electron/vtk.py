import os
import sys
import logging

logger = logging.getLogger(__name__)

_shared_textures_initialized = False


def init_vtk_for_shared_textures():
    """Make VTK render on the GPU Electron composites with.

    The shared texture can only be imported on the GPU Chromium uses, and VTK reads
    some of these settings when its render window is constructed: call this before
    creating any. It can be called more than once.

    Linux: ``RENDER_NODE`` overrides the render node (default: the GPU driving the
    display).
    Windows: ``D3D_ADAPTER`` overrides the DXGI adapter index (default 0).
    MacOS: Calling this method is unnecessary.
    """
    global _shared_textures_initialized
    if _shared_textures_initialized:
        return
    _shared_textures_initialized = True

    if sys.platform == "linux":
        from trame_rca.electron.passports import wayland_dmabuf

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
        from trame_rca.electron.passports import nthandle

        # The shared texture must live on the GPU Chromium uses, which is DXGI adapter 0
        # unless told otherwise. VTK's WGL context has to be on that GPU too.
        nthandle.init_device(int(os.environ.get("D3D_ADAPTER", "0")))
        # Ask for a 1ms resolution in the Python process. Otherwise, asyncio.sleep
        # rounds short waits to ~15.6ms
        import ctypes

        ctypes.WinDLL("winmm").timeBeginPeriod(1)
