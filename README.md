# Flow station: flowmeter and flow control valve on one wall plate

Parametric CAD (Python, [build123d](https://github.com/gumyr/build123d)) for a
small wall-mounted water station. Water passes through an ifm SV3051 vortex
flowmeter, a short straight 12 mm tube, and a needle valve. Seen from the
front, flow runs left to right:

```
inlet tube → ifm SV3051 flowmeter → 140.3 mm link tube → RS 283-8289 needle valve → outlet tube
```

Both components sit in 3D-printed PETG clamps on a laser-cut acrylic plate,
which screws to the wall.

[![Flow station assembly](output/assembly.png)](https://3dviewer.net/#model=https://raw.githubusercontent.com/zhuming15/cooling_system_cad/main/output/step/00_flow_station_assembly.step)

[Open the assembly in a 3D viewer](https://3dviewer.net/#model=https://raw.githubusercontent.com/zhuming15/cooling_system_cad/main/output/step/00_flow_station_assembly.step)
(runs in the browser; it loads `output/step/00_flow_station_assembly.step` from
`main`, so it shows the last pushed version).

Contents: [Ratings](#ratings) · [Bill of materials](#bill-of-materials) ·
[Manufacturing](#manufacturing) · [Assembly](#assembly) ·
[Tests on real parts](#tests-on-real-parts) ·
[How the design works](#how-the-design-works) · [Open items](#open-items) ·
[Part data sources](#where-the-part-dimensions-come-from) ·
[Working with the code](#working-with-the-code) ·
[Maintaining the design](#maintaining-the-design)

## Ratings

| | |
|---|---|
| Medium | Water |
| Pressure | 6 bar max (limited by the Festo QSF fittings) |
| Water temperature | 0–40 °C (limited by the SMC KQ2 fittings) |
| Flow measured | 0.5–10 l/min (SV3051) |
| Tube | 12 mm OD × 8 mm ID, PU or PA |
| Station size | 300 × 92 mm plate; 78 mm deep from the wall to the valve knob |

The valve itself is rated 210 bar and the meter 16 bar. Don't use those
numbers for the station.

## Bill of materials

`output/step/bom.csv` is generated from the model and lists every part with
its STEP file.

### Bought-in parts

| Part | Qty | Model |
|---|---|---|
| ifm SV3051 vortex flowmeter, G1/2 male both ends | 1 | `flowmeter/flowmeter.py` |
| Festo QSF-1/2-12-B push-in fitting, G1/2 female × 12 mm tube | 2 | `flowmeter_connector/flowmeter_connector.py` |
| RS PRO 283-8289 needle valve, G1/4 (made by Tognella, FT 1251/2-01-14) | 1 | `valve/valve.py` |
| SMC KQ2H12-U02A push-in fitting, 12 mm tube × G1/4 male | 2 | `valve_connector/valve_connector.py` |
| G1/2 flat sealing washer, OD ≤ 18.6, ID ≥ 11.5, about 1 mm, FKM or EPDM (see [Open items](#open-items)) | 2 | |
| 12 × 8 mm tube: link 140.3 mm cut square, plus inlet (≥ 100 mm straight) and outlet | | |

### Made parts

| Part | Qty | Process | File |
|---|---|---|---|
| Station plate, wall layer | 1 | Laser cut, 6 mm cast acrylic | `flowmeter_clamp/base_back.dxf` |
| Station plate, front layer | 1 | Laser cut, 6 mm cast acrylic | `flowmeter_clamp/base_front.dxf` |
| Valve clamp base | 1 | FDM print, PETG | `output/step/07_valve_clamp_base.step` |
| Valve clamp cap | 1 | FDM print, PETG | `output/step/08_valve_clamp_cap.step` |
| Flowmeter clamp base (both pedestals and the locating pad, one piece) | 1 | FDM print, PETG | `output/step/09_flowmeter_clamp_base.step` |
| Flowmeter strap | 2 | FDM print, PETG | `output/step/10_flowmeter_clamp_strap.step` |

### Hardware

| Part | Qty | Where | Torque |
|---|---|---|---|
| Dowel pin ISO 8734, Ø4 m6 × 12 | 4 | Locate each clamp base on the plate | |
| ISO 4762 M4 × 16 and M4 × 12 | 2 + 2 | Clamp bases to the plate | 0.2 N·m |
| ISO 4032 M4 nut | 4 | Captive in the plate | |
| ISO 4762 M4 × 20 + DIN 125 washer | 4 | Valve cap | 0.5 N·m |
| ISO 4762 M4 × 30 + DIN 125 washer | 4 | Flowmeter straps | 0.5 N·m |
| Heat-set insert M4 × 8.1 (ruthex RX-M4x8.1 or equal), Ø5.6 hole | 8 | In the clamp bases | |
| M6 socket head screw + wall plug | 8 | Plate to the wall | |

## Manufacturing

### Laser-cut plate

- Two layers of 6 mm cast acrylic. The DXFs are in mm, outlines on layer
  `CUT`. Regenerate them with `uv run python flowmeter_clamp/flowmeter_clamp.py`.
- Cut all the dowel holes in the front layer in one job. The two clamps are
  only coaxial if their dowel holes come from the same cut.
- Solvent-weld the two layers together. The M4 nuts go into the hex pockets
  from the wall side before the plate goes on the wall; the wall then traps
  them.
- The design assumes ±0.1 mm on hole positions. Cut the calibration coupon
  first (test 2 below).

### Printed parts

- PETG. Walls are at least 1.2 mm, which is 3 perimeters with a 0.4 mm nozzle.
- Print orientation:
  - clamp bases and the valve cap: the wall-side face on the bed;
  - straps: on their end face.

  In that orientation nothing needs support: the longest bridge is under
  15 mm, and the only curved overhangs are holes up to Ø10.
- Every part fits a 250 mm bed. The largest is the flowmeter clamp base,
  120 mm long.
- The STEP files in `output/step/` are not rotated into print orientation.
  Lay them on the face given above in the slicer.
- The caps and straps are exported in their as-printed position. In
  service, they close 0.15 mm further onto the part they clamp.
- The design assumes ±0.2 mm on printed features. The 1.0 mm gap between
  each cap or strap and its base is sized for that. Print the coupon first
  (test 3 below).
- Press 2 dowel pins into each clamp base. Set the M4 inserts into its split
  face with a soldering iron.

## Assembly

1. **On the bench:**
   - Screw both KQ2 fittings into the valve with a 19 mm spanner.
   - Screw both QSF fittings onto the flowmeter, each with a flat G1/2
     washer. Hold the meter by its 12 mm flats, and tighten to 12 N·m at
     most: the meter body is plastic.
   - Push the 140.3 mm link tube fully home into the flowmeter outlet QSF
     and the valve KQ2, with the parts lying straight. The flow arrow on the
     meter must point at the valve.

   The link tube is cut exactly stop-to-stop, so it can't be fitted once
   both parts are clamped. That's why the meter, tube and valve go in as one
   unit.
2. Screw the plate to the wall with 8 × M6. The vertical slots give ±3 mm of
   adjustment and move both clamps together.
3. Push each clamp base onto its dowel holes and fix it with 2 × M4 through
   the channel floor at **0.2 N·m**. This torque has a narrow window: at
   0.15 N·m the valve base can tip under a hard tube pull; at 0.3 N·m the
   nut starts to crush the acrylic.
4. Lower the bench unit into both clamp bases at once, with the meter's
   housing and M12 connector on top and the valve knob facing out.
   - The fitting hexes can sit at any angle; the straps grip the round body
     next to the hex.
   - The meter's lower 12 mm flat rests on the locating pad of its clamp
     base. That sets its angle.
5. Fit the valve cap with 4 × M4 × 20 and washers, and the two straps with
   M4 × 30 and washers. Tighten evenly to **0.5 N·m**. Re-check after 24 h.
6. Push in the inlet and outlet tubes. Keep at least 100 mm of straight tube
   ahead of the meter, and support the tubes beyond the station.

## Tests on real parts

The model is checked in software (see [Design checks](#design-checks)). These
tests need the real parts, in this order:

| # | Test | How | Pass when |
|---|---|---|---|
| 1 | Measure the bought-in parts | Calipers on the valve body (18 × 18, chamfers, port chamfer), the QSF round body (Ø20.8 × 15.3), the KQ2 hex, and the meter's end faces | Within 0.1 mm of the model; otherwise update the part file and re-run the checks |
| 2 | Laser coupon | Cut a strip with Ø4.1 dowel holes, Ø4.5 holes and a 7.2 AF hex at the plate spacing; measure the sheet | Dowel slides in with no play you can feel; nut drops in and doesn't turn; sheet 5.4–6.6 mm |
| 3 | Print coupon | Print a 20 mm slice of each clamp (channel, bore, dowel hole, insert hole) | Valve body and QSF body slide in with slight drag; dowel presses in with a hand vise; insert sets square |
| 4 | Insert pull-out | M4 into a set insert in the coupon, pull | Holds about 1.9 kN (3 × the 625 N screw preload) |
| 5 | Dry fit | Assemble without tightening | Every step goes in by hand; the bench unit drops into both bases without forcing the tube |
| 6 | Clamp gap | Feeler gauge at the split faces of the cap and both straps after tightening | Gap still open at all four corners (model: 0.85 mm) |
| 7 | Leak | Fill with water, 6 bar, hold 30 min | No pressure drop, no weep at the threads or tubes |
| 8 | Torque retention | Re-check all M4 after 24 h and after 1 week | Less than about 30 % loss; otherwise add wave washers |
| 9 | Pull and twist | 500 N axial pull on the outlet tube; 50 N sideways on the M12 cable | Nothing moves; the meter stays on its pad |
| 10 | Valve use | Open and close the valve fully 20 times | The valve doesn't turn or shift in its clamp |
| 11 | Thermal | Run with water at 5 °C and at 40 °C, an hour each | No leaks, no visible tube bow, clamps still tight |
| 12 | Alignment | With the straps loose, sight along the link tube, then tighten | No visible bend, and the meter doesn't jump (model worst case 1.24 mm offset) |

## How the design works

- **Meter upstream of the valve.** The valve keeps the meter under
  back-pressure, which ifm asks for to avoid cavitation, and the valve's
  turbulence stays downstream of the measurement. The meter is directional
  (arrow on the pipe). The valve is not: Tognella's datasheet shows it
  double-acting, so either port can be the inlet. (RS's product text says
  "single-acting"; that is wrong.)
- **Straight runs.** ifm wants at least 15 × DN = 90 mm of straight pipe
  before and after the meter, and advises against mounting it directly in
  front of a valve (manual 11592037, sec. 4). The link tube has 100 mm of free straight length.
- **Meter position.** Pipe horizontal, housing and M12 connector on top:
  ifm's recommended position (manual Fig. 1). The plate hangs on the wall
  with the pipe parallel to it.
- **Modular clamps.** The plate has holes only. Each clamp base is located
  by 2 steel dowels and held by 2 M4 into captive nuts. Its cap or straps
  screw into heat-set inserts in the base. The base screws sit under the
  channel floor, so they are reachable until the component goes in.
- **Valve clamp.** The square valve body sits in a channel split between
  base and cap. The halves stop 1.0 mm short of each other, more than the
  2 × 0.2 mm print tolerance, so the cap always bears on the valve, not on
  the base. The knob comes out through a Ø27.5 hole in the cap.
- **Flowmeter clamp.**
  - The straps grip the round Ø20.8 body of each QSF fitting, never the hex.
    How far a fitting turns when it is tightened decides where its hex ends
    up, so the hex angle can't be controlled. A check spins each fitting
    through a full hex pitch to prove any angle fits.
  - The meter's angle comes from the meter itself: its lower 12 mm flat
    rests on a pad on the clamp base. Gravity keeps it there; the pad
    carries no screw load.
  - All clamp load goes through the brass fittings, so tube loads never pass
    through the meter's plastic threads.
  - The QSF fittings are tightened on the bench, with the meter held by its
    flats. The printed straps are not meant to take the thread torque.
- **No strain on the link tube.** The tube must be straight, with no side
  offset and no axial load:
  - Both clamp bases locate on dowel holes cut in one pass in the same plate
    layer, and both flowmeter pedestals are one printed part. At worst-case
    tolerances (print ±0.2, laser ±0.1), the side offset is 1.24 mm. That
    bends the 100 mm free tube by 0.45 %, under the 0.5 % limit.
  - Valve and meter sit on their cradle floors with the same 0.15 mm
    clearance, so both axes are the same distance from the wall.
  - The tube is cut stop-to-stop. The straps allow ±1.65 mm of axial float:
    push the tube home first and tighten the straps after, and the meter
    settles where the tube puts it.

### Tight margins

These pass, but with little room. Re-check them after any change nearby:

- Worst-case link-tube strain: 0.45 % against a 0.5 % limit.
- Valve clamp base against tipping under a 500 N tube pull: × 1.17.
- Clamp-base screw torque: 0.2 N·m (0.15 lets the valve base tip; 0.3
  overloads the acrylic).
- Contact pressure: washer on PETG 12.7 MPa (limit 15), nut on acrylic
  9.4 MPa (limit 10).

## Open items

- **Seal at the meter's end faces.** The design uses a flat G1/2 washer
  between the meter and each QSF fitting. ifm's 3D model shows a seal-ring
  groove in each end face (ID 12.85, OD 16.75, 1.2 deep). With that groove,
  a flat washer only bears on two narrow lands, Ø11.7–12.65 and Ø16.95–18.4.
  Check on a real meter, or in ifm manual 11592037, whether it ships with
  seal rings in the grooves before ordering washers.
- **Material values are estimates** (no single source): PETG 15 MPa and
  acrylic 10 MPa allowable contact pressure, friction 0.3 PETG on brass,
  print ±0.2 mm, laser ±0.1 mm, tube strain limit 0.5 %, tube expansion
  150e-6/K, PETG heat limit 70 °C, 100 N per wall plug. The clamp gaps,
  pressures and strain checks depend on them; the coupons and tests above
  confirm them.
- **Valve port chamfer.** The KQ2 gasket seats on the chamfer of the female
  thread (SMC catalogue). Check that the valve ports have one.
- **Load cases** (500 N tube pull, 50 N cable pull, plasterboard wall) are
  engineering judgement agreed with the owner, not from a standard.

## Where the part dimensions come from

Every bought-in part is modelled from its vendor's data and compared with the
vendor's own 3D model by `tools/cad_compare.py`. Features that something
touches (threads, sealing faces, clamped diameters, spanner flats) must match
within 0.02 mm; the rest of the outline within 0.5 mm.

| Part | Sources | Result |
|---|---|---|
| ifm SV3051 | ifm datasheet SV3051-00, ifm STEP CAD_STP_300_0358, manual 11592037 (torque 12 N·m, straight runs, orientation) | All dimensions read off the STEP. G1/2 ends, end-face groove, shoulder, bore, 16 AF hex and 12 AF flats within 0.001 mm; outline within 0.32 mm. The datasheet lists a display; this unit has none, so none is modelled |
| Festo QSF-1/2-12-B | Festo datasheet 190653, RS/TraceParts 3D model | Round body, hex and port face within 0.003 mm; outline 0.01 mm. Insertion depth 23.3 mm |
| SMC KQ2H12-U02A | SMC KQ2 catalogue, RS/TraceParts 3D model | Thread, undercut, seal face and hex within 0.001 mm |
| RS 283-8289 valve | Tognella FT 1251/2-01 datasheet, table type 14 | Body 18 × 18 × 46, G1/4 ports 12 deep, M17×1 bush, Ø22 knob, height 57 from the table. Edge chamfer 2.5, boss 18 × 2.5 and the back groove scaled from the drawing (±0.3 mm). No vendor 3D model exists |

The comparison images are in each part folder (`cad_check.png`,
`drawing_check.png`).

## Working with the code

### Setup

Needs Python 3.12 and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
```

### Commands

```bash
uv run python assembly.py           # build the station, run the design checks (~1 min)
uv run pytest                       # tests (-m "not slow" for the quick ones)
uv run python tools/export_step.py  # output/step/: one STEP per part, assembly STEP, bom.csv
uv run python tools/render.py       # output/assembly.png, output/components.png
uv run python flowmeter_clamp/flowmeter_clamp.py   # plate DXFs + flowmeter clamp sizes
uv run python valve_clamp/clamp.py                 # valve clamp sizes
uv run ruff check .
```

To look at the model interactively, start the standalone OCP CAD viewer
with `uv run python -m ocp_viewer`, open http://127.0.0.1:3939/viewer, then:

```bash
uv run python tools/view.py            # whole station
uv run python tools/view.py exploded   # pulled apart in assembly order
uv run python tools/view.py flowmeter  # or valve, connector, base, cap, flowmeter_connector, flowmeter_fitted
```

### Repository layout

```
assembly.py            places every part, runs the design checks, writes output/
valve/                 needle valve model
valve_connector/       SMC KQ2 fitting model
valve_clamp/           valve clamp base + cap; shared constants (tolerances, hardware)
flowmeter/             ifm SV3051 model
flowmeter_connector/   Festo QSF fitting model
flowmeter_clamp/       flowmeter clamp base + straps; station plate and its DXFs
tools/checks.py        reusable check library (interference, access, stacks, loads, printing)
tools/export_step.py   STEP export and BOM
tools/render.py        PNG renders
tools/view.py          send the model to the OCP CAD viewer (ocp_viewer)
tools/cad_compare.py   compare a part model with the vendor's 3D model
tools/drawing_check.py overlay a part model on its datasheet drawing
tools/fetch_rs_cad.py  unpack an RS website 3D model
tests/                 pytest
output/                generated, don't edit: STEP files, BOM, renders
```

Each part file has its dimensions as named constants at the top, each with
its source, and `make_*()` functions that return the solid. The clamps are
sized from the part constants, so a corrected part dimension carries through
to the clamps.

Coordinates: the wall is Y = 0 with +Y out of the wall, Z is up, and the
flow axis runs along X, 30 mm from the wall. Flow goes towards −X, which is
left to right for someone facing the wall. Units are mm. Each part file's
docstring gives its own local frame.

### Design checks

`assembly.py` prints PASS or FAIL for each check and exits non-zero if any
fail. The checks cover:

- interference between every pair of parts;
- clamping: each cap or strap closes on its part before it reaches the base,
  slip and rotation resistance, and contact pressure on the plastics;
- tool access to every screw, and operator access to the knob, the release
  collars and the M12 plug;
- fitting engagement, seal seating and flow direction (read from the placed
  geometry, so a meter mounted backwards fails);
- link-tube alignment and strain: worst case, RSS, Monte Carlo and thermal;
- the flowmeter clamp at every fitting hex angle;
- screw preload, tipping under a 500 N tube pull, wall-screw loads;
- that every assembly step can move into place in order without a collision;
- printability: no support needed, minimum wall thickness, bed size.

`uv run pytest` runs the same checks as tests. It also breaks the design on
purpose (meter mounted backwards, link tube fitted last, looser tolerances)
and checks that the matching check fails.

## Maintaining the design

### After any geometry change

1. `uv run python assembly.py` must end with `ALL CHECKS PASS`. If a check
   fails, fix the design. Don't loosen a limit or delete a check to get a
   pass; if a check is wrong, fix the check and say why in the commit.
2. `uv run pytest` must pass. A new or changed check needs a negative test
   in `tests/test_assembly.py` that breaks the design and expects that check
   to fail.
3. Run `tools/export_step.py` and `tools/render.py` (and
   `flowmeter_clamp/flowmeter_clamp.py` if the plate changed), then look at
   `output/assembly.png` and `output/components.png`. A passing check can
   still hide a wrong shape.
4. `uv run ruff check .` must be clean.
5. Commit and push `output/` with the change, so the online viewer and the
   manufacturing files match the code.

### Replacing or correcting a bought-in part

- Every dimension must come from a datasheet, catalogue or vendor 3D model,
  and its constant says which. Mark anything else `ESTIMATE` in the code.
- If you measure a real part with calipers, change the part file, not the
  clamp. The clamps resize from the part constants.
- Re-run the vendor comparison and look at the image it writes:

  ```bash
  uv run python tools/cad_compare.py flowmeter <ifm STEP file>
  uv run python tools/drawing_check.py flowmeter <SV3051 datasheet pdf>
  ```

  Presets exist for `valve_connector`, `flowmeter_connector` and
  `flowmeter`. Keep downloaded vendor files outside the repo; only the
  comparison images are kept here.
- Where to get the vendor data:
  - ifm publishes the SV3051 datasheet, manual 11592037 and STEP model on
    the product page (Downloads tab).
  - RS product pages block scripts; open them in a browser. Datasheet PDFs
    on `docs.rs-online.com` download normally.
  - RS's 3D viewer models are simplified TraceParts meshes, solid inside and
    without bores: good for the outline only. `tools/fetch_rs_cad.py`
    unpacks one; its docstring explains how to get the link.

### Adding a part to the station

- Give it a `make_*()` function in its part file, and add it in
  `assembly.build()` with a name that follows the existing pattern
  (`valve_knob`, `fm_clamp_strap_0`, `m4_nut_*`, ...). The checks, the
  colours in `tools/render.py`, the exploded view in `tools/view.py` and
  `tools/dims.py` all look parts up by name.
- Add it to an assembly step in `assembly.ASSEMBLY_ORDER`, or the
  assembly-order check fails.
- Add it to `SUBASSEMBLIES`, `components()` and `QTY_PATTERN` in
  `tools/export_step.py`, or the export fails.

### Rules that keep the design working

- Never clamp or locate on a fitting's hex: its angle depends on how tight
  the thread is. Clamp on round features and take angles from features on
  the part body.
- The link tube must stay straight and unstrained: both clamp bases dowel
  into the same plate layer, the valve and meter pocket clearances stay
  equal, and the tube length comes from the two tube stops, never a typed
  number.
- Threads are modelled without helices: female threads at the major
  diameter, screw threads at the minor diameter, so threaded joints don't
  show as interference.
- Screws go into heat-set inserts (printed parts) or captive nuts (plate),
  never into tapped plastic. Keep contact pressures under the PETG and
  acrylic allowables in `valve_clamp/clamp.py`.
- Caps and straps are modelled in two positions: clamped (in the assembly)
  and as printed (for export). The 1.0 mm split gap must stay larger than
  the clamp travel plus twice the print tolerance.
- Part folders are not Python packages. Scripts add the repo root and part
  folders to `sys.path`; keep that pattern.
