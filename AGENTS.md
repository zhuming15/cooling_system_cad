# AGENTS.md

Guidance for AI coding agents working in this repo. For humans, start with
`README.md`.

## What this is

Parametric build123d CAD for a wall-mounted water flow station: flowmeter,
then a straight link tube, then the flow control valve, all on one wall base.
Three identical sets are stacked on the wall (`assembly.STACK_N`,
`STACK_PITCH`), all on ONE station plate.
`assembly.py` is the acceptance test for the whole station.

- `valve/valve.py`: RS PRO 283-8289 G1/4 needle valve, which is the Tognella
  FT 1251/2-01-14. Its dimensions come from Tognella's datasheet table; a few
  details are scaled from Tognella's drawing.
- `valve_connector/valve_connector.py`: SMC KQ2H12-U02A push-in fitting.
  Dimensions come from the SMC catalogue and are checked against the RS-website
  3D model (fit-critical zones and feature edges within 0.001 mm).
- `valve_clamp/clamp.py`: the valve clamp module (printed clamp base
  `make_base` + cap) and the shared constants and helpers: `AXIS_Y`, process
  tolerances and plastic allowables, M4 / insert / dowel hardware,
  `make_hardware()`, `base_holes()`, `cap_holes()`.
- `flowmeter_clamp/flowmeter_clamp.py`: the flowmeter clamp module (one
  printed base with both pedestals and one lower bar, no roll-stop pad;
  two straps that grip the round Ø20.8 QSF bodies, never the hexes) and
  `make_station_base()`: the station plate (`base_plate`). It is ONE 12 mm
  acrylic plate with through-cuts plus two 6 mm pocket features: M4 nut hex
  pockets from the wall face and M6 head counterbore slots from the front.
  One plate carries all `STACK_N` sets (outline from the lowest set to the
  highest, every set's holes repeated). `base_plate.dxf` has one layer per
  feature.
- **The clamps are modules on a plain station base.** Each printed clamp
  base is located on the plate by 2 dowel pins and fixed by 2 × M4 from the
  front into captive nuts; its clamp head screws into heat-set inserts in it.
- `flowmeter/flowmeter.py`: ifm SV3051 vortex flowmeter. Its dimensions are
  read off ifm's own STEP model (CAD_STP_300_0358) and agree with the ifm
  datasheet drawing. `tools/cad_compare.py flowmeter` passes: fit-critical
  features (G1/2 ends with the end-face groove, shoulder, bore, hex, 12 AF
  flats) within 0.001 mm, envelope 0.32 mm. No display is modelled (the user
  confirmed there is none). Which seal the end-face groove takes is still
  open (README "Verification status").
- `flowmeter_connector/flowmeter_connector.py`: Festo QSF-1/2-12-B, a G1/2
  female push-in fitting. The user's caliper measurements of the real part
  override the RS-website 3D model (hex 18 not 21, round body 11 not 15.3,
  length 40, port floor 17 deep), so its `cad_compare` no longer matches.
  The QSF is placed by its real stop: the meter end face bottoms (through
  the `WASHER_T` washer) on the port floor; the meter has no shoulder.
- `flowmeter_electronic_interconnect/flowmeter_electronic_interconnect.py`: Amphenol
  LTW MSAP-04BFFC-SR7001 A-coded M12 elbow, fitted to the SV3051. OEM CAD
  comparison passes (fit < 0.001 mm, exterior 0.414 mm). User confirmed the
  exact physical parts mate despite the vendor CAD's Ø8.20 insert / Ø8.15
  socket discrepancy. The interference check accounts only for that nominal
  cylindrical skin; displaced inserts must still fail. `electrical_*` parts
  belong to the flowmeter bench unit and count as one BOM component.
- `assembly.py`: places every part of ONE set (`build()`), runs 78 design
  checks on it (about 1 minute), and writes `output/assembly.step` and
  `output/assembly.png` for the whole stack (`build_stack()`: names
  `set<k>_<part>`, set 1 at the bottom). Each check section is a
  `check_<topic>(parts, r)` function listed in `SECTIONS`; `check_stack`
  places copies of the set above and below to check what stacking adds
  (collisions, the one plate carrying every set, M12 unplugging room, tool
  and operator access, service with neighbours fitted). `build()` is the
  middle set (`PLATE_SET`) with the whole plate (`make_station_base(x, stack_zs())`);
  `build_stack()` keeps the plate once, unprefixed (`SHARED`).
- `tools/checks.py`: the reusable check library (Report, interference, tool
  access, assembly sweep, printability, wall thickness, laser profile, worst
  case / RSS / Monte Carlo stacks, preload, pressures, tipping, wall loads).
  Station-independent: takes solids and numbers, never part names.
- `tests/`: pytest. `test_checks.py` and `test_vendor_tools.py` unit-test the
  tools (each with a good and a deliberately bad case); `test_assembly.py` runs
  every `assembly.py` section as a test, plus negative tests that break the
  design and expect the named check to fail.
- `tools/export_step.py` writes `output/step/`: the whole station as a named,
  coloured STEP assembly tree, one STEP per distinct component, and
  `bom.csv` with quantities counted from `assembly.build()`. It fails if an
  assembly part has no sub-assembly or no component file, so a new part needs
  an entry in its `SUBASSEMBLIES`, `components()` and `QTY_PATTERN`.
- `tools/render.py` writes the PNG renders. `tools/view.py` sends the model to
  the standalone OCP CAD viewer (`ocp_viewer`). `tools/dims.py` builds dimension annotations measured
  from the placed parts.
- `tools/cad_compare.py` compares a part model with the vendor's 3D model
  (RS/TraceParts mesh, STEP or STL), zone by zone: fit-critical zones must be
  exact (<= 0.02 mm, surfaces and feature edges), the rest within 0.5 mm, skip
  zones only for documented conventions. Presets: `valve_connector`,
  `flowmeter_connector`, `flowmeter`. `tools/drawing_check.py` overlays a model
  on its datasheet drawing (preset `flowmeter`) and has `grid` / `scale` modes
  for reading a drawing's scale. `tools/fetch_rs_cad.py` unpacks an RS 3D
  viewer zip. All need vendor files kept in a scratch directory.
- `.agents/skills/` (symlinked as `.claude/skills/`): project skills. `model-component` models a bought-in
  part from its vendor sources; `design-component` designs a made part from
  requirements (requirements, concepts, DFMEA, checks, DVP&R, manufacturing
  rules in `design-component/manufacturing.md`). Follow them for that work.

## Commands

```bash
uv sync                                   # deps (build123d, matplotlib, ocp-viewer, ruff, pytest, pytest-xdist)
uv run python assembly.py                 # MUST print "ALL CHECKS PASS" (exit 0)
uv run pytest                             # MUST pass (4 isolated workers by default)
uv run pytest -n 0                        # serial debug; add -m "not slow" for quicker feedback
uv run python tools/render.py             # output/assembly.png + output/components.png
uv run python tools/export_step.py        # output/step/: per-component + assembly STEP, bom.csv
uv run python flowmeter_clamp/flowmeter_clamp.py  # plate DXF (laser) + flowmeter clamp sizes
uv run python valve_clamp/clamp.py        # valve clamp sizes (likewise for the bought-in parts)
uv run python tools/view.py [assembly|exploded|parts|valve|connector|base|cap|
                            flowmeter|flowmeter_connector|flowmeter_fitted]
uv run python tools/cad_compare.py <preset | spec.json> <vendor _000.bin | .step | .stl>
uv run python tools/drawing_check.py <preset | spec.json> <datasheet pdf>
uv run python tools/drawing_check.py grid <pdf>       # pixel grid to read a drawing's scale
uv run python tools/fetch_rs_cad.py "<presigned url>" <scratch dir>
uv run ruff check .                       # must be clean
```

`tools/view.py` exits with an error if no viewer is listening on port 3939.
Don't treat that as a code bug; the user has to start the viewer with
`uv run python -m ocp_viewer` (page: http://127.0.0.1:3939/viewer).

## Definition of done for any geometry change

1. `uv run python assembly.py` passes all checks. Never weaken a threshold or
   delete a check to make a change pass. If a check is wrong, say why.
2. When you add or change a check, prove it can fail with a negative test in
   `tests/test_assembly.py` (shift a part, loosen a tolerance, reorder the
   build) that asserts the check's name fails. New `tools/checks.py`
   functions get a unit test with a good and a bad case. `uv run pytest`
   must pass.
3. Run `tools/export_step.py` so `output/step/` is current (and the part's
   own script if it writes a DXF), then run `tools/render.py`. Look at `output/components.png` and
   `output/assembly.png`; a passing check can still hide a visibly wrong
   shape.
4. For a bought-in part, re-run `tools/cad_compare.py` (and
   `tools/drawing_check.py` where there is a drawing preset) and look at the
   PNG they write. Fit-critical zones must stay exact.
5. Run `ruff check .`.

## Conventions

- **Units are mm**, angles in degrees.
- **Global frame** (assembly and clamp): the wall is Y = 0, +Y points toward
  the operator, Z is up. The flow axis is along X at (Y = `clamp.AXIS_Y`,
  Z = 0).
- **Part-local frames** are documented in each part file's docstring:
  - valve: flow along X, stem along +Y;
  - valve fitting: axis +Z, seat datum at Z = 0;
  - flowmeter: flow along −X (inlet at +X), housing and M12 connector on +Z.
    It is placed with local +Z = global +Z: horizontal pipe, housing on top,
    which is the user's choice and ifm's recommended position (Fig. 1). The
    strap bores alone set its height and strap friction holds its angle;
    the user removed the roll-stop pad and second bar (2026-11-25);
  - QSF fitting: axis +Z, female port face at Z = 0.
- **Flow direction.** System flow is `assembly.FLOW_DIR` (−X), which is left
  to right as the operator sees it; the operator faces the wall, so +X is
  their left. The layout (`X_FM`, `VALVE_INLET`, the link-tube ends) is
  derived from `FLOW_DIR`.
  - **The valve is bidirectional.** Confirmed by the user and by Tognella's
    datasheet (double-acting); RS's product text saying "single-acting" is
    wrong. Don't add flow-direction constraints for it.
  - **The flowmeter is directional.** Its arrow is local −X, and the M12
    connector and spanner flats are at the inlet end. It must stay upstream
    of the valve with its arrow along `FLOW_DIR`. The flow-direction checks
    read this from the placed geometry; don't turn them back into
    re-computations of the placement formula, which would pass even with the
    meter mounted backwards.
- **Never clamp or locate on a screwed-on fitting's hex.** Where a hex ends
  up depends on how tight the thread is, so its angle can't be controlled.
  Clamp on round features, and take the angle from a feature fixed to the
  body.
  `assembly.phase_sweep()` spins every fitting through 60° and must stay
  clash-free.
- **Link-tube alignment is a hard requirement** from the user: no offset, no
  bend, no axial strain. Locate every clamp base by dowels in the one
  station plate (`base_plate`), keep both flowmeter pedestals in
  one printed base, and
  keep the valve and flowmeter pocket clearances equal so that
  `clamp.VALVE_Y == flowmeter_clamp.FM_Y`. Derive the tube length from the two
  tube stops; never hard-code it.
- **Put every dimension in a named UPPER_CASE constant** at the top of the
  part file, with a comment giving its source or reason. Derive dependent
  values from those constants rather than hard-coding numbers. The clamp is
  sized from `valve.BODY_W` and the other valve constants, so changing the
  valve resizes the clamp.
- **Each part file exposes `make_*() -> Solid` functions.** Its
  `if __name__ == "__main__":` block only prints sizes (and writes the laser
  DXFs for the plate). STEP files are written only into `output/`, by
  `assembly.py` and `tools/export_step.py`; don't put STEP files in the part
  folders. `assembly.py` and `tools/` import the `make_*` functions; they
  never load STEP files.
- **Imports:** part folders are not packages. Entry scripts add the repo root
  and each part folder to `sys.path`, then `import valve as V`,
  `import valve_connector as F`, `import clamp as C`,
  `import flowmeter as FM`, `import flowmeter_connector as FC`,
  `import flowmeter_clamp as FCL`. Keep that pattern and those aliases.
- **Threads are cosmetic.** Female threads are modelled at the major diameter
  and screw threads at the minor diameter, so threaded joints don't register
  as interference. Don't model helical threads.
- **The cap is modelled at two positions.** `make_cap()` is the clamped
  position used in the assembly; it sits `CAP_DROP` lower than the free
  position. `make_cap_unclamped()` is the as-printed position used for
  export. The 1.0 mm `SPLIT_GAP` must stay larger than `CAP_DROP` plus
  2 × `PRINT_TOL`, otherwise a printed cap can bottom on its base instead of
  clamping the valve. The flowmeter straps work the same way.
- **Assembly order is a check.** `assembly.ASSEMBLY_ORDER` lists the README
  assembly steps; section 11 sweeps each one into place. If you add a part,
  put it in a step, or the check fails. The link tube goes in with the bench
  unit because it is cut stop-to-stop.
- **Plastic parts.** Clamp blocks are printed (PETG), the station plate is
  one cut and pocketed acrylic plate. Keep contact pressures under `PRINT_P_ALLOW` /
  `ACRYLIC_P_ALLOW` and torques low. Tolerances, allowables and friction are
  estimates; say so if you change them. Screws go into heat-set inserts
  (printed parts) or captive nuts (plate), never into tapped plastic.
- **Part names in `assembly.build()`** are used by the checks, by the colour
  lookup in `tools/render.py`, and by the exploded view in `tools/view.py`.
  Examples: `valve_knob`, `fitting_A`, `qsf_body_out`, `tube_link`,
  `base_plate`, `valve_clamp_base`, `valve_clamp_cap`, `fm_clamp_base`,
  `fm_clamp_strap_0`, `m4_cap_screw_*`, `m4_mount_screw_*`, `m4_nut_*`,
  `m4_insert_*`, `dowel_*`, `wall_screw_*`. Renaming a part means updating
  all three, plus `tools/dims.py` and `tools/export_step.py`. Stacked names
  carry a `set<k>_` prefix; `assembly.split_set_name()` strips it, and
  `color_of()` and the STEP exporter use it.

## Data provenance (important)

- **Don't invent vendor dimensions.** Every number for a bought-in part must
  cite a datasheet, catalogue or vendor CAD model. If you have to estimate
  one, say so in the code comment and tell the user.
- **The valve's OEM is Tognella** (FT 1251/2-01, type 14). Its datasheet is
  at paro.nl (`Tognella_FT1251-2-01_en.pdf/datasheet.html`). The PDF itself
  is behind Cloudflare, so read the page in the browser; the page images are
  embedded inline. If the user supplies caliper measurements, update
  `valve/valve.py` first and re-run everything. Don't adjust clamp numbers to
  make up for valve errors.
- **ifm publishes the SV3051 operating instructions and a STEP model** on
  ifm.com/…/product/SV3051 (Downloads tab, media.ifm.com links). The manual
  (11592037) sets the straight runs at 15 × DN, the torque at 12 N·m, and
  the recommended orientations. The README "Verification status" table is
  the register of what is verified and what isn't; keep it current.
- **Pressure and temperature limits** come from the weakest part: the QSF
  takes water at 6 bar at most up to 50 °C, and the KQ2 takes water at
  0–40 °C. Don't quote the valve's 210 bar as the system rating.
- **RS product pages return 403 to plain fetch tools.** Read them in a real
  browser. Datasheet PDFs on docs.rs-online.com download fine with curl.
- **The RS 3D viewer is a TraceParts mesh preview.** It is solid inside, has no
  flow bores, and is simplified. Use it for the outer envelope only.
- **Keep downloaded vendor files in a scratch directory, outside this repo.**
  Only their derived numbers and the `cad_check.png` / `drawing_check.png`
  comparison images are kept here.
- **Getting the RS 3D model** (there is none for 283-8289 or the SV3051): open
  `https://sg.rs-online.com/web/services/product/cad-download/3DViewer?articleId=<RS no.>`
  in the browser, then read the `api/v/path` network response. It holds a
  presigned S3 link to a zip, valid for about 15 minutes. Some RS parts have
  no 3D model; the SV3051 flowmeter is one.
- **The flowmeter's thread limits the tightening torque.** The QSF fitting is
  rated for 26 N·m on G1/2, but the flowmeter's plastic body is rated for
  12 N·m. A G-thread joint here also needs a flat sealing washer. Don't drop
  either point from the docs.

## Tight margins

Some checks pass with little room. A change that touches these needs care,
and the README "Tight margins" list must stay current:

- Worst-case link-tube strain: 0.45 % against `TUBE_STRAIN_MAX` 0.5 %.
- Valve clamp base tipping under a 500 N pull: × 1.17.
- Clamp-base M4 torque `MOUNT_TORQUE` 0.2 N·m: 0.15 N·m lets the valve base
  tip, 0.3 N·m overloads the acrylic under the nut.
- Flowmeter strap torque `FCL.STRAP_TORQUE` is 0.55 N·m for the elbow's
  67.12 mm cable lever: ×5.11 margin against ×5 at 50 N. Valve cap stays
  at 0.5 N·m. At 0.5 the strap pull margin fails; 0.6 overloads PETG.
- Strap washer on PETG 14.0 / 15 MPa (valve washer 12.7); nut on acrylic 9.4 / 10 MPa.
- Flowmeter strap float `FCL.AXIAL_FLOAT` ±1.0 against ±1.0: 12 mm straps
  `FCL.HEX_CLEAR` off the QSF hex cone, overhanging the collar (estimated
  Ø19.3, inside the bore) because the real round body is only 11 mm.
- Flowmeter strap counterbores (`C.CAP_CB_D` 9.5 in a 12 mm strap): 1.25 mm
  side walls against `MIN_WALL` 1.2.
- Wall screws: 6 × M6 for the whole stack (`FCL.wall_screw_xz`), 88 / 100 N per
  screw; they are `SHARED` (the plate's), not per set.

## build123d gotchas seen here

- `Plane.XZ` has its normal along **−Y**, and its local y axis maps to global Z.
  Extruding from it with a positive amount goes toward −Y.
- `RegularPolygon(r, 6, major_radius=False)` puts the hex corners on local ±x.
  Add `rotation=30` to put the corners on local ±y.
- `BoundingBox.add()` returns a new box; it doesn't modify the original.
- In build123d 0.13, `BoundBox.overlaps()` excludes containment and equal
  boxes. Do not use it to reject collision candidates; use the inclusive
  bounds logic in `tools/checks.py`. Bounds caches are local to one check
  invocation so changed solids cannot reuse stale measurements.
  `GeometryQueries` detects moves and wrapped replacements; direct OCCT topology
  edits require `invalidate(shape)` or a fresh context.
- `ocp_viewer.show()` does nothing and raises no error when no viewer is
  running. That's why `tools/view.py` checks the port first.

## Don't

- Don't commit, push or create branches unless the user asks. The default
  branch is `main`, pushed to `origin` on GitHub; so far the user has had
  commits go straight to `main`.
- Don't hand-edit anything in `output/`; it is regenerated by the scripts.
- Don't add `__init__.py` files or turn the project back into an installable
  package. `pyproject.toml` sets `[tool.uv] package = false` on purpose.
