"""Tests for tools/cad_compare.py and tools/drawing_check.py.

The comparison runs end to end against synthetic "vendor" STL files written
here, so no vendor download is needed. Each acceptance rule is shown to pass
on a faithful model and to fail on a deliberately wrong one.
"""

import math

import numpy as np
import pytest
from build123d import Box, Cylinder, Pos, Rot

from tools import cad_compare as CC
from tools import drawing_check as DC


def part() -> Box:
    """The 'our model' used by the end-to-end tests (spec part test_vendor_tools:part)."""
    return Box(20, 20, 10) - Cylinder(3, 20)


def write_stl(solid, path, shift=(0, 0, 0)) -> None:
    tris = CC.tessellate(Pos(*shift) * solid, 0.01)
    with open(path, "w") as f:
        f.write("solid vendor\n")
        for t in tris:
            f.write(" facet normal 0 0 0\n  outer loop\n")
            f.writelines(f"   vertex {p[0]:.6f} {p[1]:.6f} {p[2]:.6f}\n" for p in t)
            f.write("  endloop\n endfacet\n")
        f.write("endsolid vendor\n")


SPEC = {
    "title": "test block",
    "part": "test_vendor_tools:part",
    "to_vendor": "",
    "zones": [{"name": "bore (fit)", "kind": "fit", "cyl": ["z", 2.9, 3.1, -6, 6]}],
}


def test_point_triangle_distance():
    tri = np.array([[[0, 0, 0], [1, 0, 0], [0, 1, 0]]], float)
    pts = np.array([[0.2, 0.2, 1.0], [2, 0, 0], [-1, -1, 0], [0.5, 0.5, 0]], float)
    d = CC.point_triangle_distance(pts, tri)
    assert d == pytest.approx([1.0, 1.0, math.sqrt(2), 0.0], abs=1e-9)


def test_zone_of_first_zone_wins():
    zones = [
        {"name": "a", "kind": "skip", "box": [-1, 1, -1, 1, -1, 1]},
        {"name": "b", "kind": "fit", "cyl": ["z", 0, 5, -1, 1]},
    ]
    pts = np.array([[0, 0, 0], [3, 0, 0], [9, 0, 0]], float)
    assert CC.zone_of(pts, zones).tolist() == [0, 1, -1]


def test_transform_round_trip():
    m = CC.matrix(CC.to_vendor_location("plane((1, 2, 3), (-1, 0, 0), (0, -1, 0))"))
    p = np.array([[1.0, 2.0, 3.0]])
    back = CC.apply(np.linalg.inv(m), CC.apply(m, p))
    assert back == pytest.approx(p)
    assert CC.apply(m, np.zeros((1, 3)))[0] == pytest.approx([1, 2, 3])


def test_compare_passes_an_exact_model(tmp_path):
    write_stl(part(), tmp_path / "v.stl")
    assert CC.compare(dict(SPEC), tmp_path / "v.stl", quiet=True)["pass"]


def test_compare_fails_a_fit_zone_off_by_005(tmp_path):
    # vendor bore 0.05 mm larger: inside the envelope limit, outside the exact fit limit
    vendor = Box(20, 20, 10) - Cylinder(3.05, 20)
    write_stl(vendor, tmp_path / "v.stl")
    spec = dict(SPEC, zones=[{"name": "bore", "kind": "fit", "cyl": ["z", 2.9, 3.2, -6, 6]}])
    res = CC.compare(spec, tmp_path / "v.stl", quiet=True)
    assert not res["pass"]
    assert not res["bore [vendor edges->our edges]"][5]  # the edge check catches it


def test_compare_envelope_limit(tmp_path):
    for grow, ok in ((0.3, True), (0.7, False)):
        vendor = Box(20 + 2 * grow, 20, 10) - Cylinder(3, 20)  # outline off by `grow`
        write_stl(vendor, tmp_path / f"v{grow}.stl")
        assert CC.compare(dict(SPEC), tmp_path / f"v{grow}.stl", quiet=True)["pass"] is ok


def test_compare_skip_zone_is_not_judged(tmp_path):
    vendor = Box(20, 20, 10) - Cylinder(2.0, 20)  # e.g. thread modelled at another dia
    write_stl(vendor, tmp_path / "v.stl")
    spec = dict(SPEC, zones=[{"name": "thread", "kind": "skip", "cyl": ["z", 1.9, 3.1, -6, 6]}])
    assert CC.compare(spec, tmp_path / "v.stl", quiet=True)["pass"]


def test_compare_finds_the_misaligned_frame(tmp_path):
    write_stl(Rot(0, 90, 0) * part(), tmp_path / "v.stl")  # vendor lies on its side
    assert not CC.compare(dict(SPEC), tmp_path / "v.stl", quiet=True)["pass"]
    spec = dict(SPEC, to_vendor="rot(0, 90, 0)")
    assert CC.compare(spec, tmp_path / "v.stl", quiet=True)["pass"]


def test_drawing_scale():
    assert DC.scale(721.1, 0, 1924.5, 0, 77) == pytest.approx(15.629, abs=1e-3)
