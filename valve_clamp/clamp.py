"""Wall-mount split clamp for the RS 283-8289 flow control valve.

Concept
    * BASE  - one-piece wall bracket: 12 mm back plate with 4 slotted,
              counterbored M6 wall-screw holes + a pedestal carrying the
              lower half of a square U-channel. The square bar body seats
              on the channel floor between the side walls, so the valve
              cannot rotate when the knob is turned.
    * CAP   - front strap with the matching upper U-channel. A central
              OPERATOR ACCESS WINDOW (dia 27.5) clears the 18 x 18 stem boss
              and lets the cap pass over the dia 22 knob at assembly; the knob
              stands proud of the cap so it can be gripped 360 deg.
    * 4 x M5 SHCS at 3 N.m clamp the cap. The two pocket halves are made 0.5 mm
      short of the body (split gap), so the screws pull the cap onto the
      body faces and the joint never bottoms out -> guaranteed clamp load.
    * Channel inner corners are R1.5 (dia 3 end mill), which fall inside
      the valve's 2.5 mm corner chamfers, so no corner relief drills needed.
    * Sized for Tognella FT 1251/2-01-14 (the OEM of RS 283-8289): body
      18 x 18 x 46. The clamp is 42 long so both port faces stay free.

Global frame (also used by assembly.py)
    Y = 0 is the wall, +Y points out of the wall toward the operator.
    Z is up. Valve flow axis is horizontal along X at (Y = AXIS_Y, Z = 0).

Material: 6061-T6 aluminium, clear anodised. Tap M5 x 19 deep in base (M5_TAP_DEPTH).
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
    RectangleRounded,
    Rot,
    SlotCenterToCenter,
    Solid,
    chamfer,
    export_step,
    extrude,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "valve"))
import valve as V

# --- Interface to the valve ------------------------------------------------
AXIS_Y = 30.0  # valve flow axis distance from wall
POCKET_CLR = 0.15  # channel width = valve body width + clearance
POCKET_W = V.BODY_W + POCKET_CLR
POCKET_R = 1.5  # channel corner radius (dia 3 end mill)
SPLIT_GAP = 0.5  # nominal gap at parting plane (before clamping)

# --- Clamp envelope --------------------------------------------------------
CLAMP_L = 42.0  # along X; < valve body (46) so port faces stay free
CLAMP_H = 41.0  # pedestal / cap height along Z
CAP_TOP_WALL = 6.0  # cap material in front of the body front face
WINDOW_D = 27.5  # access window: boss half-diagonal 12.7, knob dia 22
VALVE_PLATE_L = 57.0  # back-plate length under the valve (wall screws at +/-20)

# --- Wall bracket ----------------------------------------------------------
PLATE_T = 12.0
PLATE_H = 92.0  # along Z
WALL_SCREW_X = 20.0
WALL_SCREW_Z = 37.0
WALL_SLOT = 6.0  # vertical adjustment (+/-3 mm)
WALL_HOLE_D = 6.6  # M6 clearance
WALL_CB_D = 11.5  # M6 SHCS head dia 10 + clearance
WALL_CB_DEPTH = 6.5

# --- Clamp screws (ISO 4762 M5 x 25, 8.8) ----------------------------------
M5_X = 14.5
M5_Z = 13.5
M5_TORQUE = 3.0  # N.m (VDI 2230 max for 8.8 at mu 0.12: 5.9 N.m)
# Preload per N.m of tightening torque, 8.8 screws, mu 0.12 (VDI 2230 table as
# published by Pfeiffer Vacuum: M4 3.0 N.m -> 4.4 kN, M5 5.9 N.m -> 7.2 kN).
PRELOAD_N_PER_NM = {"M4": 4400 / 3.0, "M5": 7200 / 5.9}
M5_CLR_D = 5.5
M5_CB_D = 9.5
M5_CB_DEPTH = 5.5
M5_TAP_D = 4.2
M5_TAP_DEPTH = 19.0
M5_LEN = 25.0
M5_HEAD_D = 8.5
M5_HEAD_H = 5.0

# Derived Y stations
Y_SPLIT_BASE = AXIS_Y - SPLIT_GAP / 2
Y_SPLIT_CAP = AXIS_Y + SPLIT_GAP / 2
Y_CAP_TOP = AXIS_Y + POCKET_W / 2 + CAP_TOP_WALL

# Clamped state: valve sits on the base cradle floor, cap pulled down onto
# the valve front face.
VALVE_Y = AXIS_Y - POCKET_W / 2 + V.BODY_W / 2  # = AXIS_Y - 0.075
CAP_DROP = (AXIS_Y + POCKET_W / 2) - (VALVE_Y + V.BODY_W / 2)  # = 0.15
CLAMP_PRELOAD_TRAVEL = SPLIT_GAP - CAP_DROP  # remaining gap


def _x_rod(d: float, y: float, z: float) -> Solid:
    return (
        Pos(-CLAMP_L / 2 - 1, y, z)
        * Rot(0, 90, 0)
        * Cylinder(d / 2, CLAMP_L + 2, align=(Align.CENTER, Align.CENTER, Align.MIN))
    )


def _y_cyl(d: float, h: float, x: float, y0: float, z: float) -> Solid:
    """Cylinder along +Y from y0 (negative h -> toward the wall)."""
    s = Cylinder(d / 2, abs(h), align=(Align.CENTER, Align.CENTER, Align.MIN))
    s = Rot(-90, 0, 0) * s if h > 0 else Rot(90, 0, 0) * s
    return Pos(x, y0, z) * s


def _channel() -> Solid:
    """Square body channel (both halves), through along X."""
    return extrude(
        Plane.YZ.offset(-CLAMP_L / 2 - 1)
        * Pos(AXIS_Y, 0)
        * RectangleRounded(POCKET_W, POCKET_W, POCKET_R),
        amount=CLAMP_L + 2,
    )


def make_base() -> Solid:
    plate = Pos(0, PLATE_T / 2, 0) * Box(VALVE_PLATE_L, PLATE_T, PLATE_H)
    ped_h = Y_SPLIT_BASE - PLATE_T
    pedestal = Pos(0, PLATE_T + ped_h / 2, 0) * Box(CLAMP_L, ped_h, CLAMP_H)
    base = plate + pedestal
    base = chamfer(base.edges().filter_by(Axis.X).group_by(Axis.Y)[-1], 1.0)

    base -= _channel()

    # tapped M5 holes for the cap (modelled at tap-drill dia)
    for sx in (-1, 1):
        for sz in (-1, 1):
            base -= _y_cyl(M5_TAP_D, -M5_TAP_DEPTH, sx * M5_X, Y_SPLIT_BASE, sz * M5_Z)

    # slotted counterbored wall-screw holes (vertical slots)
    for sx in (-1, 1):
        for sz in (-1, 1):
            for d, depth, y0 in (
                (WALL_HOLE_D, PLATE_T + 2, -1.0),
                (WALL_CB_D, WALL_CB_DEPTH + 1, PLATE_T - WALL_CB_DEPTH),
            ):
                slot = (
                    Plane.XZ.offset(-y0)
                    * Pos(sx * WALL_SCREW_X, sz * WALL_SCREW_Z)
                    * (SlotCenterToCenter(WALL_SLOT, d, rotation=90))
                )
                base -= extrude(slot, amount=-depth)
    return base


def make_cap_unclamped() -> Solid:
    """Cap at its free (as-machined) position, Y from split+gap to top."""
    h = Y_CAP_TOP - Y_SPLIT_CAP
    cap = Pos(0, Y_SPLIT_CAP + h / 2, 0) * Box(CLAMP_L, h, CLAMP_H)
    cap = chamfer(cap.edges().filter_by(Axis.X).group_by(Axis.Y)[-1], 1.0)
    cap -= _channel()

    # operator access window for the adjusting knob, chamfered for fingers
    window = _y_cyl(WINDOW_D, 40.0, 0, Y_SPLIT_CAP - 5, 0)
    cap -= window
    cap = chamfer(
        cap.edges().filter_by(
            lambda e: (
                abs(e.radius - WINDOW_D / 2) < 1e-3 and e.center().Y > Y_CAP_TOP - 0.01
                if e.geom_type.name == "CIRCLE"
                else False
            )
        ),
        1.5,
    )

    # counterbored M5 clearance holes
    for sx in (-1, 1):
        for sz in (-1, 1):
            cap -= _y_cyl(M5_CLR_D, -(h + 2), sx * M5_X, Y_CAP_TOP + 1, sz * M5_Z)
            cap -= _y_cyl(M5_CB_D, -(M5_CB_DEPTH + 1), sx * M5_X, Y_CAP_TOP + 1, sz * M5_Z)
    return cap


def make_cap() -> Solid:
    """Cap in the clamped position (pulled down onto the valve flat)."""
    return Pos(0, -CAP_DROP, 0) * make_cap_unclamped()


def make_m5_screws() -> list[Solid]:
    """ISO 4762 M5x25, seated in the clamped cap. Thread shown at minor dia."""
    y_seat = Y_CAP_TOP - M5_CB_DEPTH - CAP_DROP
    screws = []
    for sx in (-1, 1):
        for sz in (-1, 1):
            head = _y_cyl(M5_HEAD_D, M5_HEAD_H, sx * M5_X, y_seat, sz * M5_Z)
            shank = _y_cyl(4.1, -M5_LEN, sx * M5_X, y_seat, sz * M5_Z)
            screws.append(head + shank)
    return screws


def make_wall_screws(length: float = 40.0) -> list[Solid]:
    """M6 SHCS into wall plugs, at slot centre."""
    y_seat = PLATE_T - WALL_CB_DEPTH
    screws = []
    for sx in (-1, 1):
        for sz in (-1, 1):
            head = _y_cyl(10.0, 6.0, sx * WALL_SCREW_X, y_seat, sz * WALL_SCREW_Z)
            shank = _y_cyl(6.0, -length, sx * WALL_SCREW_X, y_seat, sz * WALL_SCREW_Z)
            screws.append(head + shank)
    return screws


if __name__ == "__main__":
    here = Path(__file__).parent
    # The base is machined as part of the one-piece station base
    # (flowmeter_clamp/station_base.step); only the cap is exported here.
    base, cap = make_base(), make_cap_unclamped()
    export_step(cap, str(here / "rs_2838289_clamp_cap.step"))
    for n, p in (("base", base), ("cap", cap)):
        bb = p.bounding_box()
        print(
            f"{n}: {bb.size.X:.1f} x {bb.size.Y:.1f} x {bb.size.Z:.1f} mm, "
            f"{p.volume * 2.70e-3:.0f} g (6061)"
        )
    print("Exported rs_2838289_clamp_cap.step (base: see flowmeter_clamp/station_base.step)")
