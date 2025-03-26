from numpy.typing import NDArray
from turbojpeg import TurboJPEG
# import time

jpeg = TurboJPEG()


def encode_np_img_to_bytes(
    image: NDArray,
    cols: int,
    rows: int,
    img_format: str,
    quality: int,
) -> bytes:
    if not (cols and rows):
        return b""

    # t0 = time.time()
    image = image.reshape((cols, rows, -1))
    image = image[::-1, :, :]
    result = jpeg.encode(image, quality=quality)
    # t1 = time.time()
    # print(f"tubo-jpeg encode {t1-t0:.04f}s")

    return result
