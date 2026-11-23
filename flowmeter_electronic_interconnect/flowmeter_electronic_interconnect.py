"""Amphenol LTW MSAP-04BFFC-SR7001, M12 A-coded 4-contact crimp elbow.

Sources: OEM MSAP-XXBFFC-SR7001 drawing rev F (2023-01-03), downloaded
from https://amphenolltw.com/down.php?prod_files=429169 ; OEM STEP
msap-04bffc-sr7001_sw0001.stp, https://amphenolltw.com/down.php?prod_files=475411 .
See dimension_register.md for source conflicts and verification status.

Local frame: mating axis +X into the connector, insert shoulder datum X=0;
insert front X=-9.7; cable exits along -Z at X=CABLE_X; Y is width.
The A-code notch is on +Z. All lengths mm. No helical threads.
The internal wiring space is filled for the assembly envelope; exposed
mating sockets, seal, keyway and cable-entry cage retain their CAD geometry.
Raised lettering and small housing blends are omitted within the envelope
limit. See cad_spec.json for the documented female-thread convention.
"""

from math import sqrt

from build123d import (
    Align,
    Axis,
    Box,
    Cone,
    Cylinder,
    Edge,
    Face,
    Plane,
    Polyline,
    Pos,
    Rot,
    Solid,
    Torus,
    Wire,
    extrude,
    fillet,
    make_face,
    revolve,
)
from interconnect_profiles import (
    CONNECTOR_HEX_PROFILE,
    FRONT_GRIP_PROFILE,
    GLAND_CAGE_PROFILE,
    GLAND_GRIP_PROFILE,
    GLAND_HEX_PROFILE,
    REAR_GRIP_PROFILE,
)

# Drawing reference dimensions, mm (not the CAD's complete ribbed envelope).
DRAWING_LENGTH_REF = 39.3  # OEM rev F, horizontal reference dimension
DRAWING_HEIGHT_REF = 35.5  # OEM rev F, housing top to gland end
DRAWING_RING_D = 18.6  # OEM rev F diameter callout
HEX_AF = 16.0  # OEM rev F, both spanner flats
CABLE_OD_RANGE = (4.0, 7.0)  # OEM rev F; web page says 4-8 mm

# OEM STEP axial stations, relative to the insert-back datum.
INSERT_FRONT = -9.7  # OEM STEP analytical geometry
INSERT_R = 4.1  # OEM STEP analytical geometry
KEY_R = 0.65  # semicircular bottom of key slot
KEY_END = -1.3  # OEM STEP keyway end face
CORE_R = 5.25  # OEM STEP rear insert shoulder
CORE_FRONT_ROUND = 0.3  # OEM STEP rear insert shoulder round
KEY_Z = 3.35  # key semicircle centre (bottom 2.7)
INSERT_BACK = 0.76  # STEP contact-cavity chamfer start
CONTACT_PCD = 5.0  # OEM STEP analytical geometry
ENTRY_R = 0.65  # OEM STEP analytical geometry
ENTRY_CHAMFER_R = 0.8  # OEM STEP analytical geometry
ENTRY_CHAMFER_END = -9.2  # OEM STEP analytical geometry
CONTACT_CAVITY_R = 0.8  # OEM STEP analytical geometry
CONTACT_CAVITY_FRONT = -8.2  # OEM STEP analytical geometry
SEAL_MAJOR_R = 4.25  # OEM STEP analytical geometry
SEAL_MINOR_R = 0.75  # OEM STEP analytical geometry
SEAL_X = -0.75  # OEM STEP analytical geometry
SEAL_LAND_R = 4.95  # OEM STEP analytical geometry
THREAD_MAJOR_R = 6.0  # M12 female cosmetic thread, major diameter
THREAD_FLOOR = 1.3  # OEM STEP analytical geometry
THREAD_LEAD_R = 6.4585  # OEM STEP threaded lead-in maximum radius
COUPLING_FRONT = -7.85  # OEM STEP analytical geometry
COUPLING_HEX_START = -1.7  # OEM STEP analytical geometry
BODY_OFFSET = -0.001445382772  # OEM STEP assembly offset of elbow vs insert
COUPLING_HEX_END = 2.3 + BODY_OFFSET  # OEM STEP analytical geometry
REAR_RING_END = 8.3 + BODY_OFFSET  # OEM STEP analytical geometry

# Contact socket profile: OEM STEP radii and axial stations.
CONTACT_OUTER = [
    (0.75, -7.95),
    (0.75, -1.95),
    (0.55, -1.6035898385),
    (0.55, 0.49),
    (0.75, 0.8364101615),
    (0.75, 1.3),
]
CONTACT_INNER = [
    (0.675, -7.95),
    (0.525, -7.8),
    (0.525, -2.45),
    (0.0, -2.0685658358),
]  # OEM STEP analytical geometry
CONTACT_SLOT_W = 0.3  # STEP opposed splits in each socket
CONTACT_SLOT_END = -3.95  # OEM STEP analytical geometry
CONTACT_SLOT_ANGLE = 28.531244  # STEP slot-plane normal atan2(0.477627,0.878563)

# Elbow envelope and internal dimensions from OEM STEP analytical faces.
BODY_START = 9.8 + BODY_OFFSET  # OEM STEP analytical geometry
BODY_BACK = 29.6 + BODY_OFFSET  # OEM STEP analytical geometry
BODY_R = 8.5  # OEM STEP analytical geometry
BODY_HALF_W = 8.0  # OEM STEP analytical geometry
BODY_BACK_ROUND = 1.0  # OEM STEP analytical geometry
BODY_BOTTOM = -11.0  # OEM STEP analytical geometry
CABLE_X = 20.6 + BODY_OFFSET  # OEM STEP analytical geometry
NECK_R = (7.375 + 7.916) / 2  # STEP gland thread root/crest midpoint, cosmetic envelope
NECK_END = -22.5  # OEM STEP analytical geometry
CABLE_BORE_END = -23.7  # STEP cable cage end face
BODY_NECK_R = 7.8  # STEP flat-to-thread elbow neck envelope
BODY_NECK_START = 3.4 + BODY_OFFSET  # STEP neck end face
CONTACT_CAVITY_BACK = [
    (0.94, 0.9),
    (0.9443375672974, 0.9),  # OEM STEP analytical geometry
    (0.9443375672974, THREAD_FLOOR),
]  # STEP rear counterbore
THREAD_LEAD_LENGTH = 1.0  # STEP threaded lead-in cone length
GEOMETRY_EPS = 1e-5  # edge selection precision, not a physical allowance

# OEM STEP gland axial stations and profiles, r measured about CABLE_X.
GLAND_TOP = -14.5  # OEM STEP analytical geometry
GLAND_LIP_BOTTOM = -15.5  # OEM STEP analytical geometry
GLAND_GRIP_BOTTOM = -23.5  # OEM STEP analytical geometry
GLAND_HEX_BOTTOM = -26.5  # OEM STEP analytical geometry
GLAND_BOTTOM = -27.0  # OEM STEP analytical geometry
GLAND_LIP_R = 9.25  # OEM STEP analytical geometry
GLAND_GRIP_ROOT_R = 9.0  # OEM STEP grip end cone at Z=-23.5
GLAND_GRIP_END_SLOPE = 1.0  # OEM STEP cone half-angle 45 degrees
GLAND_BORE = [
    (5.5, -27.0),
    (4.5, -26.0),
    (4.5, -25.0173),
    (6.0699, -23.7),
]
CUT_MARGIN = 1.0  # Boolean cutter overrun, not a part dimension


def _xcyl(r, x0, x1):
    return (
        Pos(x0, 0, 0)
        * Rot(0, 90, 0)
        * Cylinder(r, x1 - x0, align=(Align.CENTER, Align.CENTER, Align.MIN))
    )


def _zcyl(r, z0, z1):
    return Pos(CABLE_X, 0, z0) * Cylinder(r, z1 - z0, align=(Align.CENTER, Align.CENTER, Align.MIN))


def _rev(profile):
    """Revolve (r, axial station) about Z."""
    return revolve(make_face(Plane.XZ * Polyline(*profile, close=True)), Axis.Z)


def _xrev(profile):
    return Rot(0, 90, 0) * _rev(profile)


def _profile_face(segments, plane):
    edges = []
    for kind, a, m, b in segments:
        edges.append(
            Edge.make_line(plane.from_local_coords(a), plane.from_local_coords(b))
            if kind == "LINE"
            else Edge.make_three_point_arc(
                plane.from_local_coords(a), plane.from_local_coords(m), plane.from_local_coords(b)
            )
        )
    return Face(Wire(edges))


def make_insert() -> Solid:
    insert = _xcyl(INSERT_R, INSERT_FRONT, INSERT_BACK)
    core = _xcyl(CORE_R, 0, THREAD_FLOOR)
    core = fillet([e for e in core.edges() if abs(e.center().X) < GEOMETRY_EPS], CORE_FRONT_ROUND)
    insert += core
    # A-code keyway: semicircle joined to straight sides, open through +Z.
    key = _xcyl(KEY_R, INSERT_FRONT - CUT_MARGIN, KEY_END).moved(Pos(0, 0, KEY_Z))
    key += Pos((INSERT_FRONT - CUT_MARGIN + KEY_END) / 2, 0, KEY_Z + INSERT_R / 2) * Box(
        KEY_END - INSERT_FRONT + CUT_MARGIN, 2 * KEY_R, INSERT_R
    )
    insert -= key
    offset = CONTACT_PCD / (2 * sqrt(2))
    for y in (-offset, offset):
        for z in (-offset, offset):
            bore = _xrev(
                [
                    (0, INSERT_FRONT - CUT_MARGIN),
                    (ENTRY_CHAMFER_R, INSERT_FRONT - CUT_MARGIN),
                    (ENTRY_CHAMFER_R, INSERT_FRONT),
                    (ENTRY_R, ENTRY_CHAMFER_END),
                    (ENTRY_R, CONTACT_CAVITY_FRONT),
                    (CONTACT_CAVITY_R, CONTACT_CAVITY_FRONT),
                    (CONTACT_CAVITY_R, INSERT_BACK),
                    *CONTACT_CAVITY_BACK,
                    (0, THREAD_FLOOR),
                ]
            )
            insert -= Pos(0, y, z) * bore
    return insert


def make_contacts() -> dict[str, Solid]:
    outer = _xrev([(0, CONTACT_OUTER[0][1])] + CONTACT_OUTER + [(0, CONTACT_OUTER[-1][1])])
    inner = _xrev([(0, CONTACT_INNER[0][1])] + CONTACT_INNER)
    contact = outer - inner
    slot = (
        Pos((CONTACT_OUTER[0][1] + CONTACT_SLOT_END) / 2, 0, 0)
        * Rot(CONTACT_SLOT_ANGLE, 0, 0)
        * Box(
            CONTACT_SLOT_END - CONTACT_OUTER[0][1],
            2 * CONTACT_OUTER[0][0] + CUT_MARGIN,
            CONTACT_SLOT_W,
        )
    )
    contact -= slot
    offset = CONTACT_PCD / (2 * sqrt(2))
    return {
        f"contact_{i}": Pos(0, y, z) * contact
        for i, (y, z) in enumerate(
            [(offset, offset), (-offset, offset), (-offset, -offset), (offset, -offset)], 1
        )
    }


def make_coupling() -> Solid:
    front = extrude(
        _profile_face(FRONT_GRIP_PROFILE, Plane.YZ.offset(COUPLING_FRONT)),
        amount=COUPLING_HEX_START - COUPLING_FRONT,
        dir=(1, 0, 0),
    )
    hexbody = extrude(
        _profile_face(CONNECTOR_HEX_PROFILE, Plane.YZ.offset(COUPLING_HEX_START)),
        amount=COUPLING_HEX_END - COUPLING_HEX_START,
        dir=(1, 0, 0),
    )
    rear = extrude(
        _profile_face(REAR_GRIP_PROFILE, Plane.YZ.offset(COUPLING_HEX_END)),
        amount=REAR_RING_END - COUPLING_HEX_END,
        dir=(1, 0, 0),
    )
    outer = front + hexbody + rear
    bore = _xrev(
        [
            (0, COUPLING_FRONT - CUT_MARGIN),
            (THREAD_LEAD_R, COUPLING_FRONT - CUT_MARGIN),
            (THREAD_LEAD_R, COUPLING_FRONT),
            (THREAD_MAJOR_R, COUPLING_FRONT + THREAD_LEAD_LENGTH),
            (THREAD_MAJOR_R, THREAD_FLOOR),
            (0, THREAD_FLOOR),
        ]
    )
    outer -= bore
    # Internal wiring space is filled in this envelope model.

    return outer


def make_body() -> Solid:
    body = _xcyl(BODY_R, BODY_START, BODY_BACK)
    end_edges = [e for e in body.edges() if abs(e.center().X - BODY_BACK) < GEOMETRY_EPS]
    body = fillet(end_edges, BODY_BACK_ROUND)
    body += _zcyl(BODY_R, BODY_BOTTOM, 0)
    body &= Pos((BODY_START + BODY_BACK) / 2, 0, (BODY_BOTTOM + BODY_R) / 2) * Box(
        BODY_BACK - BODY_START + 2 * CUT_MARGIN,
        2 * BODY_HALF_W,
        BODY_R - BODY_BOTTOM + 2 * CUT_MARGIN,
    )
    body += _zcyl(NECK_R, NECK_END, BODY_BOTTOM)
    body += _xcyl(BODY_NECK_R, BODY_NECK_START, BODY_START)

    return body


def make_gland() -> Solid:
    hexbody = extrude(
        _profile_face(GLAND_HEX_PROFILE, Plane.XY.offset(GLAND_BOTTOM)),
        amount=GLAND_GRIP_BOTTOM - GLAND_BOTTOM,
    )
    grip = extrude(
        _profile_face(GLAND_GRIP_PROFILE, Plane.XY.offset(GLAND_GRIP_BOTTOM)),
        amount=GLAND_LIP_BOTTOM - GLAND_GRIP_BOTTOM,
        dir=(0, 0, 1),
    )
    grip_height = GLAND_LIP_BOTTOM - GLAND_GRIP_BOTTOM
    grip &= Pos(CABLE_X, 0, GLAND_GRIP_BOTTOM) * Cone(
        GLAND_GRIP_ROOT_R,
        GLAND_GRIP_ROOT_R + GLAND_GRIP_END_SLOPE * grip_height,
        grip_height,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )
    body = hexbody + grip
    body += _zcyl(GLAND_LIP_R, GLAND_LIP_BOTTOM, GLAND_TOP)
    cutter = Pos(CABLE_X, 0, 0) * _rev(
        [(0, GLAND_BOTTOM - CUT_MARGIN), (GLAND_BORE[0][0], GLAND_BOTTOM - CUT_MARGIN)]
        + GLAND_BORE
        + [(0, CABLE_BORE_END)]
    )
    cage = extrude(
        _profile_face(GLAND_CAGE_PROFILE, Plane.XY.offset(GLAND_BOTTOM - CUT_MARGIN)),
        amount=CABLE_BORE_END - GLAND_BOTTOM + CUT_MARGIN,
        dir=(0, 0, 1),
    )
    return body - (cutter & cage)


def make_seal() -> Solid:
    return Pos(SEAL_X, 0, 0) * Rot(0, 90, 0) * Torus(SEAL_MAJOR_R, SEAL_MINOR_R)


def make_interconnect_parts() -> dict[str, Solid]:
    """Named solids; subtract shared envelope material to avoid overlapping parts."""
    body, coupling, gland, seal = make_body(), make_coupling(), make_gland(), make_seal()
    return {
        "insert": make_insert() - seal,
        "coupling": coupling - body,
        "body": body,
        "gland": gland - body,
        "seal": seal,
        **make_contacts(),
    }


def make_interconnect() -> Solid:
    parts = list(make_interconnect_parts().values())
    return parts[0].fuse(*parts[1:])


if __name__ == "__main__":
    s = make_interconnect()
    print("MSAP-04BFFC-SR7001:", s.bounding_box())
