"""Platform specific ways to share a VTK texture with Electron."""

from .base import TexturePassport

__all__ = [
    "TexturePassport",
    "texture_passport_class",
]


def texture_passport_class(name):
    """The name of the passport class that the EMP wants to use."""
    if not isinstance(name, str):
        raise TypeError("Passport name must be a string")
    if name == "iosurface":
        from .iosurface import IOSurfaceTexturePassport

        return IOSurfaceTexturePassport
    if name == "nthandle":
        from .nthandle import NTHandleTexturePassport

        return NTHandleTexturePassport
    if name == "wayland-dmabuf":
        from .wayland_dmabuf import WaylandDMABUFTexturePassport

        return WaylandDMABUFTexturePassport
    if name == "x11-dmabuf":
        raise NotImplementedError("x11-dmabuf passport is not supported yet")
    raise ValueError(f"Passport name '{name}' is not recognized")
