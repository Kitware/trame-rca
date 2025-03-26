from numpy.typing import NDArray
from io import BytesIO
import pillow_avif  # noqa
from PIL import Image
# import time


def encode_np_img_to_bytes(
    image: NDArray,
    cols: int,
    rows: int,
    img_format: str,
    quality: int,
) -> bytes:
    """
    Numpy implementation of JPEG conversion of the input image.
    Input image should be a numpy array as extracted from the render to image function.
    This method uses numpy arrays as input for compatibility with Python's multiprocessing.
    """

    if not (cols and rows):
        return b""

    # t0 = time.time()
    image = image.reshape((cols, rows, -1))
    image = image[::-1, :, :]
    fake_file = BytesIO()
    image = Image.fromarray(image)
    image.save(fake_file, img_format, quality=quality)
    # t1 = time.time()
    # print(f"pill encode {t1-t0:.04f}s")

    return fake_file.getvalue()
