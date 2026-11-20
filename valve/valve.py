"""RS PRO 283-8289 in-line flow control valve = Tognella FT 1251/2-01-14.

Sources
  1. RS product page 283-8289: BSP 1/4, 210 bar, 20 L/min, nickel-plated
     brass, NBR seals, -20..+100 degC, "Manufacturer series FT1251/2".
  2. Tognella datasheet "In line double-acting flow control valves
     FT 1251/2-01" (via paro.nl), dimension table, type 14 (G1/4):
        A G1/4 | B (thread depth) 12 | C (length) 46 | D (overall) 57 |
        E (knob travel) 4.5 | dia F (knob) 22 | G (bush) 11.5 | H M17x1 |
        L (axis -> boss face) 11.5 | CH (square body) 18 | 0.122 kg
     Symbol A-B: adjustable restrictor, NO check valve -> double-acting:
     flow is controlled in both directions (either port may be the inlet).
     NOTE: RS's marketing text for 283-8289 says "single-acting" - this
     contradicts the manufacturer datasheet; check the symbol on the body.
  3. Scaled from that drawing (20.7 px/mm, cross-checked on CH, C, H, G, L):
     body edge chamfer 2.5, boss 18 wide x 2.5 high, groove on the face
     opposite the stem (14.3 wide at the face, 7.0 at the bottom, 6.0 deep).
     Boss depth (Z), internal bores and the knob detail are ESTIMATED.

Local frame
    X : flow axis (port A at -X, port B at +X), body centred on origin
    Y : adjusting-stem axis (stem/knob on +Y)
    Z : completes right-hand frame; square body, faces normal to +/-Y, +/-Z
"""

from build123d import (
    Align,
    Axis,
    Box,
    Cylinder,
    Plane,
    Polyline,
    Pos,
    Rectangle,
    Rot,
    Solid,
    chamfer,
    export_step,
    extrude,
    fillet,
    make_face,
)

# --- Body (Tognella type 14) --------------------------------------------------
BODY_W = 18.0          # CH, square bar body across flats (Y and Z)
BODY_CHAMFER = 2.5     # 45 deg chamfer on the four long edges (scaled from drawing)
BODY_L = 46.0          # C, face-to-face length between ports
END_CHAMFER = 0.8
GROOVE = (14.3, 7.0, 6.0)  # face-opposite-stem groove: top width, bottom width, depth

# --- Ports (G1/4 female, modelled at thread major dia = cosmetic thread) ---
PORT_D = 13.157
PORT_DEPTH = 12.0      # B
FLOW_BORE = 4.0        # ESTIMATED internal passage (not on the drawing)

# --- Adjusting stem, measured from the flow axis ------------------------------
BOSS = (18.0, 18.0)    # "ITALY" boss X x Z (Z ESTIMATED = body width)
L_BOSS = 11.5          # L, axis -> boss face (boss is 2.5 above the body face)
BUSH_D = 17.0          # H, M17x1 bonnet bush
BUSH_H = 11.5          # G
D_TOTAL = 57.0         # D, body bottom -> knob top (closed)
KNOB_TRAVEL = 4.5      # E, knob rises this much when fully open
KNOB_D = 22.0          # F
KNOB_KNURLS = 18
CAP_D = 20.0           # blue scale cap on top of the knob (RS photo)
CAP_H = 2.0
SETSCREW_D = 3.0       # knob lock grub screw (RS photo)

# Derived stem stations (Y in valve frame)
Y_FLAT = BODY_W / 2
Y_BUSH_TOP = L_BOSS + BUSH_H                 # 23.0
Y_TOP = D_TOTAL - BODY_W / 2                 # 48.0, knob top (closed)
Y_KNOB_TOP = Y_TOP - CAP_H
KNOB_H = Y_KNOB_TOP - Y_BUSH_TOP             # 23.0
Y_TOP_OPEN = Y_TOP + KNOB_TRAVEL             # 52.5


def _y_cyl(d: float, h: float, y0: float) -> Solid:
    """Cylinder along +Y starting at y0."""
    return Pos(0, y0, 0) * Rot(-90, 0, 0) * Cylinder(
        d / 2, h, align=(Align.CENTER, Align.CENTER, Align.MIN)
    )


def _x_cyl(d: float, h: float, x0: float) -> Solid:
    """Cylinder along +X starting at x0."""
    return Pos(x0, 0, 0) * Rot(0, 90, 0) * Cylinder(
        d / 2, h, align=(Align.CENTER, Align.CENTER, Align.MIN)
    )


def make_body() -> Solid:
    section = Plane.YZ.offset(-BODY_L / 2) * Rectangle(BODY_W, BODY_W)
    body = extrude(section, amount=BODY_L)
    body = chamfer(body.edges().filter_by(Axis.X), BODY_CHAMFER)
    body = chamfer(body.faces().filter_by(Axis.X).edges(), END_CHAMFER)

    # groove across the face opposite the stem (-Y), through the full width
    top, bot, depth = GROOVE
    y0 = -BODY_W / 2
    prof = Plane.XY * Polyline((-top / 2, y0 - 1), (-top / 2, y0), (-bot / 2, y0 + depth),
                               (bot / 2, y0 + depth), (top / 2, y0), (top / 2, y0 - 1),
                               close=True)
    body -= extrude(make_face(prof), amount=BODY_W / 2 + 1, both=True)

    # G1/4 ports both ends + through flow bore + needle cross-bore
    body -= _x_cyl(PORT_D, PORT_DEPTH, -BODY_L / 2)
    body -= _x_cyl(PORT_D, PORT_DEPTH, BODY_L / 2 - PORT_DEPTH)
    body -= _x_cyl(FLOW_BORE, BODY_L, -BODY_L / 2)
    body -= _y_cyl(FLOW_BORE, Y_FLAT, 0)
    return body


def make_bonnet() -> Solid:
    """Boss on the body face + M17x1 bonnet bush (fixed part of the stem)."""
    boss = Pos(0, (Y_FLAT + L_BOSS) / 2, 0) * Box(BOSS[0], L_BOSS - Y_FLAT, BOSS[1])
    boss = chamfer(boss.edges().group_by(Axis.Y)[-1], 1.0)
    return boss + _y_cyl(BUSH_D, BUSH_H, L_BOSS)


def make_knob() -> Solid:
    """Knurled adjusting knob (closed position) with grub screw and scale cap."""
    knob = _y_cyl(KNOB_D, KNOB_H, Y_BUSH_TOP)
    r_groove = 0.9
    for i in range(KNOB_KNURLS):
        knob -= Rot(0, 360 / KNOB_KNURLS * i, 0) * Pos(KNOB_D / 2, 0, 0) * _y_cyl(
            2 * r_groove, KNOB_H - 6.0, Y_BUSH_TOP + 6.0
        )
    knob -= Pos(0, Y_BUSH_TOP + 2.5, 0) * _x_cyl(SETSCREW_D, KNOB_D / 2 + 1, 0)
    cap = _y_cyl(CAP_D, CAP_H, Y_KNOB_TOP)
    cap = fillet(cap.edges().sort_by(Axis.Y)[-1:], 0.8)
    return knob + cap


def make_valve_parts() -> dict[str, Solid]:
    return {"body": make_body(), "bonnet": make_bonnet(), "knob": make_knob()}


def make_valve() -> Solid:
    p = make_valve_parts()
    return p["body"] + p["bonnet"] + p["knob"]


if __name__ == "__main__":
    from pathlib import Path

    v = make_valve()
    bb = v.bounding_box()
    print(f"valve bbox: {bb.size.X:.2f} x {bb.size.Y:.2f} x {bb.size.Z:.2f} mm "
          f"(Tognella C 46, D 57, CH 18)")
    out = Path(__file__).with_name("rs_2838289_valve.step")
    export_step(v, str(out))
    print(f"Exported {out}")
