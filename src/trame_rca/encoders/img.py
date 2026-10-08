import numpy as np

TO_IMAGE_TYPE = {
    "avif": "image/avif",
    "jpeg": "image/jpeg",
    "turbo-jpeg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
}

TO_IMAGE_FORMAT = {
    "avif": "avif",
    "jpeg": "jpeg",
    "turbo-jpeg": "jpeg",
    "png": "png",
    "webp": "webp",
}


def rgbx_view(image):
    """
    Return the RGBX buffer behind an RGB view over 4-byte pixels, or None.
    VtkRemoteControlledArea returns such a view so the encoders can skip a copy.
    """
    base = image.base
    if (
        image.dtype == np.uint8
        and image.ndim == 3
        and image.shape[2] == 3
        and isinstance(base, np.ndarray)
        and base.dtype == np.uint8
        and base.flags.c_contiguous
        and base.shape == (*image.shape[:2], 4)
        and image.strides == base.strides
        and image.ctypes.data == base.ctypes.data
    ):
        return base
    return None
