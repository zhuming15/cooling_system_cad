"""Overlay a part model on its vendor datasheet drawing, and read scales off it.

Three modes. The datasheet PDF is a vendor file: keep it in a scratch
directory, outside this repo.

  1. Grid: rasterise a page with a pixel grid, to read coordinates off it.
        uv run python tools/drawing_check.py grid <pdf> [--page 1] [--dpi 300] [--out grid.png]
     Zoom into the PNG to find the pixel positions of two ends of a dimension
     the drawing states (e.g. the overall length).

  2. Scale: px/mm from two points of a known dimension, to set up a view and
     to cross-check it on further dimensions (a drawing that isn't to scale
     shows up here).
        uv run python tools/drawing_check.py scale <x0> <y0> <x1> <y1> <mm>

  3. Overlay: the model's silhouette on each view of the drawing.
        uv run python tools/drawing_check.py <preset | spec.json> <pdf>
     Spec (preset dict or JSON file):
       {"title": "...", "part": "module:function", "page": 1, "dpi": 300,
        "out": "part_folder/drawing_check.png",
        "views": [{"name": "side (Z up)",
                   "crop": [row0, row1, col0, col1],       # pixels, at that dpi
                   "px_per_mm": 15.63,
                   "origin_px": [col, row],                # where model (0, 0) lands
                   "axes": [0, 2]}]}                       # model axes -> image right, up
     Look at the PNG: the blue silhouette must sit on the drawing's lines. Note
     the scale and any feature off by more than the drawing's own accuracy in
     the part file's docstring.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
for sub in ("", "valve", "valve_connector", "flowmeter", "flowmeter_connector"):
    sys.path.insert(0, str(ROOT / sub))


def rasterise(pdf: Path, page: int = 1, dpi: int = 300) -> np.ndarray:
    """One PDF page as a greyscale array (needs poppler's pdftoppm)."""
    from PIL import Image

    with tempfile.TemporaryDirectory() as td:
        subprocess.run(
            [
                "pdftoppm",
                "-f",
                str(page),
                "-l",
                str(page),
                "-r",
                str(dpi),
                "-png",
                str(pdf),
                f"{td}/p",
            ],
            check=True,
        )
        return np.asarray(Image.open(next(Path(td).glob("p*.png"))).convert("L"))


def presets() -> dict[str, dict]:
    # SV3051 datasheet (docs.rs-online.com/7765/A700000014516681.pdf), page 1 at
    # 300 dpi: 77 mm = 1203.4 px (also checks 52.7, 30.2, G1/2); left (outlet)
    # thread end X = -38.5 at column 721.1
    px, x_left = 15.63, 721.1
    origin_col = x_left + 38.5 * px
    return {
        "flowmeter": {
            "title": "SV3051 datasheet drawing vs flowmeter.py",
            "part": "flowmeter:make_flowmeter",
            "page": 1,
            "dpi": 300,
            "out": "flowmeter/drawing_check.png",
            "views": [
                {
                    "name": "side (Z up)",
                    "crop": [520, 1520, int(x_left - 60), int(x_left + 77 * px + 120)],
                    "px_per_mm": px,
                    "origin_px": [origin_col, 1250.7],
                    "axes": [0, 2],
                },
                {
                    "name": "top (Y up)",
                    "crop": [1560, 2120, int(x_left - 60), int(x_left + 77 * px + 120)],
                    "px_per_mm": px,
                    "origin_px": [origin_col, 1846.2],
                    "axes": [0, 1],
                },
            ],
        }
    }


def grid(pdf: Path, page: int, dpi: int, out: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    img = rasterise(pdf, page, dpi)
    h, w = img.shape
    fig, ax = plt.subplots(figsize=(w / 150, h / 150))
    ax.imshow(img, cmap="gray")
    step = 100
    ax.set_xticks(range(0, w, step))
    ax.set_yticks(range(0, h, step))
    ax.tick_params(labelsize=5, labeltop=True, labelright=True)
    ax.grid(color="r", alpha=0.25, lw=0.4)
    fig.savefig(out, dpi=150, bbox_inches="tight")
    print(f"saved {out} ({w} x {h} px at {dpi} dpi; grid every {step} px)")


def scale(x0: float, y0: float, x1: float, y1: float, mm: float) -> float:
    px = float(np.hypot(x1 - x0, y1 - y0))
    k = px / mm
    print(f"{px:.1f} px over {mm} mm -> {k:.3f} px/mm")
    return k


def overlay(spec: dict, pdf: Path) -> Path:
    import importlib

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection

    img = rasterise(pdf, spec.get("page", 1), spec.get("dpi", 300))
    mod, fn = spec["part"].split(":")
    solid = getattr(importlib.import_module(mod), fn)()
    verts, faces = solid.tessellate(0.05, 0.2)
    pts = np.array([(v.X, v.Y, v.Z) for v in verts])
    tris = pts[np.array(faces)]

    views = spec["views"]
    heights = [v["crop"][1] - v["crop"][0] for v in views]
    fig, axes = plt.subplots(
        len(views), 1, figsize=(10, 12), gridspec_kw={"height_ratios": heights}, squeeze=False
    )
    for ax, v in zip(axes[:, 0], views):
        r0, r1, c0, c1 = v["crop"]
        k, (oc, orow) = v["px_per_mm"], v["origin_px"]
        right, up = v["axes"]

        def to_x(c, oc=oc, k=k):
            return (c - oc) / k

        def to_y(r, orow=orow, k=k):
            return (orow - r) / k

        ax.imshow(img[r0:r1, c0:c1], cmap="gray", extent=(to_x(c0), to_x(c1), to_y(r1), to_y(r0)))
        poly = tris[:, :, [right, up]]
        ax.add_collection(PolyCollection(poly, facecolors=(0.1, 0.4, 1.0, 0.05), edgecolors="none"))
        ax.set_title(f"{spec['title']} - {v['name']} ({k:.2f} px/mm)")
        ax.set_xlabel(f"model {'XYZ'[right]} mm")
        ax.set_aspect("equal")
    fig.tight_layout()
    out = ROOT / spec["out"]
    fig.savefig(out, dpi=110)
    plt.close(fig)
    print(f"saved {out.relative_to(ROOT)}")
    return out


def main(argv: list[str]) -> None:
    import argparse

    if len(argv) > 1 and argv[1] == "grid":
        p = argparse.ArgumentParser()
        p.add_argument("mode")
        p.add_argument("pdf", type=Path)
        p.add_argument("--page", type=int, default=1)
        p.add_argument("--dpi", type=int, default=300)
        p.add_argument("--out", type=Path, default=Path("grid.png"))
        a = p.parse_args(argv[1:])
        grid(a.pdf, a.page, a.dpi, a.out)
    elif len(argv) == 7 and argv[1] == "scale":
        scale(*map(float, argv[2:7]))
    elif len(argv) == 3:
        name, pdf = argv[1], Path(argv[2])
        spec = json.loads(Path(name).read_text()) if name.endswith(".json") else presets()[name]
        overlay(spec, pdf)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv)
