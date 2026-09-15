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
