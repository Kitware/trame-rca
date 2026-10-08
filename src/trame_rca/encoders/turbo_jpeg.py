from numpy.typing import NDArray
from turbojpeg import TurboJPEG, TJPF_RGB, TJPF_RGBX
from trame_rca.encoders.img import TO_IMAGE_TYPE, rgbx_view
# import time

jpeg = TurboJPEG()


def encode(
    np_image: NDArray,
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
        encode_np_img_to_bytes(np_image, cols, rows, quality),
        meta,
        now_ms,
    )


def encode_np_img_to_bytes(
    image: NDArray,
    cols: int,
    rows: int,
    quality: int,
) -> bytes:
    if not (cols and rows):
        return b""

    # t0 = time.time()
    pixel_format = TJPF_RGB
    rgbx = rgbx_view(image)
    if rgbx is not None:
        image, pixel_format = rgbx, TJPF_RGBX
    result = jpeg.encode(image, quality=quality, pixel_format=pixel_format)
    # t1 = time.time()
    # print(f"tubo-jpeg encode {t1-t0:.04f}s")

    return result
