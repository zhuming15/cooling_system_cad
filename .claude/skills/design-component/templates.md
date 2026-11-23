# Templates

## Requirements checklist

Ask what isn't already known; propose a default with a reason for the rest.

- **Function**: what it holds, joins, guides or protects; what it must never do
  (e.g. never clamp a screwed-on hex).
- **Interfaces**: each bought-in part it touches (modelled with
  model-component first), and how the design itself mounts (wall, plate,
  rail, bench).
- **Loads**: pulls, torques, weight, pressure thrust, vibration, knocks; the
  design load and the factor of safety.
- **Alignment and fit**: offsets, straightness, axial strain limits between
  parts.
- **Environment**: temperature range, water / chemicals, UV, indoor / outdoor.
- **Manufacturing**: process (FDM, laser, ...), material, the user's machine
  (bed, sheet size), quantity, tools at hand, supplier if any.
- **Use and service**: assembly order, what is replaced or adjusted, operator
  access (knobs, release rings, cables, line of sight), torques the user can
  apply.
- **Standards / rules**: vendor instructions (straight runs, orientations,
  torques), safety.
- **Constraints vs preferences**: which are hard limits, which are wishes.

Write them as:

| ID | Requirement | Limit | Verified by |
|---|---|---|---|
| R1 | Link tube is straight between the fittings | bending strain < 0.5 % at worst-case tolerance | check: section 7 |
| R2 | Parts print without support | bridge <= 15 mm, overhangs only on holes <= Ø10 | check: section 11 |
| R3 | Holds a 500 N tube pull | slip resistance > 500 N | check: section 2; test: pull test |

## Concept trade-off

| Criterion | Weight | Concept A | Concept B | Concept C |
|---|---|---|---|---|
| Meets every hard requirement | must | yes / no (which) | | |
| Makeable in the chosen process | must | | | |
| Alignment / tolerance stack | 3 | short stack, 1 plate layer | | |
| Assembly and service | 3 | | | |
| Part count, hardware | 2 | | | |
| Print / cut time, material | 1 | | | |
| **Score** (1-5 × weight) | | | | |

End with a recommendation and its reason.

## DFMEA

Severity (S), occurrence (O), detection (D) on 1-10; RPN = S × O × D. Every
S >= 7 or RPN >= 100 row needs a design action, and a check or test.

| Function | Failure mode | Effect | Cause | S | O | D | RPN | Action / check / test |
|---|---|---|---|---|---|---|---|---|
| Keep link tube straight | Clamp axes offset | Tube bends, fitting leaks | Print + laser tolerance stack | 7 | 4 | 3 | 84 | Dowels in one plate layer; check: worst case + MC + RSS; test: alignment |
| Assemble the station | Link tube can't be fitted | Can't build | Tube cut stop-to-stop between fixed fittings | 8 | 9 | 2 | 144 | Bench unit; check: assembly-order sweep |
| Grip the fitting | Clamp on a hex | Angle uncontrolled, clash | Thread tightness sets the hex angle | 6 | 8 | 2 | 96 | Clamp round body; check: phase sweep |

## DVP&R

Design Verification Plan & Report: one row per requirement (and per DFMEA
action), kept current until every row has a result.

| Req | Verification | Method | Limit | Result | Status |
|---|---|---|---|---|---|
| R1 | link tube strain, worst case | `assembly.py` section 7 | < 0.5 % | 0.45 % | PASS (tight) |
| R1 | alignment on real parts | physical test 12 | no visible bend, no jump | - | to test |
| R2 | printed parts need no support | `assembly.py` section 11 | bridge <= 15 mm | 9.5 mm | PASS |
| R3 | 500 N tube pull | physical test 9 | nothing moves | - | to test |
