"""Tunable constants.

World units are "pixels at zoom 1" and time is in seconds. The gravitational
constant is chosen so the simulation feels like the original prototype, which
used G = 6.674e-11, mass = pi * r^2 * 2e9 and velocities in px/frame at 60 FPS.
"""

from __future__ import annotations

from dataclasses import dataclass

# Original prototype: G * MASS_AREA_RATIO = 6.67408e-11 * 2e9 per frame^2.
# Converted to seconds at 60 FPS (x 60^2) with mass expressed as area (pi*r^2).
_PROTOTYPE_G_PER_FRAME = 6.67408e-11 * 2e9
DEFAULT_G = _PROTOTYPE_G_PER_FRAME * 60**2  # ~480.5 px^3 / (area * s^2)


@dataclass(frozen=True)
class PhysicsConfig:
    gravity: float = DEFAULT_G
    # Plummer softening length; keeps forces finite when bodies nearly coincide.
    softening: float = 2.0
    # Fixed integration step (s). Simulation speed changes the number of steps,
    # never the step size, so results do not depend on frame rate.
    dt: float = 1.0 / 120.0
    max_radius: float = 200.0
    max_bodies: int = 50
    # Bodies beyond this distance from the origin, or faster than max_speed,
    # are removed (they would never come back and only cost CPU).
    world_limit: float = 50_000.0
    max_speed: float = 60_000.0


@dataclass(frozen=True)
class AppConfig:
    fps: int = 60
    background: tuple[int, int, int] = (25, 25, 25)
    # Radius growth while the mouse button is held (world px / s); the
    # prototype grew 0.35 px per frame.
    growth_rate: float = 0.35 * 60
    initial_radius: float = 2.0
    # Release velocity = mouse velocity * flick_scale. The prototype used half
    # of the per-frame mouse delta.
    flick_scale: float = 0.5
    # Number of recent frames averaged to estimate the flick velocity.
    flick_window: int = 4
    max_particles: int = 4000
    min_zoom: float = 0.02
    max_zoom: float = 8.0
    max_frame_time: float = 1.0 / 20.0
    max_substeps: int = 64
    speed_levels: tuple[float, ...] = (0.25, 0.5, 1.0, 2.0, 4.0)


PALETTE: tuple[tuple[int, int, int], ...] = (
    (236, 37, 37),
    (236, 151, 37),
    (247, 219, 41),
    (41, 247, 72),
    (46, 231, 208),
    (46, 63, 231),
    (221, 53, 232),
    (255, 84, 180),
)
