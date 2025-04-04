# Required for rendering initialization, not necessary for
# local rendering, but doesn't hurt to include it
from numpy import asarray
from pathlib import Path
from PIL import Image
from trame.app.testing import enable_testing
from trame.decorators import TrameApp, change
from trame_rca.widgets import rca
from trame_rca.utils import AbstractWindow
from trame.app import get_server
from trame.ui.vuetify3 import SinglePageLayout
from trame.widgets import vuetify3 as v3


DEFAULT_ROTATION_STEP = 45


class RotatableImageWindow(AbstractWindow):
    def __init__(self, path):
        self._image = Image.open(path).convert("RGB")
        self._image_angle = 0
        self._image_width, self._image_height = self._image.size
        self.rotation_step = DEFAULT_ROTATION_STEP

    @property
    def _updated_image(self):
        return self._image.resize((self._image_width, self._image_height)).rotate(
            self._image_angle, fillcolor="white"
        )

    @property
    def img_cols_rows(self):
        np_image = asarray(self._updated_image)
        rows, cols, _ = np_image.shape
        return np_image, cols, rows

    def process_resize_event(self, width, height):
        image_ratio = self._image_width / self._image_height
        target_ratio = width / height
        if image_ratio > target_ratio:
            self._image_width, self._image_height = width, int(width / image_ratio)
        else:
            self._image_width, self._image_height = int(height * image_ratio), height

    def process_interaction_event(self, event):
        event_type = event["type"]
        if event_type == "KeyDown":
            self._image_angle += self.rotation_step
        elif event_type == "MouseWheel":
            spin = event.get("spinY", None)  # Get scroll direction
            if spin is not None:
                self._image_angle += spin * self.rotation_step


@TrameApp()
class VanillaApp:
    def __init__(self, server=None):
        self.server = get_server(server, client_type="vue3")
        image_path = Path(__file__).parent / "trame_logo.png"
        self.window = RotatableImageWindow(image_path)
        self._build_ui()

    @property
    def state(self):
        return self.server.state

    @property
    def ctrl(self):
        return self.server.controller

    @change("rotation_step")
    def update_rotation_step(self, rotation_step, **kwargs):
        self.window.rotation_step = rotation_step

    def reset_rotation_step(self):
        self.state.rotation_step = DEFAULT_ROTATION_STEP

    def _build_ui(self):
        with SinglePageLayout(self.server, full_height=True) as layout:
            layout.title.set_text("RCA rendering")

            with layout.toolbar:
                v3.VSpacer()
                v3.VSlider(
                    label="Rotation step",
                    thumb_label=True,
                    thumb_size=10,
                    v_model=("rotation_step", DEFAULT_ROTATION_STEP),
                    min=15,
                    max=90,
                    step=5,
                    hide_details=True,
                    dense=True,
                    style="max-width: 300px",
                )

                v3.VBtn(icon="mdi-undo-variant", click=self.reset_rotation_step)

            with layout.content:
                with v3.VContainer(
                    fluid=True,
                    classes="pa-0 fill-height position-relative",
                ):
                    view = rca.RemoteControlledArea(
                        name="view",
                        display="image",
                        image_style=({},),  # restore default style with width: 100%
                    )
                    print(view.html)
                    self.view_handler = view.create_view_handler(
                        self.window,
                    )


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    app = VanillaApp()
    enable_testing(app.server)
    app.server.start()
