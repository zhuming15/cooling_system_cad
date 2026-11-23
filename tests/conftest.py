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
    "flowmeter_clamp",
):
    sys.path.insert(0, str(ROOT / sub))


@pytest.fixture(scope="session")
def parts():
    """Every placed part of the station, as assembly.build() returns them."""
    import assembly as A

    return A.build()
