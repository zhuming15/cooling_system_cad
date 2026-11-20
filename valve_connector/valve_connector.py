"""SMC KQ2H12-U02A - KQ2 one-touch male connector, 12 mm tube x Uni 1/4.

RS stock no. 771-5217. Brass, electroless nickel plated, gasket seal.
Uni thread fits both G1/4 (BSPP, sealed by the gasket) and R1/4 ports, so it
screws directly into the G1/4 ports of the RS 283-8289 valve.

Sources
  1. SMC KQ2 catalogue, "Metric Size Uni One-touch Fittings, Male Connector:
     KQ2H (Gasket seal)", row KQ2H12-U02:
        H (hex AF) 19.0 | D 18.2 | L 24.8 | A (seat->top) 18.4 | M 17.0 |
        min. port 9.0
  2. Manufacturer 3D model served on the RS product page (TraceParts
     viewer, product 10-29022016-093195, kq2h12-u02a). The profile below
     follows that model; every catalogue dimension above agrees with it.
     The viewer model is solid inside, so the dia 9 flow bore comes from (1).

Local frame: fitting axis = Z, seat datum (catalogue "A" reference, valve
port face) at Z = 0, thread toward -Z, tube enters from +Z.
"""

from build123d import (
    Align,
    Axis,
    Cylinder,
    Plane,
    Polyline,
    Pos,
    RegularPolygon,
    Solid,
    export_step,
    extrude,
    make_face,
    revolve,
)

# --- Catalogue dimensions --------------------------------------------------
HEX_AF = 19.0
HEX_AC = HEX_AF / 0.8660254          # 21.94
BODY_D = 18.2                         # D: release-button OD
L_TOTAL = 24.8
A_SEAT_TO_TOP = 18.4
THREAD_L = L_TOTAL - A_SEAT_TO_TOP   # 6.4
THREAD_D = 13.157                     # G1/4 major dia (cosmetic thread)
TUBE_OD = 12.0
TUBE_INSERT = 17.0                    # M
MIN_PORT = 9.0

# --- Stations from the RS/TraceParts 3D model (Z, radius) -------------------
THREAD_CHAMFER_R = 5.72              # thread end / run-out chamfer dia 11.44
THREAD_FULL_Z = (-5.54, -2.43)        # full-dia thread length
NECK = ((-1.57, 5.72), (-0.76, 5.65))  # thread undercut
HEX_Z0 = 3.09                         # hex underside (r = AF/2)
HEX_FULL_Z = (4.56, 15.61)            # full corners between these
HEX_TOP_CHAMFER = (15.90, 9.89)
HEX_Z1 = 16.00                        # hex top (r = AF/2)
TUBE_STOP_Z = A_SEAT_TO_TOP - TUBE_INSERT   # 1.40
BUTTON_RECESS = (12.95, 16.00, 16.90)   # internal recess under button (dia, z0, z1)


def _z_cyl(d: float, h: float, z0: float) -> Solid:
    return Pos(0, 0, z0) * Cylinder(d / 2, h, align=(Align.CENTER, Align.CENTER, Align.MIN))


def _revolve_rz(pts: list[tuple[float, float]]) -> Solid:
    """Revolve a closed (r, z) profile about Z. Plane.XZ local (x, y) = (X, Z)."""
    face = make_face(Plane.XZ * Polyline(*pts, close=True))
    return revolve(face, Axis.Z)


def make_fitting() -> Solid:
    r_af = HEX_AF / 2
    r_ac = HEX_AC / 2
    # axisymmetric core: thread, undercut, 45 deg conical gasket seat, body
    # core under the hex, release button
    core = _revolve_rz([
        (0, -THREAD_L),
        (THREAD_CHAMFER_R, -THREAD_L),
        (THREAD_D / 2, THREAD_FULL_Z[0]),
        (THREAD_D / 2, THREAD_FULL_Z[1]),
        NECK[0][::-1],
        NECK[1][::-1],
        (r_af, HEX_Z0),
        (r_af, HEX_Z1),
        (BODY_D / 2, HEX_Z1),
        (BODY_D / 2, A_SEAT_TO_TOP),
        (0, A_SEAT_TO_TOP),
    ])
    # hex with chamfered corners top and bottom
    prism = extrude(Plane.XY.offset(HEX_Z0) * RegularPolygon(r_af, 6, major_radius=False),
                    amount=HEX_Z1 - HEX_Z0)
    chamfer_env = _revolve_rz([
        (0, HEX_Z0),
        (r_af, HEX_Z0),
        (r_ac + 0.01, HEX_FULL_Z[0]),
        (r_ac + 0.01, HEX_FULL_Z[1]),
        (HEX_TOP_CHAMFER[1], HEX_TOP_CHAMFER[0]),
        (r_af, HEX_Z1),
        (0, HEX_Z1),
    ])
    f = core + (prism & chamfer_env)
    # tube socket down to the tube stop, then min. port through bore
    f -= _z_cyl(TUBE_OD, TUBE_INSERT + 0.1, TUBE_STOP_Z)
    f -= _z_cyl(MIN_PORT, L_TOTAL + 1, -THREAD_L - 0.5)
    d, z0, z1 = BUTTON_RECESS
    f -= _z_cyl(d, z1 - z0, z0)
    return f


def make_tube(length: float = 40.0) -> Solid:
    """12x8 polyurethane/nylon tube stub, seated on the tube stop."""
    t = _z_cyl(TUBE_OD - 0.05, length, TUBE_STOP_Z)
    return t - _z_cyl(8.0, length + 1, TUBE_STOP_Z - 0.5)


if __name__ == "__main__":
    from pathlib import Path

    f = make_fitting()
    bb = f.bounding_box()
    print(f"fitting bbox: {bb.size.X:.2f} x {bb.size.Y:.2f} x {bb.size.Z:.2f} mm "
          f"(Z {bb.min.Z:.2f}..{bb.max.Z:.2f}; catalogue L 24.8 = -6.4..18.4)")
    out = Path(__file__).with_name("smc_kq2h12-u02a.step")
    export_step(f, str(out))
    print(f"Exported {out}")
