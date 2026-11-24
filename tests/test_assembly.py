"""The station's design checks under pytest, one test per check section.

`uv run python assembly.py` remains the human-readable report; these tests run
the same section functions, so a failing check fails CI with its detail line.
The negative tests break the design on purpose and confirm the checks catch it.
"""

import json

import pytest
from build123d import Box, Pos, Rot

import assembly as A
from tools.checks import Report

CHECK_INVENTORY = json.loads((A.ROOT / "tests" / "check_inventory.json").read_text())


def run(section, parts) -> Report:
    r = Report(echo=False)
    section(parts, r)
    return r


def test_every_section_function_is_run():
    defined = {n for n in dir(A) if n.startswith("check_") and callable(getattr(A, n))}
    assert defined == {s.__name__ for s in A.SECTIONS}
    assert defined == {entry["section"] for entry in CHECK_INVENTORY.values()}
    checks = [(entry["section"], entry["name"]) for entry in CHECK_INVENTORY.values()]
    assert len(checks) == len(set(checks)), "duplicate check in the accepted inventory"


@pytest.mark.slow
@pytest.mark.parametrize(
    "section",
    [
        pytest.param(section, marks=pytest.mark.long_geometry)
        if section in (A.check_assembly_order, A.check_printing)
        else section
        for section in A.SECTIONS
    ],
    ids=lambda s: s.__name__,
)
def test_section_passes(section, parts):
    r = run(section, parts)
    assert r.results, "section ran no checks"
    expected = {
        entry["name"] for entry in CHECK_INVENTORY.values() if entry["section"] == section.__name__
    }
    actual = [name for _, name, _, _ in r.results]
    assert set(actual) == expected and len(actual) == len(expected), "check inventory changed"
    assert not r.failed(), "\n".join(f"{n}: {d}" for _, n, _, d in r.failed())


# --- negative tests: a broken design must fail -------------------------------
def failed_names(section, parts) -> set[str]:
    return {n for _, n, _, _ in run(section, parts).failed()}


def test_interference_catches_a_cap_pushed_into_the_valve(parts):
    bad = {k: parts[k] for k in ("valve_body", "valve_clamp_cap")}
    bad["valve_clamp_cap"] = Pos(0, -1.0, 0) * bad["valve_clamp_cap"]
    assert "no solid interference" in failed_names(A.check_interference, bad)


def test_interference_catches_a_part_embedded_in_solid_material(parts):
    # An embedded solid in a local test block must reach the station report.
    body = parts["valve_body"]
    point = next(v.center() for v in body.faces() if v.geom_type.name == "PLANE")
    # Use a guaranteed solid test block in station coordinates, without relying
    # on which body face the CAD kernel returns first.
    bad = {"block": Pos(*point) * Box(10, 10, 10), "embedded": Pos(*point) * Box(2, 2, 2)}
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


@pytest.mark.parametrize("kind", ["block", "blocked bore", "wrong bore"])
def test_alignment_rejects_fake_tubes_with_the_same_bounding_box(parts, kind):
    from build123d import Cylinder

    bb = parts["tube_link"].bounding_box()
    if kind == "block":
        fake = Pos(*bb.center()) * Box(*bb.size)
    else:
        fake = (
            Pos(bb.min.X, bb.center().Y, bb.center().Z)
            * Rot(0, 90, 0)
            * Cylinder(A.LINK_TUBE_OD / 2, bb.size.X, align=A.ALIGN_MIN)
        )
        if kind == "wrong bore":
            fake -= (
                Pos(bb.min.X - 1, bb.center().Y, bb.center().Z)
                * Rot(0, 90, 0)
                * Cylinder(A.LINK_TUBE_ID / 4, bb.size.X + 2, align=A.ALIGN_MIN)
            )
    bad = dict(parts, tube_link=fake)
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
    # Isolate the physically impossible final step from the old README order:
    # both real fittings are already fixed, then the stop-to-stop tube goes in.
    # The full correct build is independently checked by test_section_passes.
    stage = {
        "base_fixed_valve_fitting": parts[A.VALVE_INLET],
        "base_fixed_meter_fitting": parts["qsf_body_out"],
        **{n: parts[n] for n in ("tube_link", "tube_in", "tube_out")},
    }
    monkeypatch.setattr(A, "ASSEMBLY_ORDER", (("link tube last", ("tube_link",)),))
    assert "assembly order is collision-free" in failed_names(A.check_assembly_order, stage)


@pytest.mark.parametrize(
    "move,check",
    [
        (Pos(0.5, 0, 0), "M12 plug coaxial with flowmeter"),
        (Pos(0, 0, 0.5), "M12 seal at mating face"),
    ],
)
def test_electrical_checks_reject_displaced_plug(parts, move, check):
    bad = dict(parts)
    for name, solid in bad.items():
        if name.startswith("electrical_"):
            bad[name] = move * solid
    assert check in failed_names(A.check_electrical_interconnect, bad)


def test_electrical_check_rejects_wrong_key_phase(parts):
    bad = dict(parts)
    c = parts["flowmeter_m12"].bounding_box().center()
    turn = Pos(c.X, c.Y, 0) * Rot(0, 0, 180) * Pos(-c.X, -c.Y, 0)
    for name, solid in bad.items():
        if name.startswith("electrical_"):
            bad[name] = turn * solid
    assert "M12 A-code keys aligned" in failed_names(A.check_electrical_interconnect, bad)


def test_electrical_insertion_detects_obstruction(parts):
    from build123d import Box

    bad = dict(parts)
    c = parts["electrical_body"].bounding_box().center()
    bad["obstruction"] = Pos(c.X, c.Y, c.Z + 20) * Box(10, 10, 10)
    assert "M12 plug insertion clear of station" in failed_names(
        A.check_electrical_interconnect, bad
    )


def test_confirmed_m12_fit_does_not_hide_insert_misalignment(parts):
    bad = {n: parts[n] for n in ("flowmeter_m12", "electrical_insert")}
    bad["electrical_insert"] = Pos(0.1, 0, 0) * bad["electrical_insert"]
    assert "no solid interference" in failed_names(A.check_interference, bad)


def test_old_strap_torque_fails_with_actual_elbow_lever(parts, monkeypatch):
    monkeypatch.setattr(A.FCL, "STRAP_TORQUE", 0.5)
    assert "meter can't rotate under a 50 N cable pull" in failed_names(
        A.check_flowmeter_holding, parts
    )


def test_excessive_strap_torque_overloads_petg(parts, monkeypatch):
    monkeypatch.setattr(A.FCL, "STRAP_TORQUE", 0.6)
    assert "screw bearing on PETG / acrylic < allowable" in failed_names(A.check_modules, parts)


def test_hex_angle_check_rejects_obstruction(parts):
    bad = dict(parts)
    bb = parts["qsf_body_in"].bounding_box()
    bad["base_plate"] = Pos(bb.center().X, A.FCL.FM_Y + A.FCL.BODY_D / 2 - 0.5, 0) * Box(2, 2, 2)
    assert "fits any hex angle (fittings 0..60 deg)" in failed_names(A.check_flowmeter_clamp, bad)


def test_printing_rejects_a_thin_wall(parts, monkeypatch):
    monkeypatch.setattr(A, "printed_parts", lambda: {"thin coupon": (Box(10, 10, 0.5), (0, 0, 1))})
    assert f"printed walls >= {A.MIN_WALL} mm (3 perimeters)" in failed_names(
        A.check_printing, parts
    )


def test_printing_rejects_absent_wall_measurements(parts, monkeypatch):
    monkeypatch.setattr(A, "printed_parts", lambda: {"coupon": (Box(10, 10, 5), (0, 0, 1))})

    def missing(*args, **kwargs):
        raise ValueError("no usable rays")

    monkeypatch.setattr(A.CK, "wall_measurement", missing)
    assert f"printed walls >= {A.MIN_WALL} mm (3 perimeters)" in failed_names(
        A.check_printing, parts
    )


def test_printing_uses_the_configured_hole_limit(parts, monkeypatch):
    from build123d import Cylinder

    coupon = Pos(0, 0, 10) * Box(20, 10, 20) - Pos(0, 0, 10) * Rot(90, 0, 0) * Cylinder(4, 12)
    monkeypatch.setattr(A, "printed_parts", lambda: {"coupon": (coupon, (0, 0, 1))})
    monkeypatch.setattr(A, "HOLE_SELF_SUPPORT_R", 3)
    assert "printed parts need no support" in failed_names(A.check_printing, parts)


def test_assembly_motion_rejects_an_obstacle_between_old_snapshots():
    # A custom bench component moves along -Y across a thin obstruction at
    # +0.52 mm. At integer distances the two thin solids are always disjoint.
    bad = {
        "valve_body": Pos(-50, 80, 70) * Box(1, 0.1, 1),
        "base_test_obstacle": Pos(-49.8, 80.52, 70) * Box(1, 0.1, 1),
        "tube_in": Pos(-500, 80, 70) * Box(1, 1, 1),
        "tube_out": Pos(500, 80, 70) * Box(1, 1, 1),
    }
    assert "assembly order is collision-free" in failed_names(A.check_assembly_order, bad)
    del bad["base_test_obstacle"]
    assert not failed_names(A.check_assembly_order, bad)


def test_plate_check_rejects_a_second_layer_and_a_stray_pocket(parts):
    bad = dict(parts, base_extra=parts["base_plate"])
    assert "station plate: one plate, through-cuts + pockets" in failed_names(A.check_modules, bad)
    stray = parts["base_plate"] - Pos(-20, 12, 0) * Box(5, 4, 5)  # 2 mm deep: not a listed depth
    bad = dict(parts, base_plate=stray)
    assert "station plate: one plate, through-cuts + pockets" in failed_names(A.check_modules, bad)


@pytest.mark.slow
def _base_with(monkeypatch, parts, **consts):
    for name, value in consts.items():
        monkeypatch.setattr(A.FCL, name, value)
    return dict(parts) | {"fm_clamp_base": A.FCL.make_base(A.X_FM, -A.FLOW_DIR)}


def test_pad_check_rejects_a_pad_touching_the_flat(parts, monkeypatch):
    # the old zero-gap pad: with the bores it sets the meter's height twice
    bad = _base_with(monkeypatch, parts, PAD_TOP_Z=A.FCL.FLAT_Z)
    names = failed_names(A.check_flowmeter_clamp, bad)
    assert "pad clear of the meter flat (bores alone set its height)" in names


def test_pad_check_rejects_a_pad_too_low_to_stop_roll(parts, monkeypatch):
    # 1.5 mm under the flat: the flat's edge (5.75 off the axis) needs > 8 deg to reach it
    bad = _base_with(monkeypatch, parts, PAD_TOP_Z=A.FCL.FLAT_Z - 1.5)
    names = failed_names(A.check_flowmeter_clamp, bad)
    assert "pad stops the meter's roll both ways" in names
    assert "pad clear of the meter flat (bores alone set its height)" not in names


def test_stack_finger_room_catches_a_pitch_that_still_clears(parts, monkeypatch):
    # 138: the lifted elbow still clears the set above (1.4 mm), but not by M12_ROOM_MIN
    monkeypatch.setattr(A, "STACK_PITCH", 138.0)
    names = failed_names(A.check_stack, parts)
    assert "finger room over the lifted M12 elbow" in names
    assert "M12 elbow plugs / unplugs under the set above" not in names


def test_stack_catches_a_short_pitch(parts, monkeypatch):
    monkeypatch.setattr(A, "STACK_PITCH", 120.0)  # elbow can't be lifted off its socket
    assert "M12 elbow plugs / unplugs under the set above" in failed_names(A.check_stack, parts)
    monkeypatch.setattr(A, "STACK_PITCH", 80.0)  # elbow runs into the meter above
    names = failed_names(A.check_stack, parts)
    # the plate was cut for 140: the neighbours' dowels and screws miss its holes
    assert {"stacked sets don't collide", "one station plate carries every set"} <= names


def test_stack_catches_a_plate_for_one_set_only(parts):
    single = A.FCL.make_station_base(A.X_FM)["base_plate"]  # holes for this set only
    names = failed_names(A.check_stack, dict(parts, base_plate=single))
    assert "one station plate carries every set" in names


def test_stack_access_catches_a_neighbour_in_front_of_the_knob(parts):
    # a block one pitch below, in front of the knob: its copy in the set above
    # sits in this set's knob sight line
    block = Pos(0, 120, -A.STACK_PITCH) * Box(10, 10, 10)
    names = failed_names(A.check_stack, dict(parts, obstruction=block))
    assert "operator and tool access with neighbours fitted" in names


def test_build_stack_names_and_offsets(parts):
    stack = A.build_stack(parts)
    shared = sum(1 for n in parts if A.is_shared(n))
    assert len(stack) == A.STACK_N * (len(parts) - shared) + shared
    assert sum(1 for n in stack if n.startswith("wall_screw")) == 6  # the plate's, not per set
    assert [n for n in stack if n.endswith("base_plate")] == ["base_plate"]  # one plate
    zs = [A.set_offset(k) for k in range(1, A.STACK_N + 1)]
    pb = stack["base_plate"].bounding_box()
    assert pb.min.Z < min(zs) - 40 and pb.max.Z > max(zs) + 40  # spans every set
    k, name = A.split_set_name(A.set_name(3, "valve_body"))
    assert (k, name) == (3, "valve_body")
    dz = (
        stack["set3_valve_body"].bounding_box().center().Z
        - parts["valve_body"].bounding_box().center().Z
    )
    assert abs(dz - 2 * A.STACK_PITCH) < 1e-6


def test_wall_screw_load_counts_the_whole_stack(parts):
    # four of the plate's six M6 can't carry the three sets (126 N per screw > 100)
    bad = {n: s for n, s in parts.items() if n not in ("wall_screw_1", "wall_screw_4")}
    assert "wall screws: load per M6 under a 500 N tube pull" in failed_names(A.check_loads, bad)
    assert "wall screws: load per M6 under a 500 N tube pull" not in failed_names(
        A.check_loads, parts
    )
