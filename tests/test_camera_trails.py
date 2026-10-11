import random

import pytest

from orbit_sim.camera import Camera
from orbit_sim.physics import Body
from orbit_sim.trails import LIFETIME, TrailSystem, darken


def make_body(radius=10.0, vx=30.0, vy=-20.0):
    return Body(id=0, x=5, y=5, vx=vx, vy=vy, mass=1, radius=radius, color=(236, 37, 37))


def test_camera_round_trip():
    cam = Camera()
    cam.x, cam.y, cam.zoom = 120.0, -40.0, 2.5
    wx, wy = cam.to_world(*cam.to_screen(33.0, 77.0))
    assert (wx, wy) == pytest.approx((33.0, 77.0))


def test_zoom_keeps_point_under_cursor_fixed():
    cam = Camera()
    before = cam.to_world(300, 200)
    cam.zoom_at(1.5, 300, 200)
    assert cam.zoom == pytest.approx(1.5)
    assert cam.to_world(300, 200) == pytest.approx(before)


def test_zoom_is_clamped():
    cam = Camera(min_zoom=0.5, max_zoom=2.0)
    cam.zoom_at(100, 0, 0)
    assert cam.zoom == 2.0
    cam.zoom_at(1e-6, 0, 0)
    assert cam.zoom == 0.5


def test_pan_moves_scene_with_drag():
    cam = Camera()
    cam.zoom = 2.0
    world_point = cam.to_world(100, 100)
    cam.pan_pixels(10, -6)
    assert cam.to_screen(*world_point) == pytest.approx((110, 94))


def test_reset_centres_origin():
    cam = Camera()
    cam.zoom = 3
    cam.reset(800, 600)
    assert cam.zoom == 1.0
    assert cam.to_screen(0, 0) == pytest.approx((400, 300))


def test_darken_clamps_at_zero():
    assert darken((10, 100, 255)) == (0, 65, 220)


@pytest.mark.parametrize("radius", [0.1, 1.0, 1.4, 50.0])
def test_emit_handles_any_radius(radius):
    """Regression: the prototype crashed with randint(1, 0) for small planets."""
    trails = TrailSystem(rng=random.Random(1))
    trails.emit(make_body(radius=radius))
    assert len(trails.particles) == 1
    assert trails.particles[0].radius >= 1.0


def test_emit_ignores_stationary_bodies():
    trails = TrailSystem()
    trails.emit(make_body(vx=0, vy=0))
    assert not trails.particles


def test_particles_shrink_and_expire():
    trails = TrailSystem(rng=random.Random(2))
    trails.emit(make_body(radius=3))
    trails.update(0.01)
    assert len(trails.particles) == 1
    trails.update(10.0)
    assert not trails.particles


def test_particle_cap_drops_oldest():
    trails = TrailSystem(max_particles=5, rng=random.Random(3))
    bodies = [make_body() for _ in range(8)]
    for i, b in enumerate(bodies):
        b.x = float(i)
        trails.emit(b)
    assert len(trails.particles) == 5
    assert [p.x for p in trails.particles] == [3.0, 4.0, 5.0, 6.0, 7.0]


def test_fit_shows_whole_circle():
    cam = Camera()
    cam.fit(700, 1280, 760)
    left, top = cam.to_world(0, 0)
    right, bottom = cam.to_world(1280, 760)
    assert left < -700 and right > 700 and top < -700 and bottom > 700


@pytest.mark.parametrize("radius", [2.0, 40.0, 200.0])
def test_trail_lifetime_does_not_depend_on_planet_size(radius):
    trails = TrailSystem(rng=random.Random(4))
    trails.emit(make_body(radius=radius))
    trails.update(LIFETIME * 0.95)
    assert len(trails.particles) == 1
    trails.update(LIFETIME * 0.1)
    assert len(trails.particles) == 0
