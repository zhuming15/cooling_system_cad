"""Compare a part model with the vendor's 3D model, zone by zone.

    uv run python tools/cad_compare.py <preset> <vendor file>
    uv run python tools/cad_compare.py <spec.json> <vendor file>

Vendor files (keep them in a scratch directory, outside this repo):
  - RS / TraceParts viewer mesh: Three.js binary `<name>_000.bin`. To get it,
    open https://sg.rs-online.com/web/services/product/cad-download/3DViewer?articleId=<RS no.>
    in a browser, take the S3 URL from the `api/v/path` response, and unpack
    it with tools/fetch_rs_cad.py.
  - Manufacturer STEP (.step / .stp) or STL (.stl).

Acceptance (model-component skill)
  - fit-critical zones (anything a clamp, fitting, seal or tool touches) must
    match exactly: deviation <= FIT_TOL, which only allows for measurement
    noise, since the vendor model is itself a tessellation or a file rounded to
    the vendor's own precision;
  - every other vendor surface is envelope only: <= ENVELOPE_TOL;
  - skip zones are documented differences of convention (for example a female
    thread modelled at its major diameter here and at its minor by the vendor).

Direction of measurement
  - vendor -> ours: every vendor surface vertex, distance to our solid. Vendor
    mesh vertices lie on the true surface, so this is exact for meshes too.
    This decides PASS / FAIL.
  - feature edges, fit zones only: vendor edge points (B-rep edges, or mesh
    vertices on edges sharper than SHARP_ANGLE) must lie on one of our edges.
    A mesh carries exact information only at its vertices, and those sit on its
    edges: a bore 0.05 mm too big leaves its edge vertices on our end face
    (surface distance 0) but 0.05 mm from our bore's edge. Decides PASS / FAIL.
  - ours -> vendor: our surface vertices, distance to the vendor surface. For a
    STEP model this is exact and also decides PASS / FAIL (it catches material
    we have and the vendor doesn't). For a mesh it includes the mesh's chord
    error, and viewer meshes are often solid inside, so it is reported only.

Spec (preset dict or JSON file), all coordinates in OUR part frame:
  {"title": "...", "part": "module:function",
   "to_vendor": "pos(0, 0, 40.8) * rot(180, 0, 0)",   # moves our model into the vendor frame;
                                                       # also plane(origin, x_dir, z_dir)
   "section_axis": 2,                                 # vendor-frame axis cut for the PNG
   "zones": [{"name": "...", "kind": "fit" | "skip",
              "box": [x0, x1, y0, y1, z0, z1]}         # or
             {"name": "...", "kind": "fit" | "skip",
              "cyl": ["x" | "y" | "z", r_min, r_max, a_min, a_max]}],
   "fit_tol": 0.02, "envelope_tol": 0.5,               # optional, with a reason
   "out": "part_folder/cad_check.png"}
The first zone a point falls in decides its kind; zones are listed with skips
first. Exit code is 1 when the part fails.
"""

from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
for sub in (
    "",
    "valve",
    "valve_connector",
    "flowmeter",
    "flowmeter_connector",
    "flowmeter_electronic_interconnect",
):
    sys.path.insert(0, str(ROOT / sub))

FIT_TOL = 0.02  # mm: measurement noise only ("fit-critical must be exact", user 2026-11-23)
ENVELOPE_TOL = 0.5  # mm: outline and clearances (user 2026-11-23)
MAX_POINTS = 15_000  # vendor vertices measured (random subset above this)
SHARP_ANGLE = 30.0  # deg: mesh edges sharper than this are feature edges


# --------------------------------------------------------------------------
# Vendor files
# --------------------------------------------------------------------------
def load_threejs_bin(path: Path) -> np.ndarray:
    """Three.js binary 3.1 -> (n_tri, 3, 3) triangle array (vendor frame)."""
    b = Path(path).read_bytes()
    assert b[:12] == b"Three.js 003", "not a Three.js binary mesh"
    nv, nn = struct.unpack_from("<II", b, 24)
    nf = struct.unpack_from("<I", b, 44)[0]
    v = np.frombuffer(b, "<f4", nv * 3, 72).reshape(-1, 3).astype(float)
    off = 72 + nv * 12 + (nn * 3 + 3) // 4 * 4
    idx = np.frombuffer(b, "<u4", nf * 3, off).reshape(-1, 3)
    if idx.max() >= nv:
        raise ValueError("unexpected Three.js layout (index out of range)")
    return v[idx]


def load_stl(path: Path) -> np.ndarray:
    """Binary or ASCII STL -> (n_tri, 3, 3)."""
    b = Path(path).read_bytes()
    n = struct.unpack_from("<I", b, 80)[0] if len(b) >= 84 else 0
    if len(b) == 84 + 50 * n:
        rec = np.frombuffer(
            b, np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")]), n, 84
        )
        return rec["v"].astype(float)
    pts = [list(map(float, ln.split()[1:4])) for ln in b.decode().splitlines() if "vertex" in ln]
    return np.array(pts).reshape(-1, 3, 3)


def load_vendor(path: Path):
    """-> (triangles (n, 3, 3), vendor solid or None)."""
    suffix = path.suffix.lower()
    if suffix in (".step", ".stp"):
        from build123d import import_step

        shape = import_step(str(path))
        return tessellate(shape, 0.01), shape
    if suffix == ".stl":
        return load_stl(path), None
    return load_threejs_bin(path), None


def tessellate(shape, tol: float) -> np.ndarray:
    """Triangles of a B-rep shape, face by face. A vendor STEP can hold a face
    OCCT can't mesh; it is reported and left out rather than aborting."""
    out, failed = [], 0
    for f in shape.faces():
        try:
            verts, faces = f.tessellate(tol, 0.1)
        except AttributeError:
            failed += 1
            continue
        if faces:
            pts = np.array([(q.X, q.Y, q.Z) for q in verts])
            out.append(pts[np.array(faces)])
    if failed:
        print(f"  note: {failed} face(s) could not be meshed and are left out")
    return np.concatenate(out)


# --------------------------------------------------------------------------
# Distances, zones, transforms
# --------------------------------------------------------------------------
def point_triangle_distance(p: np.ndarray, tris: np.ndarray) -> np.ndarray:
    """Distance from each point (n, 3) to the nearest triangle of (m, 3, 3)."""
    chunk = max(1, 1_000_000 // len(tris))  # keeps the (4, chunk, m, 3) array small
    a, b, c = tris[:, 0], tris[:, 1], tris[:, 2]
    ab, ac = b - a, c - a
    out = np.empty(len(p))
    for i in range(0, len(p), chunk):
        q = p[i : i + chunk, None, :]  # (k, 1, 3)
        ap = q - a
        d1, d2 = (ab * ap).sum(-1), (ac * ap).sum(-1)
        bp = q - b
        d3, d4 = (ab * bp).sum(-1), (ac * bp).sum(-1)
        cp = q - c
        d5, d6 = (ab * cp).sum(-1), (ac * cp).sum(-1)
        va = d3 * d6 - d5 * d4
        vb = d5 * d2 - d1 * d6
        vc = d1 * d4 - d3 * d2
        denom = va + vb + vc
        denom = np.where(np.abs(denom) < 1e-18, 1e-18, denom)
        v, w = vb / denom, vc / denom
        closest = a + ab * v[..., None] + ac * w[..., None]  # interior
        # edge and vertex regions (Ericson, Real-Time Collision Detection 5.1.5)
        t_ab = np.clip(d1 / np.where(d1 - d3 == 0, 1e-18, d1 - d3), 0, 1)
        e_ab = a + ab * t_ab[..., None]
        t_ac = np.clip(d2 / np.where(d2 - d6 == 0, 1e-18, d2 - d6), 0, 1)
        e_ac = a + ac * t_ac[..., None]
        bc = c - b
        t_bc = np.clip(
            (d4 - d3) / np.where((d4 - d3) + (d5 - d6) == 0, 1e-18, (d4 - d3) + (d5 - d6)), 0, 1
        )
        e_bc = b + bc * t_bc[..., None]
        inside = (va >= 0) & (vb >= 0) & (vc >= 0)
        cand = np.stack([closest, e_ab, e_ac, e_bc])  # (4, k, m, 3)
        dist = np.linalg.norm(cand - q[None], axis=-1)
        dist[0] = np.where(inside, dist[0], np.inf)
        out[i : i + chunk] = dist.min(axis=0).min(axis=-1)
    return out


def distances_to_shapes(points: np.ndarray, shapes, progress: bool = False) -> np.ndarray:
    """Exact OCCT distance, pruning faces/edges by conservative bounding boxes.

    A box's distance is a lower bound on distance to its shape. Only shapes
    whose box could improve the current minimum need an OCCT query. This
    changes neither sampling nor acceptance thresholds.
    """
    from build123d import Vector

    shapes = list(shapes)
    boxes = [s.bounding_box() for s in shapes]
    low = np.array([tuple(b.min) for b in boxes]) - 1e-7
    high = np.array([tuple(b.max) for b in boxes]) + 1e-7
    distances = []
    for n, p in enumerate(points):
        lower = np.linalg.norm(np.maximum(np.maximum(low - p, p - high), 0), axis=1)
        best = float("inf")
        point = Vector(*p)
        for i in np.argsort(lower):
            if lower[i] > best:
                break
            best = min(best, shapes[i].distance_to(point))
            if best < 1e-9:
                break
        distances.append(best)
        if progress and (n + 1) % 5000 == 0:
            print(f"  {n + 1}/{len(points)} exact distances", flush=True)
    return np.array(distances)


def zone_of(pts: np.ndarray, zones: list[dict]) -> np.ndarray:
    """Index of the first zone each point (our frame) falls in; -1 = envelope."""
    idx = np.full(len(pts), -1)
    for k in range(len(zones) - 1, -1, -1):
        z = zones[k]
        if "box" in z:
            x0, x1, y0, y1, z0, z1 = z["box"]
            m = (
                (pts[:, 0] >= x0)
                & (pts[:, 0] <= x1)
                & (pts[:, 1] >= y0)
                & (pts[:, 1] <= y1)
                & (pts[:, 2] >= z0)
                & (pts[:, 2] <= z1)
            )
        else:
            ax, r0, r1, a0, a1 = z["cyl"]
            i = "xyz".index(ax)
            r = np.hypot(*(pts[:, j] for j in range(3) if j != i))
            m = (r >= r0) & (r <= r1) & (pts[:, i] >= a0) & (pts[:, i] <= a1)
        idx[m] = k
    return idx


def to_vendor_location(expr: str):
    from build123d import Location, Plane, Pos, Rot

    def plane(origin, x_dir, z_dir):  # our X, Z axes -> these vendor directions
        return Location(Plane(origin=origin, x_dir=x_dir, z_dir=z_dir))

    names = {"pos": Pos, "rot": Rot, "plane": plane}
    loc = eval(expr or "pos(0, 0, 0)", {"__builtins__": {}}, names)
    return loc if isinstance(loc, Location) else Location(loc)


def matrix(loc) -> np.ndarray:
    t = loc.wrapped.Transformation()
    m = np.eye(4)
    for i in range(3):
        for j in range(4):
            m[i, j] = t.Value(i + 1, j + 1)
    return m


def apply(m: np.ndarray, pts: np.ndarray) -> np.ndarray:
    return pts @ m[:3, :3].T + m[:3, 3]


def section(tris: np.ndarray, axis: int = 2, eps: float = 1e-4) -> np.ndarray:
    """Segments where triangles cross the plane coord[axis] = 0."""
    tris = tris.copy()
    tris[:, :, axis] += eps
    segs = []
    for t in tris:
        d = t[:, axis]
        pts = [
            t[i] + d[i] / (d[i] - d[(i + 1) % 3]) * (t[(i + 1) % 3] - t[i])
            for i in range(3)
            if (d[i] < 0) != (d[(i + 1) % 3] < 0)
        ]
        if len(pts) == 2:
            segs.append(pts)
    return np.array(segs)


def sharp_vertices(tris: np.ndarray, angle: float = SHARP_ANGLE) -> np.ndarray:
    """Vertices on the feature edges of a mesh: edges whose two triangles meet at
    more than `angle` degrees, or that border a single triangle."""
    pts, inv = np.unique(tris.reshape(-1, 3).round(6), axis=0, return_inverse=True)
    idx = inv.reshape(-1, 3)
    n = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
    faces_of: dict[tuple[int, int], list[int]] = {}
    for f, (a, b, c) in enumerate(idx):
        for e in ((a, b), (b, c), (c, a)):
            faces_of.setdefault((min(e), max(e)), []).append(f)
    cos = np.cos(np.radians(angle))
    sharp = set()
    for e, fs in faces_of.items():
        if len(fs) != 2 or n[fs[0]] @ n[fs[1]] < cos:
            sharp.update(e)
    return pts[sorted(sharp)]


def brep_feature_points(shape, per_edge: int = 9, angle: float = SHARP_ANGLE) -> np.ndarray:
    """Points along a B-rep's real feature edges: edges where two faces meet at
    more than `angle` degrees. Seams and splits between coplanar or tangent faces
    (a vendor face divided into rings for colour or marking) are not features.
    A seam is listed only once by `edges()`, so it is found by BRep_Tool.IsClosed."""
    from OCP.BRep import BRep_Tool
    from OCP.TopoDS import TopoDS

    faces_of: dict = {}
    for f in shape.faces():
        for e in f.edges():
            if BRep_Tool.IsClosed_s(TopoDS.Edge(e.wrapped), TopoDS.Face(f.wrapped)):
                faces_of[e] = [f, f]  # seam: the same face on both sides
                continue
            faces_of.setdefault(e, []).append(f)
    cos = np.cos(np.radians(angle))
    pts = []
    for e, fs in faces_of.items():
        mid = e.position_at(0.5)
        if len(fs) == 2 and not fs[0].is_same(fs[1]):
            n0, n1 = fs[0].normal_at(mid), fs[1].normal_at(mid)
            if n0.dot(n1) >= cos:
                continue  # smooth join: not a feature
        elif len(fs) == 2:
            continue  # seam: the same face on both sides
        pts += [tuple(e.position_at(u)) for u in np.linspace(0, 1, per_edge)]
    return np.array(pts).reshape(-1, 3)


def feature_edges(shape):
    """The shape's real edges as one compound: seam edges (where a closed face
    meets itself, e.g. along a cylinder) are left out, since they aren't features."""
    from build123d import Compound
    from OCP.BRep import BRep_Tool
    from OCP.TopoDS import TopoDS

    seams = [
        e
        for f in shape.faces()
        for e in f.edges()
        if BRep_Tool.IsClosed_s(TopoDS.Edge(e.wrapped), TopoDS.Face(f.wrapped))
    ]
    keep = [e for e in shape.edges() if not any(e.is_same(s) for s in seams)]
    return Compound(keep)


# --------------------------------------------------------------------------
# Presets: the bought-in parts of this repo
# --------------------------------------------------------------------------
def presets() -> dict[str, dict]:
    import flowmeter as FM
    import flowmeter_connector as FC
    import valve_connector as VC

    g12_r = FC.THREAD_MAJOR_D / 2 + 0.05
    h, x_sh = FM.L_TOTAL / 2, FM.L_TOTAL / 2 - FM.THREAD_L  # meter end face, shoulder
    r_bore, af = FM.END_BORE_D / 2, FM.SPANNER_AF / 2
    # QSF round body between hex and release ring, in the fitting frame (Z = L - v)
    round_z = (FC.L_TOTAL - FC.BODY_PROFILE[-1][1], FC.L_TOTAL - FC.BODY_PROFILE[2][1])
    return {
        "valve_connector": {
            "title": "SMC KQ2H12-U02A",
            "part": "valve_connector:make_fitting",
            "to_vendor": "rot(-90, 0, 0)",  # our +Z -> vendor +Y
            "section_axis": 2,
            "zones": [
                {
                    "name": "G1/4 thread, undercut and seal face",
                    "kind": "fit",
                    "cyl": ["z", 0, VC.THREAD_D / 2 + 0.05, -VC.THREAD_L - 0.01, 0.01],
                },
                {  # a flat face's mesh vertices are its corners: take the whole hex band
                    "name": "19 AF hex (spanner)",
                    "kind": "fit",
                    "cyl": ["z", VC.HEX_AF / 2 - 0.05, VC.HEX_AC / 2 + 0.05, *VC.HEX_FULL_Z],
                },
            ],
            "out": "valve_connector/cad_check.png",
        },
        "flowmeter_connector": {
            "title": "Festo QSF-1/2-12-B",
            "part": "flowmeter_connector:make_fitting",
            "to_vendor": f"pos(0, 0, {FC.L_TOTAL}) * rot(180, 0, 0)",
            "section_axis": 1,  # through the hex flats (vendor flats on +/-X)
            "zones": [
                {
                    "name": "female thread bore (vendor: minor dia, ours: major dia)",
                    "kind": "skip",
                    "cyl": [
                        "z",
                        FC.THREAD_MINOR_D / 2 - 0.02,
                        FC.THREAD_MINOR_D / 2 + 0.02,
                        0,
                        14.01,
                    ],
                },
                {
                    "name": "round body dia 20.8 (strap seat)",
                    "kind": "fit",
                    "cyl": ["z", FC.BODY_D / 2 - 0.05, FC.BODY_D / 2 + 0.05, *round_z],
                },
                {
                    "name": "24 AF hex (spanner)",
                    "kind": "fit",
                    "cyl": ["z", FC.HEX_AF / 2 - 0.05, FC.HEX_AC / 2 + 0.05, 0, round_z[0]],
                },
                {
                    "name": "port face",
                    "kind": "fit",
                    "box": [-15, 15, -15, 15, -0.01, 0.01],
                },
            ],
            "out": "flowmeter_connector/cad_check.png",
        },
        "flowmeter": {
            "title": "ifm SV3051 (vs ifm STEP CAD_STP_300_0358)",
            "part": "flowmeter:make_flowmeter",
            # ifm frame: length along X (centre 24.1), housing DOWN (-Y), pipe axis at
            # Y = 42.25 (= Z_TOP), inlet (M12 end) at X = -14.4: our X -> -X, our Z -> -Y
            "to_vendor": f"plane(({FM.L_TOTAL / 2 - 14.4}, {FM.Z_TOP}, 0), (-1, 0, 0), (0, -1, 0))",
            "section_axis": 2,
            # no skip zones: ifm models the G1/2 thread at its major dia, as we do
            "zones": [
                {  # the QSF seats on the shoulder; a seal on the end face / in the groove
                    "name": "G1/2 inlet end: shoulder, thread, lead-in, end face, groove",
                    "kind": "fit",
                    "cyl": ["x", r_bore + 0.05, g12_r, x_sh - 0.01, h + 0.01],
                },
                {
                    "name": "G1/2 outlet end: shoulder, thread, lead-in, end face, groove",
                    "kind": "fit",
                    "cyl": ["x", r_bore + 0.05, g12_r, -h - 0.01, -x_sh + 0.01],
                },
                {
                    "name": "inlet bore dia 11.5",
                    "kind": "fit",
                    "cyl": ["x", r_bore - 0.05, r_bore + 0.05, x_sh, h + 0.01],
                },
                {
                    "name": "16 AF spanner hex",
                    "kind": "fit",
                    "cyl": ["x", FM.SPANNER_HEX_AF / 2 - 0.05, 9.3, FM.SPANNER_X[0] - 0.01, x_sh],
                },
                {  # the clamp's locating pad sits on the downward flat
                    "name": "12 AF flats (locating pad)",
                    "kind": "fit",
                    "box": [FM.NECK_X - 0.01, x_sh, -6, 6, -af - 0.05, -af + 0.05],
                },
                {
                    "name": "12 AF flats, top",
                    "kind": "fit",
                    "box": [FM.NECK_X - 0.01, x_sh, -6, 6, af - 0.05, af + 0.05],
                },
            ],
            "out": "flowmeter/cad_check.png",
        },
    }


# --------------------------------------------------------------------------
# Compare
# --------------------------------------------------------------------------
def compare(spec: dict, vendor_path: Path, quiet: bool = False) -> dict:
    """Run the comparison; returns {zone name: (kind, n, max, mean, limit, ok)} and 'pass'."""
    import importlib

    from build123d import Compound

    mod, fn = spec["part"].split(":")
    ours = getattr(importlib.import_module(mod), fn)()
    to_v = to_vendor_location(spec.get("to_vendor", ""))
    m = matrix(to_v)
    m_inv = np.linalg.inv(m)
    fit_tol = spec.get("fit_tol", FIT_TOL)
    env_tol = spec.get("envelope_tol", ENVELOPE_TOL)
    zones = spec.get("zones", [])

    vendor_tris, vendor_solid = load_vendor(vendor_path)
    ours_v = to_v * ours  # our model in the vendor frame
    # distances are to the SURFACE: a solid reports 0 for any point inside it,
    # which would hide a vendor face lying inside our material (model too big)
    ours_skin = Compound(ours_v.faces())

    # vendor -> ours
    vv = np.unique(vendor_tris.reshape(-1, 3).round(6), axis=0)
    if len(vv) > MAX_POINTS:  # fixed seed: the same subset every run
        vv = vv[np.random.default_rng(0).choice(len(vv), MAX_POINTS, replace=False)]
    if not quiet:
        print(f"Comparing {len(vv)} vendor surface points...", flush=True)
    dev_v = distances_to_shapes(vv, ours_skin.faces())
    zone_v = zone_of(apply(m_inv, vv), zones)
    # A B-rep vendor model often carries internal detail (sockets, hollow housings,
    # bores) that an envelope model leaves solid. In envelope areas, vendor points
    # inside our solid are reported, not judged; material we have and the vendor
    # doesn't is still caught by ours -> vendor. Meshes are judged on every point.
    internal = np.zeros(len(vv), bool)
    if vendor_solid is not None:
        env = zone_v == -1
        from OCP.BRepClass3d import BRepClass3d_SolidClassifier
        from OCP.gp import gp_Pnt
        from OCP.TopAbs import TopAbs_IN

        classifier = BRepClass3d_SolidClassifier(ours_v.wrapped)

        def inside(q):
            classifier.Perform(gp_Pnt(*q), 1e-6)
            return classifier.State() == TopAbs_IN or classifier.IsOnAFace()

        internal[env] = [inside(q) for q in vv[env]]

    if not quiet:
        print("Comparing model surface points...", flush=True)
    # ours -> vendor
    our_tris = tessellate(ours_v, 0.01)
    ov = np.unique(our_tris.reshape(-1, 3).round(6), axis=0)
    if vendor_solid is not None:
        # Preserve the exact sampled points but compute distances in the part
        # frame: aligned boxes prune far more faces than an oblique STEP frame.
        vendor_skin = Compound(vendor_solid.moved(to_v.inverse()).faces())
        dev_o = distances_to_shapes(apply(m_inv, ov), vendor_skin.faces(), progress=not quiet)
    else:
        dev_o = point_triangle_distance(ov, vendor_tris)
    zone_o = zone_of(apply(m_inv, ov), zones)

    if not quiet:
        print(f"Compared {len(ov)} model points; checking feature edges...", flush=True)
    # feature edges (fit zones only): a mesh carries exact information only at its
    # vertices, which sit on its edges. A bore 0.05 too big leaves its edge vertices
    # on our end face (surface distance 0), but 0.05 from our bore's edge.
    if vendor_solid is not None:
        ve = brep_feature_points(vendor_solid)
    else:
        ve = sharp_vertices(vendor_tris)
    zone_e = zone_of(apply(m_inv, ve), zones)
    fit_keys = [k for k, z in enumerate(zones) if z["kind"] == "fit"]
    in_fit = np.isin(zone_e, fit_keys)
    our_edges = feature_edges(ours_v)
    dev_e = np.full(len(ve), np.nan)
    dev_e[in_fit] = distances_to_shapes(ve[in_fit], our_edges.edges())

    result, ok_all = {}, True
    names = [z["name"] for z in zones] + ["envelope (everything else)"]
    kinds = [z["kind"] for z in zones] + ["envelope"]
    for k, (name, kind) in enumerate(zip(names, kinds)):
        key = k if k < len(zones) else -1
        limit = fit_tol if kind == "fit" else env_tol if kind == "envelope" else None
        for direction, dev, sel, judged in (
            ("vendor->ours", dev_v, (zone_v == key) & ~internal, True),
            (
                "vendor->ours, internal detail not modelled",
                dev_v,
                (zone_v == key) & internal,
                False,
            ),
            ("ours->vendor", dev_o, zone_o == key, vendor_solid is not None),
            ("vendor edges->our edges", dev_e, (zone_e == key) & in_fit, True),
        ):
            d = dev[sel]
            if not len(d):
                continue
            ok = limit is None or not judged or d.max() <= limit
            ok_all &= ok
            result[f"{name} [{direction}]"] = (kind, len(d), d.max(), d.mean(), limit, ok, judged)

    if not quiet:
        print(f"{spec['title']}: {len(vv)} vendor vertices, {len(ov)} model vertices")
        for key, (kind, n, mx, mean, limit, ok, judged) in result.items():
            verdict = "skip" if limit is None else ("PASS" if ok else "FAIL")
            verdict = verdict if judged else "info"
            lim = "" if limit is None else f" (limit {limit})"
            print(f"  [{verdict:4}] {kind:8} {key:<62} n={n:<6} max {mx:.3f} mean {mean:.4f}{lim}")
        print("RESULT:", "PASS" if ok_all else "FAIL")
    result["pass"] = bool(ok_all)
    if spec.get("out"):
        plot(spec, vendor_tris, our_tris, result, ROOT / spec["out"], ok_all)
    return result


def plot(spec, vendor_tris, our_tris, result, out: Path, ok_all: bool) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    axis = spec.get("section_axis", 2)
    keep = [i for i in range(3) if i != axis]
    fig, ax = plt.subplots(figsize=(7, 8))
    for s in section(vendor_tris, axis):
        ax.plot(s[:, keep[0]], s[:, keep[1]], "r-", lw=4, alpha=0.45)
    for s in section(our_tris, axis):
        ax.plot(s[:, keep[0]], s[:, keep[1]], "b-", lw=1)
    ax.plot([], [], "r-", lw=4, alpha=0.45, label="vendor 3D model")
    ax.plot([], [], "b-", label=spec["part"].split(":")[0] + ".py")
    lines = [
        f"{k.split(' [')[0][:38]} {k.split('[')[1][:-1]}: max {v[2]:.3f}"
        + ("" if v[4] is None else f" / {v[4]}")
        for k, v in result.items()
        if k != "pass" and v[6]
    ]
    ax.set_title(
        f"{spec['title']} - section, {'PASS' if ok_all else 'FAIL'}\n" + "\n".join(lines[:6]),
        fontsize=8,
    )
    ax.set_aspect("equal")
    ax.grid(alpha=0.3)
    ax.legend(loc="lower right")
    ax.set_xlabel("mm (vendor frame)")
    fig.savefig(out, dpi=110, bbox_inches="tight")
    plt.close(fig)
    print(f"  saved {out.relative_to(ROOT)}")


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        sys.exit(__doc__)
    name, vendor = argv[1], Path(argv[2])
    spec = json.loads(Path(name).read_text()) if name.endswith(".json") else presets()[name]
    return 0 if compare(spec, vendor)["pass"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
