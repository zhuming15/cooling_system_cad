"""Unit tests for tools/checks.py.

Each check gets a known-good geometry and a deliberately bad one, so every
function is proven both to pass and to fail.
"""

import math

import pytest
from build123d import Box, Cylinder, Pos, Rot

from tools import checks as CK


# --- geometry --------------------------------------------------------------
def test_overlap_measures_shared_volume():
    a = Box(10, 10, 10)
    assert CK.overlap(a, Pos(5, 0, 0) * Box(10, 10, 10)) == pytest.approx(500, rel=1e-6)
    assert CK.overlap(a, Pos(20, 0, 0) * Box(10, 10, 10)) == 0.0


def test_interferences_lists_only_clashing_pairs():
    parts = {
        "a": Box(10, 10, 10),
        "b": Pos(9, 0, 0) * Box(10, 10, 10),  # 1 mm into a
        "c": Pos(30, 0, 0) * Box(10, 10, 10),
    }
    hits = CK.interferences(parts)
    assert [(na, nb) for _, na, nb in hits] == [("a", "b")]
    assert hits[0][0] == pytest.approx(100, rel=1e-6)


def test_ray_clear_finds_blocking_parts():
    parts = {"wall": Pos(0, 20, 0) * Box(30, 4, 30), "side": Pos(40, 20, 0) * Box(10, 4, 10)}
    probe = CK.axis_probe(6, (0, 0, 0), (0, 1, 0), 50)
    assert CK.ray_clear(parts, probe) == ["wall"]
    assert CK.ray_clear(parts, probe, ignore={"wall"}) == []
    assert CK.ray_clear(parts, CK.axis_probe(6, (0, 0, 0), (0, -1, 0), 50)) == []


def test_sweep_detects_a_blocked_path():
    # a peg pushed down -Y into a plate with a hole, then into one without
    peg = Pos(0, 5, 0) * Rot(90, 0, 0) * Cylinder(2, 10)
    holed = Box(20, 4, 20) - Rot(90, 0, 0) * Cylinder(2.5, 10)
    solid = Box(20, 4, 20)
    clear = CK.sweep({"peg": peg, "plate": holed}, ["peg"], ["plate"], travel=20)
    blocked = CK.sweep({"peg": peg, "plate": solid}, ["peg"], ["plate"], travel=20)
    assert clear == {}
    assert ("peg", "plate") in blocked


# --- manufacturing ---------------------------------------------------------
def test_overhangs_bridge_span():
    # an arch: two 5 mm legs, 12 mm bridge on top, printed with +Z up
    arch = Pos(0, 0, 10) * Box(22, 10, 20) - Pos(0, 0, 7.5) * Box(12, 12, 15)
    spans, bad = CK.overhangs(arch, (0, 0, 1))
    assert max(spans) == pytest.approx(10.0)  # the smaller width of the bridge face
    assert bad == []


def test_overhangs_flags_big_horizontal_hole_only():
    block = Pos(0, 0, 15) * Box(40, 10, 30)
    small = block - Pos(0, 0, 15) * Rot(90, 0, 0) * Cylinder(4, 20)  # dia 8
    big = block - Pos(0, 0, 15) * Rot(90, 0, 0) * Cylinder(10, 20)  # dia 20
    assert CK.overhangs(small, (0, 0, 1), hole_self_support_r=5.0)[1] == []
    assert CK.overhangs(big, (0, 0, 1), hole_self_support_r=5.0)[1] != []


def test_min_wall_finds_thin_wall():
    cup = Box(20, 20, 20) - Pos(0, 0, 1) * Box(18, 18, 20)  # 1 mm walls, open top
    assert CK.min_wall(cup) == pytest.approx(1.0, abs=0.02)
    thick = Box(20, 20, 20) - Pos(0, 0, 5) * Box(10, 10, 20)  # 5 mm walls
    assert CK.min_wall(thick) == pytest.approx(5.0, abs=0.02)


def test_is_flat_profile():
    plate = Box(50, 6, 30) - Rot(90, 0, 0) * Cylinder(3, 10)
    assert CK.is_flat_profile(plate, 6, axis=1)
    assert not CK.is_flat_profile(plate, 5, axis=1)  # wrong sheet
    counterbore = plate - Pos(10, 3, 0) * Rot(90, 0, 0) * Cylinder(4, 4)  # blind step
    assert not CK.is_flat_profile(counterbore, 6, axis=1)  # a ledge inside the sheet
    through = plate - Pos(10, 0, 0) * Rot(90, 0, 0) * Cylinder(4, 10)
    assert CK.is_flat_profile(through, 6, axis=1)
    from build123d import Axis, chamfer

    corner = chamfer(plate.edges().filter_by(Axis.Y)[0], 1)
    assert CK.is_flat_profile(corner, 6, axis=1)  # outline chamfer, square to the sheet
    sloped = chamfer(plate.edges().filter_by(Axis.Z)[0], 1)
    assert not CK.is_flat_profile(sloped, 6, axis=1)  # slope across the sheet: not laser


def test_max_extent():
    assert CK.max_extent(Box(120, 30, 40), (0, 2)) == pytest.approx(120)
    assert CK.max_extent(Box(120, 30, 40), (1, 2)) == pytest.approx(40)


# --- tolerance -------------------------------------------------------------
TERMS = [(0.2, 1), (0.2, -1), (0.1, 1)]


def test_worst_case_and_rss():
    assert CK.worst_case(TERMS) == pytest.approx(0.5)
    assert CK.rss(TERMS) == pytest.approx(math.sqrt(0.09))
    assert CK.rss(TERMS) < CK.worst_case(TERMS)
    assert CK.rss([(0.3, 1)]) == pytest.approx(CK.worst_case([(0.3, 1)]))  # one term: equal


def test_monte_carlo_is_repeatable_and_bounded():
    a = CK.monte_carlo([TERMS], n=50_000, seed=3)
    assert a == CK.monte_carlo([TERMS], n=50_000, seed=3)
    assert CK.rss(TERMS) < a < CK.worst_case(TERMS)  # uniform MC sits between
    # one uniform term: the 99.73 % point of |U(-t, t)| is 0.9973 t
    assert CK.monte_carlo([[(1.0, 1)]], n=400_000) == pytest.approx(0.9973, abs=0.005)


# --- mechanics -------------------------------------------------------------
def test_mechanics_formulas():
    assert CK.preload(0.5, 4.0) == pytest.approx(625)
    assert CK.annulus_area(9, 4.3) == pytest.approx(math.pi / 4 * (81 - 4.3**2))
    assert CK.hex_bearing_area(7, 4.5) == pytest.approx(3**0.5 / 2 * 49 - math.pi / 4 * 4.5**2)
    assert CK.fixed_fixed_strain(12, 1.0, 100) == pytest.approx(0.0036)
    assert CK.thermal_growth(20, [(1e-4, 100), (2e-5, 50)]) == pytest.approx(0.22)
    assert CK.end_thrust(0.6, 12) == pytest.approx(67.86, abs=0.01)


def test_tip_factor_takes_the_weaker_edge():
    # screws at x = -15, 15; edges at -21, 21; 625 N each; 9 N.m overturning
    k = CK.tip_factor(625, (-15, 15), (-21, 21), 9.0)
    assert k == pytest.approx(625 * (6 + 36) / 1000 / 9)
    assert CK.tip_factor(625, (-15, 15), (-21, 21), 30.0) < 1  # too weak: fails


def test_wall_screw_load():
    per, tension, shear = CK.wall_screw_load(9.81, 500, 30, 300, 8)
    assert tension == pytest.approx(500 * 0.03 / 0.3 / 2)
    assert shear == pytest.approx((9.81**2 + 500**2) ** 0.5 / 8)
    assert per == pytest.approx((tension**2 + shear**2) ** 0.5)


def test_report_counts_failures():
    r = CK.Report(echo=False)
    r.start("x")
    r.check("good", True, "")
    r.check("bad", False, "why")
    assert r.fails == 1
    assert r.failed() == [("x", "bad", False, "why")]
