# MSAP-04BFFC-SR7001 — dimension register

Amphenol LTW, M12 A-coded, four female contacts, right-angle plastic
field-installable crimp connector. Selected by the user on 2026-11-23.
This replaces the initially requested D-coded MSDP variant. Both drawings
specify the same reference length, height, coupling diameter and spanner size.

## Sources

- [OEM exact product page](https://amphenolltw.com/product-info/MetricCircularConnector/M12/MSAP-04BFFC-SR7001.html).
- [OEM drawing](https://amphenolltw.com/down.php?prod_files=429169),
  MSAP-XXBFFC-SR7001, revision F, 2023-01-03, four-contact illustration.
- [OEM STEP archive](https://amphenolltw.com/down.php?prod_files=475411),
  `MSAP-04BFFC-SR7001-STP/msap-04bffc-sr7001_sw0001.stp`.
- [OEM M12 A/B/D product specification](https://mm.digikey.com/Volume0/opasdata/d220001/medias/docus/8932/ALTW%20M.pdf),
  ratings table page 3.
- [D-coded drawing used for size comparison](https://amphenolltw.com/upload/prod_files/MSERIES/2D/MSDP-04BFFC-SR7001.pdf),
  revision C, 2020-04-08. No D-coded insert dimensions are used in the A model.

Vendor files remain outside this repository, in the browser Downloads folder
and `/tmp/flow-interconnect-sources/`. The code needs no vendor files to run.

## Datum

X is the mating axis, positive into the elbow. X=0 is the shoulder behind
the insert. The insert front is X=-9.7. The key is on +Z; the cable exits
along -Z at X=20.598554617228. Y is width. The STEP's arbitrary rotation is
recorded in `cad_spec.json`, using the insert cylinder and perpendicular
gland axis to establish the frame.

## Dimensions (mm)

All rows below are **Verified source values** (drawing labels or measured
analytic STEP surfaces). The complete model passed the CAD comparison below.
There are no Scaled, Measured or ESTIMATE fit dimensions.

| Constants / feature | Value | Source | Fit-critical? |
|---|---|---|---|
| `DRAWING_LENGTH_REF`, `DRAWING_HEIGHT_REF` | 39.3, 35.5 (reference dimensions) | A and D drawings | no |
| `DRAWING_RING_D` | 18.6 | A and D drawings | no |
| `HEX_AF` | 16 | A and D drawings | yes |
| `CABLE_OD_RANGE` | 4–7 | A drawing rev F | yes, seal range |
| `INSERT_FRONT`, `INSERT_R` | -9.7, 4.1 | A STEP face and cylinder | yes |
| `KEY_R`, `KEY_Z`, `KEY_END` | 0.65, 3.35, -1.3 | A STEP keyway cylinder and planes | yes |
| `CORE_R`, `CORE_FRONT_ROUND` | 5.25, 0.3 | A STEP rear insert shoulder cylinder and torus | yes |
| `CONTACT_PCD` | 5.0 | A STEP socket centres, ±1.767766952966 in Y and Z | yes |
| `ENTRY_R`, `ENTRY_CHAMFER_R`, `ENTRY_CHAMFER_END` | 0.65, 0.8, -9.2 | A STEP entry cylinder and cone | yes |
| `CONTACT_CAVITY_R`, `CONTACT_CAVITY_FRONT`, `INSERT_BACK` | 0.8, -8.2, 0.76 | A STEP socket pocket | yes |
| `CONTACT_CAVITY_BACK` | r0.94 at X0.9; r0.9443375672974 from X0.9 to 1.3 | A STEP rear counterbore | yes |
| `CONTACT_OUTER`, `CONTACT_INNER` | (radius, axial station) arrays in the model | A STEP contact cylinders/cones | yes |
| `CONTACT_SLOT_W`, `CONTACT_SLOT_END`, `CONTACT_SLOT_ANGLE` | 0.3, -3.95, 28.531244° | A STEP slot planes | yes |
| `SEAL_MAJOR_R`, `SEAL_MINOR_R`, `SEAL_X` | 4.25, 0.75, -0.75 | A STEP torus | yes |
| `THREAD_MAJOR_R`, `THREAD_FLOOR` | 6.0, 1.3 | A STEP M12 thread root and rear face | yes, cosmetic convention |
| `THREAD_LEAD_R`, `THREAD_LEAD_LENGTH` | 6.4585, 1 | A STEP thread entrance cone | yes, cosmetic convention |
| `COUPLING_FRONT`, `COUPLING_HEX_START` | -7.85, -1.7 | A STEP planes | yes at hex |
| `BODY_OFFSET` | -0.001445382772 | A STEP elbow placement relative to insert | derived datum |
| `COUPLING_HEX_END`, `REAR_RING_END` | 2.3 + offset, 8.3 + offset | A STEP planes | yes at hex |
| `BODY_START`, `BODY_BACK`, `CABLE_X` | (9.8, 29.6, 20.6) + offset | A STEP cylinders/planes | no |
| `BODY_R`, `BODY_HALF_W`, `BODY_BACK_ROUND`, `BODY_BOTTOM` | 8.5, 8, 1, -11 | A STEP cylinder, flats, torus, plane | no |
| `BODY_NECK_R`, `BODY_NECK_START` | 7.8, 3.4 + offset | A STEP neck | no |
| `NECK_R`, `NECK_END` | mean of STEP thread root 7.375 and crest 7.916; -22.5 | Cosmetic gland thread envelope | no, assembled housing envelope |
| Gland axial stations | -14.5, -15.5, -23.5, -26.5, -27 | A STEP lip, grip, hex and end planes | yes at hex/entry |
| `GLAND_LIP_R` | 9.25 | A STEP cylinder | no |
| `GLAND_GRIP_ROOT_R`, `GLAND_GRIP_END_SLOPE` | 9.0 at Z-23.5, slope 1 (45°) | A STEP cone at grip-to-hex transition | yes at hex edge |
| `GLAND_BORE` | r5.5/-27, r4.5/-26, r4.5/-25.0173, r6.0699/-23.7 | A STEP entry cone/cylinder | yes |
| `CABLE_BORE_END` | -23.7 | A STEP cage end face | yes |
| `CONNECTOR_HEX_PROFILE`, `GLAND_HEX_PROFILE` | analytic line/arc arrays in `interconnect_profiles.py` | A STEP sections at X0.01 and Z-25 | yes |
| `GLAND_CAGE_PROFILE` | serrated line/arc array | A STEP face 77 at Z-23.7 | yes |
| Front/rear/gland grip profiles | analytic line/arc arrays | A STEP outer sections at X-4, X4, Z-20 | no |

The profiles store edge endpoints and, for circular arcs, a point on the arc.
They preserve the mould parting flats, rounds and ribs that a perfect regular
hexagon or plain cylinder would lose. Coordinates are rounded to 1e-8 mm.
`CUT_MARGIN` and `GEOMETRY_EPS` are construction controls, not vendor dimensions.

## Ratings, materials and source conflicts

- 4 A, 250 V, −40 to +105 °C: OEM specification, four-contact A-code,
  field-installable rows. Mass 15 g: exact OEM product page.
- IP67 **mated**: drawing rev F and exact product page.
- Contacts: gold-plated copper alloy. Housing, extension nut, coupling nut,
  clamp ring and sealing nut: black thermoplastic. Seal and O-ring: grey
  rubber. These are the A drawing's material descriptions; do not carry
  the D drawing's more specific silicone claim over to this variant.
- Wire size 20–24 AWG: A drawing rev F.
- The drawing says cable OD 4–7 mm; the product page says 4–8 mm. Use the
  drawing's 4–7 mm limit until Amphenol or the supplied seal confirms 8 mm.
- The generic specification supplies electrical/environmental ratings. The
  A drawing rev F does **not** specify tightening torques. The old D drawing's
  torque values are not adopted as verified A-variant requirements.
- The OEM product page and loose-contact drawing identify crimp termination.
  This model follows the OEM information.
- Nominal dimensions agree between A and D drawings; their STEP internals
  differ, so the A model is built from its own CAD.
- Complete A STEP envelope: approximately 39.5486 × 19.0 × 36.5 mm. The
  drawing's 35.5 reference height starts at the housing top, excluding the
  higher coupling ribs. Its Ø18.6 callout does not capture the rear grip's
  19.0 mm extreme. The model follows the actual STEP geometry.

## Modeling scope

The component is placed in `assembly.build()` and counted once in the station
BOM. M12 coding is A, matching the coding documented for the SV3051. The
uncompressed seal tangent seats on the M12 top at Z42.25, giving a plug datum
at Z43.75; the key follows the ifm −45° phase. The cable outlet points outward
and downstream. No wiring assignment or cable routing is modeled.

The source CAD dimensions conflict at the mating cylinder: Amphenol insert
Ø8.20 mm versus ifm socket Ø8.15 mm. Nominal mating overlaps by about 5.00 mm³
(0.025 mm radially). The source geometry and strict interference check remain
unchanged. **The user confirmed on 2026-11-23 that these exact parts fit
together physically.** The all-pairs check accounts for only the nominal
0.025 mm radial cylindrical skin at this pair, with the original 0.001 mm³
limit everywhere outside it. A deliberate insert offset fails the check.
Standalone CAD geometry remains unchanged and source-verified.

The M12 female thread is represented at its major diameter with a cosmetic
lead-in. That difference is the named skip zone. The gland's secondary
thread uses a smooth envelope between its root and crest. Internal wiring
space is filled; the comparison tool reports omitted vendor internal faces
as information under its existing envelope convention. Exposed socket bores,
contact springs, A key, seal, hex profiles and cable-entry cage are modeled.
Raised lettering and small exterior blends are simplified. No cable or
wire routing is modeled.

## Reproduce

```bash
uv run python flowmeter_electronic_interconnect/flowmeter_electronic_interconnect.py
uv run python tools/export_interconnect.py
uv run python tools/cad_compare.py flowmeter_electronic_interconnect/cad_spec.json <OEM-A-STEP>
uv run python tools/drawing_check.py flowmeter_electronic_interconnect/drawing_spec.json <OEM-A-drawing-PDF>
```

The drawing overlay uses 6.06 px/mm at 154 dpi: the 39.3 mm reference spans
about 238 pixels, checked against Ø18.6 and the 35.5 mm vertical reference.

## Verification results — 2026-11-23

`cad_compare.py` **PASS** against the exact A-coded OEM STEP:

- A-coded insert, four contacts, seal, connector flats and gland flats:
  all surface and feature-edge deviations below 0.001 mm (limit 0.02 mm).
- Exterior: vendor→model maximum 0.292 mm; model→vendor maximum 0.414 mm
  (limit 0.5 mm).
- 15,000 vendor surface samples, 40,327 model surface samples and 4,843
  fit-critical feature-edge samples. The same sampled points are used when
  computing exact distances in the part frame for tighter search bounds.
- M12 helical thread skipped only for the documented cosmetic convention.
  Filled internal wiring space is reported separately, not exterior accuracy.
- CAD section and drawing-overlay PNGs inspected; standalone STEP and
  two-view render regenerated and inspected.
- Station acceptance: **ALL CHECKS PASS**. Full pytest: **52 passed**.
  Latest component/vendor-tool tests after the gland correction: **16 passed**.
  Ruff and whitespace checks clean.

The standalone STEP is
`output/flowmeter_electronic_interconnect_msap-04bffc-sr7001.step`; the preview
is `output/flowmeter_electronic_interconnect.png`. The station exporter also includes this component in its assembly, per-part
STEP and BOM.

## Station integration verification

- User-confirmed dry fit of these exact parts, recorded 2026-11-23.
- Coaxial mating, A-code key phase, uncompressed seal datum, vertical insertion,
  and station assembly order checked from placed geometry.
- All **71 station design checks** pass; full pytest **63 passed**.
- OEM CAD comparison re-run after integration: **PASS**, with the same
  <0.001 mm fit and 0.414 mm maximum exterior deviations. CAD and drawing
  comparison images inspected again. Ruff clean.
- Flowmeter strap torque changed to 0.55 N·m; valve cap remains 0.5 N·m.
  The placed cable-exit centre has a 67.12 mm arm about the flow axis. Estimated
  friction gives ×5.11 margin at 50 N; washer pressure 14.0/15 MPa. Friction,
  preload and PETG strength remain engineering estimates; recheck torque after
  24 hours. Negative tests reject 0.5 N·m (pull margin) and 0.6 N·m (PETG stress).
- STEP export/re-import verifies 75 solids in the station, with 21 distinct
  components in its BOM, including one MSAP connector. A dedicated fitted
  flowmeter STEP and PNG are in `output/flowmeter_fitted.*`.
