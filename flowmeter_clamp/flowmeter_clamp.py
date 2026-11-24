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
    * ORIENTATION OF THE METER comes from the meter itself: its downward 12 AF
      flat rests on the LOCATING PAD, a ledge of the clamp base under the meter.
      The pad only locates; no screw load passes through it.
    * CLAMP BASE (printed PETG, one piece): two pedestals with lower half-bores
      (dia 20.95), a lower bar joining them (so both bores print coaxial), and
      the pad. Located on the station plate by 2 dowel pins in the bar and fixed
      by 1 x M4 per pedestal, from the front through the bottom of the half-bore
      into a captive nut in the plate: fit it BEFORE the meter, which then
      covers the heads.
    * STRAPS (printed) - two clamp heads with upper half-bores, 2 x M4 + DIN 125
      washers each (on the strap face: a counterbore would leave 1.25 mm walls
      in a 12 mm strap) into heat-set inserts in the pedestals. Split-gap preload:
      the half-bores are 1.0 mm short of closing.
    * Straps are 12 mm wide on a 15.3 mm round section: +/-1.65 mm axial float.
      Assembly order: push the link tube fully home in both fittings FIRST,
      then tighten the straps, so the tube is never stretched or compressed.
    * STATION BASE: ONE 12 mm cast acrylic plate. Through-cuts: outline, M6
      wall slots, the dowel holes for every clamp module (cut in one pass,
      which keeps the link tube coaxial) and M4 clearance holes. Pockets,
      6 mm deep: hex pockets for the captive M4 nuts from the wall face, M6
      head counterbore slots from the front face. One DXF, one layer per
      feature (CUT, POCKET_WALL_FACE, POCKET_FRONT_FACE).

Global frame: as valve_clamp/clamp.py (wall Y = 0, +Y to operator, Z up).
The flowmeter axis is along X at (Y = FM_Y, Z = 0), centred on X = x_center;
`inlet_sign` is the global X sign of the meter's inlet end (spanner flats).
"""

import sys
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
SPLIT_GAP = C.SPLIT_GAP  # 0.5
STRAP_TORQUE = 0.55  # N.m, design setting for MSAP elbow cable lever; preload/friction
# remain estimates. Verified against 5x cable-pull margin and PETG bearing pressure.

# Round section of the QSF, in fitting-local Z (port face = 0): from the end of
# the hex chamfer cone (v = 19.8) to the start of the release-ring shoulder (v = 4.5)
X_FACE = FM.L_TOTAL / 2 - FM.THREAD_L  # 25.5, QSF face on the meter
ROUND_Z = (FC.L_TOTAL - FC.BODY_PROFILE[-1][1], FC.L_TOTAL - FC.BODY_PROFILE[2][1])  # 21.0, 36.3
ROUND_LEN = ROUND_Z[1] - ROUND_Z[0]  # 15.3
STRAP_X = X_FACE + (ROUND_Z[0] + ROUND_Z[1]) / 2  # strap centre from meter centre
STRAP_W = 12.0  # along X
AXIAL_FLOAT = (ROUND_LEN - STRAP_W) / 2  # +/-1.65

# Locating pad under the meter's wall-side spanner flat (meter-local X range)
PAD_X = (FM.SPANNER_X[0] + 1.0, FM.SPANNER_X[1] - 1.0)  # 16.6 .. 24.5
PAD_W = 9.0  # across the flat (Y), inside its 11.5
PAD_T = 8.0  # ledge thickness below the flat

# --- Envelope ----------------------------------------------------------------
PED_H = 46.0  # pedestal / strap height along Z
CAP_TOP_WALL = 6.0
BAR_Z = (-PED_H / 2, -10.0)  # lower bar joining the pedestals, below the pipe (Z >= -6)
BAR_T = 6.0  # along Y, from the plate; clear of the hexes (corners reach Y 16.1)
PLATE_T = C.PLATE_T  # 12, the one station plate
PLATE_H = C.PLATE_H  # 92
PLATE_L = 2 * (STRAP_X + STRAP_W / 2 + 3.5)  # station-plate length around the meter
WALL_SCREW_X = 36.0  # between housing (+/-24.1) and straps (>= 48): hex-key path
WALL_SCREW_Z = C.WALL_SCREW_Z  # 37 - clear of the flowmeter housing (Z +/-15.1)

# --- Fasteners ---------------------------------------------------------------------
M4_Z = 15.5  # strap screws (x, +/-M4_Z) into inserts
DOWEL_DX = 40.0  # dowels in the bar at x_center +/- 40, clear of the pad
DOWEL_Z = (BAR_Z[0] + BAR_Z[1]) / 2

# Derived Y stations
Y_SPLIT_BASE = AXIS_Y - SPLIT_GAP / 2
Y_SPLIT_CAP = AXIS_Y + SPLIT_GAP / 2
Y_CAP_TOP = AXIS_Y + POCKET_D / 2 + CAP_TOP_WALL
Y_BORE_BOTTOM = AXIS_Y - POCKET_D / 2
FM_Y = AXIS_Y - POCKET_D / 2 + BODY_D / 2  # clamped fitting/meter axis
CAP_DROP = (AXIS_Y + POCKET_D / 2) - (FM_Y + BODY_D / 2)  # 0.15
CLAMP_PRELOAD_TRAVEL = SPLIT_GAP - CAP_DROP
PAD_TOP_Z = -FM.SPANNER_AF / 2  # touches the downward flat
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


def pad_box(x_center: float, inlet_sign: int) -> Solid:
    xs = sorted(x_center + inlet_sign * x for x in PAD_X)
    return C.box3d(xs, (PLATE_T, FM_Y + PAD_W / 2), (PAD_TOP_Z - PAD_T, PAD_TOP_Z))


def make_base(x_center: float, inlet_sign: int) -> Solid:
    """Printed clamp base: 2 pedestals + bar + pad, on the station plate at Y = PLATE_T."""
    xs = strap_xs(x_center)
    base = None
    for xc in xs:
        ped = C.box3d(
            (xc - STRAP_W / 2, xc + STRAP_W / 2), (PLATE_T, Y_SPLIT_BASE), (-PED_H / 2, PED_H / 2)
        )
        base = ped if base is None else base + ped
    base = chamfer(base.edges().filter_by(Axis.X).group_by(Axis.Y)[-1], 1.0)
    x0, x1 = xs[0] - STRAP_W / 2, xs[1] + STRAP_W / 2
    base += C.box3d((x0, x1), (PLATE_T, PLATE_T + BAR_T), BAR_Z)
    base += pad_box(x_center, inlet_sign)
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
    cap = chamfer(cap.edges().filter_by(Axis.X).group_by(Axis.Y)[-1], 1.0)
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


def make_wall_screws(x_center: float, length: float = 40.0) -> list[Solid]:
    return C.make_wall_screws(xs=[x_center + sx * WALL_SCREW_X for sx in (-1, 1)], length=length)


# --- Station base plate (one acrylic plate: through-cuts + 6 mm pockets) -------------
def _outline(x_center: float) -> Sketch:
    xs = [-C.VALVE_PLATE_L / 2, C.VALVE_PLATE_L / 2, x_center - PLATE_L / 2, x_center + PLATE_L / 2]
    x0, x1 = min(xs), max(xs)
    return Pos((x0 + x1) / 2, 0) * RectangleRounded(x1 - x0, PLATE_H, C.PLATE_R)


def _wall_slots(x_center: float, d: float) -> Sketch:
    xs = [sx * C.WALL_SCREW_X for sx in (-1, 1)] + [x_center + sx * WALL_SCREW_X for sx in (-1, 1)]
    out = None
    for x in xs:
        for sz in (-1, 1):
            s = Pos(x, sz * WALL_SCREW_Z) * SlotCenterToCenter(C.WALL_SLOT, d, rotation=90)
            out = s if out is None else out + s
    return out


def all_mount_xz(x_center: float) -> list[tuple[float, float]]:
    return list(C.MOUNT_XZ) + mount_xz(x_center)


def all_dowel_xz(x_center: float) -> list[tuple[float, float]]:
    return list(C.DOWEL_XZ) + dowel_xz(x_center)


def plate_cut_profile(x_center: float) -> Sketch:
    """Through-cuts: outline, M6 wall slots, dowel holes (the alignment datum), M4 holes."""
    p = _outline(x_center) - _wall_slots(x_center, C.WALL_HOLE_D)
    for x, z in all_dowel_xz(x_center):
        p -= Pos(x, z) * Circle(C.DOWEL_HOLE_D / 2)
    for x, z in all_mount_xz(x_center):
        p -= Pos(x, z) * Circle(C.M4_CLR_D / 2)
    return p


def nut_pockets(x_center: float) -> Sketch:
    """Hex pockets for the captive M4 nuts, NUT_POCKET_DEPTH deep from the wall face."""
    out = None
    for x, z in all_mount_xz(x_center):
        h = Pos(x, z) * RegularPolygon(C.NUT_POCKET_AF / 2, 6, major_radius=False)
        out = h if out is None else out + h
    return out


def head_pockets(x_center: float) -> Sketch:
    """M6 head counterbore slots, WALL_CB_DEPTH deep from the front face."""
    return _wall_slots(x_center, C.WALL_CB_D)


def plate_layers(x_center: float) -> dict[str, Sketch]:
    """DXF layers: through-cut and the two pocket features (6 mm each)."""
    return {
        "CUT": plate_cut_profile(x_center),
        "POCKET_WALL_FACE": nut_pockets(x_center),
        "POCKET_FRONT_FACE": head_pockets(x_center),
    }


def make_station_base(x_center: float) -> dict[str, Solid]:
    """Station base: one plate, through-cuts plus 6 mm pockets from each face."""
    plate = C.plate(plate_cut_profile(x_center), 0.0, PLATE_T)
    plate -= C.plate(nut_pockets(x_center), 0.0, C.NUT_POCKET_DEPTH)
    plate -= C.plate(head_pockets(x_center), C.WALL_SEAT_Y, C.WALL_CB_DEPTH)
    return {"base_plate": plate}


if __name__ == "__main__":
    here = Path(__file__).parent
    import assembly as A

    xc, inlet = A.X_FM, -A.FLOW_DIR
    C.export_layers(plate_layers(xc), here / "base_plate.dxf")
    parts = make_station_base(xc) | {
        "sv3051_clamp_base": make_base(xc, inlet),
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
        f"POCKET_FRONT_FACE ({C.NUT_POCKET_DEPTH:.0f} / {C.WALL_CB_DEPTH:.0f} mm deep)"
    )
    print("STEP: uv run python tools/export_step.py -> output/step/")
