"""Wall-mounted flow station: flowmeter -> straight link tube -> flow control valve.

    ifm SV3051 vortex flowmeter (directional)           (flowmeter/flowmeter.py)
    2 x Festo QSF-1/2-12-B push-in, G1/2 female         (flowmeter_connector/...)
    RS PRO 283-8289 G1/4 flow control valve (bidirectional)  (valve/valve.py)
    2 x SMC KQ2H12-U02A push-in, Uni 1/4 male           (valve_connector/...)
    Station base: laser-cut acrylic plate, holes only. Clamp modules screw onto
    it (3D printed, dowel-located): valve base + cap, flowmeter base + 2 straps.
    M4 into heat-set inserts / captive nuts, 8 x M6 wall screws
    (valve_clamp/clamp.py, flowmeter_clamp/flowmeter_clamp.py)

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

from build123d import Align, Location, Pos, Rot, Solid, export_step

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
# Build / service / environment (section 11). Values marked ESTIMATE have no single source.
DT_WATER = 20.0  # K: water 0..40 degC vs assembly at 20 degC (system limit, README)
CTE = {"brass": 19e-6, "tube": 150e-6}  # 1/K, ESTIMATE: brass; PU tube (PA ~100e-6)
HDT_PETG = 70.0  # degC, ESTIMATE: PETG heat deflection (0.45 MPa); water max 40 degC
P_MAX = 0.6  # MPa: system limit (QSF, Festo datasheet 190653)
BRIDGE_MAX = 15.0  # mm, ESTIMATE: PETG bridge without support
HOLE_SELF_SUPPORT_R = 5.0  # mm: horizontal holes up to dia 10 print without support
MIN_WALL = 1.2  # mm: 3 perimeters of a 0.4 mm nozzle
WALL_PLUG_MAX = 100.0  # N per M6 screw, ESTIMATE: conservative plug in plasterboard
DENSITY = {"brass": 8.5e-3, "steel": 7.85e-3, "PETG": 1.27e-3, "PMMA": 1.19e-3, "PPS": 1.6e-3}
# Order of assembly (README): each step moves along -Y into place, in turn.
ASSEMBLY_ORDER = (
    (
        "clamp bases + dowels + inserts",
        ("valve_clamp_base", "fm_clamp_base", "dowel_", "m4_insert"),
    ),
    ("base mount screws", ("m4_mount_screw",)),
    (
        "bench unit: valve + KQ2 + link tube + flowmeter + QSF",
        ("valve_body", "valve_bonnet", "valve_knob", "fitting_", "tube_link", "flowmeter_", "qsf_"),
    ),
    (
        "valve cap, straps, washers, screws",
        ("valve_clamp_cap", "fm_clamp_strap", "m4_washer", "m4_cap"),
    ),
)
# Printed parts as printed: (builder, build direction). Strap on its side: bore vertical.
TUBE_STRAIN_MAX = 0.005  # ESTIMATE: 0.5 % bending strain, well inside PU / PA tube elasticity

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

    # station base: laser-cut plate with holes only; printed clamp modules screw onto it
    parts |= FCL.make_station_base(X_FM)
    parts["valve_clamp_base"] = C.make_base()
    parts["valve_clamp_cap"] = C.make_cap()
    parts["fm_clamp_base"] = FCL.make_base(X_FM, -FLOW_DIR)
    for i, s in enumerate(FCL.make_caps(X_FM)):
        parts[f"fm_clamp_strap_{i}"] = s
    hw = C.make_hw()
    for k, v in FCL.make_hw(X_FM).items():
        hw[k] = hw[k] + v
    for kind, solids in hw.items():
        for i, s in enumerate(solids):
            parts[f"m4_{kind}_{i}" if kind != "dowel" else f"dowel_{i}"] = s
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


CLAMP_PREFIXES = ("base_", "valve_clamp", "fm_clamp")


def clamp_parts(parts: dict[str, Solid]) -> list[str]:
    """Station plate layers and every printed clamp part."""
    return [n for n in parts if n.startswith(CLAMP_PREFIXES)]


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

    print("\n2. Valve clamp (printed saddle: base + cap)")
    r.check(
        "cap pocket closes onto valve before gap",
        C.CLAMP_PRELOAD_TRAVEL - 2 * C.PRINT_TOL > 0.1,
        f"cap travels {C.CAP_DROP:.3f} mm, residual split gap {C.CLAMP_PRELOAD_TRAVEL:.3f} mm "
        f"({C.CLAMP_PRELOAD_TRAVEL - 2 * C.PRINT_TOL:.2f} after 2 x {C.PRINT_TOL} print tolerance)",
    )
    base_gap = parts["valve_body"].distance_to(parts["valve_clamp_base"])
    cap_gap = parts["valve_body"].distance_to(parts["valve_clamp_cap"])
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
    # holding capacity: 4 x M4 into heat-set inserts, low torque for PETG
    preload = 4 * C.preload(C.CAP_TORQUE)
    axial_hold = 2 * C.MU * preload  # friction at cap + base faces
    r.check(
        "axial slip resistance > 500 N tube pull",
        axial_hold > 500,
        f"{axial_hold:.0f} N @ 4 x M4 {C.CAP_TORQUE} N.m ({C.preload(C.CAP_TORQUE):.0f} N each), "
        f"mu {C.MU}",
    )
    contact = 2 * (C.CLAMP_L / 2 - C.WINDOW_D / 2) * (V.BODY_W - 2 * V.BODY_CHAMFER)
    bearing = preload / contact
    r.check(
        "cap pressure on the printed part < PETG allowable",
        bearing < C.PRINT_P_ALLOW,
        f"{bearing:.1f} MPa on {contact:.0f} mm2 front-face strips (< {C.PRINT_P_ALLOW:.0f})",
    )

    print("\n3. Wall mounting")
    min_y = min(p.bounding_box().min.Y for n, p in parts.items() if not n.startswith("wall_screw"))
    r.check(
        "nothing but wall screws behind wall plane",
        min_y >= -1e-6,
        f"min Y of hardware = {min_y:.3f} mm",
    )
    base_back = parts["base_back"].bounding_box().min.Y
    r.check("base back face flush on wall", abs(base_back) < 1e-6, f"Y = {base_back:.3f}")
    blocked = []
    screws = [n for n in parts if n.startswith("wall_screw")]
    for n in screws:
        bb = parts[n].bounding_box()
        probe = y_probe(10.5, bb.center().X, bb.center().Z, bb.max.Y + 0.1, 150)
        blocked += ray_clear(parts, probe, {n})
    r.check(
        f"{len(screws)} wall screws: straight hex-key access",
        not blocked,
        "clear" if not blocked else f"blocked by {sorted(set(blocked))}",
    )
    blocked = []
    screws = [n for n in parts if n.startswith("m4_cap_screw")]
    for n in screws:
        bb = parts[n].bounding_box()
        probe = y_probe(8.0, bb.center().X, bb.center().Z, bb.max.Y + 0.1, 150)
        blocked += ray_clear(parts, probe, {n, n.replace("cap_screw", "washer")})
    r.check(
        f"{len(screws)} clamp screws: hex-key access from front",
        not blocked,
        "clear" if not blocked else f"blocked by {sorted(set(blocked))}",
    )

    print("\n4. Operator access")
    knob = parts["valve_knob"]
    kbb = knob.bounding_box()
    cap_front = parts["valve_clamp_cap"].bounding_box().max.Y
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
    ww = parts["valve_knob"].distance_to(parts["valve_clamp_cap"])
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
    fit_clamp = min(
        parts[f"fitting_{s}"].distance_to(parts[n]) for s in "AB" for n in clamp_parts(parts)
    )
    r.check(
        "fittings clear of clamp (tube release / wrench)",
        fit_clamp >= 1.0,
        f"{fit_clamp:.2f} mm fitting-to-clamp",
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
    verify_modules(parts, r)
    verify_build(parts, r)
    return r.fails


def verify_modules(parts: dict[str, Solid], r: "Report") -> None:
    print("\n10. Clamp modules on the station base (printed clamps, laser-cut plate)")
    # plate layers: flat laser-cut profiles with holes only
    flat = []
    for n in ("base_back", "base_front"):
        p = parts[n]
        ok = abs(p.bounding_box().size.Y - C.SHEET_T) < 1e-6 and all(
            (
                f.geom_type.name == "PLANE"
                and abs(abs(f.normal_at().Y) - 1) < 1e-6
                or abs(f.normal_at().Y) < 1e-6
            )
            for f in p.faces()
        )
        flat += [] if ok else [n]
    r.check(
        "station plate: 2 flat layers, holes only (laser)",
        not flat,
        f"{C.SHEET_T:.0f} mm profiles: wall slots, nut pockets, dowel and M4 holes"
        if not flat
        else f"not a flat profile: {flat}",
    )
    # every clamp base: 2 dowels in plate holes, >= 2 mount screws in nuts
    dowels = [n for n in parts if n.startswith("dowel_")]
    bad = []
    for base in ("valve_clamp_base", "fm_clamp_base"):
        mine = [d for d in dowels if parts[d].distance_to(parts[base]) < 1e-3]
        slip = (C.DOWEL_HOLE_D - C.DOWEL_D) / 2 + 1e-3
        in_plate = [
            d
            for d in mine
            if parts[d].distance_to(parts["base_front"]) <= slip
            and parts[d].bounding_box().min.Y <= C.SHEET_T + 1e-6
        ]
        mounts = [
            n
            for n in parts
            if n.startswith("m4_mount_screw") and parts[n].distance_to(parts[base]) < 1e-3
        ]
        if len(mine) != 2 or len(in_plate) != 2 or len(mounts) < 2:
            bad.append(f"{base}: {len(in_plate)} dowels, {len(mounts)} screws")
    r.check(
        "each clamp base: 2 dowels in the plate + 2 M4",
        not bad,
        "located by pins (no screw-clearance play), held by screws" if not bad else "; ".join(bad),
    )
    # mount screws: through the whole captive nut, off the wall, heads below the seat
    bad, tips = [], []
    mounts = sorted(n for n in parts if n.startswith("m4_mount_screw"))
    for n in mounts:
        i = n.rsplit("_", 1)[1]
        sb, nb = parts[n].bounding_box(), parts[f"m4_nut_{i}"].bounding_box()
        tips.append(sb.min.Y)
        if not (C.TIP_MIN_Y - 1e-6 <= sb.min.Y <= nb.min.Y + 1e-6):
            bad.append(n)
        if round(sb.size.Y - C.M4_HEAD[1], 3) not in C.ISO4762_LENGTHS:
            bad.append(n)
    r.check(
        f"{len(mounts)} mount M4: full nut engagement, tip off the wall",
        not bad,
        f"tips at Y {min(tips):.2f}..{max(tips):.2f} (nut far face {C.Y_NUT[0]:.1f}); "
        f"M4 x {C.MOUNT_LEN:.0f} / x {FCL.MOUNT_LEN:.0f}"
        if not bad
        else f"bad: {bad}",
    )
    # mount screws reachable from the front with only the plate and bases fitted
    blocked = []
    for n in mounts:
        bb = parts[n].bounding_box()
        probe = y_probe(6.5, bb.center().X, bb.center().Z, bb.max.Y + 0.1, 150)
        stage = {
            k: parts[k] for k in ("base_back", "base_front", "valve_clamp_base", "fm_clamp_base")
        }
        blocked += ray_clear(stage, probe, set())
    r.check(
        "mount M4 reachable before the component goes in",
        not blocked,
        "hex key straight in through the channel floor / bore bottom"
        if not blocked
        else f"blocked by {sorted(set(blocked))}",
    )
    # cap / strap screws: whole insert engaged, tip short of the hole bottom
    bad, eng = [], []
    caps = sorted(n for n in parts if n.startswith("m4_cap_screw"))
    for n in caps:
        i = n.rsplit("_", 1)[1]
        sb, ib = parts[n].bounding_box(), parts[f"m4_insert_{i}"].bounding_box()
        eng.append(ib.max.Y - max(sb.min.Y, ib.min.Y))
        hole_bottom = ib.max.Y - C.INSERT_HOLE_DEPTH
        if not (hole_bottom + 0.5 - 1e-6 <= sb.min.Y <= ib.min.Y + 1e-6):
            bad.append(n)
        if round(sb.size.Y - C.M4_HEAD[1], 3) not in C.ISO4762_LENGTHS:
            bad.append(n)
    r.check(
        f"{len(caps)} cap/strap M4: full insert engagement",
        not bad,
        f"{min(eng):.1f} mm of thread in {C.INSERT[1]} mm heat-set inserts; "
        f"M4 x {C.CAP_SCREW_LEN:.0f} / x {FCL.CAP_SCREW_LEN:.0f}"
        if not bad
        else f"bad: {bad}",
    )
    # contact pressures on plastic
    washer_a = 3.14159 / 4 * (C.WASHER[0] ** 2 - C.WASHER[1] ** 2)
    head_a = 3.14159 / 4 * (C.M4_HEAD[0] ** 2 - C.M4_CLR_D**2)
    nut_a = 3**0.5 / 2 * C.NUT_AF**2 - 3.14159 / 4 * C.M4_CLR_D**2
    p_w = C.preload(C.CAP_TORQUE) / washer_a
    p_h = C.preload(C.MOUNT_TORQUE) / head_a
    p_n = C.preload(C.MOUNT_TORQUE) / nut_a
    r.check(
        "screw bearing on PETG / acrylic < allowable",
        p_w < C.PRINT_P_ALLOW and p_h < C.PRINT_P_ALLOW and p_n < C.ACRYLIC_P_ALLOW,
        f"washer {p_w:.1f} / mount head {p_h:.1f} MPa on PETG (< {C.PRINT_P_ALLOW:.0f}), "
        f"nut {p_n:.1f} MPa on acrylic (< {C.ACRYLIC_P_ALLOW:.0f})",
    )
    # base can't tip under the 500 N tube pull at axis height: it pivots on its far
    # edge; the mount screws' preload holds it back (the pins add to this)
    tip = []
    for base, xz in (("valve_clamp_base", C.MOUNT_XZ), ("fm_clamp_base", FCL.mount_xz(X_FM))):
        bb = parts[base].bounding_box()
        m_pull = 500 * (C.AXIS_Y - C.PLATE_T) / 1000
        k = min(
            C.preload(C.MOUNT_TORQUE) * sum(abs(edge - x) for x, _ in xz) / 1000 / m_pull
            for edge in (bb.min.X, bb.max.X)
        )
        tip.append((base, k))
    r.check(
        "clamp base can't tip under a 500 N tube pull",
        all(k >= 1.0 for _, k in tip),
        ", ".join(f"{b} x{k:.2f}" for b, k in tip) + " (screw preload about the far edge)",
    )
    printed = ["valve_clamp_base", "valve_clamp_cap", "fm_clamp_base", "fm_clamp_strap_0"]
    big = max(max(parts[n].bounding_box().size.X, parts[n].bounding_box().size.Z) for n in printed)
    r.check(
        f"printed parts fit a {C.PRINT_BED:.0f} mm printer bed",
        big <= C.PRINT_BED,
        f"largest printed part {big:.0f} mm (flowmeter base); the 300 mm plate is laser-cut",
    )
    print(
        f"  [INFO] torque: caps/straps {C.CAP_TORQUE} N.m, bases {C.MOUNT_TORQUE} N.m; "
        "re-torque after 24 h (plastic creep)"
    )


def sweep(parts, moving, installed, axis=(0.0, -1.0, 0.0), travel=60.0, step=1.0):
    """Move `moving` into place along `axis` over `travel`; return {(moving, hit): mm}."""
    hits, d = {}, travel
    while d > 1e-9:
        off = Pos(-axis[0] * d, -axis[1] * d, -axis[2] * d)
        for m in moving:
            sm = off * parts[m]
            for n in installed:
                if (m, n) not in hits and overlap(sm, parts[n]) > 1e-3:
                    hits[(m, n)] = d
        d -= step
    return hits


def printed_parts() -> dict:
    return {
        "valve_clamp_base": (C.make_base(), (0, 1, 0)),
        "valve_clamp_cap": (C.make_cap_unclamped(), (0, 1, 0)),
        "fm_clamp_base": (FCL.make_base(X_FM, -FLOW_DIR), (0, 1, 0)),
        "fm_clamp_strap": (FCL.make_cap_unclamped(FCL.STRAP_X), (1, 0, 0)),
    }


def overhangs(solid: Solid, build) -> tuple[list[float], list[str]]:
    """Bridge spans (flat down-facing faces above the bed) and unsupported curved faces."""
    import numpy as np

    b = np.array(build, float)
    bed = min(float(np.dot(b, (v.X, v.Y, v.Z))) for v in solid.vertices())
    spans, bad = [], []
    for f in solid.faces():
        verts, tris = f.tessellate(0.05, 0.3)
        if not tris:
            continue
        pts = np.array([(v.X, v.Y, v.Z) for v in verts])
        t = np.array(tris)
        n = np.cross(pts[t[:, 1]] - pts[t[:, 0]], pts[t[:, 2]] - pts[t[:, 0]])
        n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
        on = f.normal_at(f.center())
        on = np.array((on.X, on.Y, on.Z))
        n *= 1 if np.dot(n.mean(0), on) >= 0 else -1
        height = pts[t].mean(1) @ b - bed
        down = (n @ b < -0.7071) & (height > 0.05)
        if not down.any():
            continue
        if f.geom_type.name == "PLANE" and abs(np.dot(on, b) + 1) < 1e-6:
            bb = f.bounding_box()
            ext = [e for e, a in zip((bb.size.X, bb.size.Y, bb.size.Z), b) if abs(a) < 0.5]
            spans.append(min(ext))
        elif not (f.geom_type.name == "CYLINDER" and f.radius <= HOLE_SELF_SUPPORT_R):
            bad.append(f"{f.geom_type.name.lower()} at {tuple(round(c, 1) for c in f.center())}")
    return spans, bad


def min_wall(solid: Solid, per_face: int = 150) -> float:
    """Smallest material thickness, by rays fired inward from surface points."""
    import numpy as np
    from build123d import Vector
    from OCP.BRepClass3d import BRepClass3d_SolidClassifier
    from OCP.gp import gp_Dir, gp_Lin, gp_Pnt
    from OCP.IntCurvesFace import IntCurvesFace_ShapeIntersector
    from OCP.TopAbs import TopAbs_IN

    inter = IntCurvesFace_ShapeIntersector()
    inter.Load(solid.wrapped, 1e-6)
    rng, worst = np.random.default_rng(0), 1e9
    for f in solid.faces():
        verts, _ = f.tessellate(0.2, 0.5)
        pts = np.array([(v.X, v.Y, v.Z) for v in verts])  # vertices lie on the surface
        if len(pts) > per_face:
            pts = pts[rng.choice(len(pts), per_face, replace=False)]
        for c in pts:
            nv = f.normal_at(Vector(*c))
            d = -np.array((nv.X, nv.Y, nv.Z))
            probe = BRepClass3d_SolidClassifier(solid.wrapped, gp_Pnt(*(c + 0.01 * d)), 1e-7)
            if probe.State() != TopAbs_IN:
                d = -d
            p0 = c + 1e-4 * d
            inter.Perform(gp_Lin(gp_Pnt(*p0), gp_Dir(*d)), 0.0, 1e3)
            ws = [inter.WParameter(i) for i in range(1, inter.NbPnt() + 1)]
            ws = [w for w in ws if w > 5e-3]
            if ws:
                worst = min(worst, min(ws))
    return worst


def verify_build(parts: dict[str, Solid], r: "Report") -> None:
    import numpy as np

    print("\n11. Build, print, service and environment")
    # --- assembly order: every step moves into place without a collision ----------
    installed = [n for n in parts if n.startswith(("base_", "m4_nut", "wall_screw"))]
    clashes = []
    for label, prefixes in ASSEMBLY_ORDER:
        moving = [n for n in parts if n.startswith(prefixes)]
        hits = sweep(parts, moving, installed)
        clashes += [f"{label}: {m}/{n} at {d:.0f} mm" for (m, n), d in hits.items()]
        installed += moving
    ends = []
    for name in ("tube_in", "tube_out"):
        out = 1 if parts[name].bounding_box().center().X > X_FM / 2 else -1
        ends += [f"{m}/{n}" for (m, n) in sweep(parts, [name], installed, (-out, 0, 0), 40)]
    left = [n for n in parts if n not in installed and not n.startswith("tube_")]
    r.check(
        "assembly order is collision-free",
        not clashes and not ends and not left,
        f"{len(ASSEMBLY_ORDER)} steps, each swept 60 mm along -Y into place; end tubes pushed "
        "in along X"
        if not (clashes or ends or left)
        else "; ".join(clashes + ends + [f"not in any step: {left}"])[:300],
    )
    # the link tube can't go in last: it is cut stop-to-stop between two fixed fittings
    late = sweep(parts, ["tube_link"], [n for n in installed if n != "tube_link"])
    print(
        "  [INFO] link tube pushed in after both components: "
        + ("blocked" if late else "possible")
        + " -> fit it on the bench (bench unit), as in the assembly order"
    )

    # --- printability ------------------------------------------------------------
    worst_span, curved, walls = 0.0, [], {}
    for name, (solid, build) in printed_parts().items():
        spans, bad = overhangs(solid, build)
        worst_span = max([worst_span] + spans)
        curved += [f"{name}: {b}" for b in bad]
        walls[name] = min_wall(solid)
    r.check(
        "printed parts need no support",
        worst_span <= BRIDGE_MAX and not curved,
        f"longest bridge {worst_span:.1f} mm (<= {BRIDGE_MAX:.0f}); curved overhangs only on "
        f"holes <= dia {2 * HOLE_SELF_SUPPORT_R:.0f}"
        if not curved
        else "; ".join(curved)[:300],
    )
    thin = min(walls, key=walls.get)
    r.check(
        f"printed walls >= {MIN_WALL} mm (3 perimeters)",
        walls[thin] >= MIN_WALL,
        ", ".join(f"{k} {v:.2f}" for k, v in walls.items()),
    )

    # --- tolerance: statistical as well as worst case ------------------------------
    rng = np.random.default_rng(1)
    n = 200_000

    def u(t):
        return rng.uniform(-t, t, n)

    pin = (C.DOWEL_HOLE_D - C.DOWEL_D) / 2
    dz = (
        u(C.CUT_TOL)
        - u(C.CUT_TOL)
        + u(pin)
        - u(pin)
        + u(C.PRINT_TOL)
        - u(C.PRINT_TOL)
        + u(C.PRINT_TOL)
        - u(C.PRINT_TOL)
        + u(C.POCKET_CLR / 2)
    )
    dy = u(C.PRINT_TOL) - u(C.PRINT_TOL)
    off = float(np.percentile(np.hypot(dz, dy), 99.73))
    strain = 3 * F.TUBE_OD * off / LINK_FREE**2
    r.check(
        "link tube strain, Monte Carlo 99.73 %",
        strain < TUBE_STRAIN_MAX,
        f"offset {off:.2f} mm -> {100 * strain:.2f} % (uniform tolerances, {n} samples)",
    )

    # --- temperature: water 0..40 degC, plate at room temperature -------------------
    brass = V.BODY_L / 2 + F.A_SEAT_TO_TOP + FC.L_TOTAL - (FCL.ROUND_Z[0] + FCL.ROUND_Z[1]) / 2
    grow = DT_WATER * (CTE["brass"] * brass + CTE["tube"] * LINK_FREE)
    r.check(
        "link tube axial strain over the water temperature range",
        grow / LINK_FREE < TUBE_STRAIN_MAX,
        f"+/-{grow:.2f} mm between clamps over +/-{DT_WATER:.0f} K -> "
        f"{100 * grow / LINK_FREE:.2f} %",
    )
    r.check(
        "printed clamps stay below PETG heat deflection",
        HDT_PETG - 40.0 >= 20.0,
        f"PETG HDT {HDT_PETG:.0f} degC vs water <= 40 degC",
    )

    # --- loads ----------------------------------------------------------------------
    thrust = P_MAX * 3.14159 / 4 * F.TUBE_OD**2  # capped tube end, sealed on its OD
    r.check(
        "line-pressure end thrust well under the 500 N design pull",
        5 * thrust <= 500,
        f"{thrust:.0f} N at {10 * P_MAX:.0f} bar on a 12 mm tube end (x{500 / thrust:.1f})",
    )

    def mat(name):
        if name.startswith(("valve_body", "valve_bonnet", "fitting", "qsf_body")):
            return "brass"
        if name.startswith(("m4_", "dowel", "wall_screw")):
            return "steel"
        if name.startswith(("valve_clamp", "fm_clamp")):
            return "PETG"
        if name.startswith("base_"):
            return "PMMA"
        return "PPS"  # flowmeter, knob, release rings, tubes (light plastics)

    grams = sum(p.volume * DENSITY[mat(k)] for k, p in parts.items() if not k.startswith("wall_"))
    mass = grams / 1000  # kg
    mass += 3.14159 / 4 * 8**2 * (LINK_X1 - LINK_X0) * 1e-3 / 1000  # water in the link tube
    screws = [n for n in parts if n.startswith("wall_screw")]
    xs = [parts[n].bounding_box().center().X for n in screws]
    weight = mass * 9.81
    # 500 N tube pull along X at the axis height turns the plate about Z: the screws on
    # the far side take it in tension, all share the shear
    m_pull = 500 * C.AXIS_Y / 1000
    tension = m_pull / ((max(xs) - min(xs)) / 1000) / 2
    shear = (weight**2 + 500**2) ** 0.5 / len(screws)
    per = (tension**2 + shear**2) ** 0.5
    r.check(
        "wall screws: load per M6 under a 500 N tube pull",
        per <= WALL_PLUG_MAX,
        f"station {mass:.2f} kg (solid-print estimate); {per:.0f} N per screw "
        f"(tension {tension:.0f}, shear {shear:.0f}) <= {WALL_PLUG_MAX:.0f} N plasterboard plug",
    )


def phase_sweep(parts: dict[str, Solid], step: float = 7.5) -> tuple[list[str], float]:
    """Spin every screwed-on fitting about its own axis through one hex pitch.

    Thread tightening decides where a fitting's hex flats end up, so the
    clamp must fit at any angle. Returns the clashes found and the worst
    seating gap of the flowmeter fittings.
    """
    groups = {  # fitting parts -> (axis Y, the clamp parts it must not hit)
        "qsf": (FCL.FM_Y, ["base_front"] + [n for n in parts if n.startswith("fm_clamp")]),
        "fitting": (C.VALVE_Y, ["base_front", "valve_clamp_base", "valve_clamp_cap"]),
    }
    hits, worst = [], 0.0
    a = 0.0
    while a < 60.0:
        for prefix, (y, clamp_names) in groups.items():
            for n in [n for n in parts if n.startswith(prefix)]:
                spun = Pos(0, y, 0) * Rot(a, 0, 0) * Pos(0, -y, 0) * parts[n]
                hits += [f"{n}@{a:g}deg/{c}" for c in clamp_names if overlap(spun, parts[c]) > 1e-3]
                if n.startswith("qsf_body"):
                    worst = max(worst, spun.distance_to(parts["fm_clamp_base"]))
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
    front = parts["base_front"]
    bases = ("valve_clamp_base", "fm_clamp_base")
    on_plate = max(front.distance_to(parts[n]) for n in bases)
    held = max(
        parts[a].distance_to(parts[b])
        for a, b in (
            ("valve_body", "valve_clamp_base"),
            ("qsf_body_in", "fm_clamp_base"),
            ("qsf_body_out", "fm_clamp_base"),
        )
    )
    r.check(
        "both clamp bases on one station-plate layer",
        len(front.solids()) == 1 and on_plate < 1e-3 and held < 1e-3,
        "valve and flowmeter clamp bases dowelled into base_front (holes cut in one pass); "
        "wall slots move both together",
    )
    dy_c = abs(C.VALVE_Y - FCL.FM_Y)
    r.check(
        "clamped axis heights equal by design",
        dy_c < 1e-6,
        f"valve {C.VALVE_Y:.3f} / flowmeter {FCL.FM_Y:.3f} mm from wall "
        f"(both pockets {C.POCKET_CLR} mm clearance, seated on cradle floor)",
    )
    # Real parts: the axes are offset by the print and laser tolerances. Worst case:
    # Z = dowel holes in the plate (laser) x2 + pin play in them x2 + dowel holes
    # in the printed bases x2 + channel / bore position in the bases x2 + valve
    # play in its square channel (the QSF centres in its round bore);
    # Y = channel floor / bore bottom above the base underside x2 (the plate
    # face is common to both).
    dz = 2 * C.CUT_TOL + (C.DOWEL_HOLE_D - C.DOWEL_D) + 4 * C.PRINT_TOL + C.POCKET_CLR / 2
    dy = 2 * C.PRINT_TOL
    delta = (dz**2 + dy**2) ** 0.5
    strain = 3 * F.TUBE_OD * delta / LINK_FREE**2  # fixed-fixed tube, lateral offset
    r.check(
        "link tube strain at worst-case tolerances",
        strain < TUBE_STRAIN_MAX,
        f"offset {delta:.2f} mm (print {C.PRINT_TOL}, laser {C.CUT_TOL}) over {LINK_FREE:.0f} mm "
        f"free -> bending strain {100 * strain:.2f} % (< {100 * TUBE_STRAIN_MAX:.1f} %)",
    )
    r.check(
        "axial float lets meter follow the tube",
        FCL.AXIAL_FLOAT >= 1.0,
        f"+/-{FCL.AXIAL_FLOAT:.1f} mm in straps: push tube home, then tighten",
    )

    print("\n8. Flowmeter clamp (grips the round QSF bodies, never the hexes)")
    r.check(
        "straps close onto round body before gap",
        FCL.CLAMP_PRELOAD_TRAVEL - 2 * C.PRINT_TOL > 0.1 - 1e-9,
        f"strap travels {FCL.CAP_DROP:.3f} mm, residual gap {FCL.CLAMP_PRELOAD_TRAVEL:.3f} mm "
        f"({FCL.CLAMP_PRELOAD_TRAVEL - 2 * C.PRINT_TOL:.2f} after print tolerance)",
    )
    seat = max(parts[f"qsf_body_{s}"].distance_to(parts["fm_clamp_base"]) for s in ("in", "out"))
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
    base_wo_pad = parts["fm_clamp_base"] - C.box3d(
        (pb.min.X - 0.1, pb.max.X + 0.1),
        (pb.min.Y - 0.1, pb.max.Y + 0.1),
        (pb.min.Z - 0.1, pb.max.Z + 0.5),
    )
    fm_names = [n for n in parts if n.startswith("flowmeter_")]
    clamp_names = [n for n in clamp_parts(parts) if n != "fm_clamp_base"]
    gap = min(
        [parts[a].distance_to(parts[b]) for a in fm_names for b in clamp_names]
        + [parts[a].distance_to(base_wo_pad) for a in fm_names]
    )
    r.check(
        "meter touches only the pad (no clamp load on plastic)",
        gap >= 1.0,
        f"min gap elsewhere {gap:.1f} mm; screw load goes through the brass fittings",
    )
    # --- Holding (round grip, so friction + pad) ----------------------------------
    # Preload per strap: 2 x M4 into heat-set inserts at low torque. Normal force on
    # the round body is F on the strap half plus F on the base half.
    f_strap = 2 * C.preload(C.CAP_TORQUE)
    t_slip = C.MU * 2 * f_strap * FCL.BODY_D / 2 / 1000  # N.m per strap
    r.check(
        "tube pull held by each strap > 500 N",
        2 * C.MU * f_strap > 500,
        f"{2 * C.MU * f_strap:.0f} N per strap (2 x M4 {C.CAP_TORQUE} N.m, mu {C.MU}) "
        "-> tube loads go fitting -> strap -> wall, not through the meter",
    )
    print(
        "  [INFO] QSF torque (<= 12 N.m) is applied on the bench, meter held by its flats;"
        f" the printed straps ({t_slip:.1f} N.m slip each) never react thread torque"
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
        f"cable {t_cable:.1f} N.m vs friction {t_hold:.1f} N.m (x{t_hold / t_cable:.1f}), "
        "plus the spanner-flat pad as a positive stop",
    )
    p_contact = f_strap / (FCL.BODY_D * FCL.STRAP_W)
    r.check(
        "bore pressure on the printed part < PETG allowable",
        p_contact < C.PRINT_P_ALLOW,
        f"{p_contact:.1f} MPa projected on dia {FCL.BODY_D} x {FCL.STRAP_W:.0f} "
        f"(< {C.PRINT_P_ALLOW:.0f})",
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
        finger &= C.box3d((x_face - 20, x_face + 20), (FCL.FM_Y, FCL.FM_Y + 40), (-40, 40))
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
    from tools.export_step import assembly_compound
    from tools.render import render_assembly

    export_step(assembly_compound(parts), str(out))  # named, coloured sub-assembly tree

    render_assembly(parts, OUTPUT / "assembly.png")
    print(f"\nExported {out.relative_to(ROOT)}, output/assembly.png")
    print("RESULT:", "ALL CHECKS PASS" if not fails else f"{fails} CHECK(S) FAILED")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
