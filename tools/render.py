"""Matplotlib renders of the assembly and of each component.

    uv run python tools/render.py      -> output/assembly.png, output/components.png

assembly.py also calls render_assembly() after its design checks.
"""

import sys
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from build123d import Box, Pos, Solid
from matplotlib.colors import to_rgb
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output"
for sub in ("", "valve", "valve_connector", "valve_clamp", "flowmeter", "flowmeter_connector",
            "flowmeter_clamp"):
    sys.path.insert(0, str(ROOT / sub))

COLORS = {
    "valve_body": "#c9ccd1", "valve_bonnet": "#aeb3ba", "valve_knob": "#c8a64a",
    "valve_scale": "#2f5fd0", "fitting": "#d9c27a", "tube": "#3b82c4",
    "clamp_base": "#8fa3b8", "clamp_cap": "#a7b9cc", "m5": "#303030", "m4": "#303030",
    "wall_screw": "#505050", "wall": "#efe6cf",
    "flowmeter_pipe": "#6f7680", "flowmeter_housing": "#4d535c", "flowmeter_m12": "#c3c8cf",
    "qsf_body": "#d3d7dc", "qsf_release_ring": "#1f6fd1", "fm_clamp": "#a7b9cc",
}
LIGHT = np.array([0.35, 0.8, 0.5]) / np.linalg.norm([0.35, 0.8, 0.5])


def color_of(name: str) -> str:
    return next((c for k, c in COLORS.items() if name.startswith(k)), "#888888")


def split_knob(parts: dict[str, Solid]) -> dict[str, Solid]:
    """Show the knob's blue scale cap in its own colour."""
    import valve as V

    if "valve_knob" not in parts:
        return parts
    knob = parts["valve_knob"]
    top = knob.bounding_box().max.Y
    zone = Pos(knob.center().X, top - V.CAP_H / 2, knob.center().Z) * Box(40, V.CAP_H + 0.01, 40)
    out = dict(parts)
    out["valve_knob"], out["valve_scale_cap"] = knob - zone, knob & zone
    return out


def shaded_tris(solids: list[tuple[Solid, str]], tol: float = 0.1):
    """Tessellate and Lambert-shade solids -> (triangles, colours, bbox lo, hi)."""
    tri_all, col_all = [], []
    for solid, color in solids:
        verts, tris = solid.tessellate(tol, 0.25)
        pts = np.array([(v.X, v.Y, v.Z) for v in verts])
        t = pts[np.array(tris)]
        n = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
        n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
        k = 0.42 + 0.58 * np.abs(n @ LIGHT)
        tri_all.append(t)
        col_all.append(np.clip(np.outer(k, to_rgb(color)), 0, 1))
    tri, col = np.concatenate(tri_all), np.concatenate(col_all)
    flat = tri.reshape(-1, 3)
    return tri, col, flat.min(0), flat.max(0)


def _frame(ax, lo, hi, elev, azim, margin=1.05):
    c, r = (lo + hi) / 2, (hi - lo).max() / 2 * margin
    ax.set_xlim(c[0] - r, c[0] + r), ax.set_ylim(c[1] - r, c[1] + r)
    ax.set_zlim(c[2] - r, c[2] + r)
    ax.set_box_aspect((1, 1, 1))
    ax.view_init(elev=elev, azim=azim)


def render_assembly(parts: dict[str, Solid], path: Path) -> None:
    parts = split_knob(parts)
    tri, col, lo, hi = shaded_tris([(p, color_of(n)) for n, p in parts.items()], 0.15)
    lo, hi = lo - 10, hi + 10
    x0, x1, z0, z1 = lo[0], hi[0], lo[2], hi[2]
    wall = np.array([[[x0, 0, z0], [x1, 0, z0], [x1, 0, z1]],
                     [[x0, 0, z0], [x1, 0, z1], [x0, 0, z1]]])
    views = [("Isometric (operator side)", 22, 60), ("Front (operator view)", 0, 90),
             ("Side (wall at left)", 0, 0), ("Top (wall at top)", 89, 90)]
    fig = plt.figure(figsize=(18, 12))
    for i, (title, elev, azim) in enumerate(views):
        ax = fig.add_subplot(2, 2, i + 1, projection="3d")
        ax.add_collection3d(Poly3DCollection(wall, facecolors=COLORS["wall"], alpha=0.35,
                                             edgecolors="none"))
        ax.add_collection3d(Poly3DCollection(tri, facecolors=col, edgecolors="none"))
        _frame(ax, np.minimum(lo, [x0, -10, z0]), hi, elev, azim, 1.0)
        ax.set_title(title)
        ax.set_xlabel("X (flow runs -X)"), ax.set_ylabel("Y (out of wall)"), ax.set_zlabel("Z (up)")
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def render_components(path: Path) -> None:
    from build123d import Rot

    import assembly as A
    import clamp as C
    import flowmeter as FM
    import flowmeter_clamp as FCL
    import flowmeter_connector as FC
    import valve as V
    import valve_connector as F

    valve = split_knob({f"valve_{k}": s for k, s in V.make_valve_parts().items()})
    flowmeter = [(s, color_of(f"flowmeter_{n}")) for n, s in FM.make_flowmeter_parts().items()]
    qsf = [(s, color_of(f"qsf_{n}")) for n, s in FC.make_fitting_parts().items()]
    fitted = list(flowmeter)
    x_face = FM.L_TOTAL / 2 - FM.THREAD_L      # fitting face at the thread run-out
    for sgn in (-1, 1):
        fitted += [(Pos(sgn * x_face, 0, 0) * Rot(0, sgn * 90, 0) * s, c) for s, c in qsf]
    rows = [
        ("Valve - RS PRO 283-8289 (G1/4, square body)",
         [(s, color_of(n)) for n, s in valve.items()], (25, 50), (0, 0), None),
        ("Push-in connector - SMC KQ2H12-U02A (x2)",
         [(F.make_fitting(), COLORS["fitting"])], (25, 40), (0, 0), None),
        ("Station base - one piece, valve + flowmeter cradles (6061-T6)",
         [(FCL.make_station_base(A.X_FM, -A.FLOW_DIR), COLORS["clamp_base"])], (25, 60), (25, 230), None),
        ("Clamp cap (6061-T6)",
         [(C.make_cap_unclamped(), COLORS["clamp_cap"])], (25, 50), (-35, 250), None),
        ("Clamp screws ISO 4762 M5x25 (x4, as fitted)",
         [(s, COLORS["m5"]) for s in C.make_m5_screws()], (25, 50), (0, 0), 1),
        ("Flowmeter - ifm SV3051 (G1/2 male, 0.5-10 l/min)", flowmeter, (25, -60), (0, -90), None),
        ("Flowmeter connector - Festo QSF-1/2-12-B (x2)", qsf, (25, 40), (0, 0), None),
        ("Flowmeter with 2 x QSF-1/2-12-B fitted", fitted, (25, -60), (0, -90), None),
        ("Flowmeter strap (x2, 6061-T6)",
         [(FCL.make_cap_unclamped(FCL.STRAP_X), COLORS["fm_clamp"])], (25, 50), (-35, 250), None),
    ]
    fig = plt.figure(figsize=(12, 5.2 * len(rows)))
    for i, (title, solids, v1, v2, size_of) in enumerate(rows):
        tri, col, lo, hi = shaded_tris(solids, 0.08)
        sized = solids[:size_of] if size_of else solids
        bb = sized[0][0].bounding_box()
        for s, _ in sized[1:]:
            bb = bb.add(s.bounding_box())
        dims = f"{bb.size.X:.1f} x {bb.size.Y:.1f} x {bb.size.Z:.1f}"
        for j, (elev, azim) in enumerate((v1, v2)):
            ax = fig.add_subplot(len(rows), 2, 2 * i + j + 1, projection="3d")
            ax.add_collection3d(Poly3DCollection(tri, facecolors=col, edgecolors="none"))
            _frame(ax, lo, hi, elev, azim)
            ax.set_axis_off()
            if j == 0:
                ax.set_title(f"{title}\n{dims} mm", loc="left", fontsize=12)
    fig.subplots_adjust(left=0.02, right=0.98, top=0.97, bottom=0.01, hspace=0.12, wspace=0.0)
    fig.savefig(path, dpi=90)
    plt.close(fig)


def main() -> None:
    import assembly as A

    OUTPUT.mkdir(exist_ok=True)
    render_assembly(A.build(), OUTPUT / "assembly.png")
    render_components(OUTPUT / "components.png")
    print(f"Saved {OUTPUT / 'assembly.png'} and {OUTPUT / 'components.png'}")


if __name__ == "__main__":
    main()
