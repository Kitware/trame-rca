import asyncio
import os
import sys
import uuid
from unittest.mock import MagicMock

import pytest
import pytest_asyncio
from playwright.async_api import async_playwright, expect
from trame.app import TrameApp, get_server
from trame.app.testing import enable_testing
from trame.decorators import change
from trame.ui.html import DivLayout
from vtkmodules.vtkFiltersSources import vtkConeSource
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleTrackballCamera
from vtkmodules.vtkInteractionWidgets import (
    vtkDistanceRepresentation2D,
    vtkDistanceWidget,
)
from vtkmodules.vtkRenderingCore import (
    vtkActor,
    vtkPolyDataMapper,
    vtkRenderer,
    vtkRenderWindow,
    vtkRenderWindowInteractor,
)

from trame.widgets import client, html, react
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
        self.left_release_event_mock = MagicMock()

    def process_interaction_event(self, event):
        if event.get("type") == "LeftButtonPress":
            self.left_press_event_mock(event)
        super().process_interaction_event(event)
        if event.get("type") == "LeftButtonRelease":
            self.left_release_event_mock(event)

    async def wait_for_left_releases(self, count):
        # Browser input returns before the throttled RPC queue reaches VTK.
        deadline = asyncio.get_running_loop().time() + 5
        while self.left_release_event_mock.call_count < count:
            assert asyncio.get_running_loop().time() < deadline, (
                f"Expected {count} completed clicks/drags, received "
                f"{self.left_release_event_mock.call_count} releases"
            )
            await asyncio.sleep(0.01)


class RcaInteractionApp(TrameApp):
    DEFAULT_CONE_RESOLUTION = 6

    def __init__(self, server=None, client_type="vue3"):
        super().__init__(server, client_type=client_type)
        self.render_window, self.cone_source, self.distance_widget = (
            self._create_render_window()
        )

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

        distance_widget_rep = vtkDistanceRepresentation2D()
        distance_widget = vtkDistanceWidget()
        distance_widget.SetInteractor(interactor)
        distance_widget.SetRepresentation(distance_widget_rep)

        return render_window, source, distance_widget

    def _build_ui(self):
        with DivLayout(self.server):
            client.Style(
                "html, body { margin: 0; height: 100%; }"
                ".rca-test-root { position: relative; width: 100%; height: 100vh; overflow: hidden; }"
                ".rca-test-gutter "
                "{ position: absolute; bottom: 0; left: 0; width: 100%; background-color: transparent; }"
                ".rca-test-slider { width: 100%; }"
            )
            with html.Div(classes="rca-test-root"):
                view = RemoteControlledArea(
                    display="image",
                    name="slider-test",
                    send_mouse_move=True,
                )
                with html.Div(classes="rca-test-gutter"):
                    self._build_resolution_slider()
                    self.state.distance_widget = False
                    html.Button(
                        "Distance Widget", click="distance_widget = !distance_widget;"
                    )

                self.view_handler = view.create_view_handler(
                    self.rca_window, encoder="png"
                )

    def _build_resolution_slider(self):
        slider = {
            "type": "range",
            "classes": "rca-test-slider",
            "min": 3,
            "max": 60,
            "step": 1,
        }
        if self.server.client_type == "react":
            html.Input(
                **slider,
                value=react.Bind("resolution", resolution=self.DEFAULT_CONE_RESOLUTION),
                on_change=react.Callback("resolution = Number($event.target.value)"),
            )
        else:
            html.Input(**slider, v_model=("resolution", self.DEFAULT_CONE_RESOLUTION))

    @change("resolution")
    def update_cone(self, resolution, **_):
        self.cone_source.SetResolution(int(resolution))
        self.view_handler.update()

    @change("distance_widget")
    def toggle_distance_widget(self, distance_widget, **_):
        self.distance_widget.SetEnabled(distance_widget)
        self.view_handler.update()


@pytest_asyncio.fixture(params=["vue3", "react"])
async def rca_interaction_app(request, unused_tcp_port):
    client_type = request.param
    server = get_server(
        f"test_rca_interaction_{client_type}_{uuid.uuid4()}", client_type=client_type
    )
    app = RcaInteractionApp(server, client_type=client_type)
    enable_testing(server)
    server.start(port=unused_tcp_port, exec_mode="task")
    try:
        await server.ready
        yield app
    finally:
        await server.stop()


@pytest.mark.asyncio
async def test_rca_view_is_interactive(rca_interaction_app: RcaInteractionApp):
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

        await browser.close()


@pytest.mark.asyncio
async def test_slider_drag_does_not_reach_rca(rca_interaction_app: RcaInteractionApp):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(f"http://127.0.0.1:{rca_interaction_app.server.port}/")

        image = page.locator("img.image-display-area")
        await expect(image).to_be_visible()
        slider = page.locator(".rca-test-slider")
        await expect(slider).to_be_visible()

        slider_box = await slider.bounding_box()
        image_box = await image.bounding_box()
        assert slider_box is not None
        assert image_box is not None

        # Start on the slider (off-center so the drag changes its value), then
        # enter the RCA while pressed. The slider must drive the cone resolution
        # while the press itself must not be captured by the RCA.
        initial_resolution = rca_interaction_app.state.resolution
        await page.mouse.move(
            slider_box["x"] + slider_box["width"] * 0.2,
            slider_box["y"] + slider_box["height"] / 2,
        )
        await page.mouse.down()
        await page.mouse.move(
            image_box["x"] + image_box["width"] / 2,
            image_box["y"] + image_box["height"] / 2,
            steps=10,
        )
        await page.mouse.up()
        await page.wait_for_timeout(100)

        assert int(rca_interaction_app.state.resolution) != initial_resolution
        assert rca_interaction_app.cone_source.GetResolution() == int(
            rca_interaction_app.state.resolution
        )
        assert rca_interaction_app.rca_window.left_press_event_mock.call_count == 0

        await browser.close()


@pytest.mark.asyncio
async def test_rca_drag_outside_slider_reaches_rca(
    rca_interaction_app: RcaInteractionApp,
):
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


@pytest.mark.asyncio
async def test_distance_widget_interaction_with_rca_scaling(
    rca_interaction_app: RcaInteractionApp,
):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(f"http://127.0.0.1:{rca_interaction_app.server.port}/")

        image = page.locator("img.image-display-area")
        rca = page.locator(".remote-controlled-area")
        await expect(image).to_be_visible()
        rca_box = await rca.bounding_box()
        assert rca_box is not None

        rca_interaction_app.distance_widget.On()
        y = rca_box["y"] + rca_box["height"] * 0.5
        x0 = rca_box["x"] + rca_box["width"] * 0.25
        x0_distance = (
            rca_interaction_app.distance_widget.GetRepresentation().GetDistance()
        )

        x1 = rca_box["x"] + rca_box["width"] * 0.5

        await page.mouse.click(x0, y)
        await page.mouse.click(x1, y)

        await rca_interaction_app.rca_window.wait_for_left_releases(2)
        x1_distance = (
            rca_interaction_app.distance_widget.GetRepresentation().GetDistance()
        )
        assert rca_interaction_app.rca_window.left_press_event_mock.call_count > 0
        assert x1_distance > x0_distance

        # Check that changing the scale does not impact the widget
        rca_interaction_app.view_handler.scale = 0.8

        x2 = rca_box["x"] + rca_box["width"] * 0.75
        await page.mouse.move(x1, y, steps=5)
        await page.mouse.down()
        await page.mouse.move(x2, y, steps=5)
        await page.mouse.up()

        await rca_interaction_app.rca_window.wait_for_left_releases(3)
        x2_distance = (
            rca_interaction_app.distance_widget.GetRepresentation().GetDistance()
        )
        assert rca_interaction_app.rca_window.left_press_event_mock.call_count > 0
        assert x2_distance > x1_distance

        await browser.close()


if __name__ == "__main__":
    app = RcaInteractionApp()
    app.server.start()
