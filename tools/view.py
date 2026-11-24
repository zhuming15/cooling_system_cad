"""Send the model to the standalone OCP CAD viewer (ocp_viewer).

Start the viewer first:
  uv run python -m ocp_viewer   (then open http://127.0.0.1:3939/viewer)

Then:
  uv run python tools/view.py              # one set on the wall (default)
  uv run python tools/view.py stack        # all assembly.STACK_N sets, stacked
  uv run python tools/view.py parts        # every component laid out side by side
  uv run python tools/view.py exploded     # assembly pulled apart along the build order
  uv run python tools/view.py valve | connector | base | cap
  uv run python tools/view.py flowmeter | flowmeter_connector | flowmeter_fitted
  add --port 3940 if the viewer runs on another port
"""

import argparse
import sys
from pathlib import Path

from build123d import Box, Pos, Rot
from ocp_viewer import Camera, set_port, show

ROOT = Path(__file__).resolve().parents[1]
for sub in (
    "",
    "valve",
    "valve_connector",
    "valve_clamp",
    "flowmeter",
    "flowmeter_connector",
    "flowmeter_clamp",
    "flowmeter_electronic_interconnect",
):
    sys.path.insert(0, str(ROOT / sub))

import assembly as A
import clamp as C
import flowmeter as FM
import flowmeter_connector as FC
import valve as V
import valve_connector as F
from tools.render import color_of, split_knob


def wall(parts):
    bb = None
    for p in parts.values():
        bb = p.bounding_box() if bb is None else bb.add(p.bounding_box())
    return Pos(bb.center().X, -5, bb.center().Z) * Box(bb.size.X + 40, 10, bb.size.Z + 40)


def exploded(parts):
    """Offset each group along its assembly direction (+Y out of the wall)."""
    step = {
        "base_": 0,
        "dowel": 20,
        "m4_nut": -25,
        "m4_mount": 30,
        "m4_insert": 30,
        "valve_clamp_base": 20,
        "fm_clamp_base": 20,
        "valve_clamp_cap": 110,
        "fm_clamp_strap": 110,
        "m4_washer": 140,
        "m4_cap": 150,
        "wall_screw": -25,
        "valve": 45,
        "fitting": 45,
        "flowmeter": 45,
        "electrical_": 45,
        "qsf": 45,
        "tube": 45,
    }
    # fittings and their tubes also move outward along the flow axis, away
    # from the body they screw into (valve at X = 0, flowmeter at A.X_FM)
    side = {
        "fitting": (25, 0.0),
        "tube_out": (60, 0.0),
        "qsf": (25, A.X_FM),
        "tube_in": (60, A.X_FM),
    }
    out = {}
    for n, p in parts.items():
        dy = next(v for k, v in step.items() if n.startswith(k))
        dx = 0.0
        for k, (mag, ref) in side.items():
            if n.startswith(k):
                dx = mag if p.bounding_box().center().X > ref else -mag
        out[n] = Pos(dx, dy, 35 if n.startswith("electrical_") else 0) * p
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "what",
        nargs="?",
        default="assembly",
        choices=[
            "assembly",
            "stack",
            "parts",
            "exploded",
            "valve",
            "connector",
            "base",
            "cap",
            "flowmeter",
            "flowmeter_connector",
            "flowmeter_fitted",
        ],
    )
    ap.add_argument("--port", type=int, default=3939)
    a = ap.parse_args()
    import socket

    with socket.socket() as s:
        s.settimeout(1)
        if s.connect_ex(("127.0.0.1", a.port)) != 0:
            sys.exit(
                f"No OCP viewer on port {a.port}. Start it first:\n"
                f"  uv run python -m ocp_viewer --port {a.port}\n"
                f"  then open http://127.0.0.1:{a.port}/viewer"
            )
    set_port(a.port)

    if a.what in ("assembly", "exploded", "stack"):
        parts = split_knob(A.build_stack() if a.what == "stack" else A.build())
        if a.what == "exploded":
            parts = exploded(parts)
        names, objs = list(parts), list(parts.values())
        names.append("wall"), objs.append(wall(parts))
        alphas = [1.0] * (len(objs) - 1) + [0.25]
    elif a.what == "parts":
        # every part once, laid out in a row, each with its dimensions
        from tools.dims import dimensions, part_groups

        groups = part_groups(A.build())
        names, objs, alphas, x = [], [], [], 0.0
        for gname, g in groups.items():
            sols = list(g["solids"].values())
            bb = sols[0].bounding_box()
            for sol in sols[1:]:
                bb = bb.add(sol.bounding_box())
            move = Pos(x - bb.min.X, -bb.min.Y, -bb.center().Z)
            for n, sol in g["solids"].items():
                names.append(f"{gname}/{n}"), objs.append(move * sol), alphas.append(1.0)
            for i, d in enumerate(dimensions(gname, g)):
                names.append(f"{gname}/dim_{i}"), objs.append(move * d), alphas.append(1.0)
            x += bb.size.X + 40
    elif a.what.startswith("flowmeter"):
        layout = {}
        if a.what != "flowmeter_connector":
            layout |= {f"flowmeter_{n}": s for n, s in FM.make_flowmeter_parts().items()}
        qsf = {f"qsf_{n}": s for n, s in FC.make_fitting_parts().items()}
        if a.what == "flowmeter_connector":
            layout |= qsf
        elif a.what == "flowmeter_fitted":
            import flowmeter_electronic_interconnect as FEI

            layout |= {
                f"electrical_{n}": A.interconnect_location() * s
                for n, s in FEI.make_interconnect_parts().items()
            }
            x_face = FM.L_TOTAL / 2 - FM.THREAD_L
            for side, sgn in (("outlet", -1), ("inlet", 1)):
                place = Pos(sgn * x_face, 0, 0) * Rot(0, sgn * 90, 0)
                layout |= {f"{n}_{side}": place * s for n, s in qsf.items()}
        names, objs = list(layout), list(layout.values())
        alphas = [1.0] * len(objs)
    else:
        single = {
            "valve": ("valve", V.make_valve()),
            "connector": ("fitting", F.make_fitting()),
            "base": ("valve_clamp_base", C.make_base()),
            "cap": ("valve_clamp_cap", C.make_cap_unclamped()),
        }[a.what]
        names, objs, alphas = [single[0]], [single[1]], [1.0]

    cols = ["#202020" if "/dim_" in n else color_of(n.split("/")[-1]) for n in names]
    show(*objs, names=names, colors=cols, alphas=alphas, reset_camera=Camera.RESET)
    print(f"Sent '{a.what}' ({len(objs)} objects) to OCP viewer on port {a.port}")


if __name__ == "__main__":
    main()
