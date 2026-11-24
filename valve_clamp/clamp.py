"""Valve saddle clamp (3D printed) + shared constants for the modular wall station.

Concept
    * The STATION BASE is ONE 12 mm acrylic plate (flowmeter_clamp.
      make_station_base): through-cut outline, wall slots, dowel-pin holes and
      M4 holes, plus two 6 mm-deep pocket features - hex pockets for captive
      nuts from the wall face, M6 head counterbores from the front face. Each
      clamp screws onto it as a module.
    * CLAMP BASE (printed PETG) - lower half of a square U-channel. It is
      located on the plate by 2 steel dowel pins (ISO 8734, pressed into the
      base) in holes of the station plate, and fixed by 2 x M4 from the
      front, through the channel floor, into captive nuts in hex pockets on
      the plate's wall face. Fit it BEFORE the valve: the M4 heads sit below the
      channel floor and the valve covers them.
    * CLAMP HEAD (cap, printed) - matching upper U-channel with a dia 27.5
      operator window that clears the 18 x 18 stem boss and passes the dia 22
      knob at assembly; the knob stands proud of the cap so it can be gripped.
      4 x M4 + DIN 125 washers into heat-set brass inserts in the base.
    * Split-gap preload: the two channel halves are 1.0 mm short of the body,
      so the screws pull the cap onto the body faces and the joint never
      bottoms out -> guaranteed clamp load.
    * Channel inner corners are R1.5, inside the valve's 2.5 mm corner chamfers.
    * Sized for Tognella FT 1251/2-01-14 (the OEM of RS 283-8289): body
      18 x 18 x 46. The clamp is 42 long so both port faces stay free.
    * Plastic creeps: torques are low and every contact pressure is held under
      the PETG / acrylic allowables. Re-torque after 24 h.

Global frame (also used by assembly.py)
    Y = 0 is the wall, +Y points out of the wall toward the operator.
    Z is up. Valve flow axis is horizontal along X at (Y = AXIS_Y, Z = 0).
"""

import sys
from pathlib import Path

from build123d import (
    Align,
    Axis,
    Box,
    Cylinder,
    ExportDXF,
    Plane,
    Pos,
    Rectangle,
    RectangleRounded,
    RegularPolygon,
    Rot,
    Sketch,
    Solid,
    Unit,
    chamfer,
    extrude,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "valve"))
import valve as V

# --- Processes / materials (values marked ESTIMATE have no single source) ----------
CUT_TOL = 0.1  # ESTIMATE: CO2 laser outline / hole position tolerance
PRINT_TOL = 0.2  # ESTIMATE: FDM (PETG) feature position tolerance
ACRYLIC_P_ALLOW = 10.0  # MPa, ESTIMATE: sustained contact pressure on PMMA (creep)
PRINT_P_ALLOW = 15.0  # MPa, ESTIMATE: sustained contact pressure on PETG (creep)
MU = 0.3  # ESTIMATE: static friction PETG on brass, conservative
PRINT_BED = 250.0  # mm, common FDM bed; every printed part must fit

# --- Interface to the valve --------------------------------------------------
AXIS_Y = 30.0  # valve flow axis distance from wall
POCKET_CLR = 0.15  # channel width = valve body width + clearance
POCKET_W = V.BODY_W + POCKET_CLR
POCKET_R = 1.5  # channel corner radius
SPLIT_GAP = 1.0  # nominal gap at parting plane: > 2 x print tolerance + clamp travel

# --- Clamp envelope --------------------------------------------------------
CLAMP_L = 42.0  # along X; < valve body (46) so port faces stay free
CLAMP_H = 47.0  # base / cap height along Z
CAP_TOP_WALL = 6.0  # cap material in front of the body front face
WINDOW_D = 27.5  # access window: boss half-diagonal 12.7, knob dia 22
VALVE_PLATE_L = 57.0  # station-plate length around the valve (wall screws at +/-20)

# --- Station base plate (one plate: through-cuts + 6 mm pockets) -------------------
PLATE_T = 12.0  # cast acrylic, one sheet; clamp bases sit on its front face at Y = PLATE_T
NUT_POCKET_DEPTH = 6.0  # hex pocket from the wall face; the nut is pulled onto its floor
WALL_CB_DEPTH = 6.0  # M6 head counterbore slot from the front face (head height 6: flush)
PLATE_H = 92.0  # along Z
PLATE_R = 5.0
WALL_SCREW_X = 20.0
WALL_SCREW_Z = 37.0
WALL_SLOT = 6.0  # vertical adjustment (+/-3 mm)
WALL_HOLE_D = 6.6  # M6 clearance slot, through
WALL_CB_D = 11.5  # counterbore slot: M6 head dia 10 + clearance
WALL_HEAD = (10.0, 6.0)  # M6 SHCS head dia, height (sits on the counterbore floor)
WALL_SEAT_Y = PLATE_T - WALL_CB_DEPTH  # M6 head seat

# --- Dowel pins: ISO 8734 4 m6 x 12, pressed into the printed base ------------------
DOWEL_D = 4.0
DOWEL_L = 12.0  # 6 in the base, 6 in the plate
DOWEL_IN_PLATE = 6.0  # dowel engagement in the plate (through hole)
DOWEL_HOLE_D = DOWEL_D + 0.1  # plate hole: slip fit
DOWEL_XZ = ((0.0, -14.0), (0.0, 14.0))  # valve base, either side of the channel

# --- M4 hardware ---------------------------------------------------------------------
M4_D = 4.0
M4_CLR_D = 4.5
M4_MINOR_D = 3.2  # screws modelled at minor dia (cosmetic thread)
M4_HEAD = (7.0, 4.0)  # ISO 4762 head dia, height
M4_CB_D = 7.5  # counterbore for a bare head
WASHER = (9.0, 4.3, 0.8)  # DIN 125-A M4: OD, ID, thickness (cap / strap screws)
CAP_CB_D = 9.5  # counterbore for washer + head
CAP_CB_DEPTH = 5.5  # washer + head (4.8) recessed 0.7
NUT_AF, NUT_M = 7.0, 3.2  # ISO 4032 M4, captive in a hex pocket on the plate's wall face
NUT_POCKET_AF = 7.2
Y_NUT = (NUT_POCKET_DEPTH - NUT_M, NUT_POCKET_DEPTH)  # nut pulled onto the pocket floor
TIP_MIN_Y = 0.5  # screw tip clear of the wall
INSERT = (5.6, 8.1)  # heat-set M4 insert (ruthex RX-M4x8.1): install hole dia, length
INSERT_HOLE_DEPTH = 14.0  # below the split face (screw tip runs past the insert)
NUT_FACTOR = 0.2  # K in T = K F d (dry steel)
CAP_TORQUE = 0.5  # N.m, cap / strap screws into inserts
MOUNT_TORQUE = 0.2  # N.m, clamp base into the captive nuts (acrylic under the nut)
ISO4762_LENGTHS = (8, 10, 12, 16, 20, 25, 30, 35, 40)


def preload(torque: float) -> float:
    return torque / (NUT_FACTOR * M4_D / 1000)


# --- Valve clamp layout -----------------------------------------------------------
CAP_SCREW_XZ = tuple((sx * 14.5, sz * 16.0) for sx in (-1, 1) for sz in (-1, 1))
MOUNT_XZ = ((-15.0, 0.0), (15.0, 0.0))  # through the channel floor, X-spaced (tipping)

# Derived Y stations
Y_SPLIT_BASE = AXIS_Y - SPLIT_GAP / 2
Y_SPLIT_CAP = AXIS_Y + SPLIT_GAP / 2
Y_CAP_TOP = AXIS_Y + POCKET_W / 2 + CAP_TOP_WALL
Y_FLOOR = AXIS_Y - POCKET_W / 2  # channel floor

# Clamped state: valve sits on the base channel floor, cap pulled down onto
# the valve front face.
VALVE_Y = AXIS_Y - POCKET_W / 2 + V.BODY_W / 2  # = AXIS_Y - 0.075
CAP_DROP = (AXIS_Y + POCKET_W / 2) - (VALVE_Y + V.BODY_W / 2)  # = 0.15
CLAMP_PRELOAD_TRAVEL = SPLIT_GAP - CAP_DROP  # remaining gap


def cap_screw_length(y_seat: float, y_split: float) -> float:
    """Shortest ISO 4762 M4 that passes the whole insert, short of the hole bottom."""
    for n in ISO4762_LENGTHS:
        tip = y_seat - n
        if tip <= y_split - INSERT[1] and tip >= y_split - INSERT_HOLE_DEPTH + 0.5:
            return float(n)
    raise ValueError(f"no M4 length for seat {y_seat:.2f}")


def mount_screw(y_top: float) -> tuple[float, float]:
    """(seat Y, length) of a mount screw recessed below y_top, tip through the nut."""
    seat_max = y_top - M4_HEAD[1] - 0.3
    for n in sorted(ISO4762_LENGTHS, reverse=True):
        seat = min(seat_max, n + Y_NUT[0])
        if seat - n >= TIP_MIN_Y and seat >= PLATE_T + 2.0:
            return seat, float(n)
    raise ValueError(f"no M4 mount length under Y = {y_top:.2f}")


CAP_SEAT = Y_CAP_TOP - CAP_CB_DEPTH + WASHER[2] - CAP_DROP  # head seat, clamped
CAP_SCREW_LEN = cap_screw_length(CAP_SEAT, Y_SPLIT_BASE)
MOUNT_SEAT, MOUNT_LEN = mount_screw(Y_FLOOR)


# --- Shared helpers (also used by flowmeter_clamp) ----------------------------------
def box3d(x: tuple, y: tuple, z: tuple) -> Solid:
    return Pos((x[0] + x[1]) / 2, (y[0] + y[1]) / 2, (z[0] + z[1]) / 2) * Box(
        x[1] - x[0], y[1] - y[0], z[1] - z[0]
    )


def box2d(u: tuple, v: tuple) -> Sketch:
    return Pos((u[0] + u[1]) / 2, (v[0] + v[1]) / 2) * Rectangle(u[1] - u[0], v[1] - v[0])


def plate(profile: Sketch, y0: float, t: float) -> Solid:
    """Profile drawn in (u, v) = (global X, global Z), extruded t from y0 to +Y."""
    return extrude(Plane.XZ.offset(-y0) * profile, -t)


def _y_cyl(d: float, h: float, x: float, y0: float, z: float) -> Solid:
    """Cylinder along +Y from y0 (negative h -> toward the wall)."""
    s = Cylinder(d / 2, abs(h), align=(Align.CENTER, Align.CENTER, Align.MIN))
    s = Rot(-90, 0, 0) * s if h > 0 else Rot(90, 0, 0) * s
    return Pos(x, y0, z) * s


def base_holes(part: Solid, mount_xz, mount_seat, dowel_xz, insert_xz, y_split, y_top):
    """Mount counterbores (from y_top), dowel holes (from the bottom), insert holes."""
    for x, z in mount_xz:
        part -= _y_cyl(M4_CLR_D, -(y_top - PLATE_T + 2), x, y_top + 1, z)
        part -= _y_cyl(M4_CB_D, -(y_top - mount_seat + 1), x, y_top + 1, z)
    for x, z in dowel_xz:
        part -= _y_cyl(DOWEL_D, DOWEL_L - DOWEL_IN_PLATE, x, PLATE_T, z)
    for x, z in insert_xz:
        part -= _y_cyl(INSERT[0], -INSERT_HOLE_DEPTH, x, y_split, z)
    return part


def cap_holes(cap: Solid, xz, y_top: float, counterbore: bool = True) -> Solid:
    for x, z in xz:
        cap -= _y_cyl(M4_CLR_D, -40, x, y_top + 1, z)
        if counterbore:
            cap -= _y_cyl(CAP_CB_D, -(CAP_CB_DEPTH + 1), x, y_top + 1, z)
    return cap


def screw(x: float, z: float, y_seat: float, length: float) -> Solid:
    """ISO 4762 M4, head on y_seat, shank toward the wall (minor dia)."""
    return _y_cyl(M4_HEAD[0], M4_HEAD[1], x, y_seat, z) + _y_cyl(M4_MINOR_D, -length, x, y_seat, z)


def washer(x: float, z: float, y_seat: float) -> Solid:
    return _y_cyl(WASHER[0], -WASHER[2], x, y_seat, z) - _y_cyl(WASHER[1], -3, x, y_seat + 1, z)


def nut(x: float, z: float) -> Solid:
    hexa = extrude(
        Plane.XZ.offset(-Y_NUT[0]) * Pos(x, z) * RegularPolygon(NUT_AF / 2, 6, major_radius=False),
        -NUT_M,
    )
    return hexa - _y_cyl(M4_D, NUT_M + 2, x, Y_NUT[0] - 1, z)


def insert(x: float, z: float, y_split: float) -> Solid:
    """Heat-set insert, flush with the split face (thread bore at the M4 major dia)."""
    return _y_cyl(INSERT[0], -INSERT[1], x, y_split, z) - _y_cyl(M4_D, -20, x, y_split + 1, z)


def dowel(x: float, z: float) -> Solid:
    return _y_cyl(DOWEL_D, DOWEL_L, x, PLATE_T - DOWEL_IN_PLATE, z)


def make_hardware(cap_xz, cap_seat, cap_len, mount_xz, mount_seat, mount_len, dowel_xz, y_split):
    """All loose hardware of one clamp module, by kind."""
    return {
        "cap_screw": [screw(x, z, cap_seat, cap_len) for x, z in cap_xz],
        "washer": [washer(x, z, cap_seat) for x, z in cap_xz],
        "insert": [insert(x, z, y_split) for x, z in cap_xz],
        "mount_screw": [screw(x, z, mount_seat, mount_len) for x, z in mount_xz],
        "nut": [nut(x, z) for x, z in mount_xz],
        "dowel": [dowel(x, z) for x, z in dowel_xz],
    }


# --- Valve clamp -------------------------------------------------------------------
def _channel() -> Solid:
    """Square body channel (both halves), through along X."""
    return extrude(
        Plane.YZ.offset(-CLAMP_L / 2 - 1)
        * Pos(AXIS_Y, 0)
        * RectangleRounded(POCKET_W, POCKET_W, POCKET_R),
        amount=CLAMP_L + 2,
    )


def make_base() -> Solid:
    """Printed clamp base: sits on the station plate at Y = PLATE_T."""
    h = Y_SPLIT_BASE - PLATE_T
    base = Pos(0, PLATE_T + h / 2, 0) * Box(CLAMP_L, h, CLAMP_H)
    base = chamfer(base.edges().filter_by(Axis.X).group_by(Axis.Y)[-1], 1.0)
    base -= _channel()
    return base_holes(base, MOUNT_XZ, MOUNT_SEAT, DOWEL_XZ, CAP_SCREW_XZ, Y_SPLIT_BASE, Y_FLOOR)


def make_cap_unclamped() -> Solid:
    """Cap at its free (as-printed) position, Y from split+gap to top."""
    h = Y_CAP_TOP - Y_SPLIT_CAP
    cap = Pos(0, Y_SPLIT_CAP + h / 2, 0) * Box(CLAMP_L, h, CLAMP_H)
    cap = chamfer(cap.edges().filter_by(Axis.X).group_by(Axis.Y)[-1], 1.0)
    cap -= _channel()

    # operator access window for the adjusting knob, chamfered for fingers
    cap -= _y_cyl(WINDOW_D, 40.0, 0, Y_SPLIT_CAP - 5, 0)
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
    return cap_holes(cap, CAP_SCREW_XZ, Y_CAP_TOP)


def make_cap() -> Solid:
    """Cap in the clamped position (pulled down onto the valve flat)."""
    return Pos(0, -CAP_DROP, 0) * make_cap_unclamped()


def make_hw() -> dict[str, list[Solid]]:
    return make_hardware(
        CAP_SCREW_XZ,
        CAP_SEAT,
        CAP_SCREW_LEN,
        MOUNT_XZ,
        MOUNT_SEAT,
        MOUNT_LEN,
        DOWEL_XZ,
        Y_SPLIT_BASE,
    )


def make_wall_screws(xs=(-WALL_SCREW_X, WALL_SCREW_X), length: float = 40.0) -> list[Solid]:
    """M6 SHCS into wall plugs, at slot centre, head on the counterbore floor."""
    out = []
    for x in xs:
        for sz in (-1, 1):
            z = sz * WALL_SCREW_Z
            out.append(
                _y_cyl(WALL_HEAD[0], WALL_HEAD[1], x, WALL_SEAT_Y, z)
                + _y_cyl(6.0, -length, x, WALL_SEAT_Y, z)
            )
    return out


def export_layers(layers: dict[str, Sketch], path: Path) -> None:
    """One DXF in mm, one DXF layer per feature (through-cut, each pocket)."""
    dxf = ExportDXF(unit=Unit.MM)
    for layer, prof in layers.items():
        dxf.add_layer(layer)
        dxf.add_shape(prof, layer=layer)
    dxf.write(str(path))


if __name__ == "__main__":
    parts = {"rs_2838289_clamp_base": make_base(), "rs_2838289_clamp_cap": make_cap_unclamped()}
    for n, p in parts.items():
        bb = p.bounding_box()
        print(
            f"{n}: {bb.size.X:.1f} x {bb.size.Y:.1f} x {bb.size.Z:.1f} mm, "
            f"{p.volume * 1.27e-3:.0f} g (PETG, solid)"
        )
    print(
        f"cap: 4 x M4x{CAP_SCREW_LEN:.0f} + DIN 125 washer into inserts, {CAP_TORQUE} N.m; "
        f"base: 2 x M4x{MOUNT_LEN:.0f} into captive nuts, {MOUNT_TORQUE} N.m; "
        "2 x dowel 4 m6 x 12"
    )
    print("STEP: uv run python tools/export_step.py -> output/step/")
