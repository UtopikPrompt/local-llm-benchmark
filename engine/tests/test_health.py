"""Slice 0 tests: health endpoint.

Verified without the ``TestClient`` (which pulls in ``httpx``) by inspecting the
registered routes and calling the endpoint function directly, so the test suite
runs with only FastAPI/uvicorn installed.
"""

from app.main import app


def _find_health_route():
    """Return the ``Route`` whose path is ``/health``, or ``None``."""
    for route in app.routes:
        path = getattr(route, "path", None)
        if path == "/health":
            return route
    return None


def test_health_route_is_registered() -> None:
    route = _find_health_route()
    assert route is not None, "/health route is not registered"
    methods = getattr(route, "methods", None)
    assert methods and "GET" in methods, "/health must respond to GET"


def test_health_endpoint_returns_ok() -> None:
    route = _find_health_route()
    assert route is not None
    assert route.endpoint() == {"status": "ok"}


def test_health_is_json_compatible() -> None:
    body = _find_health_route().endpoint()
    # The contract is a JSON-serializable body with status == "ok".
    import json

    assert json.loads(json.dumps(body)) == {"status": "ok"}
