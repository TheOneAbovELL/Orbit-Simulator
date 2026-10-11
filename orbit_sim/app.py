"""Pygame front end: input handling, rendering and the main loop."""

from __future__ import annotations

import math
import random
from collections import deque
from dataclasses import dataclass, field

import pygame

from .camera import Camera
from .config import PALETTE, AppConfig, PhysicsConfig
from .physics import World, WorldFullError, load_sample_system
from .trails import TrailSystem

TEXT = (225, 225, 225)
TEXT_DIM = (150, 150, 150)
PANEL = (12, 12, 12, 200)
ACCENT = (247, 219, 41)

CONTROLS = (
    ("Left drag", "Create a planet; hold to grow, flick to throw"),
    ("Ctrl + click", "Delete the planet under the cursor"),
    ("Right drag", "Pan the view"),
    ("Mouse wheel", "Zoom at the cursor"),
    ("Space", "Pause / resume"),
    (".", "Step one frame while paused"),
    ("+ / -", "Faster / slower simulation"),
    ("S", "Load the sample solar system"),
    ("Tab / C", "Clear all planets"),
    ("T", "Toggle trails"),
    ("Home", "Reset the view"),
    ("H", "Show / hide this help"),
    ("Esc", "Quit"),
)


@dataclass
class PendingBody:
    """A planet that is still being created under the mouse cursor."""

    x: float
    y: float
    radius: float
    color: tuple[int, int, int]
    # Recent (world_x, world_y, frame_dt) samples for the flick velocity.
    samples: deque = field(default_factory=deque)

    def velocity(self, flick_scale: float) -> tuple[float, float]:
        if len(self.samples) < 2:
            return (0.0, 0.0)
        x0, y0, _ = self.samples[0]
        x1, y1, _ = self.samples[-1]
        elapsed = sum(s[2] for s in list(self.samples)[1:])
        if elapsed <= 0:
            return (0.0, 0.0)
        return ((x1 - x0) / elapsed * flick_scale, (y1 - y0) / elapsed * flick_scale)


class App:
    def __init__(
        self,
        size: tuple[int, int] = (1280, 800),
        *,
        seed: int | None = None,
        app_config: AppConfig | None = None,
        physics_config: PhysicsConfig | None = None,
        sample: bool = False,
    ) -> None:
        self.config = app_config or AppConfig()
        pygame.init()
        pygame.display.set_caption("Orbit Simulator")
        self.screen = pygame.display.set_mode(size, pygame.RESIZABLE)
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 22)
        self.font_large = pygame.font.Font(None, 30)

        self.rng = random.Random(seed)
        self.world = World(physics_config)
        self.camera = Camera(self.config.min_zoom, self.config.max_zoom)
        self.camera.reset(*size)
        self.trails = TrailSystem(self.config.max_particles, random.Random(seed))

        self.mouse: tuple[int, int] = (size[0] // 2, size[1] // 2)
        self.pending: PendingBody | None = None
        self.panning = False
        self.paused = False
        self.step_once = False
        self.speed_index = self.config.speed_levels.index(1.0)
        self.show_help = True
        self.show_trails = True
        self.running = True
        self.elapsed = 0.0
        self._accumulator = 0.0
        self._message: tuple[str, float] | None = None
        if sample:
            self.load_sample()

    # ---------------------------------------------------------------- state
    @property
    def speed(self) -> float:
        return self.config.speed_levels[self.speed_index]

    def notify(self, text: str, seconds: float = 2.0) -> None:
        self._message = (text, self.elapsed + seconds)

    def load_sample(self) -> None:
        extent = load_sample_system(self.world)
        self.trails.clear()
        self.pending = None
        self.camera.fit(extent, *self.screen.get_size())

    def mouse_world(self) -> tuple[float, float]:
        return self.camera.to_world(*self.mouse)

    # ---------------------------------------------------------------- input
    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self.running = False
        elif event.type == pygame.MOUSEMOTION:
            self.mouse = event.pos
            if self.panning:
                self.camera.pan_pixels(*event.rel)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            self.mouse = event.pos
            if event.button == 1:
                self._on_left_down()
            elif event.button in (2, 3):
                self.panning = True
        elif event.type == pygame.MOUSEBUTTONUP:
            self.mouse = event.pos
            if event.button == 1:
                self._release_pending()
            elif event.button in (2, 3):
                self.panning = False
        elif event.type == pygame.MOUSEWHEEL:
            self.camera.zoom_at(1.15**event.y, *self.mouse)
        elif event.type in (pygame.WINDOWFOCUSLOST, pygame.WINDOWLEAVE):
            # A release outside the window never reaches us; finish the
            # gesture instead of leaving a planet stuck to the cursor.
            self.panning = False
            if event.type == pygame.WINDOWFOCUSLOST:
                self._release_pending()
        elif event.type == pygame.KEYDOWN:
            self._on_key(event)

    def _on_left_down(self) -> None:
        # A missed button-up must not silently discard the planet in progress.
        self._release_pending()
        if pygame.key.get_mods() & pygame.KMOD_CTRL:
            wx, wy = self.mouse_world()
            body = self.world.body_at(wx, wy, padding=4 / self.camera.zoom)
            if body is not None:
                self.world.remove_body(body.id)
            return
        if self.world.is_full:
            self.notify(f"Planet limit reached ({self.world.config.max_bodies}). Clear some first.")
            return
        wx, wy = self.mouse_world()
        self.pending = PendingBody(
            wx,
            wy,
            self.config.initial_radius,
            self.rng.choice(PALETTE),
            deque([(wx, wy, 0.0)], maxlen=self.config.flick_window + 1),
        )

    def _release_pending(self) -> None:
        pending, self.pending = self.pending, None
        if pending is None:
            return
        vx, vy = pending.velocity(self.config.flick_scale)
        try:
            self.world.add_body(pending.x, pending.y, pending.radius, vx, vy, pending.color)
        except WorldFullError:
            self.notify("Planet limit reached.")

    def _on_key(self, event: pygame.event.Event) -> None:
        key = event.key
        if key == pygame.K_ESCAPE:
            self.running = False
        elif key == pygame.K_SPACE:
            self.paused = not self.paused
        elif key == pygame.K_PERIOD:
            if self.paused:
                self.step_once = True
        elif key in (pygame.K_TAB, pygame.K_c):
            self.world.clear()
            self.trails.clear()
            self.pending = None
        elif key in (pygame.K_h, pygame.K_F1):
            self.show_help = not self.show_help
        elif key == pygame.K_t:
            self.show_trails = not self.show_trails
            if not self.show_trails:
                self.trails.clear()
        elif key == pygame.K_s:
            self.load_sample()
            self.notify("Sample solar system loaded")
        elif key == pygame.K_HOME:
            self.camera.reset(*self.screen.get_size())
        elif key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS, pygame.K_RIGHTBRACKET):
            self.speed_index = min(self.speed_index + 1, len(self.config.speed_levels) - 1)
            self.notify(f"Speed {self.speed:g}x", 1.0)
        elif key in (pygame.K_MINUS, pygame.K_KP_MINUS, pygame.K_LEFTBRACKET):
            self.speed_index = max(self.speed_index - 1, 0)
            self.notify(f"Speed {self.speed:g}x", 1.0)

    # --------------------------------------------------------------- update
    def update(self, frame_dt: float) -> None:
        frame_dt = max(0.0, min(frame_dt, self.config.max_frame_time))
        self.elapsed += frame_dt
        self._update_pending(frame_dt)

        if self.paused and not self.step_once:
            return
        if self.step_once:
            sim_dt = frame_dt if frame_dt > 0 else 1.0 / self.config.fps
            self.step_once = False
        else:
            sim_dt = frame_dt * self.speed

        dt = self.world.config.dt
        self._accumulator += sim_dt
        steps = 0
        while self._accumulator >= dt and steps < self.config.max_substeps:
            self.world.step()
            self._accumulator -= dt
            steps += 1
        if steps >= self.config.max_substeps:
            # The machine cannot keep up; drop the backlog instead of
            # spiralling into ever longer frames.
            self._accumulator = 0.0

        if self.show_trails and steps:
            for body in self.world.bodies:
                self.trails.emit(body)
        self.trails.update(sim_dt)

    def _update_pending(self, frame_dt: float) -> None:
        pending = self.pending
        if pending is None:
            return
        pending.x, pending.y = self.mouse_world()
        pending.samples.append((pending.x, pending.y, frame_dt))
        max_radius = self.world.config.max_radius
        pending.radius = min(pending.radius + self.config.growth_rate * frame_dt, max_radius)

    # --------------------------------------------------------------- render
    def render(self) -> None:
        screen = self.screen
        screen.fill(self.config.background)
        cam = self.camera
        w, h = screen.get_size()

        if self.show_trails:
            for p in self.trails.particles:
                sx, sy = cam.to_screen(p.x, p.y)
                r = p.radius * cam.zoom
                if -r <= sx <= w + r and -r <= sy <= h + r and r >= 0.5:
                    pygame.draw.circle(screen, p.color, (sx, sy), max(1, round(r)))

        for b in self.world.bodies:
            sx, sy = cam.to_screen(b.x, b.y)
            r = b.radius * cam.zoom
            if -r <= sx <= w + r and -r <= sy <= h + r:
                pygame.draw.circle(screen, b.color, (sx, sy), max(1, round(r)))

        if self.pending is not None:
            self._draw_pending()

        self._draw_hud()
        if self.show_help:
            self._draw_help()
        if not self.world.bodies and self.pending is None:
            self._draw_empty_hint()

    def _draw_pending(self) -> None:
        p = self.pending
        assert p is not None
        cam = self.camera
        sx, sy = cam.to_screen(p.x, p.y)
        r = max(1, round(p.radius * cam.zoom))
        pygame.draw.circle(self.screen, p.color, (sx, sy), r)
        pygame.draw.circle(self.screen, TEXT, (sx, sy), r + 3, 1)
        vx, vy = p.velocity(self.config.flick_scale)
        if vx or vy:
            # Arrow length: where the planet would be after 0.5 s.
            ex, ey = sx + vx * 0.5 * cam.zoom, sy + vy * 0.5 * cam.zoom
            pygame.draw.line(self.screen, TEXT, (sx, sy), (ex, ey), 2)
            angle = math.atan2(ey - sy, ex - sx)
            for side in (2.6, -2.6):
                hx = ex + 10 * math.cos(angle + side)
                hy = ey + 10 * math.sin(angle + side)
                pygame.draw.line(self.screen, TEXT, (ex, ey), (hx, hy), 2)

    def _text(self, text: str, pos: tuple[int, int], color=TEXT, font=None) -> pygame.Rect:
        surf = (font or self.font).render(text, True, color)
        return self.screen.blit(surf, pos)

    def _draw_hud(self) -> None:
        cfg = self.world.config
        parts = [
            f"Planets {len(self.world.bodies)}/{cfg.max_bodies}",
            f"Speed {self.speed:g}x",
            f"Zoom {self.camera.zoom * 100:.0f}%",
        ]
        rect = self._text("     ".join(parts), (12, 10), TEXT_DIM)
        if self.paused:
            self._text("PAUSED", (rect.right + 20, 10), ACCENT)
        w, h = self.screen.get_size()
        if not self.show_help:
            self._text("H  help", (12, h - 26), TEXT_DIM)
        if self._message is not None:
            text, until = self._message
            if self.elapsed > until:
                self._message = None
            else:
                surf = self.font_large.render(text, True, TEXT)
                self.screen.blit(surf, surf.get_rect(midtop=(w // 2, 36)))

    def _draw_help(self) -> None:
        line_h = 22
        key_w = 120
        width = 470
        height = 44 + line_h * len(CONTROLS)
        w, _ = self.screen.get_size()
        x = max(12, w - width - 12)
        panel = pygame.Surface((width, height), pygame.SRCALPHA)
        panel.fill(PANEL)
        self.screen.blit(panel, (x, 12))
        self._text("Controls", (x + 14, 22), ACCENT)
        for i, (key, action) in enumerate(CONTROLS):
            y = 44 + 12 + i * line_h
            self._text(key, (x + 14, y), TEXT)
            self._text(action, (x + 14 + key_w, y), TEXT_DIM)

    def _draw_empty_hint(self) -> None:
        w, h = self.screen.get_size()
        lines = (
            "Click and hold to grow a planet, flick the mouse as you release to throw it.",
            "Press S to load a sample solar system.",
        )
        for i, line in enumerate(lines):
            surf = self.font_large.render(line, True, TEXT_DIM)
            self.screen.blit(surf, surf.get_rect(center=(w // 2, h // 2 + i * 36)))

    # ----------------------------------------------------------------- loop
    def run(self) -> None:
        try:
            while self.running:
                frame_dt = self.clock.tick(self.config.fps) / 1000.0
                for event in pygame.event.get():
                    self.handle_event(event)
                self.update(frame_dt)
                self.render()
                pygame.display.flip()
        finally:
            pygame.quit()


def default_window_size() -> tuple[int, int]:
    """Fit the window to the primary display, capped at 1600x900."""
    pygame.display.init()
    try:
        desktop_w, desktop_h = pygame.display.get_desktop_sizes()[0]
    except (pygame.error, IndexError):
        return (1280, 800)
    return (min(1600, int(desktop_w * 0.85)), min(900, int(desktop_h * 0.85)))
