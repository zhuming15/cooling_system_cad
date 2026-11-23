"""The station's design checks under pytest, one test per check section.

`uv run python assembly.py` remains the human-readable report; these tests run
the same section functions, so a failing check fails CI with its detail line.
The negative tests break the design on purpose and confirm the checks catch it.
"""

import pytest
from build123d import Pos, Rot

import assembly as A
from tools.checks import Report


def run(section, parts) -> Report:
    r = Report(echo=False)
    section(parts, r)
    return r


def test_every_section_function_is_run():
    defined = {n for n in dir(A) if n.startswith("check_") and callable(getattr(A, n))}
    assert defined == {s.__name__ for s in A.SECTIONS}


@pytest.mark.slow
@pytest.mark.parametrize("section", A.SECTIONS, ids=lambda s: s.__name__)
def test_section_passes(section, parts):
    r = run(section, parts)
    assert r.results, "section ran no checks"
    assert not r.failed(), "\n".join(f"{n}: {d}" for _, n, _, d in r.failed())


# --- negative tests: a broken design must fail -------------------------------
def failed_names(section, parts) -> set[str]:
    return {n for _, n, _, _ in run(section, parts).failed()}


def test_interference_catches_a_cap_pushed_into_the_valve(parts):
    bad = {k: parts[k] for k in ("valve_body", "valve_clamp_cap")}
    bad["valve_clamp_cap"] = Pos(0, -1.0, 0) * bad["valve_clamp_cap"]
    assert "no solid interference" in failed_names(A.check_interference, bad)


def test_flow_direction_catches_a_backwards_flowmeter(parts):
    bad = dict(parts)
    # turn the meter end for end about its own vertical axis: housing stays on top
    flip = Pos(A.X_FM, A.FCL.FM_Y, 0) * Rot(0, 0, 180) * Pos(-A.X_FM, -A.FCL.FM_Y, 0)
    for n in [n for n in parts if n.startswith("flowmeter_")]:
        bad[n] = flip * parts[n]
    assert "flowmeter arrow points along system flow" in failed_names(A.check_flow_direction, bad)


def test_alignment_catches_an_offset_link_tube(parts):
    bad = dict(parts)
    bad["tube_link"] = Pos(0, 0, 0.5) * parts["tube_link"]
    assert "tube on that axis, dead straight" in failed_names(A.check_alignment, bad)


def test_variation_catches_loose_tolerances(parts, monkeypatch):
    for stack in ("ALIGN_STACK_Z", "ALIGN_STACK_Y"):  # every part 3x less accurate
        monkeypatch.setattr(A, stack, tuple((t * 3, s) for t, s in getattr(A, stack)))
    names = failed_names(A.check_variation, parts)
    assert {"link tube strain, Monte Carlo 99.73 %", "link tube strain, RSS (3 sigma)"} <= names


def test_loads_catch_a_weak_wall_plug(parts, monkeypatch):
    monkeypatch.setattr(A, "WALL_PLUG_MAX", 30.0)
    assert "wall screws: load per M6 under a 500 N tube pull" in failed_names(A.check_loads, parts)


@pytest.mark.slow
def test_assembly_order_catches_link_tube_fitted_last(parts, monkeypatch):
    # the original README order: both components clamped first, link tube pushed in after
    order = [
        (label, tuple(p for p in prefixes if p != "tube_link"))
        for label, prefixes in A.ASSEMBLY_ORDER
    ]
    order.append(("link tube last", ("tube_link",)))
    monkeypatch.setattr(A, "ASSEMBLY_ORDER", tuple(order))
    assert "assembly order is collision-free" in failed_names(A.check_assembly_order, parts)
