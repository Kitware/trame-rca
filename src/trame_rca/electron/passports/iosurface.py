import ctypes
import logging
import os

from .base import TexturePassport
from vtkmodules.vtkRenderingOpenGL2 import vtkTextureObject

logger = logging.getLogger(__name__)

vp = ctypes.c_void_p

# --- CoreFoundation / IOSurface ----------------------------------------------
cf = ctypes.CDLL("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")
cf.CFNumberCreate.restype = vp
cf.CFNumberCreate.argtypes = [vp, ctypes.c_long, vp]
cf.CFDictionaryCreateMutable.restype = vp
cf.CFDictionaryCreateMutable.argtypes = [vp, ctypes.c_long, vp, vp]
cf.CFDictionarySetValue.argtypes = [vp, vp, vp]
cf.CFRelease.argtypes = [vp]
kCFNumberSInt32Type = 3
kCFBooleanTrue = vp.in_dll(cf, "kCFBooleanTrue")

iosurface = ctypes.CDLL("/System/Library/Frameworks/IOSurface.framework/IOSurface")
iosurface.IOSurfaceCreate.restype = vp
iosurface.IOSurfaceCreate.argtypes = [vp]
iosurface.IOSurfaceGetID.restype = ctypes.c_uint32
iosurface.IOSurfaceGetID.argtypes = [vp]
iosurface.IOSurfaceGetBytesPerRow.restype = ctypes.c_size_t
iosurface.IOSurfaceGetBytesPerRow.argtypes = [vp]

# --- CGL / GL ------------------------------------------------------------------
cgl = ctypes.CDLL("/System/Library/Frameworks/OpenGL.framework/OpenGL")
cgl.CGLGetCurrentContext.restype = vp
cgl.CGLErrorString.restype = ctypes.c_char_p
cgl.CGLErrorString.argtypes = [ctypes.c_int]
cgl.CGLTexImageIOSurface2D.argtypes = [
    vp,
    ctypes.c_uint32,
    ctypes.c_uint32,
    ctypes.c_int32,
    ctypes.c_int32,
    ctypes.c_uint32,
    ctypes.c_uint32,
    vp,
    ctypes.c_uint32,
]
cgl.glGenTextures.argtypes = [ctypes.c_int32, ctypes.POINTER(ctypes.c_uint32)]
cgl.glDeleteTextures.argtypes = [ctypes.c_int32, ctypes.POINTER(ctypes.c_uint32)]
cgl.glBindTexture.argtypes = [ctypes.c_uint32, ctypes.c_uint32]
cgl.glGetString.restype = ctypes.c_char_p
cgl.glGetString.argtypes = [ctypes.c_uint32]

GL_VERSION = 0x1F02
GL_RENDERER = 0x1F01
GL_TEXTURE_RECTANGLE = 0x84F5
GL_RGBA = 0x1908
GL_BGRA = 0x80E1
GL_UNSIGNED_INT_8_8_8_8_REV = 0x8367
GL_FRAMEBUFFER = 0x8D40

# IOSurface pixel format 'BGRA' -> electron pixelFormat
PIXEL_FORMAT_BGRA = 0x42475241


def check(err, what):
    if err != 0:
        raise RuntimeError(f"{what} failed: {cgl.CGLErrorString(err).decode()} ({err})")


def _iosurface_key(name):
    return vp.in_dll(iosurface, name)


def _create_surface(width, height):
    """A BGRA IOSurface that other processes can open with IOSurfaceLookup(id)."""
    props = cf.CFDictionaryCreateMutable(
        None,
        0,
        ctypes.addressof(ctypes.c_char.in_dll(cf, "kCFTypeDictionaryKeyCallBacks")),
        ctypes.addressof(ctypes.c_char.in_dll(cf, "kCFTypeDictionaryValueCallBacks")),
    )
    for key, value in (
        ("kIOSurfaceWidth", width),
        ("kIOSurfaceHeight", height),
        ("kIOSurfaceBytesPerElement", 4),
        ("kIOSurfacePixelFormat", PIXEL_FORMAT_BGRA),
    ):
        v = ctypes.c_int32(value)
        number = cf.CFNumberCreate(None, kCFNumberSInt32Type, ctypes.byref(v))
        cf.CFDictionarySetValue(props, _iosurface_key(key), number)
        cf.CFRelease(number)
    # Deprecated, but the only way to share an IOSurface without passing a Mach port.
    cf.CFDictionarySetValue(props, _iosurface_key("kIOSurfaceIsGlobal"), kCFBooleanTrue)
    surface = iosurface.IOSurfaceCreate(props)
    cf.CFRelease(props)
    if not surface:
        raise RuntimeError(f"IOSurfaceCreate failed for {width}x{height}")
    return surface


def _attach_surface(render_window, surface, width, height):
    """Make the IOSurface the color attachment 0 of the window's DisplayFramebuffer."""
    render_window.MakeCurrent()
    ctx = cgl.CGLGetCurrentContext()

    # CGL only binds IOSurfaces to rectangle textures.
    handle = ctypes.c_uint32()
    cgl.glGenTextures(1, ctypes.byref(handle))
    cgl.glBindTexture(GL_TEXTURE_RECTANGLE, handle.value)
    check(
        cgl.CGLTexImageIOSurface2D(
            ctx,
            GL_TEXTURE_RECTANGLE,
            GL_RGBA,
            width,
            height,
            GL_BGRA,
            GL_UNSIGNED_INT_8_8_8_8_REV,
            surface,
            0,
        ),
        "CGLTexImageIOSurface2D",
    )
    cgl.glBindTexture(GL_TEXTURE_RECTANGLE, 0)

    tex = vtkTextureObject()
    tex.SetContext(render_window)
    tex.AssignToExistingTexture(handle.value, GL_TEXTURE_RECTANGLE)
    # Only records the size: an assigned texture has no dimensions, so Resize() never
    # calls glTexImage2D (which would detach the IOSurface). The DisplayFramebuffer
    # resizes its attachments on every Start(), and this keeps that a no-op too.
    tex.Resize(width, height)

    display_fbo = render_window.GetDisplayFramebuffer()
    display_fbo.AddColorAttachment(0, tex)
    display_fbo.Bind()
    complete = display_fbo.CheckFrameBufferStatus(GL_FRAMEBUFFER)
    display_fbo.UnBind()
    if not complete:
        raise RuntimeError(
            "DisplayFramebuffer incomplete with the IOSurface attachment"
        )
    return tex, handle


class IOSurfaceTexturePassport(TexturePassport):
    def __init__(self, render_window, width, height):
        super().__init__(render_window, width, height)
        self.surface = _create_surface(width, height)
        self.vtk_texture, self.handle = _attach_surface(
            render_window, self.surface, width, height
        )
        self.surface_id = iosurface.IOSurfaceGetID(self.surface)
        logger.info(
            f"IOSurface id={self.surface_id} {width}x{height} BGRA "
            f"stride={iosurface.IOSurfaceGetBytesPerRow(self.surface)}"
        )

    def to_json(self):
        return {
            "type": "texture",
            "pid": os.getpid(),
            "width": self.width,
            "height": self.height,
            "pixelFormat": "bgra",
            "ioSurfaceId": self.surface_id,
        }

    def release(self):
        self.render_window.MakeCurrent()
        cgl.glDeleteTextures(1, ctypes.byref(self.handle))
        cf.CFRelease(self.surface)

    async def flush_graphics_commands(self):
        # no need to call superclass method since we already call glFinish.
        cgl.glFinish()
