"""World <-> screen coordinate transforms with pan and zoom."""

from __future__ import annotations


class Camera:
    """Maps world coordinates to screen pixels.

    ``(x, y)`` is the world point shown at the top-left corner of the screen;
    ``zoom`` is screen pixels per world unit.
    """

    def __init__(self, min_zoom: float = 0.02, max_zoom: float = 8.0) -> None:
        self.x = 0.0
        self.y = 0.0
        self.zoom = 1.0
        self.min_zoom = min_zoom
        self.max_zoom = max_zoom

    def to_screen(self, wx: float, wy: float) -> tuple[float, float]:
        return ((wx - self.x) * self.zoom, (wy - self.y) * self.zoom)

    def to_world(self, sx: float, sy: float) -> tuple[float, float]:
        return (sx / self.zoom + self.x, sy / self.zoom + self.y)

    def pan_pixels(self, dx: float, dy: float) -> None:
        """Move the view so the scene follows a drag of (dx, dy) screen pixels."""
        self.x -= dx / self.zoom
        self.y -= dy / self.zoom

    def zoom_at(self, factor: float, sx: float, sy: float) -> None:
        """Zoom by ``factor`` keeping the world point under (sx, sy) fixed."""
        wx, wy = self.to_world(sx, sy)
        self.zoom = min(self.max_zoom, max(self.min_zoom, self.zoom * factor))
        self.x = wx - sx / self.zoom
        self.y = wy - sy / self.zoom

    def center_on(self, wx: float, wy: float, screen_w: int, screen_h: int) -> None:
        self.x = wx - screen_w / (2 * self.zoom)
        self.y = wy - screen_h / (2 * self.zoom)

    def fit(self, radius: float, screen_w: int, screen_h: int, margin: float = 0.9) -> None:
        """Centre the origin and zoom so a circle of ``radius`` fits on screen."""
        zoom = margin * min(screen_w, screen_h) / (2 * radius)
        self.zoom = min(self.max_zoom, max(self.min_zoom, zoom))
        self.center_on(0.0, 0.0, screen_w, screen_h)

    def reset(self, screen_w: int, screen_h: int) -> None:
        """Zoom 1 with the world origin at the screen centre."""
        self.zoom = 1.0
        self.center_on(0.0, 0.0, screen_w, screen_h)
