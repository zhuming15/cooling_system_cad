"""Wall-mounted flow station: flowmeter -> straight link tube -> flow control valve.

    ifm SV3051 vortex flowmeter (directional)           (flowmeter/flowmeter.py)
    2 x Festo QSF-1/2-12-B push-in, G1/2 female         (flowmeter_connector/...)
    RS PRO 283-8289 G1/4 flow control valve (bidirectional)  (valve/valve.py)
    2 x SMC KQ2H12-U02A push-in, Uni 1/4 male           (valve_connector/...)
    One-piece station base (both clamps) + valve cap + 2 flowmeter straps,
    4 x M5x25 + 4 x M4x25, 8 x M6 wall screws   (valve_clamp/clamp.py, flowmeter_clamp/...)

Global frame: wall = plane Y=0 (+Y toward operator), Z up, flow along +X.
Flow direction: the VALVE has no flow direction (either port can be the
inlet). The FLOWMETER does: its arrow (local -X) must point along the system
flow, so it is rotated to suit. It sits upstream of the valve so the valve
keeps it under back-pressure (ifm: avoid cavitation) and the valve's
disturbance stays downstream of the measurement.

Run:  uv run python assembly.py   -> design checks, output/assembly.step, output/assembly.png
Exit code is non-zero if any design check fails.
"""

import itertools
import sys
from pathlib import Path

from build123d import Align, Compound, Location, Pos, Rot, Solid, export_step

ALIGN_MIN = (Align.CENTER, Align.CENTER, Align.MIN)

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "output"
for sub in (
    "valve",
    "valve_connector",
    "valve_clamp",
    "flowmeter",
    "flowmeter_connector",
    "flowmeter_clamp",
):
    sys.path.insert(0, str(ROOT / sub))

from build123d import Cylinder, Plane

import clamp as C
import flowmeter as FM
import flowmeter_clamp as FCL
import flowmeter_connector as FC
import valve as V
import valve_connector as F

TUBE_LEN = 40.0  # outlet tube stub after the valve (model only)
FLOW_DIR = -1  # system flow along -X = left -> right as the operator
# sees it (operator faces the wall, so +X is their left)
STRAIGHT_DN = 15  # ifm SV3051 manual 11592037 Fig. 2: >= 15 x DN in and out
LINK_FREE = 100.0  # free straight tube, meter outlet -> valve (>= 15 x DN6 = 90)
INLET_FREE = 100.0  # free straight tube ahead of the meter inlet (>= 90)

# Station layout along X (all derived; the link tube is exactly stop-to-stop)
UP = -FLOW_DIR  # upstream side of the valve
VALVE_INLET = "fitting_A" if UP < 0 else "fitting_B"  # valve port facing the meter
VALVE_OUTLET = "fitting_B" if UP < 0 else "fitting_A"
VALVE_FIT_TIP_X = UP * (V.BODY_L / 2 + F.A_SEAT_TO_TOP)  # +/-48.4
QSF_REACH = FCL.X_FACE + FC.L_TOTAL  # flowmeter centre -> QSF tip
X_FM = VALVE_FIT_TIP_X + UP * (LINK_FREE + QSF_REACH)  # flowmeter centre X
QSF_STOP_X = X_FM + FLOW_DIR * (FCL.X_FACE + FC.L_TOTAL - FC.TUBE_INSERT)  # QSF outlet stop
KQ2_STOP_X = UP * (V.BODY_L / 2 + F.TUBE_STOP_Z)  # valve inlet fitting stop
LINK_X0, LINK_X1 = sorted((QSF_STOP_X, KQ2_STOP_X))


# --------------------------------------------------------------------------
# Build
# --------------------------------------------------------------------------
def build() -> dict[str, Solid]:
    to_wall = Location((0, C.VALVE_Y, 0))  # valve frame -> global (clamped)
    vp = V.make_valve_parts()
    parts: dict[str, Solid] = {f"valve_{k}": to_wall * s for k, s in vp.items()}

    fitting = F.make_fitting()
    for side, sign in (("A", -1), ("B", 1)):
        # fitting Z axis -> +/-X, seat face on the valve port face
        place = to_wall * Pos(sign * V.BODY_L / 2, 0, 0) * Rot(0, sign * 90, 0)
        parts[f"fitting_{side}"] = place * fitting
    # outlet tube from valve fitting B
    parts["tube_out"] = (
        to_wall
        * Pos(FLOW_DIR * V.BODY_L / 2, 0, 0)
        * Rot(0, FLOW_DIR * 90, 0)
        * F.make_tube(TUBE_LEN)
    )

    # flowmeter: local -X (flow arrow) -> global FLOW_DIR; housing/M12 (local +Z)
    # ON TOP (global +Z) - ifm manual Fig. 1, horizontal pipe, recommended
    fm_place = Location(Plane(origin=(X_FM, FCL.FM_Y, 0), x_dir=(-FLOW_DIR, 0, 0), z_dir=(0, 0, 1)))
    parts |= {f"flowmeter_{k}": fm_place * s for k, s in FM.make_flowmeter_parts().items()}
    qsf = FC.make_fitting_parts()
    for side, sgn in (("in", 1), ("out", -1)):  # flowmeter local +X = inlet
        place = fm_place * Pos(sgn * FCL.X_FACE, 0, 0) * Rot(0, sgn * 90, 0)
        parts |= {f"qsf_{k}_{side}": place * s for k, s in qsf.items()}
        if side == "in":
            parts["tube_in"] = place * FC.make_tube(INLET_FREE)

    # straight link tube, exactly stop-to-stop: QSF outlet -> valve fitting A
    parts["tube_link"] = make_link_tube()

    parts["clamp_base"] = FCL.make_station_base(X_FM, -FLOW_DIR)  # one piece: both clamps
    parts["clamp_cap"] = C.make_cap()
    for i, s in enumerate(FCL.make_caps(X_FM)):
        parts[f"fm_clamp_strap_{i}"] = s
    for i, s in enumerate(C.make_m5_screws()):
        parts[f"m5_screw_{i}"] = s
    for i, s in enumerate(FCL.make_m4_screws(X_FM)):
        parts[f"m4_screw_{i}"] = s
    for i, s in enumerate(C.make_wall_screws() + FCL.make_wall_screws(X_FM)):
        parts[f"wall_screw_{i}"] = s
    return parts


def make_link_tube() -> Solid:
    """12 x 8 tube on the common axis (Y = C.VALVE_Y, Z = 0), LINK_X0 .. LINK_X1."""
    od = F.TUBE_OD - 0.05
    length = LINK_X1 - LINK_X0
    t = Pos(LINK_X0, C.VALVE_Y, 0) * Rot(0, 90, 0) * Cylinder(od / 2, length, align=ALIGN_MIN)
    return t - Pos(LINK_X0 - 1, C.VALVE_Y, 0) * Rot(0, 90, 0) * Cylinder(
        4.0, length + 2, align=ALIGN_MIN
    )


# --------------------------------------------------------------------------
# Checks
# --------------------------------------------------------------------------
class Report:
    def __init__(self) -> None:
        self.fails = 0

    def check(self, name: str, ok: bool, detail: str) -> None:
        self.fails += not ok
        print(f"  [{'PASS' if ok else 'FAIL'}] {name:<46} {detail}")


def overlap(a: Solid, b: Solid) -> float:
    bba, bbb = a.bounding_box(), b.bounding_box()
    if not bba.overlaps(bbb):
        return 0.0
    common = a & b
    return sum(s.volume for s in common.solids()) if common else 0.0


def ray_clear(parts: dict[str, Solid], probe: Solid, ignore: set[str]) -> list[str]:
    return [n for n, p in parts.items() if n not in ignore and overlap(p, probe) > 1e-3]


def y_probe(d: float, x: float, z: float, y0: float, y1: float) -> Solid:
    return C._y_cyl(d, y1 - y0, x, y0, z)


def verify(parts: dict[str, Solid]) -> int:
    r = Report()

    print("\n1. Interference (all part pairs)")
    worst = []
    for (na, a), (nb, b) in itertools.combinations(parts.items(), 2):
        v = overlap(a, b)
        if v > 1e-3:
            worst.append((v, na, nb))
    r.check(
        "no solid interference",
        not worst,
        "0 clashes" if not worst else "; ".join(f"{a}/{b} {v:.2f}mm3" for v, a, b in worst),
    )

    print("\n2. Clamp function")
    r.check(
        "cap pocket closes onto valve before gap",
        C.CLAMP_PRELOAD_TRAVEL > 0.1,
        f"cap travels {C.CAP_DROP:.3f} mm, residual split gap {C.CLAMP_PRELOAD_TRAVEL:.3f} mm",
    )
    base_gap = parts["valve_body"].distance_to(parts["clamp_base"])
    cap_gap = parts["valve_body"].distance_to(parts["clamp_cap"])
    r.check(
        "valve seated on base cradle & cap flat",
        base_gap < 1e-3 and cap_gap < 1e-3,
        f"body-base {base_gap:.4f} mm, body-cap {cap_gap:.4f} mm",
    )
    r.check(
        "anti-rotation: square body in U-channel",
        C.POCKET_W - V.BODY_W < 0.3,
        f"channel {C.POCKET_W:.2f} vs body {V.BODY_W:.2f} mm",
    )
    r.check(
        "channel corner radius fits in body chamfer",
        C.POCKET_R * (2**0.5 - 1) * 2**0.5 < V.BODY_CHAMFER,
        f"R{C.POCKET_R} channel corners vs {V.BODY_CHAMFER} mm body chamfer",
    )
    # M5 thread engagement into aluminium (want >= 2 x d)
    y_seat = C.Y_CAP_TOP - C.M5_CB_DEPTH - C.CAP_DROP
    engage = C.M5_LEN - (y_seat - C.Y_SPLIT_BASE)
    tap_ok = engage <= C.M5_TAP_DEPTH - 2.0
    r.check(
        "M5 engagement >= 2d, screw short of tap bottom",
        engage >= 10.0 and tap_ok,
        f"engagement {engage:.1f} mm (tap depth {C.M5_TAP_DEPTH:.0f})",
    )
    tap_bottom = C.Y_SPLIT_BASE - C.M5_TAP_DEPTH
    r.check(
        "tapped holes blind (don't break out at wall)",
        tap_bottom > 3.0,
        f"{tap_bottom:.1f} mm of material behind tap drill",
    )
    # holding capacity: 4 x M5 8.8, preload from the VDI 2230 table
    preload = 4 * C.M5_TORQUE * C.PRELOAD_N_PER_NM["M5"]
    mu = 0.15
    axial_hold = 2 * mu * preload  # friction at cap + base faces
    r.check(
        "axial slip resistance > 500 N tube pull",
        axial_hold > 500,
        f"{axial_hold / 1000:.1f} kN @ 4 x M5 {C.M5_TORQUE:g} N.m (VDI 2230), mu {mu}",
    )
    contact = 2 * (C.CLAMP_L / 2 - C.WINDOW_D / 2) * (V.BODY_W - 2 * V.BODY_CHAMFER)
    bearing = preload / contact
    r.check(
        "brass bearing stress under cap < 100 MPa",
        bearing < 100,
        f"{bearing:.0f} MPa on {contact:.0f} mm2 front-face strips",
    )

    print("\n3. Wall mounting")
    min_y = min(p.bounding_box().min.Y for n, p in parts.items() if not n.startswith("wall_screw"))
    r.check(
        "nothing but wall screws behind wall plane",
        min_y >= -1e-6,
        f"min Y of hardware = {min_y:.3f} mm",
    )
    base_back = parts["clamp_base"].bounding_box().min.Y
    r.check("base back face flush on wall", abs(base_back) < 1e-6, f"Y = {base_back:.3f}")
    blocked = []
    screws = [n for n in parts if n.startswith("wall_screw")]
    for n in screws:
        bb = parts[n].bounding_box()
        probe = y_probe(10.5, bb.center().X, bb.center().Z, C.PLATE_T + 0.5, 150)
        blocked += ray_clear(parts, probe, {n})
    r.check(
        f"{len(screws)} wall screws: straight hex-key access",
        not blocked,
        "clear" if not blocked else f"blocked by {sorted(set(blocked))}",
    )
    blocked = []
    screws = [n for n in parts if n.startswith(("m5_screw", "m4_screw"))]
    for n in screws:
        bb = parts[n].bounding_box()
        probe = y_probe(8.0, bb.center().X, bb.center().Z, bb.max.Y + 0.1, 150)
        blocked += ray_clear(parts, probe, {n})
    r.check(
        f"{len(screws)} clamp screws: hex-key access from front",
        not blocked,
        "clear" if not blocked else f"blocked by {sorted(set(blocked))}",
    )

    print("\n4. Operator access")
    knob = parts["valve_knob"]
    kbb = knob.bounding_box()
    cap_front = parts["clamp_cap"].bounding_box().max.Y
    grip = kbb.max.Y - max(cap_front, kbb.min.Y)
    r.check(
        "knob stands proud of clamp (grip length)",
        grip >= 15,
        f"{grip:.1f} mm of {V.KNOB_D:.0f} mm knob ahead of cap face",
    )
    # finger envelope: 18 mm-wide ring of fingertips around the knob grip zone
    finger_zone = C._y_cyl(
        V.KNOB_D + 2 * 18, kbb.max.Y - cap_front - 0.5, 0, cap_front + 0.5, 0
    ) - C._y_cyl(V.KNOB_D, 200, 0, 0, 0)
    blocked = ray_clear(parts, finger_zone, {"valve_knob", "valve_bonnet"})
    r.check(
        "18 mm finger clearance all round the knob",
        not blocked,
        "clear" if not blocked else f"blocked by {blocked}",
    )
    ww = parts["valve_knob"].distance_to(parts["clamp_cap"])
    r.check(
        "cap window passes over knob (assembly)",
        (C.WINDOW_D - V.KNOB_D) / 2 >= 1.5,
        f"radial clearance {(C.WINDOW_D - V.KNOB_D) / 2:.1f} mm, min gap knob-cap {ww:.1f} mm",
    )
    blocked = ray_clear(parts, y_probe(C.WINDOW_D, 0, 0, kbb.max.Y + 0.1, 400), {})
    r.check("scale cap readable / line of sight from front", not blocked, "clear")
    fit_wall = min(parts[f"fitting_{s}"].bounding_box().min.Y for s in "AB")
    r.check(
        "push-in release collar finger room to wall >= 15",
        fit_wall >= 15,
        f"{fit_wall:.1f} mm fitting-to-wall",
    )
    fit_clamp = min(parts[f"fitting_{s}"].distance_to(parts["clamp_base"]) for s in "AB")
    r.check(
        "fittings clear of clamp (tube release / wrench)",
        fit_clamp >= 1.0,
        f"{fit_clamp:.2f} mm fitting-to-base",
    )

    print("\n5. Connector mating (KQ2H12-U02A into G1/4 valve ports)")
    body_bb = parts["valve_body"].bounding_box()
    tubes = {VALVE_INLET: "tube_link", VALVE_OUTLET: "tube_out"}
    for s, sign in (("A", -1), ("B", 1)):
        tube_name = tubes[f"fitting_{s}"]
        fit, tube = parts[f"fitting_{s}"], parts[tube_name]
        fbb = fit.bounding_box()
        port_face_x = body_bb.max.X if sign > 0 else body_bb.min.X
        thread_tip_x = fbb.min.X if sign > 0 else fbb.max.X
        depth = abs(port_face_x - thread_tip_x)
        r.check(
            f"{s}: thread engaged, bottoms short of port",
            abs(depth - F.THREAD_L) < 1e-3 and V.PORT_DEPTH - depth >= 2.0,
            f"{depth:.1f} mm in a {V.PORT_DEPTH:.0f} mm port "
            f"({depth / 1.337:.1f} threads of G1/4 x 19 tpi)",
        )
        off = max(abs(fbb.center().Y - C.VALVE_Y), abs(fbb.center().Z))
        r.check(f"{s}: fitting coaxial with valve port", off < 1e-3, f"offset {off:.4f} mm")
        tube_gap = tube.distance_to(fit)
        tube_tip = tube.bounding_box().min.X if sign > 0 else tube.bounding_box().max.X
        seated = abs(abs(tube_tip - port_face_x) - F.TUBE_STOP_Z) < 1e-3
        r.check(
            f"{s}: 12 mm tube pushed home to the tube stop",
            seated and tube_gap < 1e-3,
            f"tube end {F.TUBE_STOP_Z:.1f} mm from port face, insertion {F.TUBE_INSERT:.0f} mm",
        )
    # conical seal face (from the RS/TraceParts model) vs the G1/4 port edge
    (z1, r1), (z2, r2) = F.NECK[1], (F.HEX_Z0, F.HEX_AF / 2)
    seal_gap = z1 + (V.PORT_D / 2 - r1) * (z2 - z1) / (r2 - r1)
    r.check(
        "seal face lands on port edge within gasket squeeze",
        0 <= seal_gap <= 0.3,
        f"{seal_gap:.2f} mm free travel at catalogue seat datum (tighten to seat)",
    )
    r.check(
        "flow path not restricted by the fittings",
        F.MIN_PORT >= V.FLOW_BORE,
        f"fitting bore {F.MIN_PORT:.0f} mm >= valve bore {V.FLOW_BORE:.0f} mm",
    )
    hex_start = V.BODY_L / 2 + F.HEX_Z0
    r.check(
        "19 mm spanner fits fitting hex clear of the clamp",
        hex_start > C.CLAMP_L / 2 and F.HEX_Z1 - F.HEX_Z0 >= 6.0,
        f"hex {F.HEX_Z1 - F.HEX_Z0:.1f} mm long, starts {hex_start - C.CLAMP_L / 2:.1f} mm "
        "past the clamp end",
    )
    verify_flowmeter(parts, r)
    return r.fails


def phase_sweep(parts: dict[str, Solid], step: float = 7.5) -> tuple[list[str], float]:
    """Spin every screwed-on fitting about its own axis through one hex pitch.

    Thread tightening decides where a fitting's hex flats end up, so the
    clamp must fit at any angle. Returns the clashes found and the worst
    seating gap of the flowmeter fittings.
    """
    groups = {  # fitting parts -> (axis Y, the clamp parts it must not hit)
        "qsf": (FCL.FM_Y, ["clamp_base"] + [n for n in parts if n.startswith("fm_clamp")]),
        "fitting": (C.VALVE_Y, ["clamp_base", "clamp_cap"]),
    }
    hits, worst = [], 0.0
    a = 0.0
    while a < 60.0:
        for prefix, (y, clamp_names) in groups.items():
            for n in [n for n in parts if n.startswith(prefix)]:
                spun = Pos(0, y, 0) * Rot(a, 0, 0) * Pos(0, -y, 0) * parts[n]
                hits += [f"{n}@{a:g}deg/{c}" for c in clamp_names if overlap(spun, parts[c]) > 1e-3]
                if n.startswith("qsf_body"):
                    worst = max(worst, spun.distance_to(parts["clamp_base"]))
        a += step
    return hits, worst


def verify_flowmeter(parts: dict[str, Solid], r: "Report") -> None:
    print("\n6. Flow direction (read from the placed geometry)")
    # SV3051: M12 connector and 12 AF flats are at the inlet end, the flow
    # arrow on the pipe points away from them (datasheet drawing).
    fm_x = parts["flowmeter_pipe"].bounding_box().center().X
    m12 = parts["flowmeter_m12"].bounding_box().center()
    arrow = 1 if fm_x - m12.X > 0 else -1
    r.check(
        "flowmeter arrow points along system flow",
        arrow == FLOW_DIR,
        f"arrow -> global {'+' if arrow > 0 else '-'}X, system flow "
        f"{'+' if FLOW_DIR > 0 else '-'}X",
    )
    v_x = parts["valve_body"].bounding_box().center().X
    r.check(
        "flowmeter upstream of the valve",
        (v_x - fm_x) * FLOW_DIR > 0,
        f"flowmeter X {fm_x:.1f} -> valve X {v_x:.1f} (valve keeps meter under back-pressure)",
    )
    r.check(
        "housing / M12 on top, horizontal pipe (ifm Fig. 1)",
        m12.Z > 20 and abs(m12.Y - FCL.FM_Y) < 1,
        f"M12 centre {m12.Z:.1f} mm above the flow axis, pipe horizontal along X",
    )
    print(
        "  [INFO] valve 283-8289 (Tognella FT 1251/2) is double-acting: either port may be the inlet"
    )

    print("\n7. Link tube alignment (flowmeter outlet -> valve inlet)")
    a = parts["qsf_body_out"].bounding_box().center()
    b = parts[VALVE_INLET].bounding_box().center()
    t = parts["tube_link"].bounding_box()
    dy, dz = abs(a.Y - b.Y), abs(a.Z - b.Z)
    r.check(
        "fitting axes coaxial (no lateral offset)",
        max(dy, dz) < 1e-3,
        f"dY {dy:.4f} mm, dZ {dz:.4f} mm between QSF outlet and KQ2 inlet axes",
    )
    r.check(
        "tube on that axis, dead straight",
        abs(t.center().Y - b.Y) < 1e-3
        and abs(t.center().Z) < 1e-3
        and abs(t.size.Y - t.size.Z) < 1e-3,
        f"tube centre Y {t.center().Y:.3f} / Z {t.center().Z:.3f}, straight cylinder",
    )

    r.check(
        "tube length = stop-to-stop (no axial strain)",
        abs(t.size.X - abs(QSF_STOP_X - KQ2_STOP_X)) < 1e-3
        and abs(t.min.X - LINK_X0) < 1e-3
        and abs(t.max.X - LINK_X1) < 1e-3,
        f"{t.size.X:.2f} mm = {FC.TUBE_INSERT} in QSF + {LINK_FREE:.0f} free + "
        f"{F.TUBE_INSERT:.0f} in KQ2",
    )
    qbb, kbb = parts["qsf_body_out"].bounding_box(), parts[VALVE_INLET].bounding_box()
    if FLOW_DIR > 0:  # meter on the -X side
        in_qsf, in_kq2 = qbb.max.X - t.min.X, t.max.X - kbb.min.X
    else:
        in_qsf, in_kq2 = t.max.X - qbb.min.X, kbb.max.X - t.min.X
    dn = FM.DN
    r.check(
        "straight runs >= 15 x DN (ifm manual Fig. 2)",
        LINK_FREE >= STRAIGHT_DN * dn and INLET_FREE >= STRAIGHT_DN * dn,
        f"outlet->valve {LINK_FREE:.0f} mm, inlet {INLET_FREE:.0f} mm >= {STRAIGHT_DN * dn:.0f} mm "
        "(meter not 'directly in front of a valve')",
    )
    r.check(
        "tube fully inserted in both fittings",
        abs(in_qsf - FC.TUBE_INSERT) < 1e-3 and abs(in_kq2 - F.TUBE_INSERT) < 1e-3,
        f"{in_qsf:.2f} mm in QSF (catalogue {FC.TUBE_INSERT}), "
        f"{in_kq2:.2f} mm in KQ2 (catalogue {F.TUBE_INSERT:.0f})",
    )
    base = parts["clamp_base"]
    on_base = max(base.distance_to(parts[n]) for n in ("valve_body", "qsf_body_in", "qsf_body_out"))
    r.check(
        "both cradles on one machined base",
        len(base.solids()) == 1 and on_base < 1e-3,
        "valve + flowmeter clamps share one plate: alignment set by machining, "
        "wall slots move both together",
    )
    dy_c = abs(C.VALVE_Y - FCL.FM_Y)
    r.check(
        "clamped axis heights equal by design",
        dy_c < 1e-6,
        f"valve {C.VALVE_Y:.3f} / flowmeter {FCL.FM_Y:.3f} mm from wall "
        f"(both pockets {C.POCKET_CLR} mm clearance, seated on cradle floor)",
    )
    r.check(
        "axial float lets meter follow the tube",
        FCL.AXIAL_FLOAT >= 1.0,
        f"+/-{FCL.AXIAL_FLOAT:.1f} mm in straps: push tube home, then tighten",
    )

    print("\n8. Flowmeter clamp (grips the round QSF bodies, never the hexes)")
    r.check(
        "straps close onto round body before gap",
        FCL.CLAMP_PRELOAD_TRAVEL > 0.1,
        f"strap travels {FCL.CAP_DROP:.3f} mm, residual gap {FCL.CLAMP_PRELOAD_TRAVEL:.3f} mm",
    )
    seat = max(parts[f"qsf_body_{s}"].distance_to(parts["clamp_base"]) for s in ("in", "out"))
    strap = max(
        min(parts[f"qsf_body_{s}"].distance_to(parts[f"fm_clamp_strap_{i}"]) for i in range(2))
        for s in ("in", "out")
    )
    r.check(
        "both fittings seated in cradle bore and strap",
        seat < 1e-3 and strap < 1e-3,
        f"body-base {seat:.4f} mm, body-strap {strap:.4f} mm",
    )
    r.check(
        "strap sits on the round section only",
        FCL.AXIAL_FLOAT >= 1.0,
        f"{FCL.STRAP_W:.0f} mm strap on {FCL.ROUND_LEN:.1f} mm of dia {FCL.BODY_D} "
        f"-> +/-{FCL.AXIAL_FLOAT:.2f} mm before hex cone / release ring",
    )
    phase_hits, worst_seat = phase_sweep(parts)
    r.check(
        "fits any hex angle (fittings 0..60 deg)",
        not phase_hits and worst_seat < 1e-3,
        "clear at every angle, still seated"
        if not phase_hits
        else f"clash: {sorted(set(phase_hits))}",
    )
    pad = FCL.pad_box(X_FM, -FLOW_DIR)
    on_pad = parts["flowmeter_pipe"].distance_to(pad)
    into_pad = overlap(parts["flowmeter_pipe"], pad)
    r.check(
        "meter flat rests on locating pad (meter square)",
        on_pad < 1e-3 and into_pad < 1e-3,
        f"downward 12 AF flat to pad {on_pad:.4f} mm, overlap {into_pad:.3f} mm3 "
        "-> rotation locked both ways",
    )
    pb = pad.bounding_box()
    base_wo_pad = parts["clamp_base"] - FCL._box(
        (pb.min.X - 0.1, pb.max.X + 0.1),
        (pb.min.Y - 0.1, pb.max.Y + 0.1),
        (pb.min.Z - 0.1, pb.max.Z + 0.5),
    )
    fm_names = [n for n in parts if n.startswith("flowmeter_")]
    clamp_names = [n for n in parts if n.startswith("fm_clamp")]
    gap = min(
        [parts[a].distance_to(parts[b]) for a in fm_names for b in clamp_names]
        + [parts[a].distance_to(base_wo_pad) for a in fm_names]
    )
    r.check(
        "meter touches only the pad (no clamp load on plastic)",
        gap >= 1.0,
        f"min gap elsewhere {gap:.1f} mm; screw load goes through the brass fittings",
    )
    y_seat = FCL.Y_CAP_TOP - FCL.M4_CB_DEPTH - FCL.CAP_DROP
    engage = FCL.M4_LEN - (y_seat - FCL.Y_SPLIT_BASE)
    r.check(
        "strap M4 engagement >= 2d", 8.0 <= engage <= FCL.M4_TAP_DEPTH - 2.0, f"{engage:.1f} mm"
    )

    # --- Rotation about the flow axis (round grip, so friction + pad) ----------
    # Preload per strap: 2 x M4 (VDI 2230 table). Normal force on the round body is
    # at least F on the strap half plus F on the base half; mu 0.15 is dry
    # aluminium on nickel-plated brass (conservative).
    f_strap = 2 * FCL.M4_TORQUE * C.PRELOAD_N_PER_NM["M4"]  # N, VDI 2230
    mu = 0.15
    t_slip = mu * 2 * f_strap * FCL.BODY_D / 2 / 1000  # N.m per strap
    r.check(
        "fitting can't spin in its strap (vs 12 N.m thread)",
        t_slip >= 1.5 * 12.0,
        f"slip torque {t_slip:.1f} N.m per strap > 1.5 x 12 N.m max tightening torque",
    )
    # Load that could turn the meter: someone pulls/drapes the M12 cable sideways,
    # 50 N at the plug, lever = M12 top above the flow axis. Push-in tubes swivel
    # in their collets, so tube torque is negligible.
    lever = parts["flowmeter_m12"].bounding_box().max.Z / 1000  # M12 top above the axis
    t_cable = 50.0 * lever
    t_hold = 2 * t_slip
    r.check(
        "meter can't rotate under a 50 N cable pull",
        t_hold >= 5 * t_cable,
        f"cable {t_cable:.1f} N.m vs friction {t_hold:.0f} N.m (x{t_hold / t_cable:.0f}), "
        "plus the spanner-flat pad as a positive stop",
    )
    p_contact = f_strap / (FCL.BODY_D * FCL.STRAP_W)
    r.check(
        "contact pressure on brass body < 60 MPa",
        p_contact < 60,
        f"{p_contact:.0f} MPa projected on dia {FCL.BODY_D} x {FCL.STRAP_W:.0f} "
        "(won't distort the push-in collet seat)",
    )

    print("\n9. Flowmeter operator access")
    mb = parts["flowmeter_m12"].bounding_box()
    plug = Pos(mb.center().X, mb.center().Y, mb.max.Z + 0.1) * Cylinder(
        10.0, 55, align=ALIGN_MIN
    )  # straight M12 plug, pointing up
    blocked = ray_clear(parts, plug, set())
    r.check(
        "M12 cable plug envelope (dia 20 x 55) clear",
        not blocked,
        "clear" if not blocked else f"blocked by {blocked}",
    )
    # To release a tube, the operator (or a release tool) pushes the ring's
    # outer face from the tube side: that outboard space must be free.
    blocked, ring_gap = [], 1e9
    for side in ("in", "out"):
        rb = parts[f"qsf_release_ring_{side}"].bounding_box()
        out_dir = 1 if rb.center().X > X_FM else -1
        x_face = rb.max.X if out_dir > 0 else rb.min.X
        finger = (
            Pos(x_face + (0.2 if out_dir > 0 else -15.2), FCL.FM_Y, 0)
            * Rot(0, 90, 0)
            * Cylinder(FC.RING_PROFILE[1][0] + 10, 15, align=ALIGN_MIN)
        )
        finger -= (
            Pos(x_face - 50, FCL.FM_Y, 0)
            * Rot(0, 90, 0)
            * Cylinder(FC.TUBE_OD / 2 + 0.3, 100, align=ALIGN_MIN)
        )
        # operator side: front half plus top and bottom (wall side is reported below)
        finger &= FCL._box((x_face - 20, x_face + 20), (FCL.FM_Y, FCL.FM_Y + 40), (-40, 40))
        blocked += ray_clear(parts, finger, set())
        ring_gap = min(
            ring_gap,
            *(
                parts[f"qsf_release_ring_{side}"].distance_to(parts[f"fm_clamp_strap_{i}"])
                for i in range(2)
            ),
        )
    ring_back = min(parts[f"qsf_release_ring_{s}"].bounding_box().min.Y for s in ("in", "out"))
    wall_side = ring_back - FCL.PLATE_T
    r.check(
        "QSF release rings: free to press from the front",
        not blocked and wall_side >= 6.0 and ring_gap >= 2.0,
        (
            f"10 mm finger room over front 180 deg x 15 mm; wall side {wall_side:.1f} mm "
            f"to base (release fork); strap {ring_gap:.1f} mm behind ring"
        )
        if not blocked
        else f"blocked by {blocked}",
    )
    sq = FM.SPANNER_X
    r.check(
        "12 AF spanner flats reachable (hold meter when tightening)",
        sq[1] - sq[0] >= 8,
        f"{sq[1] - sq[0]:.1f} mm of flats on the inlet side",
    )
    print("  [INFO] tighten QSF onto the flowmeter <= 12 N.m (ifm), with a flat G1/2 washer")


# --------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------
def main() -> int:
    parts = build()
    print("Wall-mounted flow station: SV3051 flowmeter -> link tube -> 283-8289 valve")
    fails = verify(parts)
    OUTPUT.mkdir(exist_ok=True)
    out = OUTPUT / "assembly.step"
    asm = Compound(children=[p for p in parts.values()], label="flow_station_assembly")
    for child, name in zip(asm.children, parts):
        child.label = name
    export_step(asm, str(out))
    from tools.render import render_assembly

    render_assembly(parts, OUTPUT / "assembly.png")
    print(f"\nExported {out.relative_to(ROOT)}, output/assembly.png")
    print("RESULT:", "ALL CHECKS PASS" if not fails else f"{fails} CHECK(S) FAILED")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
