"""ifm electronic SV3051 vortex flow meter (SVR12XGXD0KG/US).

RS stock no. 596-791. Water / ultra-pure water, 0.5...10 l/min, DN6,
16 bar (<= 90 degC), medium 0...125 degC, 8...33 V DC, 4...20 mA out,
M12 A-coded connector, IP65. No display is modelled (confirmed by the user,
2026-11-20; note the RS/ifm datasheet text lists a 1.44" colour display).
Housing PPS GF40 / PC GF10; wetted: PPSU sensor, PPS GF40 pipe, FKM seal.
Process connection G1/2 external thread both ends; tightening torque 12 Nm.

Source: ifm datasheet SV3051-00 (19.04.2024), dimension drawing.
    Dimensioned: overall 77 x 30.2 x 52.7 | G1/2 both ends | bore dia 11.5 |
                 M12 axis 27.4 from the inlet end | spanner flats 12
    Everything else was scaled from that drawing (13.55 px/mm at 300 dpi,
    checked against the 77, 52.7, G1/2 and 30.2 dimensions; +/-0.3 mm).
    Not shown on the drawing, so ESTIMATED: side LED-window depth.
Checked against ifm's own STEP model (ifm.com SV3051 downloads,
CAD_STP_300_0358): envelope 77 x 52.73 x 30.2 and M12 position agree. The
measuring pipe is a dia 15.4 round with flats 12 apart top and bottom (the
"12" spanner dimension); the spanner section on the inlet side is a 16 AF hex
(corners sideways) cut by the same flats - both taken from that model. Lower housing width (ifm
+/-12.7..13.4) agrees with BODY_W. RS has no 3D model for this part.

Local frame
    X : flow axis, body centred on X = 0. Flow direction is -X (inlet +X,
        outlet -X), per the arrow on the pipe.
    Z : up - housing and M12 connector on +Z.
    Y : width (housing 30.2 across).
"""

from build123d import (
    Align,
    Axis,
    Box,
    Cylinder,
    Plane,
    Polyline,
    Pos,
    RectangleRounded,
    RegularPolygon,
    Rot,
    SlotCenterToCenter,
    Solid,
    chamfer,
    export_step,
    extrude,
    make_face,
    revolve,
)

# --- Datasheet dimensions --------------------------------------------------
L_TOTAL = 77.0
H_TOTAL = 52.7
W_TOTAL = 30.2
THREAD_D = 20.955          # G1/2 major dia (cosmetic male thread)
END_BORE_D = 11.5
DN = 6.0                   # measuring-pipe bore
M12_FROM_INLET = 27.4      # inlet = +X end (flow arrow points to -X)
SPANNER_AF = 12.0

# --- Pipe section (scaled from drawing) ------------------------------------
THREAD_L = 13.0            # each end
LEAD_IN_D = 18.8           # unthreaded lead-in at the very end
LEAD_IN_L = 2.2
NECK = (14.9, 12.1, 5.0)   # outlet-side cone: start dia, end dia, length
PIPE_D = 12.1             # neck end diameter (drawing)
PIPE_H = SPANNER_AF        # pipe height: flat top/bottom faces 12 apart (ifm STEP)
PIPE_ROUND_D = 15.4        # pipe round between the flats, neck -> spanner (ifm STEP)
SPANNER_X = (15.6, 25.5)   # spanner section, inlet side (drawing + ifm STEP)
SPANNER_HEX_AF = 16.0      # its hex (corners at +/-9.24 sideways), cut by the flats
BORE_TAPER_L = 5.0         # end bore dia 11.5 -> DN6 taper length

# --- Housing (scaled from drawing; Z above flow axis) ----------------------
LID = {"x": (-23.5, 24.1), "z": (23.2, 30.4), "r": 3.0}        # top cover, full 30.2 wide
LID_PLATE = {"x": (-23.4, 24.0), "z": (22.1, 23.2), "w": 30.0}
# x/z from the drawing; widths "w" from ifm's STEP model (sections at x = -22..22)
FLANGE = {"x": (-22.6, 23.4), "z": (20.6, 22.1), "w": 27.6}
UPPER_BODY = {"x": (-22.3, 3.2), "z": (17.0, 20.6), "w": 26.8}
LOWER_BODY = {"x": (-20.9, 1.5), "z": (8.5, 17.0), "w": 24.6}
NECK_WEB = {"x": (-14.0, 3.0), "z": (6.0, 8.5), "w": 10.0}    # joins the pipe flat
FILLET_BODY = {"x": (1.5, 16.5), "z": (6.0, 20.6), "w": 5.8}  # thin rib under the M12
FILLET_ARC = {"cx": 16.5, "cz": 11.4, "r": 9.2}                # concave sweep down to the pipe
FILLET_FOOT_X = 7.3
BODY_W = LOWER_BODY["w"]   # lower-housing width (ifm STEP)
LED_SLOTS = [(-16.4, -3.1), (3.6, 17.0)]                  # side windows, x-range
LED_SLOT = {"z": 25.6, "h": 1.9, "depth": 0.3}

# --- M12 connector (scaled from drawing) -----------------------------------
M12_X = L_TOTAL / 2 - M12_FROM_INLET      # +11.1
Z_TOP = H_TOTAL - THREAD_D / 2             # 42.22
M12_STACK = [  # (dia, z0, z1)
    (15.1, 30.4, 31.45),   # flange
    (12.1, 31.45, 38.3),   # body
    (10.5, 38.3, 40.0),    # groove
    (10.7, 40.0, Z_TOP),   # coupling end
]


def _revolve_x(pts: list[tuple[float, float]]) -> Solid:
    """Revolve a closed (x, r) profile about the X axis."""
    face = make_face(Plane.XY * Polyline(*pts, close=True))
    return revolve(face, Axis.X)


def _x_cyl(d: float, x0: float, x1: float) -> Solid:
    return Pos(x0, 0, 0) * Rot(0, 90, 0) * Cylinder(
        d / 2, x1 - x0, align=(Align.CENTER, Align.CENTER, Align.MIN))


def _box(x: tuple, y: tuple, z: tuple) -> Solid:
    return Pos((x[0] + x[1]) / 2, (y[0] + y[1]) / 2, (z[0] + z[1]) / 2) * Box(
        x[1] - x[0], y[1] - y[0], z[1] - z[0])


def make_pipe() -> Solid:
    """Measuring pipe: G1/2 ends, outlet-side neck, flat-sided 12-high section."""
    h = L_TOTAL / 2
    rt, rl = THREAD_D / 2, LEAD_IN_D / 2
    x_out_thr = -h + THREAD_L               # -25.5
    x_in_thr = h - THREAD_L                 # +25.5
    prof = [
        (-h, 0), (-h, rl), (-h + LEAD_IN_L, rl), (-h + LEAD_IN_L, rt),
        (x_out_thr, rt), (x_out_thr, NECK[0] / 2), (x_out_thr + NECK[2], NECK[1] / 2),
        (x_out_thr + NECK[2] + 0.5, PIPE_H / 2 - 0.5),                     # inside the flats
        (x_in_thr, PIPE_H / 2 - 0.5), (x_in_thr, rt), (h - LEAD_IN_L, rt),
        (h - LEAD_IN_L, rl), (h, rl), (h, 0),
    ]
    pipe = _revolve_x(prof)
    x_neck = x_out_thr + NECK[2]
    flats = _box((x_neck - 1, SPANNER_X[1] + 1), (-20, 20), (-PIPE_H / 2, PIPE_H / 2))
    rnd = _x_cyl(PIPE_ROUND_D, x_neck, SPANNER_X[0])
    hexp = extrude(Plane.YZ.offset(SPANNER_X[0]) * RegularPolygon(
        SPANNER_HEX_AF / 2, 6, major_radius=False), amount=SPANNER_X[1] - SPANNER_X[0])
    pipe += (rnd + hexp) & flats
    # bore: dia 11.5 in each thread, tapering to DN6
    for sgn in (-1, 1):
        x_end = sgn * h
        x_thr = sgn * (h - THREAD_L)
        x_dn = sgn * (h - THREAD_L - BORE_TAPER_L)
        pipe -= _revolve_x([(x_end + sgn, 0), (x_end + sgn, END_BORE_D / 2),
                            (x_thr, END_BORE_D / 2), (x_dn, DN / 2), (x_dn, 0)])
    pipe -= _x_cyl(DN, -h, h)
    return pipe


def make_housing() -> Solid:
    hw = W_TOTAL / 2
    bw = BODY_W / 2
    lid = Pos((LID["x"][0] + LID["x"][1]) / 2, 0, LID["z"][0]) * extrude(
        RectangleRounded(LID["x"][1] - LID["x"][0], W_TOTAL, LID["r"]),
        amount=LID["z"][1] - LID["z"][0])
    lid = chamfer(lid.edges().group_by(Axis.Z)[-1], 1.0)
    plate = _box(LID_PLATE["x"], (-LID_PLATE["w"] / 2, LID_PLATE["w"] / 2), LID_PLATE["z"])
    flange = _box(FLANGE["x"], (-FLANGE["w"] / 2, FLANGE["w"] / 2), FLANGE["z"])
    def blk(d):
        return _box(d["x"], (-d["w"] / 2, d["w"] / 2), d["z"])
    upper, lower, web = blk(UPPER_BODY), blk(LOWER_BODY), blk(NECK_WEB)
    fil = blk(FILLET_BODY)
    fil -= _box((FILLET_FOOT_X, FILLET_ARC["cx"] + 1), (-bw - 1, bw + 1),
                (-1, FILLET_ARC["cz"]))
    fil -= Pos(FILLET_ARC["cx"], 0, FILLET_ARC["cz"]) * Rot(90, 0, 0) * Cylinder(
        FILLET_ARC["r"], BODY_W + 2)
    housing = lid + plate + flange + upper + lower + web + fil
    housing -= make_pipe()                                     # seat on the pipe

    # side LED windows (both sides)
    for x0, x1 in LED_SLOTS:
        for sgn in (-1, 1):
            slot = Plane.XZ.offset(-sgn * hw) * Pos((x0 + x1) / 2, LED_SLOT["z"]) * (
                SlotCenterToCenter(x1 - x0 - LED_SLOT["h"], LED_SLOT["h"]))
            housing -= extrude(slot, amount=LED_SLOT["depth"], both=True)
    return housing


def make_m12() -> Solid:
    m12 = None
    for d, z0, z1 in M12_STACK:
        c = Pos(M12_X, 0, z0) * Cylinder(d / 2, z1 - z0,
                                         align=(Align.CENTER, Align.CENTER, Align.MIN))
        m12 = c if m12 is None else m12 + c
    return m12


def make_flowmeter_parts() -> dict[str, Solid]:
    return {"pipe": make_pipe(), "housing": make_housing(), "m12": make_m12()}


def make_flowmeter() -> Solid:
    p = make_flowmeter_parts()
    return p["pipe"] + p["housing"] + p["m12"]


if __name__ == "__main__":
    from pathlib import Path

    f = make_flowmeter()
    bb = f.bounding_box()
    print(f"SV3051 bbox: {bb.size.X:.2f} x {bb.size.Y:.2f} x {bb.size.Z:.2f} mm "
          f"(datasheet 77 x 30.2 x 52.7)")
    print(f"M12 axis {L_TOTAL / 2 - M12_X:.1f} mm from inlet end (datasheet 27.4)")
    out = Path(__file__).with_name("ifm_sv3051.step")
    export_step(f, str(out))
    print(f"Exported {out}")
