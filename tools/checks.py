"""Reusable design checks for build123d assemblies.

Every function here is independent of this station: it takes solids and
numbers, never part names or station constants. A design's own check script
(`assembly.py` here) decides what to check and with which limits, and reports
through `Report`. The pytest suite (`tests/`) unit-tests every function,
including that each one detects a deliberately bad geometry.

Groups
  Report                       PASS/FAIL/INFO lines, failure count
  geometry                     overlap, interferences, axis_probe, ray_clear, sweep
  manufacturing                overhangs, min_wall, is_flat_profile, max_extent
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

import numpy as np
from build123d import Align, Cylinder, Location, Plane, Pos, Solid, Vector


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
    if not a.bounding_box().overlaps(b.bounding_box()):
        return 0.0
    common = a & b
    return sum(s.volume for s in common.solids()) if common else 0.0


def interferences(parts: dict[str, Solid], tol: float = 1e-3) -> list[tuple[float, str, str]]:
    """Every pair of parts sharing more than `tol` mm3: [(volume, name_a, name_b)]."""
    out = []
    for (na, a), (nb, b) in itertools.combinations(parts.items(), 2):
        v = overlap(a, b)
        if v > tol:
            out.append((v, na, nb))
    return out


def axis_probe(
    d: float, start: Sequence[float], direction: Sequence[float], length: float
) -> Solid:
    """Cylinder of diameter `d` from `start` along `direction` (a tool or finger path)."""
    plane = Plane(origin=tuple(start), z_dir=tuple(direction))
    return Location(plane) * Cylinder(d / 2, length, align=(Align.CENTER, Align.CENTER, Align.MIN))


def ray_clear(parts: dict[str, Solid], probe: Solid, ignore: Iterable[str] = ()) -> list[str]:
    """Names of the parts (other than `ignore`) that the probe solid hits."""
    ignore = set(ignore)
    return [n for n, p in parts.items() if n not in ignore and overlap(p, probe) > 1e-3]


def sweep(
    parts: dict[str, Solid],
    moving: Sequence[str],
    installed: Sequence[str],
    axis: Sequence[float] = (0.0, -1.0, 0.0),
    travel: float = 60.0,
    step: float = 1.0,
) -> dict[tuple[str, str], float]:
    """Move `moving` into its final place along `axis`, from `travel` mm out.

    Returns {(moving part, installed part): distance from home at first contact}.
    Empty means that assembly step goes in without a collision.
    """
    # A translated box has exactly the translated bounds. Cache these once:
    # rebuilding OCCT boxes for every pair at every step dominates detailed
    # connector sweeps. Potential contacts still use the same solid Boolean,
    # sampling positions and volume threshold below.
    bounds = {
        n: (tuple(parts[n].bounding_box().min), tuple(parts[n].bounding_box().max))
        for n in set(moving) | set(installed)
    }
    hits, d = {}, travel
    while d > 1e-9:
        off = Pos(-axis[0] * d, -axis[1] * d, -axis[2] * d)
        for m in moving:
            low, high = bounds[m]
            shift = tuple(-v * d for v in axis)
            sm = None
            for n in installed:
                nl, nh = bounds[n]
                if any(
                    high[i] + shift[i] < nl[i] - 1e-9 or low[i] + shift[i] > nh[i] + 1e-9
                    for i in range(3)
                ):
                    continue
                if sm is None:
                    sm = off * parts[m]
                if (m, n) not in hits and overlap(sm, parts[n]) > 1e-3:
                    hits[(m, n)] = d
        d -= step
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


def min_wall(solid: Solid, per_face: int = 150) -> float:
    """Smallest material thickness (mm), by rays fired inward from surface points."""
    from OCP.BRepClass3d import BRepClass3d_SolidClassifier
    from OCP.gp import gp_Dir, gp_Lin, gp_Pnt
    from OCP.IntCurvesFace import IntCurvesFace_ShapeIntersector
    from OCP.TopAbs import TopAbs_IN

    inter = IntCurvesFace_ShapeIntersector()
    inter.Load(solid.wrapped, 1e-6)
    rng, worst = np.random.default_rng(0), 1e9
    for f in solid.faces():
        verts, _ = f.tessellate(0.2, 0.5)
        pts = np.array([(v.X, v.Y, v.Z) for v in verts])  # vertices lie on the surface
        if len(pts) > per_face:
            pts = pts[rng.choice(len(pts), per_face, replace=False)]
        for c in pts:
            nv = f.normal_at(Vector(*c))
            d = -np.array((nv.X, nv.Y, nv.Z))
            probe = BRepClass3d_SolidClassifier(solid.wrapped, gp_Pnt(*(c + 0.01 * d)), 1e-7)
            if probe.State() != TopAbs_IN:
                d = -d
            p0 = c + 1e-4 * d
            inter.Perform(gp_Lin(gp_Pnt(*p0), gp_Dir(*d)), 0.0, 1e3)
            ws = [inter.WParameter(i) for i in range(1, inter.NbPnt() + 1)]
            ws = [w for w in ws if w > 5e-3]
            if ws:
                worst = min(worst, min(ws))
    return worst


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
