"""Wall-mount clamp for the ifm SV3051 flowmeter with two Festo QSF-1/2-12-B fittings.

Concept
    * HEX PHASE IS NOT CONTROLLABLE. Each QSF fitting is torqued onto the
      flowmeter's G1/2 thread (<= 12 Nm), so where its hex flats end up is
      random, and the flowmeter itself must face the operator. The clamp
      therefore never touches the hexes. It grips the ROUND dia 20.8 body of
      each fitting (Festo D5), which fits at any angle.
    * MOUNTING POSITION (ifm manual 11592037, Fig. 1, recommended): horizontal
      pipe, housing and M12 connector ON TOP. The station hangs on the wall;
      the pipe runs parallel to the wall.
    * ORIENTATION OF THE METER comes from the meter itself. Its 12 AF spanner
      flats are moulded into the pipe, fixed relative to the housing. The
      flat facing DOWN rests on a LOCATING PAD - a ledge growing out of the
      base under the meter. Gravity keeps it seated, and a flat on a flat pad
      can't roll either way, so the housing stays upright. The pad only
      locates; no screw load passes through it.
    * Tube push/pull loads go fitting -> strap -> base -> wall and never pass
      through the flowmeter's plastic (PPS) G1/2 threads.
    * BASE  - two pedestals with lower half-bores (dia 20.95) and the locating
              pad, part of the COMMON STATION BASE (make_station_base): one
              12 mm plate that also carries the valve cradle, machined in one
              setup. The valve axis and the flowmeter-fitting axis are
              therefore coaxial by machining; the wall slots move the whole
              plate, never one clamp relative to the other.
    * STRAPS - two straps with upper half-bores, 2 x M4 each. Split-gap
              preload as in the valve clamp: the two half-bores are 0.5 mm
              short of closing, so the screws pull the straps onto the round
              body. A round body in a round seat also centres itself
              vertically (Z), so it lines up with the valve.
    * Straps are 12 mm wide on a 15.3 mm round section: +/-1.65 mm axial
      float, and they never reach the hex chamfer or the POM release ring.
      Assembly order: push the link tube fully home in both fittings FIRST,
      then tighten the straps, so the tube is never stretched or compressed.

Global frame: same as valve_clamp/clamp.py (wall Y = 0, +Y to operator,
Z up). The flowmeter axis is horizontal along X at (Y = FM_Y, Z = 0),
centred on X = x_center. `inlet_sign` is the global X sign of the
flowmeter's inlet end (where the spanner flats are).
Material: 6061-T6, clear anodised.
"""

import sys
from pathlib import Path

from build123d import (
    Align,
    Axis,
    Box,
    Cylinder,
    Plane,
    Pos,
    Rot,
    SlotCenterToCenter,
    Solid,
    chamfer,
    export_step,
    extrude,
)

ROOT = Path(__file__).resolve().parents[1]
for sub in ("", "valve_clamp", "valve", "valve_connector", "flowmeter", "flowmeter_connector"):
    sys.path.insert(0, str(ROOT / sub))

import clamp as C
import flowmeter as FM
import flowmeter_connector as FC

# --- Interface ---------------------------------------------------------------
AXIS_Y = C.AXIS_Y               # same height as the valve -> straight link tube
BODY_D = FC.BODY_D              # 20.8, round body of the QSF (catalogue D5)
POCKET_CLR = C.POCKET_CLR       # 0.15 - same as the valve channel -> same axis height
POCKET_D = BODY_D + POCKET_CLR
SPLIT_GAP = C.SPLIT_GAP         # 0.5

# Round section of the QSF, in fitting-local Z (port face = 0): from the end of
# the hex chamfer cone (v = 19.8) to the start of the release-ring shoulder (v = 4.5)
X_FACE = FM.L_TOTAL / 2 - FM.THREAD_L                      # 25.5, QSF face on the meter
ROUND_Z = (FC.L_TOTAL - FC.BODY_PROFILE[-1][1], FC.L_TOTAL - FC.BODY_PROFILE[2][1])  # 21.0, 36.3
ROUND_LEN = ROUND_Z[1] - ROUND_Z[0]                        # 15.3
STRAP_X = X_FACE + (ROUND_Z[0] + ROUND_Z[1]) / 2           # strap centre from meter centre
STRAP_W = 12.0                                             # along X
AXIAL_FLOAT = (ROUND_LEN - STRAP_W) / 2                    # +/-1.65

# Locating pad under the meter's wall-side spanner flat (meter-local X range)
PAD_X = (FM.SPANNER_X[0] + 1.0, FM.SPANNER_X[1] - 1.0)     # 16.6 .. 24.5
PAD_W = 9.0                                                # across the flat (Y), inside its 11.5
PAD_T = 8.0                                                # ledge thickness below the flat

# --- Envelope ----------------------------------------------------------------
PED_H = 46.0                    # pedestal / strap height along Z
CAP_TOP_WALL = 6.0
PLATE_T = C.PLATE_T             # 12
PLATE_H = C.PLATE_H             # 92
PLATE_L = 2 * (STRAP_X + STRAP_W / 2 + 3.5)               # along X

# --- Fasteners -----------------------------------------------------------------
M4_Z = 15.5                     # strap screws, ISO 4762 M4 x 25, 8.8, 2.5 Nm
M4_CLR_D, M4_CB_D, M4_CB_DEPTH = 4.5, 8.0, 4.5
M4_TAP_D, M4_TAP_DEPTH = 3.3, 16.0
M4_LEN, M4_HEAD_D, M4_HEAD_H = 25.0, 7.0, 4.0
M4_TORQUE = 2.5                 # N.m, 8.8 (VDI 2230 max 3.0 N.m at mu 0.12 -> ~3.7 kN)
WALL_SCREW_X = 36.0             # between housing (+/-24.1) and straps (>= 48): hex-key path
                                # clear of the M12 connector on top
WALL_SCREW_Z = C.WALL_SCREW_Z   # 37 - clear of the flowmeter housing (Z +/-15.1)

# Derived Y stations
Y_SPLIT_BASE = AXIS_Y - SPLIT_GAP / 2
Y_SPLIT_CAP = AXIS_Y + SPLIT_GAP / 2
Y_CAP_TOP = AXIS_Y + POCKET_D / 2 + CAP_TOP_WALL
FM_Y = AXIS_Y - POCKET_D / 2 + BODY_D / 2                  # clamped fitting/meter axis
CAP_DROP = (AXIS_Y + POCKET_D / 2) - (FM_Y + BODY_D / 2)   # 0.15
CLAMP_PRELOAD_TRAVEL = SPLIT_GAP - CAP_DROP
PAD_TOP_Z = -FM.SPANNER_AF / 2                             # touches the downward flat


def _box(x: tuple, y: tuple, z: tuple) -> Solid:
    return Pos((x[0] + x[1]) / 2, (y[0] + y[1]) / 2, (z[0] + z[1]) / 2) * Box(
        x[1] - x[0], y[1] - y[0], z[1] - z[0])


def _bore(xc: float) -> Solid:
    """Round dia POCKET_D bore along X through one pedestal/strap."""
    return Pos(xc - STRAP_W / 2 - 1, AXIS_Y, 0) * Rot(0, 90, 0) * Cylinder(
        POCKET_D / 2, STRAP_W + 2, align=(Align.CENTER, Align.CENTER, Align.MIN))


def strap_xs(x_center: float) -> tuple[float, float]:
    return (x_center - STRAP_X, x_center + STRAP_X)


def pad_box(x_center: float, inlet_sign: int) -> Solid:
    xs = sorted(x_center + inlet_sign * x for x in PAD_X)
    return _box(xs, (PLATE_T - 0.5, FM_Y + PAD_W / 2), (PAD_TOP_Z - PAD_T, PAD_TOP_Z))


def make_base(x_center: float, inlet_sign: int) -> Solid:
    x0, x1 = x_center - PLATE_L / 2, x_center + PLATE_L / 2
    base = _box((x0, x1), (0, PLATE_T), (-PLATE_H / 2, PLATE_H / 2))
    for xc in strap_xs(x_center):
        base += _box((xc - STRAP_W / 2, xc + STRAP_W / 2), (PLATE_T, Y_SPLIT_BASE),
                     (-PED_H / 2, PED_H / 2))
    base = chamfer(base.edges().filter_by(Axis.X).group_by(Axis.Y)[-1], 1.0)
    base += pad_box(x_center, inlet_sign)
    for xc in strap_xs(x_center):
        base -= _bore(xc)
        for sz in (-1, 1):
            base -= C._y_cyl(M4_TAP_D, -M4_TAP_DEPTH, xc, Y_SPLIT_BASE, sz * M4_Z)
    for sx in (-1, 1):
        for sz in (-1, 1):
            for d, depth, y0 in (
                (C.WALL_HOLE_D, PLATE_T + 2, -1.0),
                (C.WALL_CB_D, C.WALL_CB_DEPTH + 1, PLATE_T - C.WALL_CB_DEPTH),
            ):
                slot = Plane.XZ.offset(-y0) * Pos(x_center + sx * WALL_SCREW_X,
                                                  sz * WALL_SCREW_Z) * (
                    SlotCenterToCenter(C.WALL_SLOT, d, rotation=90))
                base -= extrude(slot, amount=-depth)
    return base


def make_station_base(x_center: float, inlet_sign: int) -> Solid:
    """One-piece wall plate: valve cradle + flowmeter pedestals and pad + bridge."""
    valve_base = C.make_base()
    fm_base = make_base(x_center, inlet_sign)
    if x_center < 0:                           # bridge the gap, 0.5 mm into each plate
        x0, x1 = x_center + PLATE_L / 2 - 0.5, -C.VALVE_PLATE_L / 2 + 0.5
    else:
        x0, x1 = C.VALVE_PLATE_L / 2 - 0.5, x_center - PLATE_L / 2 + 0.5
    bridge = _box((x0, x1), (0, PLATE_T), (-PLATE_H / 2, PLATE_H / 2))
    return valve_base + fm_base + bridge


def make_cap_unclamped(xc: float) -> Solid:
    """One strap, free (as-machined) position, centred at X = xc."""
    cap = _box((xc - STRAP_W / 2, xc + STRAP_W / 2), (Y_SPLIT_CAP, Y_CAP_TOP),
               (-PED_H / 2, PED_H / 2))
    cap = chamfer(cap.edges().filter_by(Axis.X).group_by(Axis.Y)[-1], 1.0)
    cap -= _bore(xc)
    h = Y_CAP_TOP - Y_SPLIT_CAP
    for sz in (-1, 1):
        cap -= C._y_cyl(M4_CLR_D, -(h + 2), xc, Y_CAP_TOP + 1, sz * M4_Z)
        cap -= C._y_cyl(M4_CB_D, -(M4_CB_DEPTH + 1), xc, Y_CAP_TOP + 1, sz * M4_Z)
    return cap


def make_caps(x_center: float) -> list[Solid]:
    """Both straps in the clamped position."""
    return [Pos(0, -CAP_DROP, 0) * make_cap_unclamped(xc) for xc in strap_xs(x_center)]


def make_m4_screws(x_center: float) -> list[Solid]:
    y_seat = Y_CAP_TOP - M4_CB_DEPTH - CAP_DROP
    out = []
    for xc in strap_xs(x_center):
        for sz in (-1, 1):
            head = C._y_cyl(M4_HEAD_D, M4_HEAD_H, xc, y_seat, sz * M4_Z)
            shank = C._y_cyl(3.2, -M4_LEN, xc, y_seat, sz * M4_Z)   # thread at minor dia
            out.append(head + shank)
    return out


def make_wall_screws(x_center: float, length: float = 40.0) -> list[Solid]:
    y_seat = PLATE_T - C.WALL_CB_DEPTH
    out = []
    for sx in (-1, 1):
        for sz in (-1, 1):
            x = x_center + sx * WALL_SCREW_X
            out.append(C._y_cyl(10.0, 6.0, x, y_seat, sz * WALL_SCREW_Z)
                       + C._y_cyl(6.0, -length, x, y_seat, sz * WALL_SCREW_Z))
    return out


if __name__ == "__main__":
    here = Path(__file__).parent
    import assembly as A

    base = make_station_base(A.X_FM, -A.FLOW_DIR)
    cap = make_cap_unclamped(STRAP_X)
    export_step(base, str(here / "station_base.step"))
    export_step(cap, str(here / "sv3051_clamp_strap.step"))
    for n, p in (("station base", base), ("strap (x2)", cap)):
        bb = p.bounding_box()
        print(f"{n}: {bb.size.X:.1f} x {bb.size.Y:.1f} x {bb.size.Z:.1f} mm, "
              f"{p.volume * 2.70e-3:.0f} g (6061)")
    print(f"axial float on the round body: +/-{AXIAL_FLOAT:.2f} mm")
    print("Exported station_base.step (valve + flowmeter, one piece) and sv3051_clamp_strap.step")
