# teardown

A Claude Code skill that turns any machine into a 3D simulator you can take apart.

Ask how something works. Claude builds it as one offline HTML page: the machine runs in the middle, every panel around it reads the real numbers, a button opens the part doing the work, and when nobody touches it the page tours itself.

![V8 four-stroke simulator](docs/v8.gif)

| Cessna 337 landing gear | Strandbeest SB-10 |
|---|---|
| ![Cessna 337 main landing gear](docs/cessna.jpg) | ![Strandbeest SB-10](docs/strandbeest.jpg) |

## Install

```
npx skills add elvarofficial/teardown -g -a claude-code
```

Then, once, in the installed folder:

```
npm install && npx playwright install chromium
```

You need Node.js 20 or newer. For the video you also need `ffmpeg`, and for the sound Python 3.

## Use

Ask Claude Code in plain words:

> Build me a simulator of a 4-stroke motorcycle engine I can take apart.

> How does a mechanical watch keep time? Show me as a simulator.

> Make a teardown of a hydraulic excavator arm and record a 20-second video of it.

Or open one of the 3 examples first:

```
node sims/build.mjs v8-live          # teardown-out/dist/v8-live.html
node sims/build.mjs cessna-live
node sims/build.mjs strandbeest-live
```

### Export to STL

Any of the 3 machines can be exported for 3D printing or CAD, in millimetres:

```
node sims/export-stl.mjs v8                   # teardown-out/stl/v8/
node sims/export-stl.mjs cessna --scale 0.1   # a 1:10 model
node sims/export-stl.mjs strandbeest --pose 0.25
```

You get `assembly.stl` (every solid part where the simulator places it, at the pose asked for), `parts/` with each distinct part once, lying flat and centred, and `report.txt` with each part's size, how many the machine uses, and whether its mesh is closed. Overlays such as arrows, glass and glows are left out. The parts are built to look right, not to work: gear teeth, bores and clearances are visual, so use them as a starting point for a model, not as a working mechanism.

### A walking Strandbeest you can print

`sims/strandbeest-print/walker.py` turns the simulator's linkage into a 12-leg Strandbeest that walks on Bambu's TT motor (LA001, from the Marble Run kit 003), with no screws: printed snap pins, a crankshaft of hex couplers, 12:48 gears.

```
pip install manifold3d trimesh shapely
python3 sims/strandbeest-print/walker.py            # parts -> teardown-out/print/strandbeest-walker/
python3 sims/strandbeest-print/pack.py teardown-out/print/strandbeest-walker   # 5 print plates
python3 sims/strandbeest-print/verify_walker.py teardown-out/print/strandbeest-walker
```

Layers are searched so that nothing collides over a full turn; `verify_walker.py` re-checks it from the STLs with its own solver. Leg phases (0/120/240° per side, 60° between sides) keep three feet down at all times.

## What is inside

| | |
|---|---|
| `SKILL.md` | What Claude reads: how a machine is built, the rules that make it look right, the review loop. |
| `sims/kit/` | Runtime, stage, shader warm-up. |
| `sims/v8-*`, `sims/cessna-*`, `sims/strandbeest-*` | 3 complete machines. `-shared` is the machine, `-live` the page you drive, `-film` the recorded tour. |
| `sims/build.mjs` | Bundles a machine into one HTML file, three.js and fonts inlined. |
| `sims/export-stl.mjs` | Exports a machine's solid parts to STL: the assembly, each distinct part, and a printability report. |
| `sims/capture.mjs` | Renders the film frame by frame to a 60 fps mp4, or to review sheets of stills. |
| `sfx/`, `run_sfx.py` | Procedural sound on the film's timeline, mastered to −14 LUFS. |

## Credits

Built on [whaleyxbt/claude-motion](https://github.com/whaleyxbt/claude-motion) (MIT): the runtime, frame capture, sound engine and review rules come from there. Recorded samples are CC0 from Freesound, prepared by [Barty-Bart/motion-graphics](https://github.com/Barty-Bart/motion-graphics); sources in `sfx/samples/SOURCES.md`.

MIT licence.
