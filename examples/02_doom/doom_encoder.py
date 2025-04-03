from io import BytesIO
import pillow_avif  # noqa
from PIL import Image
from trame_rca.encoders.img import TO_IMAGE_TYPE, TO_IMAGE_FOMAT


def encode(
    image: Image,
    img_format: str,
    cols: int,
    rows: int,
    quality: int,
    now_ms: int,
) -> tuple[bytes, dict, int]:
    meta = dict(
        type=TO_IMAGE_TYPE[img_format],
        codec="",
        w=cols,
        h=rows,
        st=now_ms,
        key="key",
        quality=quality,
    )

    return (
        encode_image_to_bytes(image, img_format, quality),
        meta,
        now_ms,
    )


def encode_image_to_bytes(
    image: Image,
    img_format: str,
    quality: int,
) -> bytes:
    """
    Numpy implementation of JPEG conversion of the input image.
    Input image should be a numpy array as extracted from the render to image function.
    This method uses numpy arrays as input for compatibility with Python's multiprocessing.
    """

    fake_file = BytesIO()
    image.save(fake_file, TO_IMAGE_FOMAT[img_format], quality=quality)

    return fake_file.getvalue()
