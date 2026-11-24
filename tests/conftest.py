"""Shared pytest setup: import paths and the station built once per session.

Part folders are not packages (AGENTS.md), so they go on sys.path here, the
same way the entry scripts do it.
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
for sub in (
    "",
    "valve",
    "valve_connector",
    "valve_clamp",
    "flowmeter",
    "flowmeter_connector",
    "flowmeter_electronic_interconnect",
    "flowmeter_clamp",
):
    sys.path.insert(0, str(ROOT / sub))


@pytest.fixture(scope="session")
def parts():
    """Every placed part of the station, as assembly.build() returns them."""
    import assembly as A

    return A.build()


def pytest_collection_modifyitems(config, items):
    """Start long geometry checks early, with a cheap next-item reservation.

    xdist reserves the next item on each worker. Interleaving a fixture-free
    test keeps two long checks from being queued on the same worker at startup.
    The serial debug order remains unchanged.
    """
    if not (config.getoption("numprocesses", default=0) or hasattr(config, "workerinput")):
        return
    long = [item for item in items if item.get_closest_marker("long_geometry")]
    remaining = [item for item in items if item not in long]
    ordered = []
    for item in long:
        ordered.append(item)
        spacer = next((test for test in remaining if "parts" not in test.fixturenames), None)
        if spacer is not None:
            remaining.remove(spacer)
            ordered.append(spacer)
    items[:] = ordered + remaining
