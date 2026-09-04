import os
import sys
import uuid
from unittest.mock import MagicMock

import pytest
import pytest_asyncio
from playwright.async_api import async_playwright, expect
from trame.app import TrameApp, get_server
from trame.app.testing import enable_testing
from trame.ui.vuetify3 import SinglePageLayout
from trame_client.widgets.html import Div
from vtkmodules.vtkFiltersSources import vtkConeSource
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleTrackballCamera
from vtkmodules.vtkRenderingCore import (
    vtkActor,
    vtkPolyDataMapper,
    vtkRenderer,
    vtkRenderWindow,
    vtkRenderWindowInteractor,
)

from trame.widgets import vuetify3 as v3
from trame_rca.rca import VtkRemoteControlledArea
from trame_rca.widgets.rca import RemoteControlledArea

if os.environ.get("CI") is not None and sys.platform != "linux":
    pytest.skip(
        "Rendering tests are disabled on CI for non Linux platforms.",
        allow_module_level=True,
    )


class MockedVtkRemoteControlledArea(VtkRemoteControlledArea):
    def __init__(self, render_window):
        super().__init__(render_window)
        self.left_press_event_mock = MagicMock()

    def process_interaction_event(self, event):
        if event.get("type") == "LeftButtonPress":
            print(event)
            self.left_press_event_mock(event)
        super().process_interaction_event(event)


class RcaInteractionApp(TrameApp):
    def __init__(self, server=None):
        super().__init__(server)
        self.render_window = self._create_render_window()
        self.rca_window = MockedVtkRemoteControlledArea(self.render_window)
        self._build_ui()

    @staticmethod
    def _create_render_window():
        renderer = vtkRenderer()
        render_window = vtkRenderWindow()
        render_window.AddRenderer(renderer)
        render_window.SetSize(500, 400)

        interactor = vtkRenderWindowInteractor()
        interactor.SetRenderWindow(render_window)
        interactor.SetInteractorStyle(vtkInteractorStyleTrackballCamera())
        interactor.Initialize()

        source = vtkConeSource()
        mapper = vtkPolyDataMapper()
        mapper.SetInputConnection(source.GetOutputPort())
        actor = vtkActor()
        actor.SetMapper(mapper)
        renderer.AddActor(actor)
        renderer.ResetCamera()
        return render_window

    def _build_ui(self):
        with SinglePageLayout(self.server, full_height=True) as layout:
            layout.title.set_text("RCA slider interaction regression")
            with layout.content:
                with v3.VContainer(fluid=True, classes="pa-0 fill-height"):
                    with Div(
                        style="position: relative; width: 100%; height: 100%; overflow: hidden;",
                    ):
                        view = RemoteControlledArea(
                            display="image",
                            image_style=({},),
                            name="slider-test",
                            send_mouse_move=True,
                            style="position: relative; width: 100%; height: 100%;",
                        )
                        with Div(
                            classes="slice-slider-gutter",
                            style="position: absolute; bottom: 0; left: 0; background-color: transparent; width: 100%;",
                        ):
                            v3.VSlider(
                                v_model=("slider_value", 50),
                                min=0,
                                max=100,
                                step=1,
                                hide_details=True,
                                classes="slice-slider",
                            )
                    view.create_view_handler(self.rca_window, encoder="png")


@pytest_asyncio.fixture
async def rca_interaction_app(unused_tcp_port):
    server = get_server(f"test_rca_interaction_{uuid.uuid4()}", client_type="vue3")
    app = RcaInteractionApp(server)
    enable_testing(server)
    server.start(port=unused_tcp_port, exec_mode="task")
    try:
        await server.ready
        yield app
    finally:
        await server.stop()


@pytest.mark.asyncio
async def test_rca_view_is_interactive(rca_interaction_app):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(f"http://127.0.0.1:{rca_interaction_app.server.port}/")

        element = page.locator("img")
        await expect(element).to_be_visible()
        initial_img_url = await element.get_attribute("src")

        box = await element.bounding_box()
        assert box is not None

        await page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        await page.mouse.down()
        await page.mouse.move(
            box["x"] + box["width"] / 2 + 100, box["y"] + box["height"] / 2
        )
        await page.mouse.up()
        await page.wait_for_timeout(100)
        new_img_url = await element.get_attribute("src")

        assert initial_img_url != new_img_url


@pytest.mark.asyncio
async def test_slider_drag_does_not_reach_rca(rca_interaction_app):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(f"http://127.0.0.1:{rca_interaction_app.server.port}/")

        image = page.locator("img.image-display-area")
        await expect(image).to_be_visible()
        slider = page.locator(".v-slider")
        await expect(slider).to_be_visible()

        slider_box = await slider.bounding_box()
        image_box = await image.bounding_box()
        assert slider_box is not None
        assert image_box is not None

        # Start on the slider, then enter the RCA while pressed.
        start_x = slider_box["x"] + slider_box["width"] / 2
        start_y = slider_box["y"] + slider_box["height"] / 2
        await page.mouse.move(start_x, start_y)
        await page.mouse.down()
        await page.mouse.move(
            image_box["x"] + image_box["width"] / 2,
            image_box["y"] + image_box["height"] / 2,
        )
        await page.mouse.up()
        await page.wait_for_timeout(100)

        assert rca_interaction_app.rca_window.left_press_event_mock.call_count == 0

        await browser.close()


@pytest.mark.asyncio
async def test_rca_drag_outside_slider_reaches_rca(rca_interaction_app):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(f"http://127.0.0.1:{rca_interaction_app.server.port}/")

        image = page.locator("img.image-display-area")
        rca = page.locator(".remote-controlled-area")
        await expect(image).to_be_visible()
        rca_box = await rca.bounding_box()
        assert rca_box is not None

        # A click that starts outside the slider remains a normal RCA interaction.
        await rca.click(
            position={"x": rca_box["width"] - 100, "y": rca_box["height"] - 100}
        )
        await page.wait_for_timeout(100)
        assert rca_interaction_app.rca_window.left_press_event_mock.call_count == 1

        await browser.close()


if __name__ == "__main__":
    app = RcaInteractionApp()
    app.server.start()
