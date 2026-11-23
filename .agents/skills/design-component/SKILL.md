---
name: design-component
description: Design a new made part (clamp, bracket, mount, adapter, plate, enclosure...) from the user's requirements, so that it does the job AND can be made by the chosen process (3D printing, laser cutting, ...). Use when the user asks to "design a ... that ...", "I need a mount / holder / bracket for X", or asks to change such a design. Captures numbered requirements, compares concepts, runs a DFMEA, builds a parametric build123d model, proves every requirement with a check (tools/checks.py + pytest), and delivers manufacturing files, BOM, assembly order and a DVP&R with the physical tests.
---

# design-component: design a part from requirements

The truth is the user's requirements and the chosen manufacturing process.
The job is a design that meets every requirement, that the process can
actually make, and a record that proves both. This follows the industrial
pattern: requirements -> concepts -> DFMEA -> design -> verification (DVP&R)
-> physical validation, scaled to a one-person code-CAD project.

Read `AGENTS.md` first (conventions, hardware rules, check rules), and keep
[manufacturing.md](manufacturing.md) and [templates.md](templates.md) open.

## Ground rules

- Every bought-in part the design touches is modelled first with the
  **model-component** skill. Never change a bought-in part's numbers to make
  the design fit.
- Every requirement ends up with at least one check or one physical test.
- Analysis is at least this repo's standard: interference, tool access,
  assembly-order sweep, printability, wall thickness, worst case + RSS +
  Monte Carlo tolerance stacks, thermal, contact pressure, preload, slip,
  tipping, fixings, mass and mounting loads.
- Never weaken a threshold or delete a check to pass. Prove every new check
  fails on a deliberately broken variant (a pytest negative test).
- Estimates (tolerances, allowables, friction, process limits) are named
  constants marked ESTIMATE, and listed for the user.

## Phase 1: requirements (CHECKPOINT)

Interview the user with the checklist in [templates.md](templates.md#requirements-checklist):
function, interfaces, loads, environment, manufacturing (process, material,
machine, quantity, tools at hand), use and service, standards, hard
constraints vs preferences. Ask only what you can't find in the repo or the
bought-in parts' registers; propose defaults with reasons.

Write numbered, testable requirements (R1, R2, ...), each with a limit and how
it will be verified (check / test / inspection). Get the user's approval of
the list before going on.

## Phase 2: concepts (CHECKPOINT)

Sketch 2-3 genuinely different concepts (e.g. one-piece base, sheet fins,
modular saddles). Fill the trade-off table from
[templates.md](templates.md#concept-trade-off): every hard requirement,
manufacturability in the chosen process, alignment / tolerance stack, part
count, assembly and service, cost. Recommend one with reasons; the user
chooses.

## Phase 3: DFMEA

Before modelling, list failure modes for the chosen concept with the table in
[templates.md](templates.md#dfmea): function, failure mode, effect, cause,
severity / occurrence / detection, and the design action or check that covers
it. Typical modes this repo met: a part can't be assembled in the stated order
(the link tube), clamping on a feature whose angle can't be controlled (a
hex), a gap that closes before the clamp grips (print tolerance), creep of
plastic under screw preload, a wall too thin to print. Every severity >= 7 row
needs a check or a test in the DVP&R.

## Phase 4: parametric model

- New folder `<part>/<part>.py`, `make_*() -> Solid` functions, STEP under
  `__main__`, docstring with purpose, process, frame and the requirements it
  serves.
- Size everything from the interfacing parts' constants (the valve clamp is
  sized from `valve.BODY_W`), so a changed component resizes the design.
- Process tolerances, allowables and limits come from
  [manufacturing.md](manufacturing.md) as named constants (shared ones live in
  `valve_clamp/clamp.py`; reuse them).
- Design for the process from the start (manufacturing.md "design rules"):
  print orientation chosen before detailing, no supports, hole and wall
  minimums, fixings the material can take (heat-set inserts in prints, captive
  nuts in acrylic, never screws into tapped plastic).
- Hardware is modelled (screws, washers, inserts, nuts, dowels) with real
  catalogue lengths, so engagement and access are checked.
- Two positions for anything that closes on a part (clamped / as printed),
  with a split gap larger than the closing travel plus 2 x the tolerance.
- Add the parts to `assembly.build()` with names, to `ASSEMBLY_ORDER`, and to
  the colour / view / dims lookups (`AGENTS.md` "Part names").

## Phase 5: verification in code

Write the checks in the design's check script (`assembly.py` here) as
`check_<topic>(parts, r)` section functions listed in `SECTIONS`, built from
`tools/checks.py`:

| Requirement kind | Functions / pattern |
|---|---|
| fit, no clash | `interferences`, `overlap`, `distance_to` for seating |
| tool / finger / cable access | `axis_probe` + `ray_clear` |
| can be assembled in order | `sweep` per `ASSEMBLY_ORDER` step |
| printable | `overhangs`, `min_wall`, `max_extent` (bed) |
| laser-cuttable | `is_flat_profile`, `max_extent` (sheet) |
| alignment / fit under tolerance | `worst_case`, `rss`, `monte_carlo` on a named tolerance stack, then the consequence (e.g. `fixed_fixed_strain`) |
| temperature | `thermal_growth` |
| holding, strength | `preload`, contact pressure (`annulus_area`, `hex_bearing_area`), friction, `tip_factor`, `end_thrust`, `wall_screw_load` |

Then:

1. `tests/test_assembly.py` runs every section under pytest automatically
   (`test_section_passes`); add a **negative test** per new check that breaks
   the design (shift a part, loosen a tolerance, weaken a material, reorder
   the build) and asserts that check's name fails.
2. `uv run python assembly.py` prints ALL CHECKS PASS; `uv run pytest` passes;
   `uv run ruff check .` is clean.
3. Render (`tools/render.py`) and look at `output/components.png` and
   `output/assembly.png`: a passing check can hide a visibly wrong shape.
4. Note the tight margins (checks passing with less than ~20 % room) for the
   README "Tight margins" list.

## Phase 6: deliverables

- Manufacturing files: STEP per printed part (in its print orientation, or
  state the face to put on the bed), DXF per laser-cut layer
  (`ExportDXF(unit=Unit.MM)`), via the part's `__main__` and
  `tools/export_step.py`.
- BOM: every made and bought part, hardware with size, length, standard and
  torque.
- Assembly order: README steps matching `ASSEMBLY_ORDER`, including bench
  sub-assemblies and torques.
- **DVP&R** ([templates.md](templates.md#dvpr)): every requirement -> its check
  or physical test -> limit -> result (PASS with the number, or "to test").
  The physical tests (coupons, dry fit, leak, load, thermal, retention) go in
  the README "Tests to do on real parts" table, process coupons first.
- README and AGENTS updated: parts table, design text, checks list, tight
  margins, estimates to confirm.

## Done when

- [ ] requirements and concept approved by the user;
- [ ] DFMEA written; every severity >= 7 mode covered;
- [ ] every requirement in the DVP&R with a check or a test;
- [ ] every new check has a failing negative test;
- [ ] `assembly.py` ALL CHECKS PASS, pytest and ruff clean;
- [ ] renders looked at;
- [ ] manufacturing files, BOM, assembly order and test table written;
- [ ] estimates and tight margins told to the user in plain words.
