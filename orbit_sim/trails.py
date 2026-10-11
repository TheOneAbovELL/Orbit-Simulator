"""Fading particle trails behind moving bodies (visual only; no physics)."""

from __future__ import annotations

import random
from collections import deque
from dataclasses import dataclass

from .physics import Body, Color

# Every particle shrinks to nothing over this many (simulated) seconds, so a
# trail's length shows how fast its planet moves regardless of planet size.
LIFETIME = 1.5
# Particles drift backwards at up to this fraction of the body's velocity.
DRIFT = 0.05


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    radius: float
    shrink: float  # radius lost per second
    color: Color


def darken(color: Color, amount: int = 35) -> Color:
    r, g, b = color
    return (max(0, r - amount), max(0, g - amount), max(0, b - amount))


class TrailSystem:
    def __init__(self, max_particles: int = 4000, rng: random.Random | None = None) -> None:
        self.max_particles = max_particles
        # Oldest first; a full deque silently drops the oldest particle, so the
        # newest (most visible) part of every trail survives.
        self.particles: deque[Particle] = deque(maxlen=max_particles)
        self.rng = rng or random.Random()

    def emit(self, body: Body) -> None:
        if body.vx == 0 and body.vy == 0:
            return
        rng = self.rng
        radius = rng.uniform(1.0, max(1.0, body.radius / 1.5))
        self.particles.append(
            Particle(
                x=body.x,
                y=body.y,
                vx=-body.vx * DRIFT * rng.random(),
                vy=-body.vy * DRIFT * rng.random(),
                radius=radius,
                shrink=radius / LIFETIME,
                color=darken(body.color),
            )
        )

    def update(self, dt: float) -> None:
        if dt <= 0:
            return
        alive: deque[Particle] = deque(maxlen=self.max_particles)
        for p in self.particles:
            p.x += p.vx * dt
            p.y += p.vy * dt
            p.radius -= p.shrink * dt
            if p.radius > 0:
                alive.append(p)
        self.particles = alive

    def clear(self) -> None:
        self.particles.clear()
