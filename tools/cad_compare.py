"""Compare a part model with the vendor 3D model shown on its RS product page.

RS product pages embed a TraceParts viewer. It loads a zip holding a
Three.js binary mesh (format 3.1: `<name>.js` + `<name>_000.bin`). To get it,
open https://sg.rs-online.com/web/services/product/cad-download/3DViewer?articleId=<RS no.>
in a browser and take the S3 URL from the `api/v/path` response. Unzip it
into a scratch directory outside this repo.

    uv run python tools/cad_compare.py valve_connector  <path/to/_000.bin>
    uv run python tools/cad_compare.py flowmeter_connector <path/to/_000.bin>

This writes <part folder>/cad_check.png and prints the deviation of every
vendor mesh vertex from our model surface.
"""

import struct
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
for sub in ("", "valve_connector", "flowmeter_connector"):
    sys.path.insert(0, str(ROOT / sub))


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


def section(tris: np.ndarray, axis: int = 2, eps: float = 1e-4) -> np.ndarray:
    """Segments where triangles cross the plane coord[axis] = 0."""
    tris = tris.copy()
    tris[:, :, axis] += eps
    segs = []
    for t in tris:
        d = t[:, axis]
        pts = [t[i] + d[i] / (d[i] - d[(i + 1) % 3]) * (t[(i + 1) % 3] - t[i])
               for i in range(3) if (d[i] < 0) != (d[(i + 1) % 3] < 0)]
        if len(pts) == 2:
            segs.append(pts)
    return np.array(segs)


# part -> (builder, transform: our local -> vendor frame, mask of vendor
#          vertices that are excluded, with the reason)
def _presets():
    from build123d import Pos, Rot

    import flowmeter_connector as FC
    import valve_connector as VC

    return {
        "valve_connector": {
            "title": "SMC KQ2H12-U02A",
            "solid": lambda: Rot(-90, 0, 0) * VC.make_fitting(),   # our +Z -> vendor +Y
            "plane_axis": 2,
            "skip": None,
        },
        "flowmeter_connector": {
            "title": "Festo QSF-1/2-12-B",
            "solid": lambda: Pos(0, 0, FC.L_TOTAL) * Rot(180, 0, 0) * FC.make_fitting(),
            "plane_axis": 1,   # section through the hex flats (vendor flats on +/-X)
            # female thread: we model it at the major dia (cosmetic thread
            # convention), the vendor mesh at the minor dia
            "skip": lambda v: (np.abs(np.hypot(v[:, 0], v[:, 1]) - FC.THREAD_MINOR_D / 2) < 0.02)
            & (v[:, 2] > FC.CONE_TOP[1] - 0.01),
            "skip_reason": "female thread bore (vendor: minor dia, ours: major dia)",
        },
    }


def compare(part: str, bin_path: Path) -> float:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from build123d import Vector

    p = _presets()[part]
    tris = load_threejs_bin(bin_path)
    ours = p["solid"]()
    verts, faces = ours.tessellate(0.02, 0.1)
    pts = np.array([(q.X, q.Y, q.Z) for q in verts])
    our_tris = pts[np.array(faces)]

    V = np.unique(tris.reshape(-1, 3), axis=0)
    skip = p["skip"](V) if p["skip"] else np.zeros(len(V), bool)
    dev = np.array([ours.distance_to(Vector(*q)) for q in V[~skip]])
    print(f"{p['title']}: {len(V)} vendor vertices, {(~skip).sum()} checked")
    print(f"  max deviation {dev.max():.3f} mm, mean {dev.mean():.4f} mm")
    if skip.any():
        print(f"  skipped {skip.sum()}: {p['skip_reason']}")

    ax_keep = [i for i in range(3) if i != p["plane_axis"]]
    sv, so = section(tris, p["plane_axis"]), section(our_tris, p["plane_axis"])
    fig, ax = plt.subplots(figsize=(7, 8))
    for s in sv:
        ax.plot(s[:, ax_keep[0]], s[:, ax_keep[1]], "r-", lw=4, alpha=0.45)
    for s in so:
        ax.plot(s[:, ax_keep[0]], s[:, ax_keep[1]], "b-", lw=1)
    ax.plot([], [], "r-", lw=4, alpha=0.45, label="RS website 3D model (TraceParts)")
    ax.plot([], [], "b-", label=f"{part}.py")
    ax.set_title(f"{p['title']} - axial section\n{(~skip).sum()} vendor vertices: "
                 f"max deviation {dev.max():.2f} mm, mean {dev.mean():.3f} mm")
    ax.set_aspect("equal")
    ax.grid(alpha=0.3)
    ax.legend(loc="lower right")
    ax.set_xlabel("mm")
    ax.set_ylabel("axial mm (vendor frame)")
    out = ROOT / part / "cad_check.png"
    fig.savefig(out, dpi=110, bbox_inches="tight")
    print(f"  saved {out.relative_to(ROOT)}")
    return float(dev.max())


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] not in ("valve_connector", "flowmeter_connector"):
        sys.exit(__doc__)
    compare(sys.argv[1], Path(sys.argv[2]))
