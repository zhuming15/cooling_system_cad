# AGENTS.md

Guidance for AI coding agents working in this repo. For humans, start with
`README.md`.

## What this is

Parametric build123d CAD for a wall-mounted water flow station: flowmeter,
then a straight link tube, then the flow control valve, all on one wall base.
`assembly.py` is the acceptance test for the whole station.

- `valve/valve.py`: RS PRO 283-8289 G1/4 needle valve, which is the Tognella
  FT 1251/2-01-14. Its dimensions come from Tognella's datasheet table; a few
  details are scaled from Tognella's drawing.
- `valve_connector/valve_connector.py`: SMC KQ2H12-U02A push-in fitting.
  Dimensions come from the SMC catalogue and are checked against the RS-website
  3D model (max deviation 0.07 mm).
- `valve_clamp/clamp.py`: the valve clamp module (printed clamp base
  `make_base` + cap) and the shared constants and helpers: `AXIS_Y`, process
  tolerances and plastic allowables, M4 / insert / dowel hardware,
  `make_hardware()`, `base_holes()`, `cap_holes()`.
- `flowmeter_clamp/flowmeter_clamp.py`: the flowmeter clamp module (one
  printed base with both pedestals, the bar and the locating pad; two straps
  that grip the round Ø20.8 QSF bodies, never the hexes) and
  `make_station_base()`: the laser-cut station plate (wall layer + front
  layer, holes only).
- **The clamps are modules on a plain station base.** Each printed clamp
  base is located on the plate by 2 dowel pins and fixed by 2 × M4 from the
  front into captive nuts; its clamp head screws into heat-set inserts in it.
- `flowmeter/flowmeter.py`: ifm SV3051 vortex flowmeter. Its main dimensions
  come from the ifm datasheet drawing, and its envelope is checked against
  ifm's own STEP model. No display is modelled (the user confirmed there is none).
- `flowmeter_connector/flowmeter_connector.py`: Festo QSF-1/2-12-B, a G1/2
  female push-in fitting. Dimensions come from the Festo catalogue and are
  checked against the RS-website 3D model (max deviation 0.01 mm).
- `assembly.py`: places every part of the station, runs 66 design checks (about 1 minute), and writes
  `output/assembly.step` and `output/assembly.png`.
- `tools/render.py` writes the PNG renders. `tools/view.py` sends the model to
  the OCP CAD Viewer.
- `tools/cad_compare.py` measures a connector model against the RS-website
  mesh. `tools/drawing_check.py` overlays the flowmeter model on its datasheet
  drawing. Both need vendor files kept in a scratch directory (see each
  tool's docstring).

## Commands

```bash
uv sync                                   # deps (build123d, matplotlib, ocp-vscode, ruff)
uv run python assembly.py                 # MUST print "ALL CHECKS PASS" (exit 0)
uv run python tools/render.py             # output/assembly.png + output/components.png
uv run python flowmeter_clamp/flowmeter_clamp.py  # plate DXF/STEP + flowmeter clamp STEP
uv run python valve_clamp/clamp.py        # valve clamp STEP (likewise for the bought-in parts)
uv run python tools/view.py [assembly|exploded|parts|valve|connector|base|cap|
                            flowmeter|flowmeter_connector|flowmeter_fitted]
uv run python tools/cad_compare.py <valve_connector|flowmeter_connector> <vendor _000.bin>
uv run python tools/drawing_check.py <SV3051 datasheet pdf>
uv run ruff check .                       # must be clean
```

`tools/view.py` exits with an error if no viewer is listening on port 3939.
Don't treat that as a code bug; the user has to start the viewer.

## Definition of done for any geometry change

1. `uv run python assembly.py` passes all checks. Never weaken a threshold or
   delete a check to make a change pass. If a check is wrong, say why.
2. When you add or change a check, prove it can fail. Build a deliberately bad
   variant in a throwaway snippet (shift a part, shrink the pocket), confirm
   the check reports FAIL, then discard the snippet.
3. Re-run the part's own script so its STEP in the part folder is current,
   then run `tools/render.py`. Look at `output/components.png` and
   `output/assembly.png`; a passing check can still hide a visibly wrong
   shape.
4. For the flowmeter or its connector, re-run `tools/drawing_check.py` or
   `tools/cad_compare.py`, and look at the PNG they write.
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
    locating pad is a ledge under its downward 12 AF flat;
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
  body (for the flowmeter, its spanner flat on the locating pad).
  `assembly.phase_sweep()` spins every fitting through 60° and must stay
  clash-free.
- **Link-tube alignment is a hard requirement** from the user: no offset, no
  bend, no axial strain. Locate every clamp base by dowels in the one
  station-plate front layer (`base_front`), keep both flowmeter pedestals in
  one printed base, and
  keep the valve and flowmeter pocket clearances equal so that
  `clamp.VALVE_Y == flowmeter_clamp.FM_Y`. Derive the tube length from the two
  tube stops; never hard-code it.
- **Put every dimension in a named UPPER_CASE constant** at the top of the
  part file, with a comment giving its source or reason. Derive dependent
  values from those constants rather than hard-coding numbers. The clamp is
  sized from `valve.BODY_W` and the other valve constants, so changing the
  valve resizes the clamp.
- **Each part file exposes `make_*() -> Solid` functions** and exports its
  STEP only under `if __name__ == "__main__":`. `assembly.py` and `tools/`
  import these functions; they never load STEP files.
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
  laser-cut acrylic. Keep contact pressures under `PRINT_P_ALLOW` /
  `ACRYLIC_P_ALLOW` and torques low. Tolerances, allowables and friction are
  estimates; say so if you change them. Screws go into heat-set inserts
  (printed parts) or captive nuts (plate), never into tapped plastic.
- **Part names in `assembly.build()`** are used by the checks, by the colour
  lookup in `tools/render.py`, and by the exploded view in `tools/view.py`.
  Examples: `valve_knob`, `fitting_A`, `qsf_body_out`, `tube_link`,
  `base_front`, `valve_clamp_base`, `valve_clamp_cap`, `fm_clamp_base`,
  `fm_clamp_strap_0`, `m4_cap_screw_*`, `m4_mount_screw_*`, `m4_nut_*`,
  `m4_insert_*`, `dowel_*`, `wall_screw_*`. Renaming a part means updating
  all three, plus `tools/dims.py`.

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

## build123d gotchas seen here

- `Plane.XZ` has its normal along **−Y**, and its local y axis maps to global Z.
  Extruding from it with a positive amount goes toward −Y.
- `RegularPolygon(r, 6, major_radius=False)` puts the hex corners on local ±x.
  Add `rotation=30` to put the corners on local ±y.
- `BoundingBox.add()` returns a new box; it doesn't modify the original.
- `ocp_vscode.show()` does nothing and raises no error when no viewer is
  running. That's why `tools/view.py` checks the port first.

## Don't

- Don't commit, push or create branches unless the user asks. The repo has no
  commits yet, and its default branch is `main`.
- Don't hand-edit anything in `output/`; it is regenerated by the scripts.
- Don't add `__init__.py` files or turn the project back into an installable
  package. `pyproject.toml` sets `[tool.uv] package = false` on purpose.
