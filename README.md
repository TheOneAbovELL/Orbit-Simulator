# Orbit Simulator

An interactive 2D gravity sandbox. Click and hold to grow a planet, flick the
mouse as you let go to throw it, and watch gravity pull planets into orbits.
Planets that touch merge into one bigger planet.

## Quick start

Requires Python 3.10+.

```bash
python -m pip install .
orbit-sim
```

Or run from the source folder without installing (needs `pygame` installed):

```bash
python -m orbit_sim
```

Double-clicking `orbit simulator.py` (the original file name) also still works.

### Command-line options

| Option | Meaning |
| --- | --- |
| `--size 1280x800` | Window size (default: 85% of the screen, max 1600x900). The window can be resized. |
| `--sample` | Start with the sample solar system loaded. |
| `--max-planets N` | Planet limit (default 50). |
| `--seed N` | Random seed for planet colours and trails. |
| `--version` | Print the version. |

## Controls

| Input | Action |
| --- | --- |
| Left drag | Create a planet. Hold to grow it; the mouse speed as you release sets its velocity. |
| Ctrl + click | Delete the planet under the cursor. |
| Right drag | Pan the view. |
| Mouse wheel | Zoom at the cursor. |
| Space | Pause / resume. |
| `.` | Advance one frame while paused. |
| `+` / `-` | Faster / slower simulation (0.25x to 4x). |
| S | Load the sample solar system. |
| Tab / C | Clear all planets. |
| T | Toggle trails. |
| Home | Reset the view. |
| H / F1 | Show / hide the controls panel. |
| Esc | Quit. |

Tip: to get an orbit, press S, then throw a small planet sideways past the star
rather than towards it.

## How the physics works

All physics lives in `orbit_sim/physics.py`, which has no pygame dependency.

- Mass is proportional to disc area (`mass = pi * r^2`).
- Gravity is Newtonian with Plummer softening (2 px), so forces stay finite
  when planets nearly overlap.
- Integration is velocity Verlet with a fixed 1/120 s step. Simulation speed
  changes how many steps run per frame, never the step size, so results do not
  depend on frame rate. Energy drift on the sample system is under 0.1% after
  30 simulated seconds (checked by a test).
- Touching planets merge: mass and momentum are conserved, the result sits at
  the pair's centre of mass, and its radius follows from its mass. Drawn size is
  capped at 200 px; mass is never discarded.
- Planets more than 50,000 px from the origin or faster than 60,000 px/s are
  removed.

Units are screen pixels at 100% zoom and seconds. The gravitational constant is
chosen so the feel matches the original prototype.

## Project layout

```
orbit_sim/
  physics.py    N-body world: bodies, gravity, integration, merging, culling
  camera.py     world <-> screen transforms, pan, zoom, fit
  trails.py     fading particle trails (visual only)
  app.py        pygame window, input, rendering, main loop
  config.py     tunable constants
  __main__.py   command-line entry point
tests/          pytest suite (runs headless)
legacy/         the original single-file prototype, kept for reference
orbit simulator.py  launcher kept for the original file name
```

## Development

```bash
python -m pip install -e ".[dev]"
python -m pytest
ruff check .
ruff format --check .
```

The tests drive the real pygame app with synthetic events using SDL's dummy
video driver, so they need no display. `tests/conftest.py` sets this up; CI
(`.github/workflows/ci.yml`) runs lint and tests on Ubuntu and Windows with
Python 3.10 and 3.13.

## Building a standalone Windows executable (optional)

[PyInstaller](https://pyinstaller.org) can bundle the game into a single `.exe`
for people without Python:

```bash
python -m pip install pyinstaller
pyinstaller --onefile --windowed --name OrbitSimulator "orbit simulator.py"
```

The executable is written to `dist/OrbitSimulator.exe` (about 15 MB). Run the
build from a short directory path on Windows; very long paths can hit the
260-character path limit while PyInstaller installs its hooks. The executable
is unsigned, so Windows SmartScreen may warn on first launch.

## Changes from the original prototype

The original `orbit simulator.py` is preserved at
`legacy/orbit_simulator_v0.py`. Fixes and changes:

- Fixed a crash on a quick click-and-flick (`randint(1, 0)` when creating trail
  particles for small planets).
- Fixed planets being removed from lists while iterating them, which skipped
  updates and could raise `ValueError` when a planet left the world on both
  axes.
- Forces are now applied symmetrically from one snapshot (momentum is
  conserved); previously each planet moved before the next one's force was
  computed.
- Merging now conserves momentum and centre of mass, uses circle overlap
  instead of an off-centre rectangle, and works for equal masses.
- Mass and merge size use the same rule (area). The prototype computed mass
  from area but merged by volume.
- Frame-rate-independent fixed-step integration with softening.
- At the planet limit, new planets are refused with a message instead of
  existing planets being deleted.
- Flick velocity is averaged over the last few frames instead of only the
  release frame, so a throw no longer depends on moving during the exact
  release frame.
- Resizable window sized to the screen (was fixed 1920x1080); `pygame.quit()`
  now actually runs on exit.
- New: pause, single-step, speed control, pan/zoom camera, sample solar
  system, trails toggle, Ctrl+click delete, on-screen help, empty-state hint,
  and command-line options.
