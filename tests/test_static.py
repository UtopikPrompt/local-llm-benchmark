"""Tests for the static asset server (:class:`Static`, :func:`install`).

Covers path traversal protection, file resolution, and the content-type
dispatch for the dashboard assets and saved reports.
"""

from pathlib import Path

from fastapi import FastAPI

from local_llm_benchmark.server import static


def _server(tmp_path):
    (tmp_path / "dashboard.html").write_text("<html></html>")
    (tmp_path / "style.css").write_text("body {}")
    (tmp_path / "chart.js").write_text("console.log('x')")
    (tmp_path / "report.json").write_text('{"ok": true}')
    return tmp_path


def test_resolve_inside_root(tmp_path):
    server = static.Static(tmp_path)
    assert server.resolve("dashboard.html") == (tmp_path / "dashboard.html").resolve()


def test_resolve_returns_none_for_traversal(tmp_path):
    server = static.Static(_server(tmp_path))
    assert server.resolve("../../etc/passwd") is None
    assert server.resolve("../secret") is None
    assert server.resolve("/../escape") is None


def test_resolve_returns_none_for_missing_file(tmp_path):
    server = static.Static(_server(tmp_path))
    assert server.resolve("missing.html") is None


def test_resolve_returns_none_for_directory(tmp_path):
    (tmp_path / "subdir").mkdir()
    server = static.Static(tmp_path)
    assert server.resolve("subdir") is None


def test_call_dispatches_content_types(tmp_path):
    server = static.Static(_server(tmp_path))

    html = server.__call__(None, url_path="dashboard.html")
    assert html.media_type == "text/html"

    css = server.__call__(None, url_path="style.css")
    assert css.media_type == "text/css"

    js = server.__call__(None, url_path="chart.js")
    assert js.media_type == "text/javascript"

    json_resp = server.__call__(None, url_path="report.json")
    assert json_resp.media_type == "application/json"


def test_call_not_found_raises(tmp_path):
    server = static.Static(_server(tmp_path))
    try:
        server.__call__(None, url_path="missing.html")
    except static.NotFound:
        pass
    else:
        raise AssertionError("expected NotFound for a missing file")


def test_install_mounts_route(tmp_path):
    root = _server(tmp_path)
    app = FastAPI()
    static.install(app, root)
    routes = [route.path for route in app.routes]
    assert "/" in routes


def test_resolve_root_returns_itself(tmp_path):
    server = static.Static(tmp_path)
    assert server.resolve(".") == server._root


def test_resolve_normalizes_whitespace_and_slashes(tmp_path):
    server = static.Static(tmp_path)
    assert server.resolve("  chart.js ") == (tmp_path / "chart.js").resolve()
