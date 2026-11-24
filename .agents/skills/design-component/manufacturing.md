# Manufacturing rules

The process limits the design checks use. Each number says where it comes
from; **ESTIMATE** means a typical value with no single source, to confirm with
a coupon (see "Process coupons"). Numbers already used by this repo name their
constant. When the user names a different machine, material or supplier, ask
for its datasheet or capability page and update the numbers here first.

Adding a process: copy a section, fill every row (with source or ESTIMATE),
add a matching check helper to `tools/checks.py` with a unit test that passes
on a good part and fails on a bad one, and a coupon to the test table.

## FDM 3D printing (PETG default, PLA)

| Item | Value | Source / constant |
|---|---|---|
| Dimensional tolerance | ±0.2 mm | ESTIMATE, `clamp.PRINT_TOL` |
| Nozzle / line width | 0.4 mm | typical printer |
| Minimum wall | 1.2 mm (3 perimeters) | `assembly.MIN_WALL`, checked by `checks.min_wall` |
| Overhang without support | 45° from vertical | common slicer default, `checks.overhangs` |
| Bridge without support | 15 mm | ESTIMATE, `assembly.BRIDGE_MAX` |
| Horizontal hole self-supporting | up to Ø10 | ESTIMATE, `assembly.HOLE_SELF_SUPPORT_R` |
| Bed size | 250 mm | ESTIMATE, `clamp.PRINT_BED`; ask the user's printer |
| Sustained contact pressure, PETG | 15 MPa | ESTIMATE, `clamp.PRINT_P_ALLOW` |
| Friction PETG on brass | 0.3 | ESTIMATE, `clamp.MU` |
| Heat deflection, PETG | 70 °C (0.45 MPa) | ESTIMATE, `assembly.HDT_PETG`; keep 20 K margin |
| Heat deflection, PLA | 55 °C | ESTIMATE; PLA only below 35 °C service |
| Density PETG | 1.27 g/cm³ | material datasheets (solid; real parts lighter) |

Design rules:

- Choose the print orientation first; strength across layers is the weak
  direction, so put bending and screw pull-out along the layers, not across.
- No support: chamfer (45°) or teardrop downward faces; horizontal holes above
  Ø10 need a teardrop or a bridge layer.
- Fixings: **heat-set inserts** for any screw that is tightened more than once
  (ruthex RX-M4x8.1: Ø5.6 hole, 14 mm deep for M4 here); captive nuts in hex
  pockets are an option; never screw into tapped plastic.
- Low screw torque (plastic creep): this repo uses 0.5 N·m for M4 into
  inserts, 0.2 N·m for M4 bearing on acrylic; re-torque after 24 h.
- Clamps that close on a part: split gap > closing travel + 2 × tolerance
  (`clamp.SPLIT_GAP` 1.0 mm), so the clamp grips before the halves touch.
- Pockets for bought parts: nominal + clearance (`clamp.POCKET_CLR` 0.15 per
  side) and a corner radius that fits the part's chamfer.
- Text and fine detail: >= 0.8 mm features.

## Laser-cut acrylic (cast PMMA)

| Item | Value | Source / constant |
|---|---|---|
| Sheet thickness | 12 mm station plate (cast: ±10 % across a sheet) | `clamp.PLATE_T`; tolerance ESTIMATE, measure the sheet |
| Pockets (stepped holes) | flat-floored, 6 mm deep, from either face; CNC router or depth-controlled engraving | `clamp.NUT_POCKET_DEPTH`, `clamp.WALL_CB_DEPTH`; checked by `checks.is_pocketed_profile` |
| Cut tolerance (hole position and size) | ±0.1 mm | ESTIMATE, `clamp.CUT_TOL` |
| Kerf | ~0.15 mm | ESTIMATE; compensate in the cutter software, not the DXF |
| Kerf taper | holes slightly conical | ESTIMATE; slip fits (dowels) need a coupon |
| Minimum hole | Ø >= sheet thickness | ESTIMATE (common shop rule) |
| Minimum web (hole to hole, hole to edge) | >= sheet thickness | ESTIMATE (common shop rule) |
| Sheet / bed size | ask the cutter (e.g. 600 × 400) | user's machine |
| Sustained contact pressure | 10 MPa | ESTIMATE, `clamp.ACRYLIC_P_ALLOW` |
| Density | 1.19 g/cm³ | material datasheets |

Design rules:

- **Holes and outline only**: every face is a sheet face or square to the
  sheet (`checks.is_flat_profile`). Counterbores, pockets and chamfers need
  a second layer (this repo's plate is two layers, solvent-welded).
- Fixings: captive nuts in through hex pockets of the back layer; clearance
  holes; dowel holes as slip fits checked by coupon. Never tap acrylic.
- Keep stress risers away from holes: round inside corners (R >= 1).
- Wall mounting: slots for adjustment; load per plug checked with
  `checks.wall_screw_load`.

## Process coupons (always the first physical tests)

| Process | Coupon | Pass when |
|---|---|---|
| FDM | 20 mm slice of each pocket / bore / dowel hole / insert hole at the real print orientation | bought part slides in with slight drag; dowel presses in; insert sets square |
| FDM | insert pull-out (screw in a set insert, pull) | holds 3 × the design preload |
| Laser | strip with the real hole sizes and hex pockets at the plate spacing; measure the sheet | dowel slides without play, nut drops in and doesn't turn, sheet within tolerance |
