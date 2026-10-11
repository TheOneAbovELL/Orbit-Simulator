"""Deterministic 2D N-body physics.

This module has no pygame dependency so it can be tested in isolation.

Model:
- Mass is proportional to disc area (mass = pi * r^2), the same scaling the
  original prototype used for gravity.
- Gravity uses Plummer softening so forces stay finite at tiny separations.
- Integration is velocity Verlet (kick-drift-kick) with a fixed time step,
  which is time-reversible and keeps orbits stable over long runs.
- Touching bodies merge perfectly inelastically: mass and momentum are
  conserved and the merged body sits at the pair's centre of mass.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from .config import PhysicsConfig

Color = tuple[int, int, int]


class WorldFullError(RuntimeError):
    """Raised when adding a body would exceed PhysicsConfig.max_bodies."""


@dataclass
class Body:
    id: int
    x: float
    y: float
    vx: float
    vy: float
    mass: float
    radius: float
    color: Color
    ax: float = 0.0
    ay: float = 0.0

    @property
    def speed(self) -> float:
        return math.hypot(self.vx, self.vy)


@dataclass
class StepReport:
    merges: int = 0
    removed: list[int] = field(default_factory=list)


def mass_for_radius(radius: float) -> float:
    return math.pi * radius * radius


class World:
    def __init__(self, config: PhysicsConfig | None = None) -> None:
        self.config = config or PhysicsConfig()
        self.bodies: list[Body] = []
        self.time = 0.0
        self._next_id = 0
        self._accel_dirty = True

    # ------------------------------------------------------------------ bodies
    @property
    def is_full(self) -> bool:
        return len(self.bodies) >= self.config.max_bodies

    def add_body(
        self,
        x: float,
        y: float,
        radius: float,
        vx: float = 0.0,
        vy: float = 0.0,
        color: Color = (255, 255, 255),
        mass: float | None = None,
    ) -> Body:
        if self.is_full:
            raise WorldFullError(f"world is limited to {self.config.max_bodies} bodies")
        values = (x, y, radius, vx, vy) + ((mass,) if mass is not None else ())
        if not all(math.isfinite(v) for v in values):
            raise ValueError("body parameters must be finite")
        if radius <= 0:
            raise ValueError("radius must be positive")
        radius = min(radius, self.config.max_radius)
        body = Body(
            id=self._next_id,
            x=x,
            y=y,
            vx=vx,
            vy=vy,
            mass=mass if mass is not None else mass_for_radius(radius),
            radius=radius,
            color=color,
        )
        if body.mass <= 0:
            raise ValueError("mass must be positive")
        self._next_id += 1
        self.bodies.append(body)
        self._accel_dirty = True
        return body

    def remove_body(self, body_id: int) -> bool:
        for i, body in enumerate(self.bodies):
            if body.id == body_id:
                del self.bodies[i]
                self._accel_dirty = True
                return True
        return False

    def body_at(self, x: float, y: float, padding: float = 0.0) -> Body | None:
        """Return the body under a point, preferring the one drawn on top."""
        for body in reversed(self.bodies):
            if math.hypot(body.x - x, body.y - y) <= body.radius + padding:
                return body
        return None

    def clear(self) -> None:
        self.bodies.clear()
        self._accel_dirty = True

    # ------------------------------------------------------------ diagnostics
    def total_mass(self) -> float:
        return sum(b.mass for b in self.bodies)

    def momentum(self) -> tuple[float, float]:
        return (
            sum(b.mass * b.vx for b in self.bodies),
            sum(b.mass * b.vy for b in self.bodies),
        )

    def center_of_mass(self) -> tuple[float, float]:
        m = self.total_mass()
        if m == 0:
            return (0.0, 0.0)
        return (
            sum(b.mass * b.x for b in self.bodies) / m,
            sum(b.mass * b.y for b in self.bodies) / m,
        )

    def energy(self) -> float:
        """Total kinetic + (softened) potential energy."""
        g = self.config.gravity
        eps2 = self.config.softening**2
        kinetic = sum(0.5 * b.mass * (b.vx * b.vx + b.vy * b.vy) for b in self.bodies)
        potential = 0.0
        bodies = self.bodies
        for i, a in enumerate(bodies):
            for b in bodies[i + 1 :]:
                d = math.sqrt((b.x - a.x) ** 2 + (b.y - a.y) ** 2 + eps2)
                potential -= g * a.mass * b.mass / d
        return kinetic + potential

    # -------------------------------------------------------------- dynamics
    def _compute_accelerations(self) -> None:
        g = self.config.gravity
        eps2 = self.config.softening**2
        bodies = self.bodies
        for b in bodies:
            b.ax = 0.0
            b.ay = 0.0
        n = len(bodies)
        for i in range(n):
            a = bodies[i]
            for j in range(i + 1, n):
                b = bodies[j]
                dx = b.x - a.x
                dy = b.y - a.y
                r2 = dx * dx + dy * dy + eps2
                inv_r3 = g / (r2 * math.sqrt(r2))
                a.ax += dx * inv_r3 * b.mass
                a.ay += dy * inv_r3 * b.mass
                b.ax -= dx * inv_r3 * a.mass
                b.ay -= dy * inv_r3 * a.mass
        self._accel_dirty = False

    def step(self, dt: float | None = None) -> StepReport:
        """Advance the simulation by one fixed step."""
        dt = self.config.dt if dt is None else dt
        report = StepReport()
        if not self.bodies:
            self.time += dt
            return report
        if self._accel_dirty:
            self._compute_accelerations()
        half = 0.5 * dt
        for b in self.bodies:
            b.vx += b.ax * half
            b.vy += b.ay * half
            b.x += b.vx * dt
            b.y += b.vy * dt
        report.merges = self._resolve_collisions()
        self._compute_accelerations()
        for b in self.bodies:
            b.vx += b.ax * half
            b.vy += b.ay * half
        report.removed = self._cull()
        self.time += dt
        return report

    def _resolve_collisions(self) -> int:
        merges = 0
        while True:
            pair = self._find_overlap()
            if pair is None:
                return merges
            survivor, absorbed = pair
            self._absorb(survivor, absorbed)
            self.bodies.remove(absorbed)
            merges += 1

    def _find_overlap(self) -> tuple[Body, Body] | None:
        bodies = self.bodies
        n = len(bodies)
        for i in range(n):
            a = bodies[i]
            for j in range(i + 1, n):
                b = bodies[j]
                reach = a.radius + b.radius
                dx = b.x - a.x
                dy = b.y - a.y
                if dx * dx + dy * dy < reach * reach:
                    # Heavier body survives; on a tie the older one does.
                    if (b.mass, -b.id) > (a.mass, -a.id):
                        return b, a
                    return a, b
        return None

    def _absorb(self, survivor: Body, absorbed: Body) -> None:
        m = survivor.mass + absorbed.mass
        survivor.x = (survivor.x * survivor.mass + absorbed.x * absorbed.mass) / m
        survivor.y = (survivor.y * survivor.mass + absorbed.y * absorbed.mass) / m
        survivor.vx = (survivor.vx * survivor.mass + absorbed.vx * absorbed.mass) / m
        survivor.vy = (survivor.vy * survivor.mass + absorbed.vy * absorbed.mass) / m
        survivor.mass = m
        # Area is conserved (radius from mass); the drawn size is capped but
        # the mass is not, so a capped body just becomes denser.
        survivor.radius = min(math.sqrt(m / math.pi), self.config.max_radius)

    def _cull(self) -> list[int]:
        limit = self.config.world_limit
        max_speed = self.config.max_speed
        kept: list[Body] = []
        removed: list[int] = []
        for b in self.bodies:
            finite = all(math.isfinite(v) for v in (b.x, b.y, b.vx, b.vy))
            if finite and abs(b.x) <= limit and abs(b.y) <= limit and b.speed <= max_speed:
                kept.append(b)
            else:
                removed.append(b.id)
        if removed:
            self.bodies = kept
            self._accel_dirty = True
        return removed


def circular_orbit_speed(gravity: float, central_mass: float, distance: float) -> float:
    return math.sqrt(gravity * central_mass / distance)


def load_sample_system(world: World, cx: float = 0.0, cy: float = 0.0) -> float:
    """Replace the world contents with a star and three circularly orbiting planets.

    Returns the radius of the system (outermost orbit plus that planet's size).
    """
    world.clear()
    star = world.add_body(cx, cy, 60.0, color=(247, 219, 41))
    planets = (
        # distance, radius, starting angle (rad), color
        (260.0, 8.0, 0.0, (46, 231, 208)),
        (430.0, 12.0, 2.1, (236, 37, 37)),
        (680.0, 10.0, 4.2, (46, 63, 231)),
    )
    g = world.config.gravity
    for distance, radius, angle, color in planets:
        speed = circular_orbit_speed(g, star.mass, distance)
        world.add_body(
            cx + distance * math.cos(angle),
            cy + distance * math.sin(angle),
            radius,
            # Counter-clockwise on screen (y grows downward).
            vx=speed * math.sin(angle),
            vy=-speed * math.cos(angle),
            color=color,
        )
    # Give the star the opposite momentum so the system does not drift.
    px, py = world.momentum()
    star.vx -= px / star.mass
    star.vy -= py / star.mass
    return max(distance + radius for distance, radius, _, _ in planets)
