"""ifm electronic SV3051 vortex flow meter (SVR12XGXD0KG/US).

RS stock no. 596-791. Water / ultra-pure water, 0.5...10 l/min, DN6,
16 bar (<= 90 degC), medium 0...125 degC, 8...33 V DC, 4...20 mA out,
M12 A-coded connector, IP65. No display is modelled (confirmed by the user,
2026-11-20; note the RS/ifm datasheet text lists a 1.44" colour display).
Housing PPS GF40 / PC GF10; wetted: PPSU sensor, PPS GF40 pipe, FKM seal.
Process connection G1/2 external thread both ends; tightening torque 12 Nm.

Sources
    ifm datasheet SV3051-00 (19.04.2024), dimension drawing:
        overall 77 x 30.2 x 52.7 | G1/2 both ends | bore dia 11.5 |
        M12 axis 27.4 from the inlet end | spanner flats 12.
    ifm STEP model CAD_STP_300_0358 (ifm.com SV3051, Downloads tab). Every
        other dimension is read off its faces (planes, cylinders, cones, tori,
        one sphere), in this file's frame: ifm's model is upside down and end
        for end (see the `flowmeter` preset in tools/cad_compare.py). ifm calls
        its CAD data "slightly simplified, medium level of detail".
    Where the two agree (77, 30.2, G1/2, 11.5, 27.4, 12) the datasheet value
    is used. Height: the STEP gives 52.7275 (thread top to M12 top); the
    datasheet's 52.7 is that, rounded.

Not from either source: nothing. Simplified (within the 0.5 mm envelope
rule, see `tools/cad_compare.py flowmeter`): blends of r <= 0.6 on the
housing, the pin holes in the M12 socket floor (0.4 deep), and a 0.02 mm
draft under the lid flange.

End faces: ifm's STEP has an annular groove in each end face (ID 12.85,
OD 16.75, 1.2 deep), most likely for an FKM sealing ring. It is modelled.
Which seal the real meter uses (flat washer or an O-ring in this groove) is
still to be checked on the part or in ifm's operating instructions 11592037.

Local frame
    X : flow axis, body centred on X = 0. Flow direction is -X (inlet +X,
        outlet -X), per the arrow on both sides of the pipe.
    Z : up - housing and M12 connector on +Z.
    Y : width (housing 30.2 across).
"""

import math

from build123d import (
    Align,
    Axis,
    Box,
    Circle,
    Cylinder,
    Face,
    Plane,
    Polygon,
    Polyline,
    Pos,
    RectangleRounded,
    RegularPolygon,
    Rot,
    SlotCenterToCenter,
    Solid,
    Sphere,
    Vector,
    chamfer,
    extrude,
    loft,
    make_face,
    revolve,
)

# --- Datasheet dimensions (each agrees with the ifm STEP) ------------------
L_TOTAL = 77.0
W_TOTAL = 30.2
THREAD_D = 20.955  # G1/2 major dia (cosmetic male thread; ifm models it the same way)
END_BORE_D = 11.5
DN = 6.0  # nominal size (sets the 15 x DN straight runs); the passage itself is below
M12_FROM_INLET = 27.4  # inlet = +X end (flow arrow points to -X)
SPANNER_AF = 12.0  # flats top and bottom of the pipe (STEP: z = -6.000 / +6.000)

# --- Pipe (ifm STEP) --------------------------------------------------------
THREAD_L = 13.0  # end face -> shoulder at x = +/-25.5 (G1/2 thread run)
THREAD_RUNOUT_D = 18.631  # thread chamfers: 45 deg from this dia up to THREAD_D
LEAD_IN_D = 18.6  # plain lead-in at the very end
LEAD_IN_L = 2.0
END_FACE_EDGE_R = 0.1  # rounds on every end-face edge
GROOVE_ID = 12.85  # annular groove in each end face (likely a seal-ring groove)
GROOVE_OD = 16.75
GROOVE_DEPTH = 1.2
GROOVE_BOTTOM_R = 0.25
INLET_BORE_L = 10.0  # dia END_BORE_D from the inlet face; floor round r 0.2
INLET_BORE_FLOOR_R = 0.2
PASSAGE_W = 9.5  # flow passage: an obround 9.5 x 4 (r 2 ends) ...
PASSAGE_H = 4.0
PASSAGE_X0 = -13.9  # ... from x = -13.9 to the inlet bore floor; on the outlet side
#                     it is lofted out to the dia END_BORE_D at the face
SPANNER_X = (15.5, 25.5)  # spanner section, inlet side: 16 AF hex cut by the flats
SPANNER_HEX_AF = 16.0  # hex corners sideways (+/-9.238)
PIPE_SIDE_R = 6.0  # pipe section, x = NECK_X .. SPANNER_X[0]: two r 6 arcs ...
PIPE_SIDE_OFFSET = 1.7  # ... centred at y = +/-1.7 (15.4 wide), flats 12 apart
PIPE_ROUND_D = 2 * (PIPE_SIDE_R + PIPE_SIDE_OFFSET)  # 15.4 across
NECK_X = -19.244  # outlet side: that section flares at 15 deg up to the shoulder
NECK_TAPER = 15.0
# flow arrow, raised on both sides of the pipe: arrow-shaped boss (outer) with an
# arrow-shaped recess (inner) down to the pipe surface; points to -X. (x, z) in mm
ARROW_BOSS_R = 6.75  # boss surface: r 6.75 about the side-arc centres (0.75 proud)
ARROW_OUT = {"tip": -15.56, "back": -3.2, "end": 11.8, "head": 4.5, "shaft": 2.25}
ARROW_IN = {"tip": -12.637, "back": -4.2, "end": 10.8, "head": 3.072, "shaft": 1.25}

# --- Housing (ifm STEP; z above the flow axis, x/y in this frame) -----------
ROOT_Z = 2.5  # housing solids start inside the pipe wall (passage top is z = 2)
COLUMN = (2.89, 0.0, 4.25)  # round column, pipe -> lid plate: centre x, y, r
POST_C = (-9.9, 0.0)  # round post, pipe -> lower body: centre ...
POST_R = 7.0  # ... r up to Z_L1; the lower body's bites follow r 7 / r 7.8
POST_R_L2 = 7.8
WAIST_F = (-1.97, 3.058, 1.5)  # concave rounds between post and column (+/-y)
Z_L1, Z_L2, Z_U, Z_PLATE = 7.755, 10.805, 16.755, 20.755  # layer bottoms
LOWER_RECT = ((-20.95, 1.939), (-12.5, 12.5), 3.0)  # x, y, corner r (z Z_L1..Z_U)
DIAG_P = ((-10.0385, 11.1011), (-4.5223, 4.4811))  # +y bite: flat face through these
DIAG_M = ((-15.2622, -4.4996), (-9.6989, -11.1294))  # -y bite
DIAG_ROUND = 3.907  # convex round, diagonal -> long side
DIAG_FILLET_L2 = 4.0  # concave round, diagonal -> r 7.8 (z Z_L2..Z_U only)
NOTCH_Y = -0.5  # -y bite starts below this line
UPPER_RECT = ((-22.2, 3.19), (-13.8, 13.8), 2.0)  # x, y, corner r (z Z_U..Z_PLATE)
# upper body bites: convex r 5.157 off the long side, concave r 4, convex r 13
UPPER_BITE_P = {"c5": (-13.04, 8.643), "f4": (-5.662, 14.0), "c13": (-12.004, -1.766)}
UPPER_BITE_M = {"c5": (-6.706, -8.643), "f4": (-14.138, -14.007), "c13": (-7.796, 1.76)}
UPPER_NOTCH_Y = -0.505
# thin rib (y +/-0.5) from the column to the plate, concave r 9 underneath
RIB_T = 1.0
RIB = {"x0": 7.385, "x1": 22.776, "arc_c": (16.385, 11.255), "arc_r": 9.0, "z_top": 20.255}
PLATE = ((-22.2, 22.8), 13.8, 2.0, (Z_PLATE, 21.8))  # x, half-width, corner r, z
FLANGE = ((-23.5, 24.1), W_TOTAL / 2, 3.3, (21.8, 23.05), 0.25)  # ..., top chamfer
LID_NECK_Z = (23.05, 23.45)  # recess between flange and lid, plate outline
LID_Z0 = 23.45  # lid: flange outline, domed top
DOME = {"r": 382.183, "c": (0.241, -351.183)}  # sphere: radius, centre x, z (top 31.0)
LED_SLOTS = [(-16.2, -3.2), (3.8, 16.8)]  # windows on both sides, x-range
LED_SLOT = {"z": (25.0, 26.4), "r": 0.65, "depth": 1.3}
END_SLOT = {"y": 13.0, "depth": 1.3}  # same window in the inlet-end face of the lid

# --- M12 connector (ifm STEP); (r, z) about the M12 axis -------------------
M12_X = L_TOTAL / 2 - M12_FROM_INLET  # +11.1
Z_TOP = 42.25  # top of the M12 (STEP)
H_TOTAL = Z_TOP + THREAD_D / 2  # 52.73 (datasheet: 52.7)
M12_PROFILE = [  # outer (r, z) from the lid up, then the socket
    (7.6, 31.25),
    (6.0, 31.25),  # concave r 1 here
    (6.0, 38.47),
    (5.0, 39.05),
    (5.0, 40.2),
    (5.2, 40.546),  # 30 deg cone meets r 5.2; round r 0.2 here
    (5.2, 41.25),
    (5.0, Z_TOP),
]
M12_SOCKET = {"r": 4.075, "floor": 33.25, "floor_r": 0.3}
M12_KEY = {"w": 1.15, "tip": 3.455, "angle": -45.0}  # coding rib in the socket


def _fillet(face: Face, spec: list[tuple[float, float, float]]) -> Face:
    """Round the face's vertices nearest each (x, y) with radius r."""
    faces = face.faces()
    assert len(faces) == 1, f"expected one face, got {len(faces)}"
    face = faces[0]
    for x, y, r in spec:
        v = min(face.vertices(), key=lambda v: (Vector(v.X, v.Y, 0) - Vector(x, y, 0)).length)
        face = face.fillet_2d(r, [v])
    return face


def _revolve(pts, axis: Axis, plane: Plane, fillets=()) -> Solid:
    """Revolve a closed (along, r) profile drawn on `plane` about `axis`."""
    face = make_face(Polyline(*pts, close=True))
    face = _fillet(face, list(fillets))
    return revolve(plane * face, axis)


def _poly(*pts) -> Face:
    """Polygon face from (x, y) points, wound counter-clockwise (normal +Z), so
    that 2D booleans with the other sections work."""
    pts = [(float(p[0]), float(p[1])) for p in pts]
    area = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(pts, pts[1:] + pts[:1]))
    return Polygon(*(pts if area > 0 else pts[::-1]), align=None)


def _disk(c, r) -> Face:
    return Pos(c[0], c[1]) * Circle(r)


def _waist(ca, ra, cb, rb, cf) -> Face:
    """Material between disks a and b, bounded by the concave round f."""
    tips = []
    for c, r in ((ca, ra), (cb, rb)):
        d = Vector(cf[0] - c[0], cf[1] - c[1])
        tips.append(Vector(c[0], c[1]) + d * (r / d.length))
    quad = _poly(ca, (tips[0].X, tips[0].Y), (tips[1].X, tips[1].Y), cb)
    return quad - _disk(cf[:2], cf[2])


def _rect(x, y) -> Face:
    return _poly((x[0], y[0]), (x[1], y[0]), (x[1], y[1]), (x[0], y[1]))


def _line_at(p, q, y):
    """x where the line through p, q crosses height y."""
    return p[0] + (q[0] - p[0]) * (y - p[1]) / (q[1] - p[1])


def _x_prism(face: Face, x0: float, x1: float, taper: float = 0) -> Solid:
    """Extrude a (y, z) section along +X."""
    return extrude(Plane.YZ.offset(x0) * face, amount=x1 - x0, taper=taper)


# --------------------------------------------------------------------------
# Pipe
# --------------------------------------------------------------------------
def _end(sgn: int) -> Solid:
    """Threaded end, x = 25.5 .. 38.5 (sgn +1, inlet) or mirrored (outlet)."""
    h = L_TOTAL / 2
    x0 = h - THREAD_L
    rt, rr, rl = THREAD_D / 2, THREAD_RUNOUT_D / 2, LEAD_IN_D / 2
    ch = rt - rr
    ro, ri, rb = GROOVE_OD / 2, GROOVE_ID / 2, END_BORE_D / 2
    xg = h - GROOVE_DEPTH
    pts = [
        (x0, 0),
        (x0, rr),
        (x0 + ch, rt),
        (h - LEAD_IN_L - ch, rt),
        (h - LEAD_IN_L, rr),
        (h - LEAD_IN_L, rl),
        (h, rl),
        (h, ro),
        (xg, ro),
        (xg, ri),
        (h, ri),
    ]
    fil = [(h, rl, END_FACE_EDGE_R), (h, ro, END_FACE_EDGE_R), (h, ri, END_FACE_EDGE_R)]
    fil += [(xg, ro, GROOVE_BOTTOM_R), (xg, ri, GROOVE_BOTTOM_R)]
    if sgn > 0:  # inlet: a round bore with a floor; outlet: lofted passage (cut later)
        xf = h - INLET_BORE_L
        pts += [(h, rb), (xf, rb), (xf, 0)]
        fil += [(h, rb, END_FACE_EDGE_R), (xf, rb, INLET_BORE_FLOOR_R)]
    else:
        pts += [(h, 0)]
    end = _revolve(pts, Axis.X, Plane.XY, fil)
    return end if sgn > 0 else end.mirror(Plane.YZ)


def _arrow(a: dict) -> Face:
    """Arrow outline in (x, z), pointing to -X."""
    pts = [
        (a["tip"], 0),
        (a["back"], a["head"]),
        (a["back"], a["shaft"]),
        (a["end"], a["shaft"]),
        (a["end"], -a["shaft"]),
        (a["back"], -a["shaft"]),
        (a["back"], -a["head"]),
    ]
    return Polygon(*pts, align=None)


def make_pipe() -> Solid:
    """Measuring pipe: G1/2 ends, spanner hex and flats, flow arrows, passage."""
    h = L_TOTAL / 2
    pipe = _end(1) + _end(-1)
    # spanner section: 16 AF hex, corners sideways, cut by the 12 AF flats
    hexp = _x_prism(RegularPolygon(SPANNER_HEX_AF / 2, 6, major_radius=False), *SPANNER_X)
    pipe += hexp & Box(100, 100, SPANNER_AF)
    # flat-sided pipe section, flaring at 15 deg on the outlet side
    sect = SlotCenterToCenter(2 * PIPE_SIDE_OFFSET, 2 * PIPE_SIDE_R)
    pipe += _x_prism(sect, NECK_X, SPANNER_X[0])
    x_sh = -(h - THREAD_L)
    r_sh = PIPE_SIDE_R + (NECK_X - x_sh) * math.tan(math.radians(NECK_TAPER))
    pipe += _x_prism(SlotCenterToCenter(2 * PIPE_SIDE_OFFSET, 2 * r_sh), x_sh, NECK_X, NECK_TAPER)
    # flow arrows (both sides)
    sides = [
        Pos(0, s * PIPE_SIDE_OFFSET, 0) * Rot(0, 90, 0) * Cylinder(ARROW_BOSS_R, 40)
        for s in (-1, 1)
    ]
    boss = extrude(Plane.XZ * _arrow(ARROW_OUT), amount=10, both=True) & (sides[0] + sides[1])
    boss -= extrude(Plane.XZ * _arrow(ARROW_IN), amount=10, both=True)
    pipe += boss
    # flow passage: obround 9.5 x 4, lofted to the round outlet bore
    slot = SlotCenterToCenter(PASSAGE_W - PASSAGE_H, PASSAGE_H)
    x_floor = h - INLET_BORE_L
    pipe -= _x_prism(slot, PASSAGE_X0, x_floor + 0.01)
    pipe -= loft([Plane.YZ.offset(-h) * Circle(END_BORE_D / 2), Plane.YZ.offset(PASSAGE_X0) * slot])
    pipe -= _x_prism(Circle(END_BORE_D / 2), -h - 1, -h)
    return pipe


# --------------------------------------------------------------------------
# Housing
# --------------------------------------------------------------------------
def _column() -> Face:
    return _disk(COLUMN[:2], COLUMN[2])


def _peanut(r_post: float) -> Face:
    """Post and column joined by the concave waist rounds."""
    f = _disk(POST_C, r_post) + _column()
    for s in (1, -1):
        cf = (WAIST_F[0], s * WAIST_F[1], WAIST_F[2])
        f += _waist(POST_C, r_post, COLUMN[:2], COLUMN[2], cf)
    return f


def _lower(r_post: float, inner_fillet: float | None) -> Face:
    """Lower body section: a rectangle with an S-shaped bite out of two corners."""
    (x0, x1), (y0, y1), rc = LOWER_RECT
    f = _rect((x0, x1), (y0, y1))
    (p, q), (m, n) = DIAG_P, DIAG_M
    f -= _poly(
        (_line_at(p, q, y1 + 1), y1 + 1), (x1 + 9, y1 + 1), (x1 + 9, 0), (_line_at(p, q, 0), 0)
    )
    f -= _poly(
        (_line_at(m, n, NOTCH_Y), NOTCH_Y),
        (x0 - 1, NOTCH_Y),
        (x0 - 1, y0 - 1),
        (_line_at(m, n, y0 - 1), y0 - 1),
    )
    f = (f + _peanut(r_post)).faces()[0]
    fil = [(x0, y1, rc), (x1, y0, rc)]
    fil += [(_line_at(p, q, y1), y1, DIAG_ROUND), (_line_at(m, n, y0), y0, DIAG_ROUND)]
    if inner_fillet:  # concave rounds where the diagonals meet the post arcs
        for a, b in ((p, q), (n, m)):
            # the diagonal meets the post circle: nearest vertex to that crossing
            d = Vector(b[0] - a[0], b[1] - a[1]).normalized()
            w = Vector(a[0] - POST_C[0], a[1] - POST_C[1])
            t = -w.dot(d) - math.sqrt(w.dot(d) ** 2 - (w.dot(w) - r_post**2))
            hit = Vector(a[0], a[1]) + d * t
            fil.append((hit.X, hit.Y, inner_fillet))
    return _fillet(f, fil)


def _upper() -> Face:
    """Upper body section: as the lower body, with arc-only bites."""
    (x0, x1), (y0, y1), rc = UPPER_RECT
    f = _rect((x0, x1), (y0, y1))
    for b, box in (
        (UPPER_BITE_P, ((UPPER_BITE_P["c5"][0], x1 + 1), (0, y1 + 1))),
        (UPPER_BITE_M, ((x0 - 1, UPPER_BITE_M["c5"][0]), (y0 - 1, UPPER_NOTCH_Y))),
    ):
        r5 = y1 - abs(b["c5"][1])  # tangent to the long side
        keep = _disk(b["c5"], r5) + _disk(b["c13"], 13.0)
        keep += _waist(b["c5"], r5, b["c13"], 13.0, (*b["f4"], 4.0))
        f -= _rect(*box) - keep
    f = (f + _column()).faces()[0]
    return _fillet(f, [(x0, y1, rc), (x1, y0, rc)])


def _z_prism(face: Face, z0: float, z1: float) -> Solid:
    return extrude(Plane.XY.offset(z0) * face, amount=z1 - z0)


def _rrect(x, hw, r) -> Face:
    return Pos((x[0] + x[1]) / 2, 0) * RectangleRounded(x[1] - x[0], 2 * hw, r)


def make_housing() -> Solid:
    housing = _z_prism(_peanut(POST_R), ROOT_Z, Z_L1)
    housing += _z_prism(_column(), Z_L1, Z_PLATE)
    housing += _z_prism(_lower(POST_R, None), Z_L1, Z_L2)
    housing += _z_prism(_lower(POST_R_L2, DIAG_FILLET_L2), Z_L2, Z_U)
    housing += _z_prism(_upper(), Z_U, Z_PLATE)
    # rib under the plate, beside the M12
    rib = Pos(0, 0, 0) * Box(RIB["x1"] - 5.0, RIB_T, Z_PLATE - 6.0, align=Align.MIN)
    rib = Pos(5.0, -RIB_T / 2, 6.0) * rib
    rib -= Pos(RIB["x0"], -1, 0) * Box(20, 2, RIB["arc_c"][1], align=Align.MIN)
    rib -= Pos(RIB["arc_c"][0], -1, 0) * Box(20, 2, RIB["z_top"], align=Align.MIN)
    rib -= Pos(RIB["arc_c"][0], 0, RIB["arc_c"][1]) * Rot(90, 0, 0) * Cylinder(RIB["arc_r"], 2)
    housing += rib
    # plate, flange, lid
    px, phw, pr, pz = PLATE
    fx, fhw, fr, fz, fch = FLANGE
    housing += _z_prism(_rrect(px, phw, pr), *pz)
    flange = _z_prism(_rrect(fx, fhw, fr), *fz)
    housing += chamfer(flange.edges().group_by(Axis.Z)[-1], fch)
    housing += _z_prism(_rrect(px, phw, pr), *LID_NECK_Z)
    dome = Pos(DOME["c"][0], 0, DOME["c"][1]) * Sphere(DOME["r"])
    lid = _z_prism(_rrect(fx, fhw, fr), LID_Z0, DOME["c"][1] + DOME["r"] + 1) & dome
    # LED windows on both sides, one in the inlet-end face
    zc = sum(LED_SLOT["z"]) / 2
    hz = LED_SLOT["z"][1] - LED_SLOT["z"][0]
    for x0, x1 in LED_SLOTS:
        win = Pos((x0 + x1) / 2, zc) * RectangleRounded(x1 - x0, hz, LED_SLOT["r"])
        lid -= extrude(Plane.XZ.offset(-fhw) * win, amount=LED_SLOT["depth"])
        lid -= extrude(Plane.XZ.offset(fhw) * win, amount=-LED_SLOT["depth"])
    win = RectangleRounded(END_SLOT["y"], hz, LED_SLOT["r"])
    lid -= extrude(Plane.YZ.offset(fx[1]) * Pos(0, zc) * win, amount=-END_SLOT["depth"])
    housing += lid
    housing -= make_pipe()  # seat on the pipe
    return housing


def make_m12() -> Solid:
    """M12 connector with its socket and coding rib."""
    s = M12_SOCKET
    z0 = LID_Z0 + 5  # starts inside the lid; trimmed to the dome below
    pts = [(0, z0), (M12_PROFILE[0][0], z0), *M12_PROFILE, (s["r"], Z_TOP), (s["r"], s["floor"])]
    pts += [(0, s["floor"])]
    fil = [(6.0, 31.25, 1.0), (5.2, 40.546, 0.2), (s["r"], s["floor"], s["floor_r"])]
    axis = Axis((M12_X, 0, 0), (0, 0, 1))
    m12 = _revolve(pts, axis, Plane.XZ.shift_origin((M12_X, 0, 0)), fil)
    k = M12_KEY
    hk = Z_TOP - s["floor"]
    rib = Cylinder(k["w"] / 2, hk, align=(Align.CENTER, Align.CENTER, Align.MIN))
    rib += Box(s["r"] + 0.3 - k["tip"], k["w"], hk, align=(Align.MIN, Align.CENTER, Align.MIN))
    rib = Pos(M12_X, 0, s["floor"]) * Rot(0, 0, k["angle"]) * Pos(k["tip"], 0, 0) * rib
    dome = Pos(DOME["c"][0], 0, DOME["c"][1]) * Sphere(DOME["r"])
    return (m12 + rib) - dome  # sits on the lid, no overlap with the housing


def make_flowmeter_parts() -> dict[str, Solid]:
    return {"pipe": make_pipe(), "housing": make_housing(), "m12": make_m12()}


def make_flowmeter() -> Solid:
    p = make_flowmeter_parts()
    return p["pipe"] + p["housing"] + p["m12"]


if __name__ == "__main__":
    f = make_flowmeter()
    bb = f.bounding_box()
    print(
        f"SV3051 bbox: {bb.size.X:.2f} x {bb.size.Y:.2f} x {bb.size.Z:.2f} mm "
        f"(datasheet 77 x 30.2 x 52.7)"
    )
    print(f"M12 axis {L_TOTAL / 2 - M12_X:.1f} mm from inlet end (datasheet 27.4)")
    print("STEP: uv run python tools/export_step.py -> output/step/")
