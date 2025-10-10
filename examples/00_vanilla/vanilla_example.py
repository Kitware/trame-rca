from numpy import asarray
from pathlib import Path
from PIL import Image
from trame.app import TrameApp
from trame.app.testing import enable_testing
from trame.decorators import change
from trame_rca.widgets import rca
from trame.ui.vuetify3 import SinglePageLayout
from trame.widgets import vuetify3 as v3
from trame_client.module.vue3 import www


DEFAULT_ROTATION_STEP = 45


class RotatableImageWindow:
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


class VanillaApp(TrameApp):
    def __init__(self, server=None):
        super().__init__(server)
        image_path = Path(www) / "logo.png"
        self.window = RotatableImageWindow(image_path)
        self._build_ui()

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
                        display="image",
                        image_style=({},),  # restore default style with width: 100%
                    )
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
