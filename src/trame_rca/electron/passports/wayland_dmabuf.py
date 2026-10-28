import ctypes
import logging
import glob
import os

from .base import TexturePassport
from vtkmodules.vtkCommonCore import VTK_UNSIGNED_CHAR
from vtkmodules.vtkRenderingOpenGL2 import vtkTextureObject

logger = logging.getLogger(__name__)

# --- EGL -----------------------------------------------------------------------
EGL_NONE = 0x3038
EGL_EXTENSIONS = 0x3055
EGL_DRM_RENDER_NODE_FILE_EXT = 0x3377
EGL_GL_TEXTURE_2D_KHR = 0x30B1
EGL_GL_TEXTURE_LEVEL_KHR = 0x30BC
GL_FRAMEBUFFER = 0x8D40

EGLint = ctypes.c_int32
EGLBoolean = ctypes.c_uint32
EGLenum = ctypes.c_uint32
EGLuint64KHR = ctypes.c_uint64
vp = ctypes.c_void_p

egl = ctypes.CDLL("libEGL.so.1")
egl.eglGetProcAddress.restype = vp
egl.eglGetProcAddress.argtypes = [ctypes.c_char_p]
egl.eglGetError.restype = EGLint
egl.eglQueryString.argtypes = [vp, EGLint]
egl.eglQueryString.restype = ctypes.c_char_p
egl.eglGetCurrentDisplay.restype = vp
egl.eglGetCurrentContext.restype = vp


def egl_ext(name, restype, *argtypes):
    addr = egl.eglGetProcAddress(name.encode())
    if not addr:
        raise RuntimeError(f"missing EGL function {name}")
    return ctypes.CFUNCTYPE(restype, *argtypes)(addr)


eglQueryDevicesEXT = egl_ext(
    "eglQueryDevicesEXT", EGLBoolean, EGLint, ctypes.POINTER(vp), ctypes.POINTER(EGLint)
)
eglQueryDeviceStringEXT = egl_ext(
    "eglQueryDeviceStringEXT", ctypes.c_char_p, vp, EGLint
)
eglCreateImageKHR = egl_ext(
    "eglCreateImageKHR", vp, vp, vp, EGLenum, vp, ctypes.POINTER(EGLint)
)
eglDestroyImageKHR = egl_ext("eglDestroyImageKHR", EGLBoolean, vp, vp)
eglExportDMABUFImageQueryMESA = egl_ext(
    "eglExportDMABUFImageQueryMESA",
    EGLBoolean,
    vp,
    vp,
    ctypes.POINTER(ctypes.c_int),
    ctypes.POINTER(ctypes.c_int),
    ctypes.POINTER(EGLuint64KHR),
)
eglExportDMABUFImageMESA = egl_ext(
    "eglExportDMABUFImageMESA",
    EGLBoolean,
    vp,
    vp,
    ctypes.POINTER(ctypes.c_int),
    ctypes.POINTER(EGLint),
    ctypes.POINTER(EGLint),
)


def attribs(*values):
    return (EGLint * (len(values) + 1))(*values, EGL_NONE)


def check(ok, what):
    if not ok:
        raise RuntimeError(f"{what} failed: EGL error 0x{egl.eglGetError():04x}")
    return ok


def fourcc_str(code):
    return "".join(chr((code >> (8 * i)) & 0xFF) for i in range(4))


# DRM fourcc -> electron pixelFormat
PIXEL_FORMATS = {"AB24": "rgba", "AR24": "bgra"}


def default_render_node():
    """Return (render node, reason). Prefers the GPU driving the display (boot_vga=1).

    Chromium can only import the dma-buf if it was allocated on the same GPU
    that it's compositor runs on. In a multi-GPU box that isn't necessarily /dev/dri/renderD128.
    """
    for boot_vga in sorted(glob.glob("/sys/class/drm/card*/device/boot_vga")):
        try:
            with open(boot_vga) as f:
                if f.read().strip() != "1":
                    continue
        except OSError:
            continue
        nodes = sorted(
            glob.glob(os.path.join(os.path.dirname(boot_vga), "drm", "renderD*"))
        )
        if nodes:
            return f"/dev/dri/{os.path.basename(nodes[0])}", "boot_vga"
    return "/dev/dri/renderD128", "fallback"


def device_index(render_node):
    """The index of render_node among the EGL devices, just the way vtkEGLRenderWindow counts them."""
    devices = (vp * 16)()
    count = EGLint()
    check(eglQueryDevicesEXT(16, devices, ctypes.byref(count)), "eglQueryDevicesEXT")
    for i in range(count.value):
        node = eglQueryDeviceStringEXT(devices[i], EGL_DRM_RENDER_NODE_FILE_EXT)
        node = node.decode() if node else None
        logger.info(f"EGL device {i}: render node {node}")
        if node == render_node:
            return i
    raise RuntimeError(f"no EGL device with render node {render_node}")


def attach_texture(render_window, width, height):
    """Make a fresh RGBA8 texture the color attachment 0 of the window's DisplayFramebuffer."""
    tex = vtkTextureObject()
    tex.SetContext(render_window)
    if not tex.Allocate2D(width, height, 4, VTK_UNSIGNED_CHAR):
        raise RuntimeError("allocating the RGBA8 texture failed")

    display_fbo = render_window.GetDisplayFramebuffer()
    display_fbo.AddColorAttachment(0, tex)
    display_fbo.Bind()
    complete = display_fbo.CheckFrameBufferStatus(GL_FRAMEBUFFER)
    display_fbo.UnBind()
    if not complete:
        raise RuntimeError("DisplayFramebuffer incomplete with the exported texture")
    return tex


def export_dmabuf(render_window, tex, height):
    render_window.MakeCurrent()
    dpy, ctx = egl.eglGetCurrentDisplay(), egl.eglGetCurrentContext()
    exts = egl.eglQueryString(dpy, EGL_EXTENSIONS).decode().split()
    for ext in ("EGL_MESA_image_dma_buf_export", "EGL_KHR_gl_texture_2D_image"):
        if ext not in exts:
            raise RuntimeError(f"display lacks {ext}")

    image = check(
        eglCreateImageKHR(
            dpy,
            ctx,
            EGL_GL_TEXTURE_2D_KHR,
            vp(tex.GetHandle()),
            attribs(EGL_GL_TEXTURE_LEVEL_KHR, 0),
        ),
        "eglCreateImageKHR",
    )
    fourcc, num_planes = ctypes.c_int(), ctypes.c_int()
    modifiers = (EGLuint64KHR * 4)()
    check(
        eglExportDMABUFImageQueryMESA(
            dpy, image, ctypes.byref(fourcc), ctypes.byref(num_planes), modifiers
        ),
        "eglExportDMABUFImageQueryMESA",
    )
    fourcc_strings = fourcc_str(fourcc.value)
    if fourcc_strings not in PIXEL_FORMATS:
        raise RuntimeError(f"unsupported fourcc {fourcc_strings}")
    fds = (ctypes.c_int * 4)(-1, -1, -1, -1)
    strides, offsets = (EGLint * 4)(), (EGLint * 4)()
    check(
        eglExportDMABUFImageMESA(dpy, image, fds, strides, offsets),
        "eglExportDMABUFImageMESA",
    )
    eglDestroyImageKHR(dpy, image)
    render_window.WaitForCompletion()

    planes = []
    for i in range(num_planes.value):
        # The dma-buf's real size; tiled layouts can be larger than stride*height.
        try:
            size = os.lseek(fds[i], 0, os.SEEK_END) - offsets[i]
        except OSError:
            size = strides[i] * height
        planes.append(
            {"fd": fds[i], "stride": strides[i], "offset": offsets[i], "size": size}
        )

    return fourcc_strings, modifiers[0], planes


class WaylandDMABUFTexturePassport(TexturePassport):
    """The texture VTK resolves into, exported as a dma-buf, at one size."""

    def __init__(self, render_window, width, height):
        super().__init__(render_window, width, height)
        render_window.MakeCurrent()
        self.vtk_texture = attach_texture(render_window, width, height)
        self.fourcc, self.modifier, self.planes = export_dmabuf(
            render_window, self.vtk_texture, height
        )
        logger.info(
            f"exported {width}x{height} fourcc={self.fourcc} modifier=0x{self.modifier:016x} "
            f"planes={self.planes}"
        )

    def to_json(self):
        return {
            "type": "texture",
            "pid": os.getpid(),
            "width": self.width,
            "height": self.height,
            "fourcc": self.fourcc,
            "pixelFormat": PIXEL_FORMATS[self.fourcc],
            "modifier": str(self.modifier),
            "planes": self.planes,
        }

    def release(self):
        for p in self.planes:
            os.close(p["fd"])
        self.render_window.MakeCurrent()
        self.vtk_texture.ReleaseGraphicsResources(self.render_window)
