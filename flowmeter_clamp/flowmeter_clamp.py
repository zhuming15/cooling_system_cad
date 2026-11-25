"""Flowmeter saddle clamp (3D printed) + the one-piece station base plate.

Concept
    * HEX PHASE IS NOT CONTROLLABLE. Each QSF fitting is torqued onto the
      flowmeter's G1/2 thread, so where its hex flats end up is random. The
      clamp never touches the hexes. It grips the ROUND dia 20.8 body of each
      fitting (Festo D5), which fits at any angle.
    * TORQUE THE QSF FITTINGS ON THE BENCH (<= 12 N.m, ifm), holding the meter
      by its 12 AF flats, before the meter goes into the clamp. The printed
      clamp is not made to react thread torque.
    * MOUNTING POSITION (ifm manual 11592037, Fig. 1, recommended): horizontal
      pipe, housing and M12 connector ON TOP.
    * ORIENTATION OF THE METER: set level by hand when the straps go on.
      Friction of the two straps on the round QSF bodies holds it against the
      M12 cable torque (assembly check); there is no roll-stop pad (user,
      2026-11-25: the straps stabilise the meter).
    * CLAMP BASE (printed PETG, one piece): two pedestals with lower half-bores
      (dia 20.95) and one lower bar joining them (so both bores print coaxial).
      In a stack the base sits over the M12 elbow of the set below, which sets
      the room left to unplug it (assembly check). Concave joints are filleted (JOINT_FILLET).
      Located on the station plate by 2 dowel pins in the bar and fixed
      by 1 x M4 per pedestal, from the front through the bottom of the half-bore
      into a captive nut in the plate: fit it BEFORE the meter, which then
      covers the heads.
    * STRAPS (printed) - two clamp heads with upper half-bores, 2 x M4 + DIN 125
      washers each (on the strap face: a counterbore would leave 1.25 mm walls
      in a 12 mm strap) into heat-set inserts in the pedestals. Split-gap preload:
      the half-bores are 1.0 mm short of closing.
    * Straps are 12 mm wide on the 11 mm round section (caliper): 1 mm off the hex cone,
      overhanging the smaller collar outboard; +/-1.0 mm axial float.
      Assembly order: push the link tube fully home in both fittings FIRST,
      then tighten the straps, so the tube is never stretched or compressed.
    * STATION BASE: ONE 12 mm cast acrylic plate. Through-cuts: outline, M6
      wall slots, the dowel holes for every clamp module (cut in one pass,
      which keeps the link tube coaxial) and M4 clearance holes. Pockets,
      6 mm deep: hex pockets for the captive M4 nuts from the wall face, M6
      head counterbore slots from the front face. One DXF, one layer per
      feature (CUT, POCKET_WALL_FACE, POCKET_FRONT_FACE).
    * STACK: STACK_N identical sets one above the other
      (assembly.STACK_PITCH) on ONE plate: the outline runs from the lowest
      set to the highest and every set's holes, pockets and wall slots are
      cut in it (make_station_base(x_center, zs)). The plate has its own 6 M6
      wall screws (wall_screw_xz), not a set of them per stacked set.

Global frame: as valve_clamp/clamp.py (wall Y = 0, +Y to operator, Z up).
The flowmeter axis is along X at (Y = FM_Y, Z = 0), centred on X = x_center.
"""

import sys
from collections.abc import Sequence
from pathlib import Path

from build123d import (
    Align,
    Axis,
    Circle,
    Cylinder,
    Pos,
    RectangleRounded,
    RegularPolygon,
    Rot,
    Sketch,
    SlotCenterToCenter,
    Solid,
    chamfer,
    fillet,
)

ROOT = Path(__file__).resolve().parents[1]
for sub in ("", "valve_clamp", "valve", "valve_connector", "flowmeter", "flowmeter_connector"):
    sys.path.insert(0, str(ROOT / sub))

import clamp as C
import flowmeter as FM
import flowmeter_connector as FC

# --- Interface ---------------------------------------------------------------
AXIS_Y = C.AXIS_Y  # same height as the valve -> straight link tube
BODY_D = FC.BODY_D  # 20.8, round body of the QSF (catalogue D5)
POCKET_CLR = C.POCKET_CLR  # 0.15 - same as the valve channel -> same axis height
POCKET_D = BODY_D + POCKET_CLR
SPLIT_GAP = C.SPLIT_GAP  # 1.0
STRAP_TORQUE = 0.55  # N.m, design setting for MSAP elbow cable lever; preload/friction
# remain estimates. Verified against 5x cable-pull margin and PETG bearing pressure.

# Round section of the QSF, in fitting-local Z (port face = 0): FC.ROUND_V, from the
# end of the hex chamfer cone to the collar (caliper)
# The meter has no shoulder that stops the QSF: its 16 AF hex corners (dia 18.48) pass
# inside the QSF thread. The fitting screws on until the meter end face bottoms, via the
# sealing washer, on the port floor (THREAD_DEPTH from the port face).
X_FACE = FM.L_TOTAL / 2 - (FC.THREAD_DEPTH - FC.WASHER_T)  # 22.5, QSF port face
ROUND_Z = (FC.L_TOTAL - FC.ROUND_V[1], FC.L_TOTAL - FC.ROUND_V[0])  # 18.0, 29.0 (caliper)
ROUND_LEN = ROUND_Z[1] - ROUND_Z[0]  # 11.0
STRAP_W = 12.0  # along X
# The real round section is only 11 long (caliper), shorter than the strap. The strap
# keeps HEX_CLEAR off the hex-cone end and overhangs the collar outboard, which is
# smaller than the bore (r <= 9.96 < POCKET_D / 2): it grips the round section only.
HEX_CLEAR = 1.0
STRAP_X = X_FACE + ROUND_Z[0] + HEX_CLEAR + STRAP_W / 2  # strap centre from meter centre
RING_Z = FC.L_TOTAL - FC.RING_END_V  # release ring starts (fitting-local Z)
# meter float before the strap meets the hex cone or reaches the release ring
AXIAL_FLOAT = min(HEX_CLEAR, RING_Z - (ROUND_Z[0] + HEX_CLEAR + STRAP_W))  # +/-1.0
# round-body length under the strap, worst case over the float
STRAP_CONTACT = min(STRAP_W, ROUND_Z[1] - (ROUND_Z[0] + HEX_CLEAR + AXIAL_FLOAT))  # 9.0


# --- Envelope ----------------------------------------------------------------
PED_H = 46.0  # pedestal / strap height along Z
CAP_TOP_WALL = 6.0
BAR_Z = (-PED_H / 2, -10.0)  # lower bar joining the pedestals, below the pipe (Z >= -6)
BAR_T = 6.0  # along Y, from the plate; clear of the hexes (corners reach Y 16.1)
PED_CHAMFER = 1.0  # pedestal / strap front edges
JOINT_FILLET = 2.0  # concave structural joints (pedestals to bar)
PLATE_T = C.PLATE_T  # 12, the one station plate
PLATE_H = C.PLATE_H  # 92
PLATE_L = 2 * (STRAP_X + STRAP_W / 2 + 3.5)  # station-plate length around the meter
WALL_SCREW_X = 36.0  # between housing (+/-24.1) and straps (>= 41.5): hex-key path
WALL_SCREW_Z = C.WALL_SCREW_Z  # 37 - clear of the flowmeter housing (Z +/-15.1)

# --- Fasteners ---------------------------------------------------------------------
M4_Z = 15.5  # strap screws (x, +/-M4_Z) into inserts
DOWEL_DX = 34.0  # dowels in the bar at x_center +/- 34: clean through-holes in the 6 mm
# bar, clear of the pedestal fillets (pedestal inner faces at +/- 41.5)
DOWEL_WALL = 1.5  # PETG under the dowel hole (>= 3 perimeters, 1.2)
DOWEL_Z = BAR_Z[0] + DOWEL_WALL + C.DOWEL_D / 2  # -19.5

# Derived Y stations
Y_SPLIT_BASE = AXIS_Y - SPLIT_GAP / 2
Y_SPLIT_CAP = AXIS_Y + SPLIT_GAP / 2
Y_CAP_TOP = AXIS_Y + POCKET_D / 2 + CAP_TOP_WALL
Y_BORE_BOTTOM = AXIS_Y - POCKET_D / 2
FM_Y = AXIS_Y - POCKET_D / 2 + BODY_D / 2  # clamped fitting/meter axis
CAP_DROP = (AXIS_Y + POCKET_D / 2) - (FM_Y + BODY_D / 2)  # 0.15
CLAMP_PRELOAD_TRAVEL = SPLIT_GAP - CAP_DROP
CAP_SEAT = Y_CAP_TOP + C.WASHER[2] - CAP_DROP  # washer on top: no counterbore in a 12 mm strap
CAP_SCREW_LEN = C.cap_screw_length(CAP_SEAT, Y_SPLIT_BASE)
MOUNT_SEAT, MOUNT_LEN = C.mount_screw(Y_BORE_BOTTOM)


def strap_xs(x_center: float) -> tuple[float, float]:
    return (x_center - STRAP_X, x_center + STRAP_X)


def cap_xz(x_center: float) -> list[tuple[float, float]]:
    return [(x, sz * M4_Z) for x in strap_xs(x_center) for sz in (-1, 1)]


def mount_xz(x_center: float) -> list[tuple[float, float]]:
    return [(x, 0.0) for x in strap_xs(x_center)]


def dowel_xz(x_center: float) -> list[tuple[float, float]]:
    return [(x_center + s * DOWEL_DX, DOWEL_Z) for s in (-1, 1)]


def _bore(xc: float) -> Solid:
    """Round dia POCKET_D bore along X through one pedestal/strap."""
    return (
        Pos(xc - STRAP_W / 2 - 1, AXIS_Y, 0)
        * Rot(0, 90, 0)
        * Cylinder(POCKET_D / 2, STRAP_W + 2, align=(Align.CENTER, Align.CENTER, Align.MIN))
    )


def _concave_edges(part: Solid) -> list:
    """Straight edges where two perpendicular planar faces meet inside a corner."""
    faces_of: dict = {}
    for f in part.faces():
        if f.geom_type.name != "PLANE":
            continue
        for e in f.edges():
            faces_of.setdefault(e, []).append(f)
    out = []
    for e in part.edges():  # the solid's own edges, so fillet() finds their parent
        fs = faces_of.get(e, [])
        if len(fs) != 2 or e.geom_type.name != "LINE" or e.length < 0.5:
            continue
        m = e.center()
        n1, n2 = fs[0].normal_at(m), fs[1].normal_at(m)
        if abs(n1.dot(n2)) > 1e-6:
            continue
        # out along one face's normal, back along the other's: material only at an inside corner
        if part.is_inside(m + (n1 - n2) * 0.05):
            out.append(e)
    return out


def _fillet_joints(base: Solid) -> Solid:
    """Fillet the concave structural joints (pedestals to bar)."""
    edges = _concave_edges(base)
    if not edges:
        raise ValueError("no concave joints found to fillet")
    return fillet(edges, JOINT_FILLET)


def make_base(x_center: float) -> Solid:
    """Printed clamp base: 2 pedestals and the lower bar, on the
    station plate at Y = PLATE_T."""
    xs = strap_xs(x_center)
    base = None
    for xc in xs:
        ped = C.box3d(
            (xc - STRAP_W / 2, xc + STRAP_W / 2), (PLATE_T, Y_SPLIT_BASE), (-PED_H / 2, PED_H / 2)
        )
        base = ped if base is None else base + ped
    base = chamfer(base.edges().filter_by(Axis.X).group_by(Axis.Y)[-1], PED_CHAMFER)
    x0, x1 = xs[0] - STRAP_W / 2, xs[1] + STRAP_W / 2
    base += C.box3d((x0, x1), (PLATE_T, PLATE_T + BAR_T), BAR_Z)
    base = _fillet_joints(base)
    for xc in xs:
        base -= _bore(xc)
    return C.base_holes(
        base,
        mount_xz(x_center),
        MOUNT_SEAT,
        dowel_xz(x_center),
        cap_xz(x_center),
        Y_SPLIT_BASE,
        Y_BORE_BOTTOM,
    )


def make_cap_unclamped(xc: float) -> Solid:
    """One strap, free (as-printed) position, centred at X = xc."""
    cap = C.box3d(
        (xc - STRAP_W / 2, xc + STRAP_W / 2), (Y_SPLIT_CAP, Y_CAP_TOP), (-PED_H / 2, PED_H / 2)
    )
    cap = chamfer(cap.edges().filter_by(Axis.X).group_by(Axis.Y)[-1], PED_CHAMFER)
    cap -= _bore(xc)
    return C.cap_holes(cap, [(xc, sz * M4_Z) for sz in (-1, 1)], Y_CAP_TOP, counterbore=False)


def make_caps(x_center: float) -> list[Solid]:
    """Both straps in the clamped position."""
    return [Pos(0, -CAP_DROP, 0) * make_cap_unclamped(xc) for xc in strap_xs(x_center)]


def make_hw(x_center: float) -> dict[str, list[Solid]]:
    return C.make_hardware(
        cap_xz(x_center),
        CAP_SEAT,
        CAP_SCREW_LEN,
        mount_xz(x_center),
        MOUNT_SEAT,
        MOUNT_LEN,
        dowel_xz(x_center),
        Y_SPLIT_BASE,
    )


def wall_screw_xz(x_center: float, zs: Sequence[float] = (0.0,)) -> list[tuple[float, float]]:
    """M6 wall screws of the ONE plate (not per set): 3 columns (the valve's outer
    column, the meter's outer column and midway) x 2 rows (below the lowest set,
    above the highest), all at slot positions proven clear in a set. Six carry the
    whole stack (assembly check "wall screws: load per M6")."""
    x0, x1 = -C.WALL_SCREW_X, x_center + WALL_SCREW_X
    rows = (min(zs) - WALL_SCREW_Z, max(zs) + WALL_SCREW_Z)
    return [(x, z) for z in rows for x in (x0, (x0 + x1) / 2, x1)]


def make_wall_screws(x_center: float, zs: Sequence[float] = (0.0,), length: float = 40.0):
    return C.make_wall_screws(wall_screw_xz(x_center, zs), length=length)


# --- Station base plate (ONE acrylic plate for the whole stack) ----------------------
# `zs` are the Z offsets of the sets the plate carries, relative to the set being
# built; (0.0,) is a plate for a single set. Every set gets the same holes, pockets
# and wall slots; the outline runs from the lowest set to the highest.
def _outline(x_center: float, zs: Sequence[float]) -> Sketch:
    xs = [-C.VALVE_PLATE_L / 2, C.VALVE_PLATE_L / 2, x_center - PLATE_L / 2, x_center + PLATE_L / 2]
    x0, x1 = min(xs), max(xs)
    z0, z1 = min(zs) - PLATE_H / 2, max(zs) + PLATE_H / 2
    return Pos((x0 + x1) / 2, (z0 + z1) / 2) * RectangleRounded(x1 - x0, z1 - z0, C.PLATE_R)


def _wall_slots(x_center: float, d: float, zs: Sequence[float]) -> Sketch:
    out = None
    for x, z in wall_screw_xz(x_center, zs):
        s = Pos(x, z) * SlotCenterToCenter(C.WALL_SLOT, d, rotation=90)
        out = s if out is None else out + s
    return out


def all_mount_xz(x_center: float, zs: Sequence[float] = (0.0,)) -> list[tuple[float, float]]:
    return [(x, z + z0) for z0 in zs for x, z in list(C.MOUNT_XZ) + mount_xz(x_center)]


def all_dowel_xz(x_center: float, zs: Sequence[float] = (0.0,)) -> list[tuple[float, float]]:
    return [(x, z + z0) for z0 in zs for x, z in list(C.DOWEL_XZ) + dowel_xz(x_center)]


def plate_cut_profile(x_center: float, zs: Sequence[float] = (0.0,)) -> Sketch:
    """Through-cuts: outline, M6 wall slots, dowel holes (the alignment datum), M4 holes."""
    p = _outline(x_center, zs) - _wall_slots(x_center, C.WALL_HOLE_D, zs)
    for x, z in all_dowel_xz(x_center, zs):
        p -= Pos(x, z) * Circle(C.DOWEL_HOLE_D / 2)
    for x, z in all_mount_xz(x_center, zs):
        p -= Pos(x, z) * Circle(C.M4_CLR_D / 2)
    return p


def nut_pockets(x_center: float, zs: Sequence[float] = (0.0,)) -> Sketch:
    """Hex pockets for the captive M4 nuts, NUT_POCKET_DEPTH deep from the wall face."""
    out = None
    for x, z in all_mount_xz(x_center, zs):
        h = Pos(x, z) * RegularPolygon(C.NUT_POCKET_AF / 2, 6, major_radius=False)
        out = h if out is None else out + h
    return out


def head_pockets(x_center: float, zs: Sequence[float] = (0.0,)) -> Sketch:
    """M6 head counterbore slots, WALL_CB_DEPTH deep from the front face."""
    return _wall_slots(x_center, C.WALL_CB_D, zs)


def plate_layers(x_center: float, zs: Sequence[float] = (0.0,)) -> dict[str, Sketch]:
    """DXF layers: through-cut and the two pocket features (6 mm each)."""
    return {
        "CUT": plate_cut_profile(x_center, zs),
        "POCKET_WALL_FACE": nut_pockets(x_center, zs),
        "POCKET_FRONT_FACE": head_pockets(x_center, zs),
    }


def make_station_base(x_center: float, zs: Sequence[float] = (0.0,)) -> dict[str, Solid]:
    """Station base: one plate for every set at `zs`, through-cuts plus 6 mm pockets."""
    plate = C.plate(plate_cut_profile(x_center, zs), 0.0, PLATE_T)
    plate -= C.plate(nut_pockets(x_center, zs), 0.0, C.NUT_POCKET_DEPTH)
    plate -= C.plate(head_pockets(x_center, zs), C.WALL_SEAT_Y, C.WALL_CB_DEPTH)
    return {"base_plate": plate}


if __name__ == "__main__":
    here = Path(__file__).parent
    import assembly as A

    xc = A.X_FM
    C.export_layers(plate_layers(xc, A.stack_zs()), here / "base_plate.dxf")
    parts = make_station_base(xc, A.stack_zs()) | {
        "sv3051_clamp_base": make_base(xc),
        "sv3051_clamp_strap": make_cap_unclamped(STRAP_X),
    }
    for n, p in parts.items():
        bb = p.bounding_box()
        mat = "PMMA" if n.startswith("base_") else "PETG, solid"
        rho = 1.19e-3 if n.startswith("base_") else 1.27e-3
        print(
            f"{n}: {bb.size.X:.1f} x {bb.size.Y:.1f} x {bb.size.Z:.1f} mm, {p.volume * rho:.0f} g ({mat})"
        )
    print(
        f"straps: 2 x M4x{CAP_SCREW_LEN:.0f} + DIN 125 each into inserts, {STRAP_TORQUE} N.m; "
        f"base: 2 x M4x{MOUNT_LEN:.0f} into captive nuts, {C.MOUNT_TORQUE} N.m; 2 x dowel 4 m6 x 12"
    )
    print(
        "Exported flowmeter_clamp/base_plate.dxf: layer CUT (through), POCKET_WALL_FACE and "
        f"POCKET_FRONT_FACE ({C.NUT_POCKET_DEPTH:.0f} / {C.WALL_CB_DEPTH:.0f} mm deep); "
        "one plate for all stacked sets"
    )
    print("STEP: uv run python tools/export_step.py -> output/step/")
