"""Shared pytest fixtures for the local-llm-benchmark test suite.

The :class:`~local_llm_benchmark.config.Defaults` engine registry is a shared,
class-level attribute. The API ``create_app`` entry point intentionally copies
the engines from the active config file into ``Defaults.engines`` so the
dashboard's engine dropdown and the ``/run`` multi-engine picker can use them.

Because that attribute is shared across every test module, an e2e test that
boots the API app with a temporary config (e.g. the ``client`` fixture in
``test_api_e2e.py``) can leak engine entries into the registry and break other
tests that assert on a pristine, empty registry. The autouse session-scoped
fixture below resets the registry after every test so tests never observe each
other's mutations.
"""

import pytest


@pytest.fixture(scope="function", autouse=True)
def _reset_defaults_registry():
    """Reset ``Defaults.engines`` to its pristine empty state around each test.

    ``Defaults.engines`` is a shared class-level attribute; the API
    ``create_app`` entry point copies the active config's engines into it. An
    e2e test booting the app with a temporary config (e.g. the ``client``
    fixture in ``test_api_e2e.py``) leaks those entries into the registry. A
    session-scoped reset would only clean up once, at the end of the session, so
    any test running after that pollution would still observe it. Function
    scope restores the registry before and after every test.
    """
    import local_llm_benchmark.config as c

    original = list(c.Defaults.engines)
    yield
    c.Defaults.engines = original
