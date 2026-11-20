"""Dimension annotations for every part of the station (build123d drafting).

build123d's drafting module builds dimension lines (extension lines, arrows
and the value as text) as ordinary planar geometry, so they can be shown in
the OCP viewer next to the part or rendered into the PNG sheets.

Every dimension here is MEASURED from the model (bounding boxes of the parts
or sub-parts as placed in the station), never typed in, so the annotation
can't drift from the geometry.

    from tools.dims import part_groups, dimensions
    groups = part_groups(assembly.build())      # one of each part
    for name, g in groups.items():
        dims = dimensions(name, g)              # list of planar dimension solids
"""

from __future__ import annotations

from build123d import Compound, Plane, Vector
from build123d.drafting import Draft, ExtensionLine

DRAFT = Draft(
    font_size=3.2,
    decimal_precision=1,
    display_units=False,
    arrow_length=2.0,
    line_width=0.2,
    extension_gap=1.0,
    pad_around_text=1.0,
)

# assembly part-name prefix -> (group name, title); one representative each
GROUPS = {
    "valve_": ("valve", "Valve RS 283-8289 (Tognella FT 1251/2-01-14)"),
    "fitting_A": ("valve_fitting", "Valve fitting SMC KQ2H12-U02A (x2)"),
    "flowmeter_": ("flowmeter", "Flowmeter ifm SV3051"),
    "qsf_": ("flowmeter_fitting", "Flowmeter fitting Festo QSF-1/2-12-B (x2)"),
    "base_front": ("station_base", "Station base, front layer (6 mm acrylic, laser)"),
    "valve_clamp_base": ("valve_clamp_base", "Valve clamp base (PETG, printed)"),
    "valve_clamp_cap": ("valve_clamp_cap", "Valve clamp cap (PETG, printed)"),
    "fm_clamp_base": ("fm_clamp_base", "Flowmeter clamp base (PETG, printed)"),
    "fm_clamp_strap_0": ("fm_strap", "Flowmeter strap (x2, PETG, printed)"),
    "m4_cap_screw_0": ("m4_screw", "M4x20 ISO 4762 (cap)"),
    "wall_screw_0": ("wall_screw", "M6 wall screw (x8)"),
    "tube_link": ("tube_link", "Tube 12x8, link (cut length)"),
    "tube_in": ("tube_in", "Tube 12x8, inlet straight run"),
}


def part_groups(parts: dict) -> dict[str, dict]:
    """One representative of each part, keyed by group name.

    Each value: {"title": str, "solids": {assembly_name: Solid}}. A prefix
    ending in "_" collects all sub-parts of a multi-body part (the QSF from
    the outlet side only); any other key names one assembly part.
    """
    out: dict[str, dict] = {}
    for key, (group, title) in GROUPS.items():
        if key.endswith("_"):
            sel = {
                n: s
                for n, s in parts.items()
                if n.startswith(key) and not n.endswith("_in") and "_clamp" not in n
            }
        else:
            sel = {key: parts[key]}
        out[group] = {"title": title, "solids": sel}
    return out


def _bb(solids):
    bb = None
    for s in solids:
        bb = s.bounding_box() if bb is None else bb.add(s.bounding_box())
    return bb


def lin(a, b, normal, offset: float, label: str | None = None) -> Compound:
    """Linear dimension from a to b, drawn in the plane with this normal.

    `offset` pushes the dimension line off the measured edge, towards
    normal x (b - a).
    """
    a, b, n = Vector(*a), Vector(*b), Vector(*normal)
    span = b - a
    plane = Plane(origin=a, x_dir=span.normalized(), z_dir=n)
    d = ExtensionLine(
        border=[(0, 0, 0), (span.length, 0, 0)], offset=offset, draft=DRAFT, label=label
    )
    return plane.location * d


def overall(solids) -> list[Compound]:
    """Overall X, Y, Z extents (station frame: X flow, Y out of wall, Z up)."""
    bb = _bb(solids)
    x0, y0, z0, x1, y1, z1 = bb.min.X, bb.min.Y, bb.min.Z, bb.max.X, bb.max.Y, bb.max.Z
    off = 6.0
    return [
        lin((x0, y1, z0), (x1, y1, z0), (0, 1, 0), off),  # length X, below, front plane
        lin((x1, y1, z0), (x1, y1, z1), (0, 1, 0), off),  # height Z, right, front plane
        lin((x0, y0, z1), (x0, y1, z1), (0, 0, 1), off),  # depth Y, left, top plane
    ]


def _sub(g, key):
    return [s for n, s in g["solids"].items() if key in n]


def key_dims(group: str, g: dict) -> list[Compound]:
    """Catalogue/critical dimensions, measured from sub-parts."""
    out = []
    if group == "valve":
        body = _bb(_sub(g, "body"))
        knob = _bb(_sub(g, "knob"))
        # CH (square body) on the end face, knob diameter across the knob
        out.append(
            lin(
                (body.min.X, body.min.Y, body.max.Z),
                (body.min.X, body.max.Y, body.max.Z),
                (0, 0, 1),
                -6,
                f"CH {body.size.Y:.0f}",
            )
        )
        out.append(
            lin(
                (knob.min.X, knob.max.Y, knob.max.Z),
                (knob.max.X, knob.max.Y, knob.max.Z),
                (0, 1, 0),
                4,
                f"Ø{knob.size.X:.0f}",
            )
        )
    elif group == "flowmeter":
        pipe = _bb(_sub(g, "pipe"))
        m12 = _bb(_sub(g, "m12"))
        inlet_x = (
            pipe.max.X
            if abs(pipe.max.X - m12.center().X) < abs(pipe.min.X - m12.center().X)
            else pipe.min.X
        )
        out.append(
            lin(
                (m12.center().X, pipe.max.Y, m12.max.Z),
                (inlet_x, pipe.max.Y, m12.max.Z),
                (0, 1, 0),
                -4,
                f"M12 {abs(inlet_x - m12.center().X):.1f} from inlet",
            )
        )
    elif group == "flowmeter_fitting":
        ring = _bb(_sub(g, "release_ring"))
        out.append(
            lin(
                (ring.center().X, ring.min.Y, ring.max.Z + 3),
                (ring.center().X, ring.max.Y, ring.max.Z + 3),
                (1, 0, 0),
                2,
                "release ring",
            )
        )
    elif group == "station_base":
        bb = _bb(g["solids"].values())
        # flow-axis height above the wall (valve cradle at X = 0)
        import clamp as C

        out.append(
            lin(
                (0, 0, bb.max.Z),
                (0, C.VALVE_Y, bb.max.Z),
                (0, 0, 1),
                -8,
                f"axis {C.VALVE_Y:.2f} from wall",
            )
        )
    elif group == "tube_link":
        pass  # overall length is the cut length
    return out


def dimensions(group: str, g: dict) -> list[Compound]:
    return overall(list(g["solids"].values())) + key_dims(group, g)
