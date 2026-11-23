# flow — wall-mounted flowmeter and flow control valve station

Parametric CAD (build123d) for a wall-mounted water flow station. Seen from the
operator's side, flow runs left to right:

```
inlet tube → ifm SV3051 flowmeter → straight 12 mm link tube → RS 283-8289 valve → outlet tube
```

| Part | Source | Qty |
|---|---|---|
| ifm SV3051 vortex flow meter, water 0.5–10 l/min, G1/2 male | `flowmeter/flowmeter.py` | 1 |
| Festo QSF-1/2-12-B push-in fitting, G1/2 female × 12 mm tube | `flowmeter_connector/flowmeter_connector.py` | 2 |
| RS PRO 283-8289 in-line flow control valve, G1/4, 210 bar (= Tognella FT 1251/2-01-14) | `valve/valve.py` | 1 |
| SMC KQ2H12-U02A push-in male connector, 12 mm tube × Uni 1/4 | `valve_connector/valve_connector.py` | 2 |
| **Station base**: plate with holes only, 2 × 6 mm laser-cut acrylic layers (wall layer + front layer), 300 × 92 | `flowmeter_clamp/flowmeter_clamp.py` | 1 + 1 |
| Valve clamp base + cap, 3D printed PETG | `valve_clamp/clamp.py` | 1 + 1 |
| Flowmeter clamp base (2 pedestals + pad, one piece) + strap, 3D printed PETG | `flowmeter_clamp/flowmeter_clamp.py` | 1 + 2 |
| ISO 8734 dowel pin Ø4 m6 × 12 (locates each clamp base on the plate) | — | 4 |
| ISO 4762 M4×16 / M4×12 + ISO 4032 M4 nut captive in the plate (clamp bases), 0.2 N·m | — | 2 + 2 (+4 nuts) |
| ISO 4762 M4×20 / M4×30 + DIN 125 washer into heat-set M4 inserts (cap, straps), 0.5 N·m | — | 4 + 4 (+8 inserts) |
| Heat-set insert M4 × 8.1 (ruthex RX-M4x8.1 or similar, Ø5.6 hole) | — | 8 |
| M6 socket screw + wall plug (wall fixing) | — | 8 |
| G1/2 flat sealing washer, OD ≤ 18.6, ID ≥ 11.5, ~1 mm, FKM/EPDM | — | 2 |
| 12 × 8 mm tube: inlet (≥ 100 mm straight), 140.3 mm link, outlet | — | — |

### Design

- **Flow direction.** The valve has no flow direction; either port can be the
  inlet. Tognella's datasheet shows it as double-acting, and you've confirmed
  it; RS's product text calling it "single-acting" is wrong. The flowmeter does have one, so it is turned to make its arrow point
  along the system flow, toward the valve. The flowmeter sits upstream of the
  valve, for two reasons. First, the valve keeps the meter under
  back-pressure, which ifm requires to avoid cavitation. Second, the
  turbulence the valve creates stays downstream of the measurement.
- **Straight runs (ifm manual 11592037, Fig. 2).** The meter needs at least
  15 × DN = 90 mm of straight pipe before and after it, and ifm advises
  against mounting it "directly in front of a valve". The link to the valve
  therefore has 100 mm of free straight tube. On the inlet side, keep the
  supply tube straight for at least 100 mm.
- **Modular clamps on a plain station base.** The station base is a flat
  laser-cut acrylic plate with holes only. Each clamp is a module: a printed
  **clamp base** is located on the plate by 2 steel dowel pins and fixed by
  2 × M4 from the front into captive nuts in the plate. Then the component
  goes in, and the printed **clamp head** (cap or strap) screws onto its
  clamp base through heat-set inserts. The base screws sit under the channel
  floor or bore bottom, so they are reachable until the component covers them.
- **Valve clamp.** The square valve body sits in a channel split between the
  clamp base and the cap. The two halves are 1.0 mm short of meeting (larger
  than the 2 × 0.2 mm print tolerance), so the cap always closes onto the body
  before it touches the base, which gives the clamping force. The knob passes through a Ø27.5 opening in
  the cap (which also clears the 18 × 18 stem boss) and stands about 25 mm
  proud of it.
- **Flowmeter clamp.**
  - **Grips round, not hex.** Each QSF fitting is torqued onto the meter's
    thread, so the angle its hex ends up at can't be controlled. The straps
    therefore grip the fitting's **round Ø20.8 body**, which fits at any
    angle. An assembly check spins every fitting through a full hex pitch to
    prove it.
  - **Torque the QSF fittings on the bench**, holding the meter by its
    flats. The printed straps are not made to react the 12 N·m thread torque.
  - **Mounting position:** horizontal pipe with the **housing and M12
    connector on top**, which is ifm's recommended position (manual 11592037,
    Fig. 1). The whole station hangs on the wall with the pipe running
    parallel to it. The LED windows on the sides of the lid face you.
  - **Meter stays upright.** The angle is set by the meter itself: its
    downward-facing 12 mm spanner flat rests on a **locating pad**, a ledge
    of the flowmeter clamp base under the meter. That flat is moulded into the
    meter, so its angle relative to the housing is fixed. Gravity keeps it
    seated, and the pad carries no screw load.
  - **Tube loads bypass the meter.** All clamp load goes through the brass
    fittings, so tube loads never pass through the meter's 12 N·m plastic
    threads.
- **Straight link tube with no strain.**
  - **No side offset:** both clamp bases are located by dowel pins in holes
    that the laser cuts into the same plate layer in one pass, so the two axes
    are nominally coaxial. Both flowmeter pedestals are one printed part. The
    wall slots move the whole plate, so they can't misalign one clamp against
    the other. At worst-case print (±0.2) and laser (±0.1) tolerances, the
    offset is 1.24 mm, which bends the 100 mm free link by 0.45 %, inside the
    0.5 % limit the checks hold.
  - **Same height:** both parts sit on their cradle floor with the same
    0.15 mm pocket clearance, so both axes end up the same distance from the
    wall.
  - **No axial strain:** the tube is cut exactly stop-to-stop (140.3 mm). The
    flowmeter straps allow ±1.65 mm of axial float, so push the tube home
    first and tighten the straps afterwards. The meter then settles where the
    tube puts it.

## Layout

```
assembly.py            build the station, run the design checks, export output/
flowmeter/             flowmeter model
                       + drawing_check.png  (overlay on the ifm datasheet drawing)
                       + ifm_check.png      (sections vs ifm's official STEP model)
flowmeter_connector/   push-in fitting model
                       + cad_check.png  (comparison with the RS-website 3D model)
flowmeter_clamp/       flowmeter clamp base + straps (print) + station base plate (laser)
                       + base_back / base_front .dxf (laser cutting)
valve/                 valve model
valve_connector/       push-in fitting model
                       + cad_check.png  (comparison with the RS-website 3D model)
valve_clamp/           valve clamp base + cap, shared constants and hardware
tools/render.py        PNG renders (assembly + component sheet)
tools/export_step.py   STEP of every component + the whole station -> output/step/
tools/view.py          send the model to the OCP CAD Viewer
tools/dims.py          dimension annotations measured from the placed parts
tools/cad_compare.py   compare a connector with the RS-website 3D model
tools/drawing_check.py overlay the flowmeter model on its datasheet drawing
output/                generated: assembly.step, assembly.png, components.png,
                       step/ (one STEP per component, assembly STEP, bom.csv)
```

## Usage

```bash
uv sync                                  # once

uv run python assembly.py                # 66 design checks (~1 min) + output/assembly.step/.png
uv run python tools/render.py            # output/assembly.png + output/components.png
uv run python tools/export_step.py       # output/step/: all components + assembly STEP, bom.csv

uv run python flowmeter_clamp/flowmeter_clamp.py   # plate DXF (laser) + flowmeter clamp sizes
uv run python valve_clamp/clamp.py                 # valve clamp base + cap sizes
uv run python valve/valve.py                       # a part's size vs its datasheet
uv run python valve_connector/valve_connector.py
uv run python flowmeter/flowmeter.py
uv run python flowmeter_connector/flowmeter_connector.py
```

`assembly.py` prints PASS/FAIL for each check and exits non-zero if any fail.
The checks cover:

1. Interference between every pair of parts.
2. Valve clamp: the cap closes onto the valve before reaching the base (after
   print tolerance), anti-rotation, slip resistance and pressure on the PETG.
3. Wall mounting: nothing behind the wall plane, and a straight hex-key path
   from the front to the 8 wall screws and the 8 cap and strap screws.
4. Valve operator access: knob grip, finger room, line of sight, and room to
   press the release collars.
5. Valve connector mating: thread engagement, alignment with the ports, tubes
   fully home, seal seating, no flow restriction, and spanner access.
6. Flow direction, read from the placed geometry: the flowmeter arrow follows
   the system flow, the meter is upstream of the valve, and the housing and
   M12 connector are on top of a horizontal pipe (ifm Fig. 1).
7. Link-tube alignment: both fitting axes coaxial (0.000 mm offset), the tube
   dead straight, its length exactly stop-to-stop, straight runs of at least
   15 × DN, fully inserted at both ends, both clamp bases on one plate layer,
   tube strain at worst-case tolerances, and axial float available.
8. Flowmeter clamp:
   - the straps close onto the round body before reaching the base, and both
     fittings are seated;
   - the straps sit on the round section only;
   - it fits at any fitting hex angle (a sweep through a full hex pitch);
   - the meter flat rests on the locating pad, and the meter touches nothing
     else;
   - holding: tube pull per strap, the meter can't roll under a cable pull,
     and pressure on the PETG.
9. Flowmeter operator access: room above for the M12 cable
   plug, release rings free to press from the front (the wall-side gap is
   reported), and reachable spanner flats.
10. Clamp modules: the plate is two flat layers with holes only, each clamp
    base has 2 dowels in the plate and 2 M4, every base screw passes through
    its captive nut and is reachable before the component goes in, every
    cap/strap screw fills its insert, screw bearing on PETG and acrylic, the
    bases can't tip under a 500 N tube pull, and every printed part fits a
    250 mm printer bed.
11. Build, print, service and environment: every assembly step swept into
    place along its path without a collision (the link tube can't go in
    last, so it is fitted on the bench), no support needed in the print
    orientation, printed walls at least 1.2 mm, link-tube strain at the
    Monte Carlo 99.73 % tolerance and over the water temperature range, PETG
    heat limit, line-pressure end thrust, and the load on each wall screw.

### 3D viewer

Start the OCP CAD Viewer (VS Code extension, or `uv run python -m ocp_vscode`
then open http://127.0.0.1:3939/viewer), then:

```bash
uv run python tools/view.py              # station (default)
uv run python tools/view.py exploded     # pulled apart in build order
uv run python tools/view.py parts        # valve-side components side by side
uv run python tools/view.py valve        # or: connector | base | cap
uv run python tools/view.py flowmeter_fitted   # or: flowmeter | flowmeter_connector
```

## Coordinates

The wall is the plane Y = 0, with +Y pointing toward the operator. Z is up.
The flow axis is horizontal, 30 mm from the wall (`AXIS_Y`). The operator
faces the wall, so global +X is on their left. System flow runs along −X
(`FLOW_DIR` in `assembly.py`), which is left to right as the operator sees it.
The valve sits at X = 0 and the flowmeter at X = +207.7. The station base is
300 mm long (laser-cut); the largest printed part is 120 mm.

## Verification status

The table shows what was checked against a primary source (checked
2026-11-20) and what still needs confirming on real parts or by you.

| Item | Status | Source / evidence |
|---|---|---|
| Valve body 18 × 18 × 46, G1/4 ports 12 deep, M17×1 bush, Ø22 knob, height 57 | **Verified** | Tognella FT 1251/2-01 datasheet, table type 14 (RS lists "manufacturer series FT1251/2") |
| Valve edge chamfer 2.5, boss 18 × 2.5, groove on the face opposite the stem | Scaled | Tognella drawing, 20.7 px/mm (about ±0.3 mm) |
| Valve flow direction: either way | **Confirmed by you** | Tognella datasheet (double-acting, A–B restrictor without a check valve). RS's product text saying "single-acting" is wrong. |
| Valve ports need a normal chamfer for the KQ2 gasket | **Measure on the real valve** | SMC KQ2 catalogue: the gasket "is seated on the chamfer of a female thread" |
| KQ2H12-U02A geometry | **Verified** | SMC catalogue + RS/TraceParts model (max deviation 0.07 mm) |
| KQ2 media: air or water, −100 kPa to 1 MPa, water 0–40 °C | **Verified** | SMC KQ2 catalogue specifications |
| QSF-1/2-12-B geometry, 23.3 mm insertion depth | **Verified** | Festo datasheet 190653 + RS/TraceParts model (max deviation 0.01 mm) |
| QSF water limit: **0.6 MPa (6 bar) at 50 °C at most** | **Verified** | Festo datasheet 190653 |
| QSF round body Ø20.8 × 15.3 (where the straps clamp) | Verified (CAD) / **measure one real fitting** | Festo D5 + RS/TraceParts model |
| SV3051 envelope 77 × 30.2 × 52.7, M12 position, pipe (Ø15.4 with flats 12 apart; 16 AF hex spanner section), housing widths | **Verified** | ifm datasheet + ifm STEP model: outer deviation mean 0.41 mm, 95th percentile 1.9 mm, max 2.4 mm (`flowmeter/ifm_check.png`) |
| SV3051 tightening torque 12 N·m | **Verified** | ifm operating instructions 11592037, Tab. 1 |
| SV3051 straight runs at least 15 × DN; not directly in front of a valve | **Verified, now designed in** | ifm operating instructions, sec. 4 and 4.1 |
| SV3051 mounting orientation: horizontal pipe, housing on top | **Decided by you; matches ifm** | ifm operating instructions 11592037, Fig. 1 (recommended position) |
| SV3051 display | **Confirmed by you: no display** | Not modelled. (The RS/ifm datasheet text mentions a 1.44" display; if one turns out to be there, it sits on the lid, which faces the operator.) |
| SV3051 sealing: a flat G1/2 washer at the meter end face | **Confirmed by you** | Washer OD ≤ 18.6, ID ≥ 11.5, about 1 mm, FKM/EPDM |
| M4 torque → preload: 0.5 N·m → 625 N (caps), 0.2 N·m → 250 N (bases) | Derived | T = K·F·d, K 0.2; limited by the plastics, not the screws. Base torque has a narrow window: 0.15 N·m lets the valve base tip at 500 N, 0.3 N·m overloads the acrylic under the nut |
| Plastics: PETG 15 MPa / acrylic 10 MPa sustained contact, μ 0.3 PETG on brass, print ±0.2 mm, laser ±0.1 mm | **Estimate, confirm** | Typical values, no single source; they drive the split gap, tolerance-strain and pressure checks |
| Heat-set insert M4 × 8.1, Ø5.6 hole | Typical | ruthex RX-M4x8.1 dimensions; check the insert you buy |
| Link-tube bending strain limit 0.5 % | **Estimate** | Conservative for PU / PA tube; no source |
| Tube CTE 150e-6/K, PETG HDT 70 °C, 15 mm bridge, 100 N per plasterboard plug | **Estimate** | Typical values; section 11 of `assembly.py` |
| System limit: water ≤ 6 bar, 0–40 °C | **Derived** | lowest of QSF (6 bar ≤ 50 °C), KQ2 (1 MPa, 0–40 °C), meter (16 bar), valve (210 bar) |
| 500 N tube pull, 50 N cable pull, wall type, tube supports | **Accepted by you** | Engineering judgement, no source |

## Assembly

1. **On the bench:**
   - Screw both KQ2 fittings into the valve with a 19 mm spanner.
   - Screw both QSF fittings onto the flowmeter, each with a flat G1/2
     washer. Tighten to **12 N·m at most**, holding the meter by its 12 mm
     spanner flats.
   - Laser-cut `base_back` and `base_front` from 6 mm cast acrylic and
     solvent-weld them together. Drop the 4 M4 nuts into the hex pockets
     from the wall side.
   - Print the clamp bases, cap and straps (PETG). Press 2 dowel pins into
     each clamp base, and melt the M4 inserts into its split face.
2. Fix the station base to the wall with 8 × M6 screws. The vertical slots
   give ±3 mm of adjustment and move both clamps together. The nuts are
   trapped between the wall and the front layer.
3. Push each clamp base's dowels into the plate and fix it with its 2 × M4
   (through the channel floor / bore bottom) at 0.2 N·m.
4. **Build the bench unit.** The link tube is cut exactly stop-to-stop, so it
   can't be pushed in once the valve and the flowmeter are both clamped
   (`assembly.py` section 11 shows the clash). On the bench, lying straight:
   push the 140.3 mm link tube fully home into the flowmeter outlet QSF and
   into the valve inlet KQ2. Check that the flow arrow points at the valve.
5. Lower the whole unit into both clamp bases at once, with the housing and
   M12 connector **on top** and the knob facing out.
   - The fitting hexes can sit at any angle.
   - Let the meter's downward spanner flat sit flat on the locating pad
     under it. The valve can slide along its channel, so the unit settles
     where the tube puts it.
6. Slide the cap over the knob and fit 4 × M4×20 with DIN 125 washers; fit
   both straps with M4×30 and washers. Tighten all of them evenly to
   0.5 N·m. Re-torque all M4 after 24 h.
7. Push the inlet and outlet tubes into place. Keep at least 100 mm of
   straight inlet tube ahead of the meter, and support the tubes beyond the
   station. Run the system at **6 bar or less** with water at 0–40 °C.

### Tight margins

These pass, but with little room. Watch them when you change the design:

- Worst-case link-tube strain is 0.45 %, against the 0.5 % limit.
- The valve clamp base resists tipping under a 500 N tube pull by only
  × 1.17.
- The clamp-base M4 torque has a narrow window. At 0.15 N·m the valve base
  can tip; at 0.3 N·m the nut overloads the acrylic. Use 0.2 N·m.
- Contact pressures are close to the estimated allowables: washer on PETG
  12.7 MPa (limit 15), nut on acrylic 9.4 MPa (limit 10).

## Tests to do on real parts

`assembly.py` checks the model. These need real parts, in this order:

| # | Test | How | Pass when |
|---|---|---|---|
| 1 | Measure the bought-in parts | Calipers on the valve body (18 × 18, chamfers, port chamfer), QSF round body Ø20.8 × 15.3, KQ2 hex | Within 0.1 mm of the model; otherwise update the part file and re-run |
| 2 | Laser calibration coupon | Cut a strip with Ø4.1 dowel holes, Ø4.5 holes and a 7.2 AF hex at the plate spacing; measure the sheet thickness | Dowel slides in without play you can feel, nut drops in and doesn't turn, sheet 5.4–6.6 mm |
| 3 | Print calibration coupon | Print a 20 mm slice of each clamp (channel, bore, dowel hole, insert hole) | Valve body and QSF body slide in with a slight drag; dowel presses in by hand vise; insert sets square |
| 4 | Insert pull-out | Screw M4 into a set insert in a coupon, hang or pull | Holds 3 × the 625 N screw preload (about 1.9 kN) without pulling out |
| 5 | Dry fit, unclamped | Assemble in the order above without tightening | Each step goes in by hand; bench unit drops into both bases without forcing the tube |
| 6 | Clamp gap | After tightening, feeler gauge at the split faces of the cap and both straps | Gap still open (model: 0.85 mm) on all four corners |
| 7 | Leak test | Fill with water, raise to 6 bar, hold 30 min | No drop, no weep at either G thread or tube |
| 8 | Torque retention | Re-check all M4 after 24 h and after 1 week | Less than about 30 % loss; otherwise fit wave washers |
| 9 | Pull and twist | 500 N axial pull on the outlet tube; 50 N sideways on the M12 cable | Nothing moves; the meter stays square on its pad |
| 10 | Knob use | Turn the valve fully open and closed 20 times | Valve doesn't rotate or shift in the clamp |
| 11 | Thermal | Run with water at 5 °C and at 40 °C for an hour each | No leaks, no visible tube bow, clamps still tight |
| 12 | Alignment | With the straps loose, look along the link tube; the meter should not jump when the straps are tightened | No visible bend or jump (model worst case 1.24 mm, 99.7 % 0.73 mm) |
