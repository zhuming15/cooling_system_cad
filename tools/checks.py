"""Reusable design checks for build123d assemblies.

Every function here is independent of this station: it takes solids and
numbers, never part names or station constants. A design's own check script
(`assembly.py` here) decides what to check and with which limits, and reports
through `Report`. The pytest suite (`tests/`) unit-tests every function,
including that each one detects a deliberately bad geometry.

Groups
  Report                       PASS/FAIL/INFO lines, failure count
  geometry                     overlap, interferences, axis_probe, ray_clear, sweep,
                               is_straight_tube, rotation_envelope
  manufacturing                overhangs, wall_measurement, min_wall, is_flat_profile, max_extent
  tolerance                    worst_case, rss, monte_carlo
  mechanics                    preload, annulus_area, hex_bearing_area,
                               fixed_fixed_strain, thermal_growth, end_thrust,
                               tip_factor, wall_screw_load

Units are mm, N, N.m, MPa, K, kg.
"""

from __future__ import annotations

import itertools
import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

import numpy as np
from build123d import Align, Box, Compound, Cylinder, Location, Plane, Pos, Solid, Vector

VOLUME_TOL = 1e-3  # mm³: existing interference acceptance threshold
GEOMETRY_EPS = 1e-7  # mm: conservative padding for OCCT bounding boxes


def _bounds(shape):
    box = shape.bounding_box()
    return tuple(box.min), tuple(box.max)


def _boxes_meet(a, b):
    """Inclusive intersection: build123d BoundBox.overlaps excludes containment."""
    return all(
        a[1][i] >= b[0][i] - GEOMETRY_EPS and b[1][i] >= a[0][i] - GEOMETRY_EPS for i in range(3)
    )


def _common_volume(a, b):
    common = a & b
    return sum(s.volume for s in common.solids()) if common else 0.0


# --------------------------------------------------------------------------
# Report
# --------------------------------------------------------------------------
class Report:
    """Collects check results; prints one line per check as it runs."""

    def __init__(self, echo: bool = True) -> None:
        self.fails = 0
        self.echo = echo
        self.section = ""
        self.results: list[tuple[str, str, bool, str]] = []  # (section, name, ok, detail)

    def start(self, title: str) -> None:
        self.section = title
        if self.echo:
            print(f"\n{title}")

    def check(self, name: str, ok: bool, detail: str) -> None:
        ok = bool(ok)
        self.fails += not ok
        self.results.append((self.section, name, ok, detail))
        if self.echo:
            print(f"  [{'PASS' if ok else 'FAIL'}] {name:<46} {detail}")

    def info(self, text: str) -> None:
        if self.echo:
            print(f"  [INFO] {text}")

    def failed(self) -> list[tuple[str, str, bool, str]]:
        return [x for x in self.results if not x[2]]


# --------------------------------------------------------------------------
# Geometry
# --------------------------------------------------------------------------
def overlap(a: Solid, b: Solid) -> float:
    """Volume (mm3) shared by two solids; 0 when their boxes don't meet."""
    if not _boxes_meet(_bounds(a), _bounds(b)):
        return 0.0
    return _common_volume(a, b)


def interferences(parts: dict[str, Solid], tol: float = 1e-3) -> list[tuple[float, str, str]]:
    """Every pair of parts sharing more than `tol` mm3: [(volume, name_a, name_b)]."""
    # Invocation-local snapshot; no global cache can survive a geometry edit.
    bounds = {n: _bounds(s) for n, s in parts.items()}
    out = []
    for (na, a), (nb, b) in itertools.combinations(parts.items(), 2):
        if not _boxes_meet(bounds[na], bounds[nb]):
            continue
        v = _common_volume(a, b)
        if v > tol:
            out.append((v, na, nb))
    return out


def axis_probe(
    d: float, start: Sequence[float], direction: Sequence[float], length: float
) -> Solid:
    """Cylinder of diameter `d` from `start` along `direction` (a tool or finger path)."""
    plane = Plane(origin=tuple(start), z_dir=tuple(direction))
    return Location(plane) * Cylinder(d / 2, length, align=(Align.CENTER, Align.CENTER, Align.MIN))


def is_straight_tube(
    solid: Solid,
    start: Sequence[float],
    end: Sequence[float],
    od: float,
    id_: float,
    tolerance: float = 1e-3,
) -> bool:
    """Verify an intact annular extrusion from its B-rep, not its bounding box.

    Require one valid solid, two full coaxial cylinders of the specified radii
    and length, and two planar annular ends at the independently supplied datums.
    Extra cuts, blocked bores, bends and disconnected pieces therefore fail.
    """
    from OCP.BRepAdaptor import BRepAdaptor_Surface

    p, q = np.array(start, float), np.array(end, float)
    length = float(np.linalg.norm(q - p))
    if length <= tolerance or not 0 < id_ < od or not solid.is_valid:
        return False
    axis = (q - p) / length
    faces = solid.faces()
    if len(solid.solids()) != 1 or len(faces) != 4:
        return False
    radii, ends = [], []
    for face in faces:
        surface = BRepAdaptor_Surface(face.wrapped)
        if face.geom_type.name == "CYLINDER":
            cylinder = surface.Cylinder()
            direction = np.array(cylinder.Axis().Direction().Coord())
            origin = np.array(cylinder.Axis().Location().Coord())
            radius = cylinder.Radius()
            if (
                np.linalg.norm(np.cross(direction, axis)) > tolerance / length
                or np.linalg.norm(np.cross(origin - p, axis)) > tolerance
                or abs(face.area - 2 * math.pi * radius * length) > 2 * math.pi * radius * tolerance
            ):
                return False
            radii.append(radius)
        elif face.geom_type.name == "PLANE":
            normal = np.array(surface.Plane().Axis().Direction().Coord())
            if np.linalg.norm(np.cross(normal, axis)) > tolerance / length:
                return False
            ends.append(float(np.dot(np.array(surface.Plane().Location().Coord()) - p, axis)))
        else:
            return False
    return (
        len(radii) == len(ends) == 2
        and np.allclose(sorted(radii), (id_ / 2, od / 2), atol=tolerance, rtol=0)
        and np.allclose(sorted(ends), (0, length), atol=tolerance, rtol=0)
        and abs(solid.volume - math.pi / 4 * (od**2 - id_**2) * length)
        <= math.pi * od * length * tolerance
    )


def rotation_envelope(solid: Solid, origin: Sequence[float], axis: Sequence[float]) -> Compound:
    """Conservative solid envelope for every angle of rotation about an axis.

    Fill the radial extent of each face over its axial bounding interval.
    Coaxial cylindrical/conical/toroidal faces retain their analytic radius;
    other faces use the conservative radial corner of their bounding box.
    The union covers all cross-sections of a closed solid, including angles
    between samples. Individual cylinders are kept as a compound: overlapping
    envelope volumes may over-report a clash, never conceal one.
    """
    from OCP.BRepAdaptor import BRepAdaptor_Surface

    frame = Location(Plane(origin=tuple(origin), z_dir=tuple(axis)))
    local = frame.inverse() * solid
    pieces = []
    for face in local.faces():
        bb = face.bounding_box()
        if bb.size.Z <= 1e-9:
            continue
        radius = math.hypot(max(abs(bb.min.X), abs(bb.max.X)), max(abs(bb.min.Y), abs(bb.max.Y)))
        surface = BRepAdaptor_Surface(face.wrapped)
        kind = face.geom_type.name
        if kind == "PLANE":
            plane = surface.Plane()
            normal = plane.Axis().Direction()
            # An axial hex flat projects to a line, not the entire radial
            # bounding rectangle. Intersect that line with the rectangle to
            # retain its exact corner radius while remaining conservative.
            if abs(normal.Z()) < 1e-12:
                nx, ny = normal.X(), normal.Y()
                centre = plane.Location()
                value = nx * centre.X() + ny * centre.Y()
                corners = []
                if abs(ny) > 1e-12:
                    corners += [(x, (value - nx * x) / ny) for x in (bb.min.X, bb.max.X)]
                if abs(nx) > 1e-12:
                    corners += [((value - ny * y) / nx, y) for y in (bb.min.Y, bb.max.Y)]
                corners = [
                    (x, y)
                    for x, y in corners
                    if bb.min.X - GEOMETRY_EPS <= x <= bb.max.X + GEOMETRY_EPS
                    and bb.min.Y - GEOMETRY_EPS <= y <= bb.max.Y + GEOMETRY_EPS
                ]
                if corners:
                    radius = max(math.hypot(x, y) for x, y in corners)
        analytic = {"CYLINDER": "Cylinder", "CONE": "Cone", "TORUS": "Torus"}
        if kind in analytic:
            geom = getattr(surface, analytic[kind])()
            direction = geom.Axis().Direction()
            centre = geom.Location()
            if math.hypot(direction.X(), direction.Y()) < 1e-12:
                eccentricity = math.hypot(centre.X(), centre.Y())
                eccentricity += max(abs(z - centre.Z()) for z in (bb.min.Z, bb.max.Z)) * (
                    math.hypot(direction.X(), direction.Y()) / abs(direction.Z())
                )
                if kind == "CYLINDER":
                    radius = geom.Radius() + eccentricity
                elif kind == "CONE":
                    radius = (
                        max(
                            abs(
                                geom.RefRadius()
                                + (z - centre.Z()) / direction.Z() * math.tan(geom.SemiAngle())
                            )
                            for z in (bb.min.Z, bb.max.Z)
                        )
                        + eccentricity
                    )
                else:
                    radius = geom.MajorRadius() + geom.MinorRadius() + eccentricity
        pieces.append(
            Pos(0, 0, bb.min.Z)
            * Cylinder(radius, bb.size.Z, align=(Align.CENTER, Align.CENTER, Align.MIN))
        )
    if not pieces:
        raise ValueError("rotation envelope needs a nonempty solid")
    return frame * Compound(pieces)


def ray_clear(parts: dict[str, Solid], probe: Solid, ignore: Iterable[str] = ()) -> list[str]:
    """Names of the parts (other than `ignore`) that the probe solid hits."""
    ignore = set(ignore)
    pb = _bounds(probe)
    return [
        n
        for n, p in parts.items()
        if n not in ignore and _boxes_meet(_bounds(p), pb) and _common_volume(p, probe) > VOLUME_TOL
    ]


def _linear_envelope(solid, direction, travel):
    """Exact swept occupancy for planar solids with axial cylindrical walls.

    Such a solid can enter new material only through a non-tangential planar
    face. Extrude those faces and include the two endpoint solids. Other
    surface types return None so the adaptive general checker remains in use.
    """
    from OCP.BRepAdaptor import BRepAdaptor_Surface

    faces = solid.faces()
    for face in faces:
        if face.geom_type.name == "PLANE":
            continue
        if face.geom_type.name != "CYLINDER":
            return None
        axis = BRepAdaptor_Surface(face.wrapped).Cylinder().Axis().Direction().Coord()
        if math.hypot(*np.cross(axis, direction)) > 1e-10:
            return None
    delta = Vector(*(v * travel for v in direction))
    pieces = [solid, Pos(*delta) * solid]
    for face in faces:
        if face.geom_type.name == "PLANE" and abs(face.normal_at().dot(Vector(*direction))) > 1e-10:
            pieces.append(Solid.extrude(face, delta))
    return Compound(pieces)


def _slab_motion_clear(a, b, axis, travel):
    """Certify sliding tangencies using conservative bounds of exact CAD slices.

    Slice both solids at their feature vertices perpendicular to a coordinate
    with no motion. Slices cannot exchange material along that coordinate.
    The sum of swept-box intersection volumes bounds collision volume at every
    time, even for a flat sliding on a ledge inside a much larger bounding box.
    Failure to prove clearance simply falls back to adaptive distance checks.
    """
    ab, bb = _bounds(a), _bounds(b)
    for coordinate, velocity in enumerate(axis):
        if abs(velocity) > 1e-12:
            continue
        low = max(ab[0][coordinate], bb[0][coordinate])
        high = min(ab[1][coordinate], bb[1][coordinate])
        if high <= low:
            return True
        cuts = sorted(
            {low, high}
            | {
                tuple(v.center())[coordinate]
                for s in (a, b)
                for v in s.vertices()
                if low < tuple(v.center())[coordinate] < high
            }
        )
        # Coalesce near-coincident feature planes into larger conservative
        # slabs; OCCT cannot construct boxes thinner than its modelling tolerance.
        merged = [low]
        for cut in cuts[1:-1]:
            if cut - merged[-1] > 1e-5 and high - cut > 1e-5:
                merged.append(cut)
        cuts = merged + [high]
        if len(cuts) > 64:
            continue
        bound = 0.0
        for lo, hi in itertools.pairwise(cuts):
            if hi - lo < 1e-6:
                # Do not omit a thin region from the volume bound.
                bound = math.inf
                break
            pieces = []
            for solid, bounds in ((a, ab), (b, bb)):
                mins = [v - 1 for v in bounds[0]]
                maxs = [v + 1 for v in bounds[1]]
                mins[coordinate], maxs[coordinate] = lo, hi
                clip = Pos(*((x + y) / 2 for x, y in zip(mins, maxs))) * Box(
                    *(y - x for x, y in zip(mins, maxs))
                )
                piece = solid & clip
                pieces.append(_bounds(piece) if piece and piece.solids() else None)
            if any(p is None for p in pieces):
                continue
            (al, ah), (bl, bh) = pieces
            bound += math.prod(
                max(
                    0.0,
                    min(ah[i] + max(0, -axis[i] * travel), bh[i])
                    - max(al[i] + min(0, -axis[i] * travel), bl[i]),
                )
                for i in range(3)
            )
            if bound > VOLUME_TOL:
                break
        if bound <= VOLUME_TOL:
            return True
    return False


class SweepHits(dict):
    """Collision witnesses; unresolved intervals are explicit, failing evidence."""

    def __init__(self):
        super().__init__()
        self.unresolved = set()

    def __repr__(self):
        return super().__repr__() + (
            f"; uncertified: {sorted(self.unresolved)}" if self.unresolved else ""
        )


def sweep(
    parts: dict[str, Solid],
    moving: Sequence[str],
    installed: Sequence[str],
    axis: Sequence[float] = (0.0, -1.0, 0.0),
    travel: float = 60.0,
    step: float = 1.0,
    *,
    max_evaluations: int = 2048,
) -> dict[tuple[str, str], float]:
    """Certify linear insertion, including both endpoints and between samples.

    `axis` is a unit direction; `step` is the initial interval width, not a
    collision sampling resolution. Swept boxes reject distant intervals. A
    midpoint separation greater than half the interval certifies the interval
    by the distance Lipschitz bound. Near contact, intersection volume can grow
    by at most surface area times translation distance (finite-perimeter bound).
    Otherwise subdivide. Contacts above VOLUME_TOL, or intervals that cannot be
    certified within 2048 subdivisions per pair, are returned as failures.

    Returns {(moving, installed): witness/uncertified distance from home}; this
    is deliberately not a claim of an exact first-contact position. No global
    shape cache is retained between calls.
    """
    if not math.isfinite(travel) or travel < 0 or not math.isfinite(step) or step <= 0:
        raise ValueError("travel must be finite and nonnegative; step must be positive")
    axis = tuple(float(v) for v in axis)
    if len(axis) != 3 or not math.isclose(math.hypot(*axis), 1.0, abs_tol=1e-9):
        raise ValueError("axis must be a finite unit vector")
    bounds = {n: _bounds(parts[n]) for n in set(moving) | set(installed)}
    areas = {}
    envelopes = {}
    hits = SweepHits()
    for m in moving:
        low, high = bounds[m]
        for n in installed:

            def swept_box(lo, hi, low=low, high=high):
                return (
                    tuple(low[i] + min(-axis[i] * lo, -axis[i] * hi) for i in range(3)),
                    tuple(high[i] + max(-axis[i] * lo, -axis[i] * hi) for i in range(3)),
                )

            if not _boxes_meet(swept_box(0, travel), bounds[n]):
                continue
            if travel > 0:
                # Axial hardware and tubes can have long sliding contacts or
                # tiny running clearances. Their exact swept occupancy is both
                # stronger and much cheaper than distance-based subdivision.
                if m not in envelopes:
                    envelopes[m] = _linear_envelope(parts[m], tuple(-v for v in axis), travel)
                envelope = envelopes[m]
                if envelope is not None and overlap(envelope, parts[n]) <= VOLUME_TOL:
                    continue
                # Sweeping the fixed object in the opposite relative direction
                # describes the same set of collisions.
                if n not in envelopes:
                    envelopes[n] = _linear_envelope(parts[n], axis, travel)
                envelope = envelopes[n]
                if envelope is not None and overlap(envelope, parts[m]) <= VOLUME_TOL:
                    continue
            # Include the seated position; static interference remains a separate
            # station check, but the generic motion checker must also cover it.
            intervals = [(max(0.0, d - step), d) for d in np.arange(travel, 0, -step)][::-1] or [
                (0.0, 0.0)
            ]
            queries = 0
            while intervals:
                lo, hi = intervals.pop()
                sb = swept_box(lo, hi)
                # The intersection of swept AABBs also bounds intersection
                # volume. In particular, planar sliding/touching is certified
                # without subdividing an entire zero-clearance contact path.
                box_volume = math.prod(
                    max(0.0, min(sb[1][i], bounds[n][1][i]) - max(sb[0][i], bounds[n][0][i]))
                    for i in range(3)
                )
                if box_volume <= VOLUME_TOL:
                    continue
                mid, radius = (lo + hi) / 2, (hi - lo) / 2
                if queries >= max_evaluations:
                    # Fail closed: never turn an unresolved near-contact motion
                    # into a clear path merely because an evaluation budget ran out.
                    hits[(m, n)] = mid
                    hits.unresolved.add((m, n))
                    break
                queries += 1
                if queries == 64 and _slab_motion_clear(parts[m], parts[n], axis, travel):
                    break
                moved = Pos(*(-v * mid for v in axis)) * parts[m]
                distance = moved.distance_to(parts[n])
                if distance > radius + GEOMETRY_EPS:
                    continue
                volume = 0.0 if distance > GEOMETRY_EPS else _common_volume(moved, parts[n])
                if volume > VOLUME_TOL:
                    hits[(m, n)] = mid
                    break
                if m not in areas:
                    areas[m] = parts[m].area
                if volume + areas[m] * radius <= VOLUME_TOL:
                    continue
                intervals.extend(((lo, mid), (mid, hi)))
    return hits


# --------------------------------------------------------------------------
# Manufacturing
# --------------------------------------------------------------------------
def overhangs(
    solid: Solid, build: Sequence[float], hole_self_support_r: float = 5.0
) -> tuple[list[float], list[str]]:
    """Printing without support, with `build` the print (up) direction.

    Returns (bridge spans, unsupported faces). A bridge is a flat down-facing
    face above the bed; its span is its smaller width. Any other face steeper
    than 45 deg downward is reported, except cylinders up to
    `hole_self_support_r`, which print as self-supporting holes.
    """
    b = np.array(build, float)
    bed = min(float(np.dot(b, (v.X, v.Y, v.Z))) for v in solid.vertices())
    spans, bad = [], []
    for f in solid.faces():
        verts, tris = f.tessellate(0.05, 0.3)
        if not tris:
            continue
        pts = np.array([(v.X, v.Y, v.Z) for v in verts])
        t = np.array(tris)
        n = np.cross(pts[t[:, 1]] - pts[t[:, 0]], pts[t[:, 2]] - pts[t[:, 0]])
        n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
        on = f.normal_at(f.center())
        on = np.array((on.X, on.Y, on.Z))
        n *= 1 if np.dot(n.mean(0), on) >= 0 else -1
        height = pts[t].mean(1) @ b - bed
        down = (n @ b < -0.7071) & (height > 0.05)
        if not down.any():
            continue
        if f.geom_type.name == "PLANE" and abs(np.dot(on, b) + 1) < 1e-6:
            bb = f.bounding_box()
            ext = [e for e, a in zip((bb.size.X, bb.size.Y, bb.size.Z), b) if abs(a) < 0.5]
            spans.append(min(ext))
        elif not (f.geom_type.name == "CYLINDER" and f.radius <= hole_self_support_r):
            bad.append(f"{f.geom_type.name.lower()} at {tuple(round(c, 1) for c in f.center())}")
    return spans, bad


@dataclass(frozen=True)
class WallMeasurement:
    """Sampling evidence, not a certified global minimum thickness."""

    minimum: float
    rays: int
    hits: int
    measured_faces: int
    faces: int


def wall_measurement(solid: Solid, per_face: int = 150) -> WallMeasurement:
    """Estimate thickness and expose coverage; reject absent measurements.

    Keep the existing seeded surface samples and add each face's tessellated
    triangle centroid nearest its centre to probe face interiors as well as
    edges. This is still a sampled estimate, requiring physical confirmation.
    """
    from OCP.BRepClass3d import BRepClass3d_SolidClassifier
    from OCP.gp import gp_Dir, gp_Lin, gp_Pnt
    from OCP.IntCurvesFace import IntCurvesFace_ShapeIntersector
    from OCP.TopAbs import TopAbs_IN

    if per_face <= 0 or not solid.solids():
        raise ValueError("wall measurement needs a solid and positive sample budget")
    inter = IntCurvesFace_ShapeIntersector()
    inter.Load(solid.wrapped, 1e-6)
    rng, worst = np.random.default_rng(0), math.inf
    rays, hits, measured_faces = 0, 0, 0
    for f in solid.faces():
        verts, triangles = f.tessellate(0.2, 0.5)
        pts = np.array([(v.X, v.Y, v.Z) for v in verts])  # vertices lie on the surface
        if len(pts) > per_face:
            pts = pts[rng.choice(len(pts), per_face, replace=False)]
        # A planar triangle centroid is on the surface; curved triangle
        # centroids are chord points and must not be treated as surface points.
        if triangles and f.geom_type.name == "PLANE":
            mesh = np.array([(v.X, v.Y, v.Z) for v in verts])
            centres = mesh[np.array(triangles)].mean(axis=1)
            centre = np.array(tuple(f.center()))
            pts = np.vstack((pts, centres[np.linalg.norm(centres - centre, axis=1).argmin()]))
        elif f.geom_type.name in ("CYLINDER", "CONE", "TORUS", "SPHERE"):
            # Parametric evaluation lies on the exact curved surface; unlike
            # triangle centroids these points are not inside tessellation chords.
            exact = [f.position_at(u, v) for u in (0.25, 0.5, 0.75) for v in (0.25, 0.5, 0.75)]
            exact = [tuple(p) for p in exact if f.is_inside(p)]
            if exact:
                pts = np.vstack((pts, exact))
        face_hits = 0
        for c in pts:
            rays += 1
            nv = f.normal_at(Vector(*c))
            d = -np.array((nv.X, nv.Y, nv.Z))
            probe = BRepClass3d_SolidClassifier(solid.wrapped, gp_Pnt(*(c + 0.01 * d)), 1e-7)
            if probe.State() != TopAbs_IN:
                d = -d
                probe.Perform(gp_Pnt(*(c + 0.01 * d)), 1e-7)
                if probe.State() != TopAbs_IN:
                    continue
            p0 = c + 1e-4 * d
            inter.Perform(gp_Lin(gp_Pnt(*p0), gp_Dir(*d)), 0.0, 1e3)
            ws = [inter.WParameter(i) for i in range(1, inter.NbPnt() + 1)]
            ws = [w for w in ws if w > 5e-3]
            if ws:
                worst = min(worst, min(ws))
                hits += 1
                face_hits += 1
        measured_faces += face_hits > 0
    if not hits or measured_faces != len(solid.faces()):
        raise ValueError(
            f"incomplete wall measurement: {measured_faces}/{len(solid.faces())} "
            f"faces, {hits}/{rays} rays returned thickness"
        )
    return WallMeasurement(worst, rays, hits, measured_faces, len(solid.faces()))


def min_wall(solid: Solid, per_face: int = 150) -> float:
    """Sampled thickness estimate in mm; raises when coverage is incomplete."""
    return wall_measurement(solid, per_face).minimum


def is_flat_profile(solid: Solid, thickness: float, axis: int = 1) -> bool:
    """True for a laser/waterjet part: `thickness` thick along `axis`, its only
    faces the two sheet faces and walls square to the sheet (outline and
    through-holes). A ledge inside the sheet (counterbore, pocket) or a slope
    across it fails."""
    bb = solid.bounding_box()
    lo, hi = (bb.min.X, bb.min.Y, bb.min.Z)[axis], (bb.max.X, bb.max.Y, bb.max.Z)[axis]
    if abs(hi - lo - thickness) > 1e-6:
        return False
    for f in solid.faces():
        n = f.normal_at()
        c = (n.X, n.Y, n.Z)[axis]
        at = (f.center().X, f.center().Y, f.center().Z)[axis]
        sheet = (
            f.geom_type.name == "PLANE"
            and abs(abs(c) - 1) < 1e-6
            and min(abs(at - lo), abs(at - hi)) < 1e-6
        )
        if not (sheet or abs(c) < 1e-6):
            return False
    return True


def max_extent(solid: Solid, axes: Sequence[int] = (0, 1, 2)) -> float:
    """Largest bounding-box size over the given axes (printer bed / sheet fit)."""
    s = solid.bounding_box().size
    return max((s.X, s.Y, s.Z)[a] for a in axes)


# --------------------------------------------------------------------------
# Tolerance stacks. A term is (half range, sign): +/-t entering the stack with
# that sign. The three methods are the usual industrial set: worst case (sure,
# pessimistic), RSS (quick statistical, assumes normal parts centred in their
# tolerance) and Monte Carlo (statistical; uniform here, which is more
# pessimistic than RSS's normal assumption, so it lands between the two).
# --------------------------------------------------------------------------
def worst_case(terms: Iterable[tuple[float, int]]) -> float:
    return float(sum(abs(t) for t, _ in terms))


def rss(terms: Iterable[tuple[float, int]]) -> float:
    """Classic root sum square: each +/-t is taken as +/-3 sigma of a normal
    distribution, so the result is the 3 sigma stack. Never above worst case."""
    return math.sqrt(sum(t * t for t, _ in terms))


def monte_carlo(
    axes: Sequence[Sequence[tuple[float, int]]],
    n: int = 200_000,
    seed: int = 1,
    percentile: float = 99.73,
) -> float:
    """Radial offset at `percentile` for independent uniform terms on 1-3 axes.

    Draws are made axis by axis, term by term, in the order given, so a fixed
    seed gives the same result every run.
    """
    rng = np.random.default_rng(seed)
    totals = []
    for terms in axes:
        s = np.zeros(n)
        for t, sign in terms:
            s = s + sign * rng.uniform(-t, t, n)
        totals.append(s)
    radial = np.sqrt(sum(s * s for s in totals))
    return float(np.percentile(radial, percentile))


# --------------------------------------------------------------------------
# Mechanics (hand calculations; each states its model)
# --------------------------------------------------------------------------
def preload(torque: float, d: float, k: float = 0.2) -> float:
    """Screw preload (N) from torque (N.m): T = K F d, K the nut factor."""
    return torque * 1000 / (k * d)


def annulus_area(od: float, id_: float) -> float:
    return math.pi / 4 * (od**2 - id_**2)


def hex_bearing_area(af: float, hole_d: float) -> float:
    """Bearing face of a hex nut (across flats `af`) around a clearance hole."""
    return 3**0.5 / 2 * af**2 - math.pi / 4 * hole_d**2


def fixed_fixed_strain(od: float, offset: float, length: float) -> float:
    """Peak bending strain of a tube clamped at both ends with ends offset
    sideways by `offset` over the free `length`: 3 * OD * offset / L^2."""
    return 3 * od * offset / length**2


def thermal_growth(dt: float, members: Iterable[tuple[float, float]]) -> float:
    """Length change (mm) of members [(CTE 1/K, length mm)] for a dT (K)."""
    return dt * sum(cte * length for cte, length in members)


def end_thrust(pressure: float, d: float) -> float:
    """Axial force (N) of `pressure` (MPa) on a capped end of diameter `d`."""
    return pressure * math.pi / 4 * d**2


def tip_factor(
    screw_preload: float, screw_xs: Iterable[float], edges: Iterable[float], moment: float
) -> float:
    """Safety factor against a base tipping about either edge.

    The resisting moment is each screw's preload times its lever from the
    pivot edge; `moment` (N.m) is the overturning moment. Returns the smaller
    factor of the two edges.
    """
    xs = list(screw_xs)
    return min(screw_preload * sum(abs(e - x) for x in xs) / 1000 / moment for e in edges)


def wall_screw_load(
    weight: float, pull: float, lever: float, span: float, n: int
) -> tuple[float, float, float]:
    """Per-screw load for a plate on the wall: a pull (N) along the wall at
    `lever` mm from it turns the plate; the outer screws, `span` mm apart, take
    the moment in tension, all `n` share the shear of weight and pull.
    Returns (combined, tension, shear) in N."""
    tension = pull * lever / 1000 / (span / 1000) / 2
    shear = (weight**2 + pull**2) ** 0.5 / n
    return (tension**2 + shear**2) ** 0.5, tension, shear
