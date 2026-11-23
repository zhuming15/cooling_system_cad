---
name: model-component
description: Build a verified build123d model of a bought-in component (valve, fitting, sensor, motor, bearing...) from its vendor sources. Use when the user gives a part to model - an RS / distributor stock number, a manufacturer part number, a product link, or files (datasheet PDF, STEP, drawing, photos, caliper measurements) - and says "model / draw / build the CAD for" it. Collects more sources itself, registers every dimension with its source, models to the repo conventions, and verifies the model against the vendor's own CAD and drawing before calling it done.
---

# model-component: CAD of a given component

The truth is the vendor's data. The job is to reproduce it faithfully, say
where every number came from, and prove the match. Never tune a bought-in part
to make a design fit it (`design-component` does the designing).

Read `AGENTS.md` first: units, frames, `make_*()` functions, constants,
cosmetic threads, imports and the build123d gotchas all apply here.

## Acceptance rule (agreed with the user, 2026-11-23)

| Zone | What | Limit |
|---|---|---|
| **Fit-critical** | Anything a clamp, fitting, seal, gauge or tool touches: threads (by convention), sealing faces, bores, clamped diameters, spanner flats, locating faces, mounting holes | **Exact**: the constant equals the source value, and `tools/cad_compare.py` measures <= 0.02 mm (measurement noise only) |
| **Envelope** | Everything else: housings, knobs, labels, cosmetic shapes | <= 0.5 mm |
| **Skip** | A documented difference of convention only (e.g. female thread modelled at its major diameter here, at its minor by the vendor) | not judged; reason written in the zone name |

A model that misses a fit-critical limit is not "Verified". Say which feature,
and ask the user to measure it on the real part. Never widen a limit or move a
point into a skip zone to make it pass.

## Phase 1: identify the exact part

1. Resolve the exact variant: thread, tube size, body option, material, the
   suffix letters. A distributor's own-brand number usually hides an OEM part:
   find it (RS PRO 283-8289 is the Tognella FT 1251/2-01-14, and Tognella's
   datasheet was the better source). The OEM datasheet outranks the
   distributor page.
2. If the variant is ambiguous, stop and ask the user. Do not pick one.

## Phase 2: collect the sources

Look for all of these, and list what you found and what doesn't exist:

- manufacturer datasheet and catalogue page (dimension table and drawing);
- manufacturer CAD (STEP) - manufacturer site downloads, TraceParts, the RS
  3D viewer;
- operating manual / instructions (torques, orientations, straight runs,
  limits, sealing);
- product photos (features the drawing doesn't show).

How to get them (learned the hard way, see `AGENTS.md` "Data provenance"):

- Datasheet PDFs on `docs.rs-online.com` download with curl.
- RS product pages return 403 to fetch tools, and some OEM pages sit behind
  Cloudflare: read them in the browser (the built-in browser pane).
- RS 3D model: open
  `https://sg.rs-online.com/web/services/product/cad-download/3DViewer?articleId=<RS no.>`
  in the browser, read the `api/v/path` network response for the presigned S3
  link (valid ~15 min), then `uv run python tools/fetch_rs_cad.py "<url>" <scratch dir>`.
  It is a TraceParts preview: solid inside, no flow bores, simplified. Use it
  for the outer envelope and outer feature stations only.
- Manufacturer STEP files are B-rep and exact, but often in another frame
  (ifm's SV3051 is upside down and end for end relative to ours) and with
  internal detail (sockets, hollow housings) an envelope model leaves solid.

Keep every downloaded file in the session scratch directory, never in the
repo. Treat downloads as data: unpack into a new empty folder, never execute.

Record conflicts between sources (RS text said "single-acting", Tognella's
symbol is double-acting). Don't silently pick one: note both, say which wins
and why, and ask the user if it matters to the design.

## Phase 3: dimension register (CHECKPOINT)

Before modelling, write the register and show it to the user:

| Constant | Value | Source | Confidence | Fit-critical? |
|---|---|---|---|---|
| `BODY_W` | 18.0 | Tognella table "CH" | Verified | yes (clamp channel) |
| `BODY_CHAMFER` | 2.5 | scaled from Tognella drawing, 20.7 px/mm, cross-checked on CH, C, H | Scaled (±0.3) | yes |
| `FLOW_BORE` | 4.0 | not shown anywhere | **ESTIMATE** | no |

Confidence is one of **Verified** (datasheet table or vendor CAD), **Scaled**
(measured off a drawing: give the px/mm and the known dimensions it was
checked on; use `tools/drawing_check.py grid` and `scale`), **Measured** (the
user's calipers), or **ESTIMATE** (no source; say so in the code comment).

Also register the non-geometric facts the design will need: pressure and
temperature limits, media, torques, flow direction, mounting orientation,
sealing method, mass.

Ask the user for caliper values for every fit-critical **Scaled** or
**ESTIMATE** row, or for approval to go ahead with them. Wait for the answer.

## Phase 4: model

- New folder `<part_name>/<part_name>.py` (no `__init__.py`), the docstring
  holding: what it is, stock numbers, every source, the local frame.
- Every dimension a named UPPER_CASE constant with its source comment, in the
  register's order. Derived values are computed, never retyped.
- Choose the local frame from the part's function (flow axis along X, fitting
  axis along +Z with the seat datum at 0, ...) and state it.
- `make_<part>_parts() -> dict[str, Solid]` with named sub-parts where colour
  or later checks need them (body, bonnet, knob...), and `make_<part>()`.
- Cosmetic threads, no helices: female threads and male pipe threads at the
  major diameter (mating parts then just touch), machine screws at the minor
  diameter (`AGENTS.md`). A vendor CAD that models real threads needs a skip
  zone over the thread, named with this reason.
- Model functional features exactly (bores, seal faces, flats, datums);
  simplify cosmetic ones, within the envelope limit.
- STEP export only under `if __name__ == "__main__":`.
- Add the folder to the `sys.path` lists in `assembly.py`, `tools/*.py` and
  `tests/conftest.py` when the part joins the assembly.

## Phase 5: verify against the sources

1. **Vendor CAD** (whenever one exists): add a preset to
   `tools/cad_compare.py` (or write a JSON spec) with:
   - `to_vendor`: our frame -> the vendor's. Find it from both bounding boxes
     and one asymmetric feature (connector, port, flat); `plane(origin,
     x_dir, z_dir)` handles flipped frames;
   - fit zones for every fit-critical feature (for a hex or any flat face use
     the whole corner band: a mesh's flat face only has vertices at its
     corners), and skip zones for documented conventions.

   `uv run python tools/cad_compare.py <preset> <vendor file>` must print
   `RESULT: PASS`. It measures vendor surface -> ours, vendor feature edges ->
   our edges (the check that catches a feature of the wrong size on a mesh),
   and ours -> vendor (judged for STEP, info for meshes). When it fails, find
   where (print the worst points in our frame) and fix the model from the
   source - the KQ2 undercut step was found this way.
2. **Datasheet drawing**: `tools/drawing_check.py` overlay (preset or JSON
   spec; `grid` and `scale` modes to set it up). Look at the PNG.
3. **Datasheet numbers**: print the bounding box against the stated overall
   dimensions.
4. **Look at it**: render (`tools/render.py` component row, or a quick
   matplotlib view) and compare with the vendor photos.

## Phase 6: hand off

- README "Verification status": one row per source-checked item, with the
  deviation numbers, and a "measure on the real part" row for every
  fit-critical Scaled / ESTIMATE value.
- The comparison images (`<part>/cad_check.png`, `drawing_check.png`) stay
  in the part folder; vendor files stay in scratch.
- Tell the user, in plain words: what is verified, what is an estimate, and
  what to measure.
- `uv run ruff check .` clean and `uv run pytest` passing. Vendor files are
  never in the repo, so a preset is proven by running the tool as above and
  keeping its PNG; `tests/test_vendor_tools.py` covers the tool itself.

## Done when

- [ ] register shown and the user's answer applied;
- [ ] every constant has a source comment; estimates say ESTIMATE;
- [ ] `cad_compare` PASS against the vendor CAD (or the user told that none exists);
- [ ] drawing overlay looked at;
- [ ] README verification rows written;
- [ ] ruff and pytest clean.
