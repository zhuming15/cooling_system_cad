"""Unit tests for tools/checks.py.

Each check gets a known-good geometry and a deliberately bad one, so every
function is proven both to pass and to fail.
"""

import math

import pytest
from build123d import Axis, Box, Cylinder, Pos, Rot, chamfer

from tools import checks as CK


# --- geometry --------------------------------------------------------------
def test_overlap_measures_shared_volume():
    a = Box(10, 10, 10)
    assert CK.overlap(a, Pos(5, 0, 0) * Box(10, 10, 10)) == pytest.approx(500, rel=1e-6)
    assert CK.overlap(a, Pos(20, 0, 0) * Box(10, 10, 10)) == 0.0


@pytest.mark.parametrize("reverse", [False, True])
def test_overlap_includes_containment_and_equal_boxes(reverse):
    a, b = Box(10, 10, 10), Box(2, 2, 2)
    if reverse:
        a, b = b, a
    assert CK.overlap(a, b) == pytest.approx(8)
    assert CK.overlap(a, a) == pytest.approx(a.volume)
    assert CK.overlap(a, Pos(30, 0, 0) * b) == 0


def test_interference_bounds_are_calculated_once_and_not_retained(monkeypatch):
    from build123d import Shape

    original = Shape.bounding_box
    calls = []

    def counted(self, *args, **kwargs):
        calls.append(self)
        return original(self, *args, **kwargs)

    parts = {str(i): Pos(i * 20, 0, 0) * Box(2, 2, 2) for i in range(10)}
    monkeypatch.setattr(Shape, "bounding_box", counted)
    assert CK.interferences(parts) == []
    assert len(calls) == len(parts)
    parts["1"] = parts["0"].moved(Pos(0.1, 0, 0))
    assert [(a, b) for _, a, b in CK.interferences(parts)] == [("0", "1")]


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


def test_is_pocketed_profile():
    plate = Box(50, 12, 30) - Rot(90, 0, 0) * Cylinder(3, 20)
    pocket = plate - Pos(10, -6, 0) * Box(8, 12, 8)  # 6 deep from the lower face
    assert CK.is_pocketed_profile(pocket, 12, [6.0], axis=1)
    assert not CK.is_pocketed_profile(pocket, 12, [4.0], axis=1)  # floor at an unlisted depth
    assert not CK.is_pocketed_profile(pocket, 10, [6.0], axis=1)  # wrong sheet
    sloped = chamfer(plate.edges().filter_by(Axis.Z)[0], 1)
    assert not CK.is_pocketed_profile(sloped, 12, [6.0], axis=1)  # slope across the sheet


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


@pytest.mark.parametrize("axis", [(1, 0, 0), (0, 0, -1), (0.6, 0.8, 0)])
def test_sweep_box_pruning_keeps_contacts_for_each_direction(axis):
    moving = Box(2, 2, 2)
    stop = Pos(*(-3 * v for v in axis)) * Box(2, 2, 2)
    far = Pos(100, 100, 100) * Box(2, 2, 2)
    parts = {"moving": moving, "stop": stop, "far": far}
    hits = CK.sweep(parts, ["moving"], ["stop", "far"], axis=axis, travel=6, step=1)
    assert set(hits) == {("moving", "stop")}
    d = hits[("moving", "stop")]
    assert CK.overlap(Pos(*(-d * v for v in axis)) * moving, stop) > CK.VOLUME_TOL
    assert CK.sweep(parts, ["moving"], ["far"], axis=axis, travel=6) == {}


@pytest.mark.parametrize("travel,step", [(1, 1), (0.95, 0.7), (1, 2)])
def test_sweep_detects_thin_obstacle_between_old_samples(travel, step):
    parts = {"peg": Box(0.1, 1, 1), "stop": Pos(0.52, 0.2, 0) * Box(0.1, 1, 1)}
    assert CK.sweep(parts, ["peg"], ["stop"], (-1, 0, 0), travel, step)
    parts["stop"] = Pos(0, 5, 0) * parts["stop"]
    assert not CK.sweep(parts, ["peg"], ["stop"], (-1, 0, 0), travel, step)


def test_sweep_checks_home_position_and_zero_travel():
    parts = {"a": Box(1, 1, 1), "b": Box(1, 1, 1)}
    assert CK.sweep(parts, ["a"], ["b"], travel=0)
    parts["b"] = Pos(5, 0, 0) * parts["b"]
    assert not CK.sweep(parts, ["a"], ["b"], travel=0)


def test_sweep_does_not_pass_an_unresolved_motion():
    from build123d import Sphere

    parts = {"a": Sphere(1), "b": Pos(0, 0.5, 0) * Sphere(1)}
    result = CK.sweep(parts, ["a"], ["b"], travel=1, max_evaluations=0)
    assert result
    assert result.unresolved == {("a", "b")}
    assert "uncertified" in repr(result)
    parts["b"] = Pos(20, 0, 0) * parts["b"]
    assert not CK.sweep(parts, ["a"], ["b"], travel=1, max_evaluations=0)


@pytest.mark.parametrize("kwargs", [{"step": 0}, {"travel": -1}, {"axis": (2, 0, 0)}])
def test_sweep_rejects_invalid_motion(kwargs):
    with pytest.raises(ValueError):
        CK.sweep({}, [], [], **kwargs)


def test_straight_tube_requires_the_actual_cylinders_and_bore():
    tube = Cylinder(6, 20) - Cylinder(4, 22)
    assert CK.is_straight_tube(tube, (0, 0, -10), (0, 0, 10), 12, 8)
    assert not CK.is_straight_tube(Box(12, 12, 20), (0, 0, -10), (0, 0, 10), 12, 8)
    assert not CK.is_straight_tube(Cylinder(6, 20), (0, 0, -10), (0, 0, 10), 12, 8)
    assert not CK.is_straight_tube(tube, (0.5, 0, -10), (0.5, 0, 10), 12, 8)
    assert not CK.is_straight_tube(tube, (0, 0, -10), (0, 0, 10), 12, 7)


def test_rotation_envelope_covers_angles_between_samples():
    from build123d import RegularPolygon, extrude

    hexagon = extrude(RegularPolygon(10, 6), 5)
    envelope = CK.rotation_envelope(hexagon, (0, 0, 0), (0, 0, 1))
    obstacle = Pos(9.95, 0, 2.5) * Box(0.1, 0.1, 1)
    assert CK.overlap(envelope, obstacle) > CK.VOLUME_TOL
    assert CK.overlap(envelope, Pos(10, 0, 0) * obstacle) == 0
    for angle in (0, 3.75, 17, 59.99, 145):
        rotated = Rot(0, 0, angle) * hexagon
        outside = rotated - envelope
        assert not outside or outside.volume < 1e-6


def test_rotation_envelope_covers_curved_offset_and_tilted_parts():
    from build123d import Cone, Torus

    shapes = [
        Cylinder(3, 6),
        Cone(5, 2, 6),
        Torus(5, 1),
        Pos(2, 0, 0) * Cylinder(2, 5),
        Rot(0, 0.00005, 0) * Cylinder(3, 1000),
    ]
    for shape in shapes:
        envelope = CK.rotation_envelope(shape, (0, 0, 0), (0, 0, 1))
        outside = Rot(0, 0, 13.7) * shape - envelope
        assert not outside or outside.volume < 1e-6


def test_sweep_certifies_axial_running_clearance_and_sliding_flat():
    peg = Rot(90, 0, 0) * Cylinder(2, 10)
    sleeve = Box(10, 20, 10) - Rot(90, 0, 0) * Cylinder(2.05, 22)
    assert CK.sweep({"peg": peg, "sleeve": sleeve}, ["peg"], ["sleeve"], travel=10) == {}
    assert CK.sweep({"peg": peg, "wall": Box(10, 20, 10)}, ["peg"], ["wall"], travel=10)
    # A flat slides along a ledge. The larger body extends below the flat,
    # outside the ledge's X range; whole-part boxes alone cannot certify it.
    moving = Box(2, 2, 2) + Pos(4, 0, -2) * Box(2, 2, 6)
    ledge = Pos(0, 0, -2) * Box(2, 10, 2)
    assert CK._slab_motion_clear(moving, ledge, (0, -1, 0), 5)
    assert not CK._slab_motion_clear(moving, Pos(0, 0, 0.1) * ledge, (0, -1, 0), 5)


def test_wall_measurement_reports_coverage_and_rejects_missing_samples():
    from build123d import Solid

    measured = CK.wall_measurement(Box(10, 10, 2))
    assert measured.minimum == pytest.approx(2, abs=0.01)
    assert measured.measured_faces == measured.faces == 6
    assert measured.rays >= measured.hits > 0
    assert CK.wall_measurement(Box(10, 10, 0.5)).minimum < 1.2
    with pytest.raises(ValueError, match="solid"):
        CK.wall_measurement(Solid())
    with pytest.raises(ValueError, match="positive"):
        CK.wall_measurement(Box(1, 1, 1), per_face=0)


def test_query_bounds_reused_and_invalidated_after_geometry_changes(monkeypatch):
    from build123d import Shape

    a, b = Box(10, 10, 10), Box(2, 2, 2)
    original = Shape.bounding_box
    calls = []

    def counted(shape, *args, **kwargs):
        calls.append(shape)
        return original(shape, *args, **kwargs)

    monkeypatch.setattr(Shape, "bounding_box", counted)
    context = CK.GeometryQueries()
    for _ in range(3):
        assert CK.overlap(a, b, context=context) == pytest.approx(8)
        assert CK.ray_clear({"a": a}, b, context=context) == ["a"]
    assert len(calls) == 2
    b.move(Pos(30, 0, 0))
    assert CK.overlap(a, b, context=context) == 0
    assert len(calls) == 3
    b.wrapped = Box(1, 1, 1).wrapped
    assert CK.overlap(a, b, context=context) == pytest.approx(1)
    before = len(calls)
    context.invalidate(a)
    context.box(a)
    assert len(calls) == before + 1
    context.clear()
    context.box(a)
    CK.GeometryQueries().box(a)
    assert len(calls) == before + 3


@pytest.mark.parametrize("first_failure", [False, True])
def test_sweep_failure_mode_preserves_clearance_and_collision_evidence(first_failure):
    parts = {
        "moving": Box(2, 2, 2),
        "far": Pos(20, 0, 0) * Box(2, 2, 2),
        "one": Box(1, 1, 1),
        "two": Box(1, 1, 1),
    }
    assert not CK.sweep(parts, ["moving"], ["far"], travel=0, first_failure=first_failure)
    hits = CK.sweep(parts, ["moving"], ["far", "one", "two"], travel=0, first_failure=first_failure)
    assert list(hits) == [("moving", "one")] + ([] if first_failure else [("moving", "two")])
    assert not hits.unresolved
    unresolved = CK.sweep(
        parts, ["moving"], ["one", "two"], travel=0, max_evaluations=0, first_failure=first_failure
    )
    assert len(unresolved) == (1 if first_failure else 2)
    assert unresolved.unresolved == set(unresolved)
