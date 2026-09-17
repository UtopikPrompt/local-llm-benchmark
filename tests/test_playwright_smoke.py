import os
import tempfile
import threading
import time

import pytest
import yaml
from pytest import MonkeyPatch

from local_llm_benchmark.server.api.controller import create_app
from playwright.sync_api import sync_playwright
from local_llm_benchmark.server.api import services as services_module


@pytest.fixture(scope="function")
def browser_url(monkeypatch: MonkeyPatch):
    config_data = {
        "engines": [
            {
                # A dummy engine; the smoke test only loads the dashboard and
                # never invokes the engine.
                "name": "Dummy",
                "base_url": "http://localhost:1",
            }
        ]
    }
    fd, path = tempfile.mkstemp(suffix=".yaml")
    with os.fdopen(fd, "w") as fh:
        fh.write(yaml.safe_dump(config_data))
    try:
        app = create_app(config_path=path)
        # Redirect benchmark reports to a throwaway dir so the test never
        # reads the real results/ directory.
        results_dir = tempfile.mkdtemp(prefix="pws-results-")
        monkeypatch.setattr(services_module, "DEFAULT_RESULTS_DIR", results_dir)

        import uvicorn

        server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=0))
        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()

        # Wait for uvicorn to bind the OS-assigned port. Scanning the bound
        # socket first works even before install() sets server_port.
        url = None
        deadline = time.time() + 10
        while time.time() < deadline:
            for sock in server.sockets:
                addr = sock.getsockname()
                if addr is not None:
                    url = f"http://127.0.0.1:{addr[1]}"
                    break
            if url is None:
                port = getattr(server, "server_port", None)
                if port is not None:
                    url = f"http://127.0.0.1:{port}"
            time.sleep(0.1)

        assert url is not None, "uvicorn did not bind a port in time"
        print("URL:", url)
        return url
    finally:
        os.remove(path)


def test_smoke(browser_url):
    url = browser_url
    print("URL:", url)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url)
        print("title:", page.title())
        print("h1:", page.inner_text("h1"))
        print("nav:", page.inner_text("#header-nav"))
        browser.close()


def test_select_all_models(browser_url):
    """End-to-end acceptance test for the global 'Select all models' checkbox.

    Exercises the full data flow: global checkbox -> per-engine checkboxes ->
    run-button gating, per ADR 0003 §2.1 and the stated acceptance test.
    """
    url = browser_url
    print("URL:", url)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url)
        print("title:", page.title())

        # The dashboard renders models after a short delay. Wait for the
        # results panel to appear and the global checkbox to be present.
        page.wait_for_selector("#all-models-checkbox", timeout=10000)
        page.wait_for_selector("#run-button", timeout=10000)

        global_checkbox = page.locator("#all-models-checkbox")
        run_button = page.locator("#run-button")
        model_checkboxes = page.locator(".model-checkbox")
        run_note = page.locator("#run-note")

        def count_checked():
            return model_checkboxes.filter_has_selector("input:checked").count()

        total = model_checkboxes.count()
        assert total > 0, "no model checkboxes rendered"

        # Step 1: with nothing selected, the run button is disabled.
        assert run_button.is_disabled(), "run button should be disabled when no model selected"
        assert count_checked() == 0, "no checkboxes should be checked initially"

        # Step 2: check the global checkbox -> all boxes ticked, run enabled.
        global_checkbox.check()
        assert count_checked() == total, "all checkboxes should be checked after ticking global"
        assert run_button.is_not_disabled(), "run button should be enabled after selecting a model"

        # Step 3: uncheck one individual box -> global becomes indeterminate,
        # run button stays enabled.
        model_checkboxes.first.uncheck()
        indeterminate = global_checkbox.evaluate("el => el.indeterminate")
        assert indeterminate, "global checkbox should be indeterminate after unchecking one"
        assert count_checked() == total - 1, "one checkbox should remain checked"
        assert run_button.is_not_disabled(), (
            "run button should stay enabled with one model selected"
        )

        # Step 4: select all again -> all ticked, global fully checked.
        model_checkboxes.first.click()
        assert count_checked() == total, "all checkboxes should be checked again"
        indeterminate = global_checkbox.evaluate("el => el.indeterminate")
        assert not indeterminate, "global checkbox should not be indeterminate when all selected"
        assert global_checkbox.is_checked(), "global checkbox should be fully checked"

        # Step 5: uncheck the global box -> all deselected, run button disabled.
        global_checkbox.uncheck()
        assert count_checked() == 0, "all checkboxes should be deselected after unchecking global"
        assert run_button.is_disabled(), (
            "run button should be disabled after deselecting all models"
        )

        browser.close()


def test_add_engine_button(browser_url):
    """Acceptance test for the 'Add Engine' button in the Benchmark panel.

    Clicking the button should open the engine CRUD modal with the expected
    fields, per ADR 0008/0009 and the frontend engine-modality pattern.
    """
    url = browser_url
    print("URL:", url)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url)
        print("title:", page.title())

        # The side menu (Benchmark panel) renders after a short delay.
        page.wait_for_selector("#add-engine", timeout=10000)

        add_engine = page.locator("#add-engine")
        assert add_engine.count() == 1, "expected exactly one Add Engine button"
        assert add_engine.is_visible(), "Add Engine button should be visible"

        # Click the button -> modal should open.
        add_engine.click()
        page.wait_for_selector("#engine-crud-modal", timeout=10000)

        modal = page.locator("#engine-crud-modal")
        assert modal.is_visible(), "engine CRUD modal should open after clicking Add Engine"
        assert modal.get_attribute("hidden") is None, "modal should not be hidden"

        # The modal should contain the expected fields.
        assert page.locator("#engine-name").count() == 1, "modal missing engine name field"
        assert page.locator("#engine-base-url").count() == 1, "modal missing base URL field"
        assert page.locator("#engine-model").count() == 1, "modal missing model field"

        # The save button should be enabled.
        save_button = page.locator("#save-engine-btn-widget")
        assert save_button.count() == 1, "modal missing save button"
        assert save_button.is_not_disabled(), "save button should be enabled"

        browser.close()
