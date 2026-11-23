"""STEP export of every component and of the whole station.

    uv run python tools/export_step.py     -> output/step/

Writes:
  00_flow_station_assembly.step  the whole station, as placed in assembly.py,
                                 as a named, coloured assembly tree
                                 (sub-assemblies: valve unit, flowmeter unit,
                                 tubes, station plate, clamps, hardware)
  NN_<component>.step            one file per distinct component
  bom.csv                        file, component, quantity, source/make, frame

Component frames:
  - bought-in parts (valve, fittings, flowmeter) use their part-local frame,
    documented in each part file's docstring;
  - made parts, tubes and hardware are taken as placed in the station, then
    moved so their bounding box is centred on X and Z and starts at Y = 0
    (Y = the direction out of the wall). Their orientation is unchanged, so
    the printed clamp parts are in their print orientation only if you lay
    them on the face you choose in the slicer.
  - printed clamp caps and straps are exported in their free (as-printed)
    position, not the clamped one.

The assembly STEP holds solids only; threads are cosmetic, as everywhere in
this repo.
"""

from __future__ import annotations

import copy
import csv
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
for sub in (
    "valve",
    "valve_connector",
    "valve_clamp",
    "flowmeter",
    "flowmeter_connector",
    "flowmeter_clamp",
):
    sys.path.insert(0, str(ROOT / sub))

from build123d import Color, Compound, Pos, Solid, export_step, import_step

import assembly as A
import clamp as C
import flowmeter as FM
import flowmeter_clamp as FCL
import flowmeter_connector as FC
import valve as V
import valve_connector as F
from tools.render import color_of

STEP_DIR = ROOT / "output" / "step"

# assembly sub-assemblies: (label, part-name prefixes)
SUBASSEMBLIES = (
    ("valve_unit", ("valve_body", "valve_bonnet", "valve_knob", "fitting_")),
    ("flowmeter_unit", ("flowmeter_", "qsf_")),
    ("tubes", ("tube_",)),
    ("station_plate", ("base_",)),
    ("valve_clamp", ("valve_clamp_",)),
    ("flowmeter_clamp", ("fm_clamp_",)),
    ("hardware", ("m4_", "dowel_", "wall_screw_")),
)


def _named(shape, label: str, color: str | None = None):
    shape.label = label
    if color is not None:
        shape.color = Color(color)
    return shape


def assembly_compound(parts: dict[str, Solid]) -> Compound:
    """The station as a STEP assembly tree: sub-assemblies of named, coloured parts."""
    groups = []
    used: set[str] = set()
    for label, prefixes in SUBASSEMBLIES:
        names = [n for n in parts if n.startswith(prefixes) and n not in used]
        used |= set(names)
        kids = [_named(copy.copy(parts[n]), n, color_of(n)) for n in names]  # don't reparent
        groups.append(Compound(children=kids, label=label))
    missing = set(parts) - used
    if missing:
        raise ValueError(f"parts not in any STEP sub-assembly: {sorted(missing)}")
    return Compound(children=groups, label="flow_station_assembly")


def _to_origin(s: Solid) -> Solid:
    """Centre on X and Z, start at Y = 0; orientation unchanged."""
    bb = s.bounding_box()
    return Pos(-bb.center().X, -bb.min.Y, -bb.center().Z) * s


def _fuse(parts: dict[str, Solid], label: str) -> Compound:
    """Multi-body bought-in part as one compound of named, coloured bodies."""
    return Compound(
        children=[_named(s, f"{label}_{k}", color_of(f"{label}_{k}")) for k, s in parts.items()],
        label=label,
    )


def components(parts: dict[str, Solid]) -> list[tuple[str, str, object, str, str]]:
    """(file stem, description, shape, source/make, frame) for each distinct component."""
    local = "part-local frame (see part file docstring)"
    placed = "as placed, moved to origin"
    qsf = FC.make_fitting_parts()
    return [
        (
            "valve_rs-283-8289",
            "Needle valve RS 283-8289 (Tognella FT 1251/2-01-14)",
            _fuse(V.make_valve_parts(), "valve"),
            "bought-in",
            local,
        ),
        (
            "valve_fitting_smc_kq2h12-u02a",
            "Push-in fitting SMC KQ2H12-U02A (12 mm x G1/4)",
            _named(F.make_fitting(), "fitting", color_of("fitting")),
            "bought-in",
            local,
        ),
        (
            "flowmeter_ifm_sv3051",
            "Vortex flowmeter ifm SV3051",
            _fuse(FM.make_flowmeter_parts(), "flowmeter"),
            "bought-in",
            local,
        ),
        (
            "flowmeter_fitting_festo_qsf-1-2-12-b",
            "Push-in fitting Festo QSF-1/2-12-B (12 mm x G1/2 female)",
            Compound(
                children=[
                    _named(qsf["body"], "qsf_body", color_of("qsf_body")),
                    _named(qsf["release_ring"], "qsf_release_ring", color_of("qsf_release_ring")),
                ],
                label="qsf",
            ),
            "bought-in",
            local,
        ),
        (
            "station_plate_back",
            "Station plate, wall layer (acrylic, laser-cut; DXF in flowmeter_clamp/)",
            _to_origin(parts["base_back"]),
            "laser-cut",
            placed,
        ),
        (
            "station_plate_front",
            "Station plate, front layer (acrylic, laser-cut; DXF in flowmeter_clamp/)",
            _to_origin(parts["base_front"]),
            "laser-cut",
            placed,
        ),
        (
            "valve_clamp_base",
            "Valve clamp base (PETG, printed)",
            _to_origin(C.make_base()),
            "3D-printed",
            placed,
        ),
        (
            "valve_clamp_cap",
            "Valve clamp cap (PETG, printed), free position",
            _to_origin(C.make_cap_unclamped()),
            "3D-printed",
            placed,
        ),
        (
            "flowmeter_clamp_base",
            "Flowmeter clamp base, 2 pedestals + pad (PETG, printed)",
            _to_origin(FCL.make_base(A.X_FM, -A.FLOW_DIR)),
            "3D-printed",
            placed,
        ),
        (
            "flowmeter_clamp_strap",
            "Flowmeter clamp strap (PETG, printed), free position",
            _to_origin(FCL.make_cap_unclamped(FCL.STRAP_X)),
            "3D-printed",
            placed,
        ),
        ("tube_link", "Tube 12x8, link (cut stop-to-stop)", _to_origin(parts["tube_link"]),
         "cut from tube", placed),
        ("tube_inlet", "Tube 12x8, inlet straight run (shown length)",
         _to_origin(parts["tube_in"]), "cut from tube", placed),
        ("tube_outlet", "Tube 12x8, outlet stub (shown length)",
         _to_origin(parts["tube_out"]), "cut from tube", placed),
        ("m4_cap_screw", "M4 ISO 4762 cap screw, clamp cap/strap",
         _to_origin(parts["m4_cap_screw_0"]), "bought-in (standard)", placed),
        ("m4_mount_screw", "M4 ISO 4762 cap screw, clamp base to plate",
         _to_origin(parts["m4_mount_screw_0"]), "bought-in (standard)", placed),
        ("m4_washer", "M4 DIN 125 washer", _to_origin(parts["m4_washer_0"]),
         "bought-in (standard)", placed),
        ("m4_insert", "M4 heat-set insert", _to_origin(parts["m4_insert_0"]),
         "bought-in (standard)", placed),
        ("m4_nut", "M4 hex nut (captive in plate)", _to_origin(parts["m4_nut_0"]),
         "bought-in (standard)", placed),
        ("dowel", "Dowel pin 4 m6 x 12", _to_origin(parts["dowel_0"]),
         "bought-in (standard)", placed),
        ("wall_screw", "M6 wall screw", _to_origin(parts["wall_screw_0"]),
         "bought-in (standard)", placed),
    ]  # fmt: skip


# component file stem -> assembly part-name pattern, for the BOM quantity
QTY_PATTERN = {
    "valve_rs-283-8289": r"valve_body",
    "valve_fitting_smc_kq2h12-u02a": r"fitting_[AB]",
    "flowmeter_ifm_sv3051": r"flowmeter_pipe",
    "flowmeter_fitting_festo_qsf-1-2-12-b": r"qsf_body_(in|out)",
    "station_plate_back": r"base_back",
    "station_plate_front": r"base_front",
    "valve_clamp_base": r"valve_clamp_base",
    "valve_clamp_cap": r"valve_clamp_cap",
    "flowmeter_clamp_base": r"fm_clamp_base",
    "flowmeter_clamp_strap": r"fm_clamp_strap_\d+",
    "tube_link": r"tube_link",
    "tube_inlet": r"tube_in",
    "tube_outlet": r"tube_out",
    "m4_cap_screw": r"m4_cap_screw_\d+",
    "m4_mount_screw": r"m4_mount_screw_\d+",
    "m4_washer": r"m4_washer_\d+",
    "m4_insert": r"m4_insert_\d+",
    "m4_nut": r"m4_nut_\d+",
    "dowel": r"dowel_\d+",
    "wall_screw": r"wall_screw_\d+",
}


def _solids(shape) -> list[Solid]:
    return list(shape.solids())


def _check(path: Path, shape) -> str:
    """Re-import the STEP and compare solid count and volume with the model."""
    back = import_step(str(path))
    n0, n1 = len(_solids(shape)), len(_solids(back))
    v0 = sum(s.volume for s in _solids(shape))
    v1 = sum(s.volume for s in _solids(back))
    if n0 != n1 or abs(v1 - v0) > 1e-4 * v0:
        raise RuntimeError(f"{path.name}: re-import mismatch ({n0}/{n1} solids, {v0:.1f}/{v1:.1f})")
    return f"{n1} solid(s), {v1 / 1000:.1f} cm3"


def main() -> int:
    STEP_DIR.mkdir(parents=True, exist_ok=True)
    for old in STEP_DIR.glob("*.step"):
        old.unlink()
    parts = A.build()

    asm_path = STEP_DIR / "00_flow_station_assembly.step"
    asm = assembly_compound(parts)
    export_step(asm, str(asm_path))
    print(f"{asm_path.relative_to(ROOT)}: {_check(asm_path, asm)}, {len(parts)} parts")

    rows = []
    comps = components(parts)
    counted = Counter()
    for i, (stem, desc, shape, make, frame) in enumerate(comps, start=1):
        qty = sum(1 for n in parts if re.fullmatch(QTY_PATTERN[stem], n))
        counted[stem] = qty
        path = STEP_DIR / f"{i:02d}_{stem}.step"
        if not shape.label:
            shape.label = stem
        export_step(shape, str(path))
        print(f"{path.relative_to(ROOT)}: x{qty}, {_check(path, shape)}")
        rows.append((path.name, desc, qty, make, frame))

    # every assembly part must be covered by exactly one component row
    covered = {n for n in parts for pat in QTY_PATTERN.values() if re.fullmatch(pat, n)}
    multi_body = re.compile(r"(valve_(bonnet|knob)|flowmeter_(housing|m12)|qsf_release_ring_.*)")
    uncovered = [n for n in parts if n not in covered and not multi_body.fullmatch(n)]
    if uncovered:
        raise RuntimeError(f"assembly parts with no component STEP: {uncovered}")

    with open(STEP_DIR / "bom.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["file", "component", "qty", "make", "frame"])
        w.writerows(rows)
    print(f"{(STEP_DIR / 'bom.csv').relative_to(ROOT)}: {len(rows)} components")
    return 0


if __name__ == "__main__":
    sys.exit(main())
