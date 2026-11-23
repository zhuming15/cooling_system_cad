"""Export and render the standalone A-coded electrical interconnect.

    uv run python tools/export_interconnect.py

The station exporter also includes this part in assembly.build() and the BOM.
This command retains a convenient standalone preview and STEP. Vendor source
files are never needed to build it.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "flowmeter_electronic_interconnect"))

import matplotlib.pyplot as plt
from build123d import Color, Compound, export_step
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

import flowmeter_electronic_interconnect as FEI
from tools.render import _frame, shaded_tris

OUTPUT = ROOT / "output"
COLORS = {
    "insert": "#31363c",
    "coupling": "#454a50",
    "body": "#353b43",
    "gland": "#444b53",
    "seal": "#899097",
}


def main():
    parts = FEI.make_interconnect_parts()
    for name, part in parts.items():
        part.label = name
        part.color = Color(COLORS.get(name, "#c8a64a"))
    # The station exporter replaces output/step/; keep standalone assets beside it.
    path = OUTPUT / "flowmeter_electronic_interconnect_msap-04bffc-sr7001.step"
    path.parent.mkdir(parents=True, exist_ok=True)
    export_step(Compound(children=list(parts.values()), label="MSAP-04BFFC-SR7001"), str(path))
    tri, col, lo, hi = shaded_tris(
        [(part, COLORS.get(name, "#c8a64a")) for name, part in parts.items()], 0.05
    )
    fig = plt.figure(figsize=(11, 5))
    for i, (title, elev, azim) in enumerate(
        [("A-coded mating face", 20, 220), ("Right-angle cable outlet", 20, 40)], 1
    ):
        ax = fig.add_subplot(1, 2, i, projection="3d")
        ax.add_collection3d(Poly3DCollection(tri, facecolors=col, linewidths=0))
        _frame(ax, lo, hi, elev, azim)
        ax.set_axis_off()
        ax.set_title(title)
    fig.suptitle("Amphenol LTW MSAP-04BFFC-SR7001")
    fig.tight_layout()
    fig.savefig(OUTPUT / "flowmeter_electronic_interconnect.png", dpi=180)
    plt.close(fig)
    print(path)


if __name__ == "__main__":
    main()
