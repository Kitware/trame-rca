import numpy as np
import pytest

from trame_rca.encoders import RcaImageEncoder

RGBA = np.random.default_rng(0).integers(0, 256, (48, 64, 4), dtype=np.uint8)
SQUARE_RGBA = np.random.default_rng(1).integers(0, 256, (48, 48, 4), dtype=np.uint8)
# RGB arrays an RCA could return, none of them C-contiguous RGB
LAYOUTS = {
    "rgb-view-of-rgba": RGBA[..., :3],
    "bottom-up": RGBA[::-1, :, :3],
    "mirrored": RGBA[:, ::-1, :3],
    "transposed": RGBA.transpose(1, 0, 2)[..., :3],
    "transposed-square": SQUARE_RGBA.transpose(1, 0, 2)[..., :3],
    "channel-offset": RGBA[..., 1:],
    "every-other-pixel": RGBA[::2, ::2, :3],
    "fortran-order": np.asfortranarray(RGBA[..., :3]),
}


@pytest.mark.parametrize("layout", LAYOUTS)
@pytest.mark.parametrize("encoder", list(RcaImageEncoder))
def test_encoders_read_any_rgb_layout(encoder, layout):
    image = LAYOUTS[layout]
    rows, cols = image.shape[:2]
    expected, *_ = encoder.encode(np.ascontiguousarray(image), cols, rows, 90)
    encoded, *_ = encoder.encode(image, cols, rows, 90)
    assert encoded == expected
