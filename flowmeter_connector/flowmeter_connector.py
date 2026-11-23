"""Festo QSF-1/2-12-B (part no. 190653) - push-in fitting, G1/2 female x 12 mm tube.

RS stock no. 121-5613. Brass, nickel plated; release ring POM (blue);
tube seal NBR. -0.95...14 bar (temperature dependent), -10...80 degC.
Screws onto the G1/2 male process connections of the ifm SV3051 flowmeter.

Sources
  1. Festo datasheet QSF-1/2-12-B and Festo QS catalogue ("Push-in fitting
     QSF, female thread with external hex", row QSF-1/2-12-B):
        D1 G1/2 | D2 12 mm tube | D5 dia 20.8 | L1 40.1 | L2 (thread) 14 |
        hex 24 AF | 56 g | tube insertion depth 23.3 (datasheet; 2016 catalogue 23.2)
        Water: liquid, ice-free, max 0.6 MPa at max 50 degC (datasheet 190653)
  2. Manufacturer 3D model served on the RS product page (TraceParts viewer,
     product 90-14062024-034676). The profile below follows that model.
     It is 40.8 long (release ring in its outer position) vs. catalogue L1
     40.1 - the model's 40.8 is used as the envelope.

Local frame: fitting axis = Z, female port face (hex end, the face that
meets the flowmeter) at Z = 0, thread cavity toward +Z, tube enters at the
release ring end, Z = L_TOTAL.
Profile stations below are given in the vendor-model frame (v = 0 at the
release ring, v = L_TOTAL at the port face) and mapped with Z = L_TOTAL - v.
"""

from build123d import (
    Align,
    Axis,
    Cylinder,
    Plane,
    Polyline,
    Pos,
    RegularPolygon,
    Rot,
    Solid,
    extrude,
    make_face,
    revolve,
)

# --- Catalogue -------------------------------------------------------------
HEX_AF = 24.0
HEX_AC = HEX_AF / 0.8660254  # 27.71
BODY_D = 20.8  # D5
THREAD_MAJOR_D = 20.955  # G1/2 (cosmetic female thread: modelled at major)
THREAD_MINOR_D = 18.631
THREAD_DEPTH = 14.0  # L2
TUBE_OD = 12.0
TUBE_INSERT = 23.3  # Festo datasheet 190653 (2026); 2016 catalogue says 23.2

# --- Vendor-model stations (v from release-ring end) -----------------------
L_TOTAL = 40.8
RING_PROFILE = [  # (r, v) outer profile of the release ring
    (7.00, 0.00),
    (9.90, 0.50),
    (9.90, 1.50),
    (9.05, 2.30),
    (9.25, 2.50),
    (9.25, 2.80),
    (9.05, 3.00),
    (9.25, 3.20),
    (9.25, 3.50),
]
RING_END_V = 3.50  # ring / body split
RING_ID = 14.0  # release ring bore; the metal collet sleeve
# (dia 14 / dia 12) sits inside it, flush at v = 0
BODY_PROFILE = [  # (r, v) body outer profile up to the hex
    (9.65, 3.50),
    (9.96, 4.34),
    (10.40, 4.50),
    (10.40, 19.80),
]
HEX_ENVELOPE = [  # chamfered-corner envelope of the hex
    (10.40, 19.80),
    (HEX_AC / 2 + 0.01, 23.27),
    (HEX_AC / 2 + 0.01, 40.30),
    (12.49, 40.67),
    (12.00, L_TOTAL),
]
TUBE_BORE_V = 23.30  # dia 12 tube bore depth (vendor model) = insertion depth
CONE_TOP = (7.27, L_TOTAL - THREAD_DEPTH)  # (r, v) thread floor inner edge, v = 26.8


def _revolve_rz(pts: list[tuple[float, float]]) -> Solid:
    """Revolve a closed (r, v) profile about Z. Plane.XZ local (x, y) = (X, Z)."""
    return revolve(make_face(Plane.XZ * Polyline(*pts, close=True)), Axis.Z)


def _v_cyl(d: float, v0: float, v1: float) -> Solid:
    return Pos(0, 0, v0) * Cylinder(d / 2, v1 - v0, align=(Align.CENTER, Align.CENTER, Align.MIN))


def _to_local(s: Solid) -> Solid:
    """Vendor frame (v) -> local frame, Z = L_TOTAL - v."""
    return Pos(0, 0, L_TOTAL) * Rot(180, 0, 0) * s


def _bores() -> Solid:
    tube = _v_cyl(TUBE_OD + 0.02, -1, TUBE_BORE_V)
    cone = _revolve_rz(
        [
            (0, TUBE_BORE_V),
            (TUBE_OD / 2 + 0.01, TUBE_BORE_V),
            (CONE_TOP[0], CONE_TOP[1]),
            (0, CONE_TOP[1]),
        ]
    )
    thread = _v_cyl(THREAD_MAJOR_D, CONE_TOP[1], L_TOTAL + 1)
    return tube + cone + thread


def make_release_ring() -> Solid:
    ring = _revolve_rz([(0, 0)] + RING_PROFILE + [(0, RING_END_V)])
    return _to_local(ring - _v_cyl(RING_ID, -1, RING_END_V + 1))


def make_body() -> Solid:
    core = _revolve_rz([(0, RING_END_V)] + BODY_PROFILE + [(0, BODY_PROFILE[-1][1])])
    core += _v_cyl(RING_ID - 0.02, 0, RING_END_V + 0.01)  # collet sleeve inside the ring
    hexp = Pos(0, 0, HEX_ENVELOPE[0][1]) * extrude(
        RegularPolygon(HEX_AF / 2, 6, major_radius=False, rotation=30),
        amount=L_TOTAL - HEX_ENVELOPE[0][1],
    )
    env = _revolve_rz([(0, HEX_ENVELOPE[0][1])] + HEX_ENVELOPE + [(0, L_TOTAL)])
    return _to_local(core + (hexp & env) - _bores())


def make_fitting_parts() -> dict[str, Solid]:
    return {"body": make_body(), "release_ring": make_release_ring()}


def make_fitting() -> Solid:
    p = make_fitting_parts()
    return p["body"] + p["release_ring"]


def make_tube(length: float = 40.0) -> Solid:
    """12x8 tube stub pushed home (insertion depth 23.2 from the ring end)."""
    z0 = L_TOTAL - TUBE_INSERT
    t = Pos(0, 0, z0) * Cylinder(
        TUBE_OD / 2 - 0.02, length + TUBE_INSERT, align=(Align.CENTER, Align.CENTER, Align.MIN)
    )
    return t - Pos(0, 0, z0 - 1) * Cylinder(
        4.0, length + TUBE_INSERT + 2, align=(Align.CENTER, Align.CENTER, Align.MIN)
    )


if __name__ == "__main__":
    f = make_fitting()
    bb = f.bounding_box()
    print(
        f"QSF-1/2-12-B bbox: {bb.size.X:.2f} x {bb.size.Y:.2f} x {bb.size.Z:.2f} mm "
        f"(Z {bb.min.Z:.2f}..{bb.max.Z:.2f})"
    )
    print("STEP: uv run python tools/export_step.py -> output/step/")
