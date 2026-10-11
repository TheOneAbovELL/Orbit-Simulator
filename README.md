# 🪐 Orbit Simulator

**An interactive 2D gravity sandbox built with Python and Pygame.**

Create planets, launch them through space, and watch gravity shape their motion. Click and hold to grow a planet, flick the mouse as you release to give it velocity, and experiment with orbital mechanics. When planets collide, they merge into larger bodies while conserving mass and momentum.

Orbit Simulator combines an interactive sandbox with a modular physics engine, deterministic fixed-step integration, a camera system, particle trails, and a headless automated test suite.

---

## ✨ Features

- **Interactive planet creation** — Click and hold to grow a planet, then flick to launch it.
- **Newtonian gravity** — Simulate gravitational interactions between multiple bodies.
- **Orbital experiments** — Create, adjust, and observe planetary motion.
- **Collision merging** — Colliding planets merge while conserving mass and momentum.
- **Fixed-step physics** — Velocity Verlet integration with a fixed simulation timestep.
- **Camera controls** — Pan, zoom, and reset the view.
- **Visual trails** — Toggle fading trails to observe planetary trajectories.
- **Simulation controls** — Pause, advance individual frames, and adjust simulation speed.
- **Sample solar system** — Load a predefined system for quick experiments.
- **Configurable command line** — Adjust window dimensions, planet limits, and random seeds.
- **Automated testing** — Run the test suite without a physical display.
- **Standalone Windows build** — Optionally package the application into an executable.

## 🚀 Quick Start

### Requirements

- Python 3.10 or newer
- A graphical desktop environment
- Pygame, installed automatically when installing the package

### Install and run

From the project root:

```bash
python -m pip install .
orbit-sim
```

Alternatively, run directly from the source folder without installing the package:

```bash
python -m pip install pygame
python -m orbit_sim
```

The original launcher filename remains supported:

```bash
python "orbit simulator.py"
```

## 🎮 Controls

| Input | Action |
|---|---|
| Left mouse drag | Create a planet. Hold to grow it; mouse movement on release determines its velocity. |
| Ctrl + click | Delete the planet under the cursor. |
| Right mouse drag | Pan the view. |
| Mouse wheel | Zoom toward or away from the cursor. |
| Space | Pause or resume the simulation. |
| `.` | Advance one frame while paused. |
| `+` / `-` | Increase or decrease simulation speed, from 0.25× to 4×. |
| `S` | Load the sample solar system. |
| `Tab` / `C` | Clear all planets. |
| `T` | Toggle planetary trails. |
| `Home` | Reset the camera view. |
| `H` / `F1` | Show or hide the controls panel. |
| `Esc` | Quit the application. |

### Getting your first orbit

1. Launch Orbit Simulator.
2. Press `S` to load the sample solar system.
3. Create a small planet near the star.
4. Flick it sideways as you release the mouse button.
5. Experiment with the launch direction and velocity to observe different trajectories.

**Tip:** A sideways launch is a better starting point for creating an orbit than throwing the planet directly toward the star.

## ⚙️ Command-Line Options

Run the application using:

```bash
orbit-sim [options]
```

When running from the source folder:

```bash
python -m orbit_sim [options]
```

| Option | Description |
|---|---|
| `--size 1280x800` | Set the window dimensions. The default is 85% of the screen size, capped at 1600×900. The window remains resizable. |
| `--sample` | Start with the sample solar system loaded. |
| `--max-planets N` | Set the maximum number of planets. Default: `50`. |
| `--seed N` | Set the random seed used for planet colours and trails. |
| `--version` | Print the application version. |

### Examples

Start with a specific window size:

```bash
orbit-sim --size 1280x800
```

Load the sample solar system immediately:

```bash
orbit-sim --sample
```

Limit the simulation to 100 planets:

```bash
orbit-sim --max-planets 100
```

Use a fixed random seed:

```bash
orbit-sim --seed 42
```

Combine multiple options:

```bash
orbit-sim --size 1280x800 --sample --max-planets 100 --seed 42
```

## 🌌 How the Physics Works

The physics engine lives in `orbit_sim/physics.py` and has **no dependency on Pygame**. This separates simulation mechanics from rendering and user interaction.

### 1. Mass and radius

Planet mass is proportional to the area of its circular disc:

\[
m = \pi r^2
\]

where:

- \(m\) is the planet's mass.
- \(r\) is its radius.

This same area-based relationship is used when calculating the radius of a merged planet.

### 2. Newtonian gravity with softening

The simulator models Newtonian gravitational interactions between planets, with Plummer softening of **2 pixels**.

Softening prevents gravitational forces from becoming singular when two planets approach or nearly overlap. It keeps the simulation numerically better behaved during close encounters.

### 3. Fixed-step velocity Verlet integration

The simulation uses velocity Verlet integration with a fixed timestep:

\[
\Delta t = \frac{1}{120}\text{ second}
\]

Changing the simulation speed changes how many physics steps are executed per rendered frame, not the duration of an individual physics step.

This design reduces dependence on rendering frame rate and provides more consistent simulation behaviour.

**Energy conservation check:** The sample system's energy drift remains below 0.1% after 30 simulated seconds, as checked by a test.

### 4. Collision detection and merging

When two planets touch, they merge into one larger body.

The merge operation preserves:

- **Total mass** — The merged body's mass equals the sum of the original masses.
- **Linear momentum** — The merged body's velocity is derived from the original bodies' combined momentum.
- **Centre of mass** — The merged body is positioned at the original pair's centre of mass.

The resulting radius follows the same area-based mass relationship used elsewhere in the simulation.

The drawn radius is capped at **200 pixels**, but the underlying mass is never discarded because of this visual limit.

### 5. Out-of-bounds and velocity culling

Planets are removed from the simulation if they exceed either of these limits:

- More than **50,000 pixels** from the world origin.
- A speed greater than **60,000 pixels per second**.

These limits prevent extreme trajectories from leaving runaway bodies in the simulation indefinitely.

### 6. Units and simulation behaviour

- Distance: screen pixels at 100% zoom.
- Time: seconds.
- Gravitational constant: selected to preserve the feel of the original prototype.

The simulator is intended as an interactive sandbox rather than a dimensionally calibrated astronomical model.

## 🏗️ Project Architecture

The project separates physics, camera transformations, trails, configuration, and application logic into dedicated modules.

```text
orbit_sim/
  physics.py       # N-body world, gravity, integration, merging, culling
  camera.py        # World-to-screen transforms, pan, zoom, fit
  trails.py        # Fading particle trails (visual only)
  app.py           # Pygame window, input, rendering, main loop
  config.py        # Tunable constants
  __main__.py      # Command-line entry point

tests/             # Pytest suite; runs headless
legacy/            # Original single-file prototype, kept for reference
orbit simulator.py # Launcher retained for the original filename
```

### Module responsibilities

| Module | Responsibility |
|---|---|
| `physics.py` | Maintains the N-body world and handles gravitational forces, integration, collision merging, and culling. |
| `camera.py` | Handles transformations between world and screen coordinates, panning, zooming, and fitting the view. |
| `trails.py` | Implements fading particle trails without affecting physics. |
| `app.py` | Manages the Pygame window, input events, rendering, and main loop. |
| `config.py` | Holds configurable constants. |
| `__main__.py` | Provides the command-line entry point. |
| `tests/` | Contains the automated test suite. |
| `legacy/` | Preserves the original single-file implementation for reference. |

## 🧪 Development and Testing

### Set up the development environment

Install the project in editable mode with development dependencies:

```bash
python -m pip install -e ".[dev]"
```

### Run the tests

```bash
python -m pytest
```

### Run lint checks

```bash
ruff check .
```

### Check formatting

```bash
ruff format --check .
```

### Headless test execution

The test suite drives the real Pygame application using synthetic events and SDL's dummy video driver. This allows automated tests to run without opening a visible application window.

The test configuration is managed by:

```text
tests/conftest.py
```

Continuous integration is configured in:

```text
.github/workflows/ci.yml
```

The CI workflow runs linting and tests on **Ubuntu and Windows**, using **Python 3.10 and Python 3.13**.

## 🪟 Building a Standalone Windows Executable

Orbit Simulator can optionally be packaged into a standalone Windows executable using [PyInstaller](https://pyinstaller.org).

This is useful for distributing the application to users who do not have Python installed.

### Install PyInstaller

```bash
python -m pip install pyinstaller
```

### Build the executable

Run the following command from the project directory on Windows:

```bash
pyinstaller --onefile --windowed --name OrbitSimulator "orbit simulator.py"
```

The resulting executable is written to:

```text
dist/OrbitSimulator.exe
```

Expected size: approximately **15 MB**.

### Windows build notes

- Build from a short directory path when possible. Very long paths can exceed the 260-character path limit while PyInstaller installs its hooks.
- The generated executable is unsigned. Windows SmartScreen may display a warning the first time it is launched.

## 🔄 Changes from the Original Prototype

The original single-file implementation is preserved at:

```text
legacy/orbit_simulator_v0.py
```

The current version introduces physics fixes, safer simulation behaviour, improved interaction, and a modular architecture.

### Physics and stability improvements

- **Fixed quick-click-and-flick crashes.** Prevents the `randint(1, 0)` failure that occurred when creating trail particles for small planets.
- **Fixed unsafe list mutation.** Prevents planets from being removed while iterating over the same lists, which could skip updates or raise `ValueError` when a planet left the world on both axes.
- **Symmetric force calculations.** Forces are applied symmetrically from a single snapshot, preserving momentum. Previously, each planet moved before the next planet's force was calculated.
- **Corrected collision merging.** Merging now conserves momentum and centre of mass, uses circle overlap instead of an off-centre rectangle, and handles equal-mass collisions.
- **Consistent mass and merge sizing.** Both now use the same area-based relationship. The prototype calculated mass from area but merged using volume.
- **Fixed-step integration.** Introduces frame-rate-independent fixed-step integration with gravitational softening.
- **Improved launch velocity estimation.** Flick velocity is averaged over the last few frames rather than relying only on the release frame, so the throw is less dependent on movement during that exact frame.

### Interaction and usability improvements

- **Safer planet-limit handling.** New planets are refused with a message when the planet limit is reached, rather than deleting existing planets.
- **Resizable window.** The window adapts to the screen instead of using a fixed 1920×1080 resolution.
- **Clean application shutdown.** `pygame.quit()` now runs on exit.
- **Pause and single-step controls.**
- **Adjustable simulation speed.**
- **Pan and zoom camera controls.**
- **Sample solar system.**
- **Toggleable particle trails.**
- **Ctrl+click planet deletion.**
- **On-screen help panel.**
- **Empty-state hint.**
- **Command-line configuration options.**

## 📋 Technical Notes and Limitations

- The physics engine is independent of Pygame, while the interactive application uses Pygame for input and rendering.
- Simulation speed changes the number of fixed physics steps per rendered frame, not the physics timestep itself.
- The 200-pixel rendered-radius cap does not reduce a planet's stored mass.
- Bodies exceeding the configured distance or speed thresholds are removed.
- The standalone executable is optional; the application can also be run from Python.
- The original prototype remains available for reference in `legacy/orbit_simulator_v0.py`.

## 🛠️ Troubleshooting

### The `orbit-sim` command is not recognised

Install the package:

```bash
python -m pip install .
```

If needed, run through Python instead:

```bash
python -m orbit_sim
```

### The application does not open a window

Ensure that you are running the application in a graphical desktop session and that Pygame is installed:

```bash
python -m pip install pygame
```

### The simulation behaves differently at different speeds

Remember that simulation speed changes the number of physics steps executed per rendered frame. It does not change the fixed physics timestep of 1/120 second.

### Planets disappear unexpectedly

Planets that exceed 50,000 pixels from the world origin or 60,000 pixels per second are removed by the configured culling rules.

### PyInstaller reports path-related errors

Try moving the project to a directory with a shorter path before installing build hooks and creating the executable.

## 📜 License

Add the project's actual license information here if a license has been selected. No specific license is declared in the supplied project description.

---

**Orbit Simulator** is a hands-on environment for exploring gravity, orbital motion, collision merging, and numerical simulation through interactive experimentation.
