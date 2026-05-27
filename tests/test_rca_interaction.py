import os
import pytest
import sys
from playwright.sync_api import expect, sync_playwright


if os.environ.get("CI") is not None and sys.platform != "linux":
    pytest.skip(
        "Rendering tests are disabled on CI for non Linux platforms.",
        allow_module_level=True,
    )


@pytest.mark.parametrize("server_path", ["examples/01_vtk/vtk_cone_simple.py"])
def test_rca_view_is_interactive(server):
    with sync_playwright() as p:
        url = f"http://127.0.0.1:{server.port}/"
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url)

        element = page.locator("img")
        expect(element).to_be_visible()
        initial_img_url = element.get_attribute("src")

        box = element.bounding_box()
        assert box is not None

        page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        page.mouse.down()
        page.mouse.move(box["x"] + box["width"] / 2 + 100, box["y"] + box["height"] / 2)
        page.mouse.up()
        page.wait_for_timeout(100)
        new_img_url = element.get_attribute("src")

        assert initial_img_url != new_img_url
