# Required for rendering initialization, not necessary for
# local rendering, but doesn't hurt to include it
from io import BytesIO
import time
from trame.app.testing import enable_testing
from trame.decorators import TrameApp, change, life_cycle
from trame_rca.utils import RcaEncoder
from trame.app import get_server
from trame_rca.encoders.img import TO_IMAGE_FORMAT
from trame.ui.vuetify3 import SinglePageLayout
from trame.widgets import vuetify3 as v3
from trame.widgets import client, rca
from PIL import Image

DEFAULT_ROTATION_ANGLE = 45


def resize_image_to_fill(image, target_width, target_height):
    img_width, img_height = image.size
    img_ratio = img_width / img_height
    target_ratio = target_width / target_height

    if img_ratio > target_ratio:
        new_width, new_height = target_width, int(target_width / img_ratio)
    else:
        new_width, new_height = int(target_height * img_ratio), target_height

    return image.resize((new_width, new_height), Image.LANCZOS)


def rotate_image(image, angle):
    return image.rotate(angle)


class ViewAdapter:
    """
    Adapter for Generic Remote Controlled Area.
    """

    def __init__(
        self,
        image: Image,
        name: str,
        rotation_angle: int,
        quality: int = 50,
        **kwargs,
    ):
        self.image = image
        self.area_name = name
        self.streamer = None
        self.rotation_angle = rotation_angle
        self._quality = quality
        self._press_set = set()

    def _get_metadata(self):
        return dict(
            type="image/jpeg",  # supported mime/type
            codec="",  # video codec, not relevant here
            w=self.image.size[1],
            h=self.image.size[0],
            st=int(time.time_ns() / 1000000),
            key=("key"),
            quality=self._quality,
        )

    def _render(self):
        fake_file = BytesIO()
        self.image.save(fake_file, TO_IMAGE_FORMAT["png"], quality=self._quality)
        content = fake_file.getvalue()
        self._push(content, self._get_metadata())

    def _push(self, content: bytes, meta: dict):
        if not self.streamer:
            return
        if content is None:
            return
        self.streamer.push_content(self.area_name, meta, content)

    def set_streamer(self, stream_manager):
        self.streamer = stream_manager

    def update_size(self, origin, size):
        width = max(1, int(size.get("w", 300)))
        height = max(1, int(size.get("h", 300)))
        self.image = resize_image_to_fill(self.image, width, height)
        self._render()

    def on_interaction(self, origin, event):
        event_type = event["type"]
        if event_type == "keydown":
            self.image = rotate_image(self.image, self.rotation_angle)
        elif event_type == "wheel":
            delta_y = event.get("deltaY", 0)  # Get scroll direction
            if delta_y is not None:
                angle = -self.rotation_angle if delta_y < 0 else self.rotation_angle
                self.image = rotate_image(self.image, angle)
            else:
                return
        else:
            return
        self._render()


@TrameApp()
class VanillaApp:
    def __init__(self, server=None):
        self.server = get_server(server, client_type="vue3")
        image = Image.open("examples/00_vanilla/trame_logo.png")
        self.view_handler = ViewAdapter(
            image,
            "view",
            rotation_angle=DEFAULT_ROTATION_ANGLE,
            rca_encoder=RcaEncoder.PNG,
        )
        client.Style("img { width: auto !important; }", trame_server=self.server)
        self._build_ui()

    @property
    def state(self):
        return self.server.state

    @property
    def ctrl(self):
        return self.server.controller

    @change("rotation_angle")
    def update_rotation_angle(self, rotation_angle, **kwargs):
        self.view_handler.rotation_angle = rotation_angle

    @life_cycle.server_ready
    def on_server_ready(self, **_):
        # can only be called when server is ready
        self.ctrl.rc_area_register(self.view_handler)

    def reset_rotation_angle(self):
        self.state.rotation_angle = DEFAULT_ROTATION_ANGLE

    def _build_ui(self):
        with SinglePageLayout(self.server, full_height=True) as layout:
            layout.title.set_text("RCA rendering")

            with layout.toolbar:
                v3.VSpacer()
                v3.VSlider(
                    label="Rotation angle",
                    thumb_label=True,
                    thumb_size=20,
                    v_model=("rotation_angle", DEFAULT_ROTATION_ANGLE),
                    min=15,
                    max=90,
                    step=5,
                    hide_details=True,
                    dense=True,
                    style="max-width: 300px",
                )

                v3.VBtn(icon="mdi-undo-variant", click=self.reset_rotation_angle)

            with layout.content:
                with v3.VContainer(
                    fluid=True,
                    classes="pa-0 fill-height position-relative",
                ):
                    rca.GenericRemoteControlledArea(
                        name="view",
                        display="image",
                    )


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    app = VanillaApp()
    enable_testing(app.server)
    app.server.start()
