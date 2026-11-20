"""Overlay the flowmeter model's silhouette on the ifm SV3051 datasheet drawing.

The datasheet is a vendor PDF and is not stored in this repo. Download it
(https://docs.rs-online.com/7765/A700000014516681.pdf) into a scratch
directory, then run:

    uv run python tools/drawing_check.py <path/to/datasheet.pdf>

This rasterises page 1 at 300 dpi and writes flowmeter/drawing_check.png,
showing the side and top views with the model filled in translucent blue.
The calibration below was measured on that page at 300 dpi.
"""

import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "flowmeter"))

DPI = 300
PX_PER_MM = 15.63          # 77 mm = 1203.4 px (also checks 52.7, 30.2, G1/2)
X_LEFT_PX = 721.1          # left (outlet) thread end, X = -38.5
SIDE_AXIS_PX = 1250.7      # flow axis row, side view
TOP_AXIS_PX = 1846.2       # flow axis row, top view
VIEWS = {                  # name: (pixel rows/cols to crop, projection axes)
    "side (Z up)": {"rows": (520, 1520), "axis_px": SIDE_AXIS_PX, "proj": 2},
    "top (Y up)": {"rows": (1560, 2120), "axis_px": TOP_AXIS_PX, "proj": 1},
}


def main(pdf: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    from PIL import Image

    import flowmeter as FM

    with tempfile.TemporaryDirectory() as td:
        subprocess.run(["pdftoppm", "-f", "1", "-l", "1", "-r", str(DPI), "-png",
                        str(pdf), f"{td}/p"], check=True)
        img = np.asarray(Image.open(next(Path(td).glob("p*.png"))).convert("L"))

    solid = FM.make_flowmeter()
    verts, faces = solid.tessellate(0.05, 0.2)
    pts = np.array([(v.X, v.Y, v.Z) for v in verts])
    tris = pts[np.array(faces)]

    fig, axes = plt.subplots(2, 1, figsize=(10, 12),
                             gridspec_kw={"height_ratios": [1000, 560]})
    for ax, (name, v) in zip(axes, VIEWS.items()):
        r0, r1 = v["rows"]
        c0, c1 = int(X_LEFT_PX - 60), int(X_LEFT_PX + 77 * PX_PER_MM + 120)
        crop = img[r0:r1, c0:c1]
        to_x = lambda c: (c - X_LEFT_PX) / PX_PER_MM - 38.5
        to_y = lambda r, a=v["axis_px"]: (a - r) / PX_PER_MM
        ax.imshow(crop, cmap="gray", extent=(to_x(c0), to_x(c1), to_y(r1), to_y(r0)))
        poly = tris[:, :, [0, v["proj"]]]
        ax.add_collection(PolyCollection(poly, facecolors=(0.1, 0.4, 1.0, 0.05),
                                         edgecolors="none"))
        ax.set_title(f"SV3051 datasheet drawing vs flowmeter.py - {name}")
        ax.set_xlabel("X mm (flow -X)")
        ax.set_aspect("equal")
    fig.tight_layout()
    out = ROOT / "flowmeter" / "drawing_check.png"
    fig.savefig(out, dpi=110)
    print(f"saved {out.relative_to(ROOT)}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(Path(sys.argv[1]))
