import os
import tempfile
import threading
import time

import pytest
import yaml
from playwright.sync_api import sync_playwright
from pytest import MonkeyPatch

from local_llm_benchmark.server.api import services as services_module
from local_llm_benchmark.server.api.controller import create_app


def wait_for_selector(page: pytest.PlaywrightBrowser, selector: str, timeout: int = 10000):
    """Helper to wait for a selector with retry logic."""
    page.wait_for_selector(selector, timeout=timeout)


def wait_for_not_selector(page: pytest.PlaywrightBrowser, selector: str, timeout: int = 10000):
    """Helper to wait for a selector to NOT be present."""
    page.wait_for_selector(f"{selector}:not(:any)", timeout=timeout)


def count_checkbox_checked(page: pytest.PlaywrightBrowser, checkbox_locator):
    """Count how many checkboxes are checked."""
    return checkbox_locator.filter_has_selector('input:checked').count()


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


class DashboardTests:
    """Test suite for Dashboard view functionality."""

    def test_nav_to_dashboard(self, browser_url):
        """Verify navigation to Dashboard view."""
        url = browser_url
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(url)

            # Verify dashboard is initially active
            dashboard_tab = page.locator('.nav-tab[data-view="dashboard"]')
            assert dashboard_tab.is_visible(), "Dashboard tab should be visible"
            assert dashboard_tab.get_attribute('aria-current') == 'page', "Dashboard tab should be active"

            # Click dashboard tab - should remain active (already on dashboard)
            dashboard_tab.click()
            assert dashboard_tab.get_attribute('aria-current') == 'page', "Dashboard tab should remain active"

            browser.close()

    def test_nav_to_benchmark(self, browser_url):
        """Verify navigation to Benchmark view."""
        url = browser_url
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(url)

            # Verify dashboard is initially active
            benchmark_tab = page.locator('.nav-tab[data-view="benchmark"]')
            assert benchmark_tab.is_visible(), "Benchmark tab should be visible"
            assert benchmark_tab.get_attribute('aria-current') != 'page', "Benchmark tab should not be active initially"

            # Click benchmark tab
            benchmark_tab.click()
            
            # Verify navigation happened
            assert page.locator('#view-dashboard').is_hidden(), "Dashboard view should be hidden"
            assert page.locator('#view-benchmark').is_visible(), "Benchmark view should be visible"
            assert benchmark_tab.get_attribute('aria-current') == 'page', "Benchmark tab should be active"

            # Navigate back to dashboard
            dashboard_tab = page.locator('.nav-tab[data-view="dashboard"]')
            dashboard_tab.click()
            assert page.locator('#view-dashboard').is_visible(), "Dashboard view should be visible again"

            browser.close()

    def test_nav_to_challenges(self, browser_url):
        """Verify navigation to Challenges view."""
        url = browser_url
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(url)

            # Verify dashboard is initially active
            challenges_tab = page.locator('.nav-tab[data-view="challenges"]')
            assert challenges_tab.is_visible(), "Challenges tab should be visible"
            assert challenges_tab.get_attribute('aria-current') != 'page', "Challenges tab should not be active initially"

            # Click challenges tab
            challenges_tab.click()
            
            # Verify navigation happened
            assert page.locator('#view-dashboard').is_hidden(), "Dashboard view should be hidden"
            assert page.locator('#view-challenges').is_visible(), "Challenges view should be visible"
            assert challenges_tab.get_attribute('aria-current') == 'page', "Challenges tab should be active"

            # Navigate back to dashboard
            dashboard_tab = page.locator('.nav-tab[data-view="dashboard"]')
            dashboard_tab.click()
            assert page.locator('#view-dashboard').is_visible(), "Dashboard view should be visible again"

            browser.close()

    def test_results_table_initial_render(self, browser_url):
        """Verify results table renders on dashboard."""
        url = browser_url
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(url)

            # Wait for results table to render
            page.wait_for_selector("#results-table", timeout=10000)
            
            assert page.locator("#results-table").is_visible(), "Results table should be visible"
            # Table should have some content (even if just headers)
            rows = page.locator("#results-table tr")
            assert rows.count() > 0, "Results table should have rows"

            browser.close()

    def test_results_search_filter(self, browser_url):
        """Verify search filter functionality on dashboard."""
        url = browser_url
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(url)

            # Wait for results to render
            page.wait_for_selector("#results-table", timeout=10000)
            
            # Get initial row count
            initial_rows = page.locator("#results-table tr").count()
            assert initial_rows > 0, "Should have initial results"

            # Enter search term
            search_input = page.locator("#results-search")
            search_input.fill("test")
            search_input.press("Enter")

            # Wait for filtered results
            page.wait_for_timeout(500)
            
            filtered_rows = page.locator("#results-table tr").count()
            assert filtered_rows <= initial_rows, "Search should not increase results count"

            # Clear search
            search_input.clear()
            search_input.fill("")
            search_input.press("Enter")

            # Wait for full results
            page.wait_for_timeout(500)
            
            full_rows = page.locator("#results-table tr").count()
            assert full_rows >= initial_rows, "Clearing search should restore results"

            browser.close()


class BenchmarkViewTests:
    """Test suite for Benchmark view functionality."""

    def test_benchmark_view_render(self, browser_url):
        """Verify Benchmark view renders correctly."""
        url = browser_url
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(url)

            # Navigate to benchmark view
            page.locator('.nav-tab[data-view="benchmark"]').click()
            page.wait_for_selector("#side-menu", timeout=10000)
            
            assert page.locator('#side-menu').is_visible(), "Side menu should be visible"
            assert page.locator('#engine-list').is_visible(), "Engine list container should be visible"

            # Verify engine list content exists
            engine_items = page.locator('#engine-list-content')
            assert engine_items.count() > 0, "Should have engine items"

            browser.close()

    def test_refresh_models_button(self, browser_url):
        """Verify Refresh Engines button functionality."""
        url = browser_url
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(url)

            # Navigate to benchmark
            page.locator('.nav-tab[data-view="benchmark"]').click()
            page.wait_for_selector("#refresh-models", timeout=10000)
            
            refresh_button = page.locator("#refresh-models")
            assert refresh_button.is_visible(), "Refresh button should be visible"

            # Click refresh
            refresh_button.click()
            
            # Button should show loading state
            assert refresh_button.is_disabled(), "Refresh button should be disabled during loading"

            browser.close()

    def test_add_engine_button(self, browser_url):
        """Verify Add Engine button opens CRUD modal."""
        url = browser_url
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(url)

            # Navigate to benchmark
            page.locator('.nav-tab[data-view="benchmark"]').click()
            page.wait_for_selector("#add-engine", timeout=10000)
            
            add_engine = page.locator("#add-engine")
            assert add_engine.is_visible(), "Add Engine button should be visible"

            # Click to open modal
            add_engine.click()
            page.wait_for_selector("#engine-crud-modal", timeout=10000)
            
            assert page.locator("#engine-crud-modal").is_visible(), "CRUD modal should be visible"

            browser.close()

    def test_run_button_enabled_with_models(self, browser_url):
        """Verify run button is enabled when models are selected."""
        url = browser_url
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(url)

            # Navigate to benchmark
            page.locator('.nav-tab[data-view="benchmark"]').click()
            page.wait_for_selector("#all-models-checkbox", timeout=10000)
            
            global_checkbox = page.locator("#all-models-checkbox")
            run_button = page.locator("#run-button")
            
            # Initially, run button should be disabled
            assert run_button.is_disabled(), "Run button should be disabled initially"

            # Select all models
            global_checkbox.check()
            
            # Run button should now be enabled
            assert run_button.is_not_disabled(), "Run button should be enabled after selecting models"

            browser.close()


class ChallengesViewTests:
    """Test suite for Challenges view functionality."""

    def test_challenges_view_render(self, browser_url):
        """Verify Challenges view renders correctly."""
        url = browser_url
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(url)

            # Navigate to challenges view
            page.locator('.nav-tab[data-view="challenges"]').click()
            page.wait_for_selector("#challenges-toolbar", timeout=10000)
            
            assert page.locator("#challenges-toolbar").is_visible(), "Challenges toolbar should be visible"
            assert page.locator("#challenge-items-list").is_visible(), "Challenges list container should be visible"

            # Verify toolbar elements
            title = page.locator(".panel-title")
            assert title.count() > 0, "Should have panel title"

            browser.close()

    def test_all_challenges_checkbox(self, browser_url):
        """Verify All Challenges checkbox functionality."""
        url = browser_url
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(url)

            # Navigate to challenges
            page.locator('.nav-tab[data-view="challenges"]').click()
            page.wait_for_selector("#all-challenges-checkbox", timeout=10000)
            
            all_challenges = page.locator("#all-challenges-checkbox")
            run_all_button = page.locator("#run-challenge-batch-button")
            
            # Initially, run button should be disabled
            assert run_all_button.is_disabled(), "Run All Challenges button should be disabled initially"

            # Select all challenges
            all_challenges.check()
            
            # Run button should now be enabled
            assert run_all_button.is_not_disabled(), "Run All Challenges button should be enabled"

            # Uncheck all challenges
            all_challenges.uncheck()
            
            # Run button should be disabled again
            assert run_all_button.is_disabled(), "Run All Challenges button should be disabled"

            browser.close()

    def test_run_all_challenges_button(self, browser_url):
        """Verify Run All Challenges button behavior."""
        url = browser_url
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(url)

            # Navigate to challenges
            page.locator('.nav-tab[data-view="challenges"]').click()
            page.wait_for_selector("#run-challenge-batch-button", timeout=10000)
            
            run_all = page.locator("#run-challenge-batch-button")
            
            # Initially disabled
            assert run_all.is_disabled(), "Button should be disabled initially"

            # Check all challenges
            page.locator("#all-challenges-checkbox").check()
            
            # Now enabled
            assert run_all.is_not_disabled(), "Button should be enabled"

            # Click to trigger
            run_all.click()
            
            # Button should be disabled again after click
            assert run_all.is_disabled(), "Button should be disabled after click"

            browser.close()


class UIInteractionTests:
    """Test suite for UI interaction patterns."""

    def test_model_checkbox_state(self, browser_url):
        """Verify model checkbox states (checked, unchecked, indeterminate)."""
        url = browser_url
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(url)

            # Navigate to benchmark
            page.locator('.nav-tab[data-view="benchmark"]').click()
            page.wait_for_selector("#all-models-checkbox", timeout=10000)
            
            global_checkbox = page.locator("#all-models-checkbox")
            model_checkboxes = page.locator(".model-checkbox")
            
            # Initially unchecked
            assert not global_checkbox.is_checked(), "Global checkbox should be unchecked"
            assert count_checkbox_checked(page, model_checkboxes) == 0, "No models selected"

            # Check all
            global_checkbox.check()
            assert global_checkbox.is_checked(), "Global checkbox should be checked"
            
            # Uncheck one individual
            model_checkboxes.first.uncheck()
            indeterminate = global_checkbox.evaluate("el => el.indeterminate")
            assert indeterminate, "Global should be indeterminate when some unchecked"
            
            # Check all again
            model_checkboxes.first.click()
            assert not global_checkbox.is_indeterminate(), "Global should not be indeterminate when all selected"
            
            # Uncheck all
            global_checkbox.uncheck()
            assert not global_checkbox.is_checked(), "Global should be unchecked"

            browser.close()

    def test_header_navigation_accessibility(self, browser_url):
        """Verify header navigation is accessible."""
        url = browser_url
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(url)

            # Verify header structure
            header = page.locator('#header-nav')
            assert header.is_visible(), "Header should be visible"
            
            # Verify all tabs are present
            tabs = page.locator('.nav-tab')
            assert tabs.count() == 3, "Should have 3 navigation tabs"
            
            # Verify aria attributes
            for tab in tabs:
                assert tab.get_attribute('aria-label') is not None, "Tab should have aria-label"

            browser.close()

    def test_results_search_validation(self, browser_url):
        """Verify search input validation."""
        url = browser_url
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(url)

            # Navigate to dashboard
            page.locator('.nav-tab[data-view="dashboard"]').click()
            page.wait_for_selector("#results-search", timeout=10000)
            
            search_input = page.locator("#results-search")
            
            # Should accept any text
            search_input.fill("test")
            assert search_input.is_enabled(), "Search should accept text"
            
            # Should clear on backspace
            search_input.press("Backspace")
            assert search_input.input_value() == "", "Should clear on backspace"

            browser.close()

    def test_page_title_content(self, browser_url):
        """Verify page title is set correctly."""
        url = browser_url
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(url)

            # Verify title
            title = page.title()
            assert "Local LLM Benchmark" in title, f"Page title should contain 'Local LLM Benchmark', got: {title}"

            browser.close()


class NavigationTests:
    """Test suite for navigation between views."""

    def test_view_panel_visibility_state(self, browser_url):
        """Verify view panels show/hide correctly."""
        url = browser_url
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(url)

            # Initially on dashboard
            assert page.locator('#view-dashboard').is_visible(), "Dashboard should be visible initially"
            assert page.locator('#view-benchmark').is_hidden(), "Benchmark should be hidden initially"
            assert page.locator('#view-challenges').is_hidden(), "Challenges should be hidden initially"

            # Navigate to benchmark
            page.locator('.nav-tab[data-view="benchmark"]').click()
            assert page.locator('#view-benchmark').is_visible(), "Benchmark should be visible"
            assert page.locator('#view-dashboard').is_hidden(), "Dashboard should be hidden"
            assert page.locator('#view-challenges').is_hidden(), "Challenges should be hidden"

            # Navigate to challenges
            page.locator('.nav-tab[data-view="challenges"]').click()
            assert page.locator('#view-challenges').is_visible(), "Challenges should be visible"
            assert page.locator('#view-benchmark').is_hidden(), "Benchmark should be hidden"
            assert page.locator('#view-dashboard').is_hidden(), "Dashboard should be hidden"

            # Navigate back to dashboard
            page.locator('.nav-tab[data-view="dashboard"]').click()
            assert page.locator('#view-dashboard').is_visible(), "Dashboard should be visible"

            browser.close()


def run_all_tests():
    """Run all test suites."""
    import traceback
    
    print("\n" + "="*60)
    print("Running Local LLM Benchmark E2E Test Suite")
    print("="*60)
    
    test_classes = [
        DashboardTests,
        BenchmarkViewTests,
        ChallengesViewTests,
        UIInteractionTests,
        NavigationTests
    ]
    
    for test_class in test_classes:
        print(f"\nRunning {test_class.__name__}...")
        instance = test_class()
        
        for method_name in dir(instance):
            if method_name.startswith('test_'):
                method = getattr(instance, method_name)
                if callable(method):
                    try:
                        method(browser_url)
                        print(f"  ✓ {method_name}")
                    except AssertionError as e:
                        print(f"  ✗ {method_name}: {e}")
                        traceback.print_exc()
                    except Exception as e:
                        print(f"  ✗ {method_name}: {e}")
                        traceback.print_exc()
    
    print("\n" + "="*60)
    print("Test suite complete!")
    print("="*60)


if __name__ == "__main__":
    # Run all tests
    import sys
    sys.exit(run_all_tests())
