"""Headless tests that drive the real pygame app with synthetic events."""

import pygame
import pytest

from orbit_sim.__main__ import build_parser
from orbit_sim.app import App
from orbit_sim.config import PhysicsConfig

FRAME = 1 / 60


@pytest.fixture
def app():
    app = App((800, 600), seed=1, physics_config=PhysicsConfig(max_bodies=3))
    yield app
    pygame.key.set_mods(0)
    pygame.quit()


def send(app, type_, **attrs):
    app.handle_event(pygame.event.Event(type_, **attrs))


def press(app, pos, button=1):
    send(app, pygame.MOUSEBUTTONDOWN, pos=pos, button=button)


def release(app, pos, button=1):
    send(app, pygame.MOUSEBUTTONUP, pos=pos, button=button)


def move(app, pos, rel=(0, 0)):
    send(app, pygame.MOUSEMOTION, pos=pos, rel=rel, buttons=(1, 0, 0))


def key(app, k):
    send(app, pygame.KEYDOWN, key=k, mod=0, unicode="", scancode=0)


def frames(app, n=1):
    for _ in range(n):
        app.update(FRAME)
        app.render()


def drag_and_release(app, start, step, n):
    press(app, start)
    x, y = start
    for _ in range(n):
        x, y = x + step[0], y + step[1]
        move(app, (x, y), step)
        frames(app)
    release(app, (x, y))
    return x, y


def test_hold_grows_planet_and_flick_sets_velocity(app):
    drag_and_release(app, (400, 300), (6, -3), 20)
    assert len(app.world.bodies) == 1
    body = app.world.bodies[0]
    # 6 px/frame at 60 FPS * flick scale 0.5 = 180 px/s
    assert body.vx == pytest.approx(180, rel=0.05)
    assert body.vy == pytest.approx(-90, rel=0.05)
    assert body.radius > app.config.initial_radius


def test_quick_flick_does_not_crash(app):
    """Regression: the prototype crashed on a short, fast click-and-flick."""
    drag_and_release(app, (400, 300), (12, 9), 2)
    frames(app, 30)
    assert len(app.world.bodies) == 1
    assert app.trails.particles


def test_click_without_moving_places_planet_at_rest(app):
    press(app, (100, 100))
    frames(app, 10)
    release(app, (100, 100))
    body = app.world.bodies[0]
    assert (body.vx, body.vy) == (0.0, 0.0)
    assert app.camera.to_screen(body.x, body.y) == pytest.approx((100, 100))


def test_pending_planet_is_not_simulated_until_released(app):
    press(app, (200, 200))
    frames(app, 5)
    assert app.world.bodies == []
    assert app.pending is not None
    release(app, (200, 200))
    assert app.pending is None


def test_planet_limit_blocks_creation_and_notifies(app):
    for x in (100, 300, 500):
        press(app, (x, 100))
        frames(app)
        release(app, (x, 100))
    assert app.world.is_full
    press(app, (700, 500))
    assert app.pending is None
    assert app._message is not None and "limit" in app._message[0]
    assert len(app.world.bodies) == 3


def test_ctrl_click_deletes_planet_under_cursor(app):
    press(app, (300, 300))
    frames(app, 30)
    release(app, (300, 300))
    pygame.key.set_mods(pygame.KMOD_LCTRL)
    press(app, (300, 300))
    assert app.world.bodies == []
    assert app.pending is None


def test_tab_and_c_clear_everything(app):
    drag_and_release(app, (300, 300), (5, 0), 5)
    frames(app, 5)
    key(app, pygame.K_TAB)
    assert app.world.bodies == [] and not app.trails.particles
    drag_and_release(app, (300, 300), (5, 0), 5)
    key(app, pygame.K_c)
    assert app.world.bodies == []


def test_pause_freezes_and_step_advances_one_frame(app):
    drag_and_release(app, (300, 300), (5, 0), 5)
    key(app, pygame.K_SPACE)
    body = app.world.bodies[0]
    x = body.x
    frames(app, 10)
    assert body.x == x
    key(app, pygame.K_PERIOD)
    frames(app)
    assert body.x > x
    x = body.x
    frames(app, 3)
    assert body.x == x


def test_speed_controls_are_clamped(app):
    for _ in range(10):
        key(app, pygame.K_EQUALS)
    assert app.speed == max(app.config.speed_levels)
    for _ in range(10):
        key(app, pygame.K_MINUS)
    assert app.speed == min(app.config.speed_levels)


def test_simulation_speed_scales_distance(app):
    def distance_after(speed_presses):
        app.world.clear()
        app.speed_index = app.config.speed_levels.index(1.0)
        for _ in range(speed_presses):
            key(app, pygame.K_EQUALS)
        app.world.add_body(0, 0, 5, vx=60)
        frames(app, 60)
        return app.world.bodies[0].x

    assert distance_after(1) == pytest.approx(2 * distance_after(0), rel=0.02)


def test_wheel_zoom_and_right_drag_pan(app):
    move(app, (400, 300))
    send(app, pygame.MOUSEWHEEL, x=0, y=2, flipped=False, precise_x=0.0, precise_y=2.0)
    assert app.camera.zoom > 1
    before = app.camera.to_world(400, 300)
    press(app, (400, 300), button=3)
    move(app, (450, 300), rel=(50, 0))
    release(app, (450, 300), button=3)
    assert app.camera.to_world(450, 300) == pytest.approx(before)
    assert app.world.bodies == []  # right button never creates planets
    key(app, pygame.K_HOME)
    assert app.camera.zoom == 1.0


def test_flick_velocity_is_in_world_units_when_zoomed(app):
    app.camera.zoom = 2.0
    drag_and_release(app, (100, 300), (6, 0), 10)
    # 6 screen px/frame at 2x zoom = 3 world px/frame -> 90 px/s after scaling
    assert app.world.bodies[0].vx == pytest.approx(90, rel=0.05)


def test_focus_loss_releases_pending_planet(app):
    press(app, (300, 300))
    frames(app, 3)
    send(app, pygame.WINDOWFOCUSLOST)
    assert app.pending is None
    assert len(app.world.bodies) == 1


def test_sample_system_runs_for_a_long_time(app):
    app.world.config = PhysicsConfig()
    key(app, pygame.K_s)
    assert len(app.world.bodies) == 4
    frames(app, 600)
    assert len(app.world.bodies) == 4


def test_toggles_and_quit(app):
    key(app, pygame.K_h)
    assert app.show_help is False
    key(app, pygame.K_t)
    assert app.show_trails is False
    frames(app, 2)
    key(app, pygame.K_ESCAPE)
    assert app.running is False


def test_render_survives_resize_and_extreme_zoom(app):
    app.world.config = PhysicsConfig()
    key(app, pygame.K_s)
    app.screen = pygame.display.set_mode((400, 300), pygame.RESIZABLE)
    for factor in (1e6, 1e-6):
        app.camera.zoom_at(factor, 200, 150)
        frames(app, 3)


def test_long_frame_does_not_spiral(app):
    app.world.add_body(0, 0, 5)
    app.update(10.0)  # e.g. after the window was dragged for 10 s
    assert app.world.time <= app.config.max_frame_time + app.world.config.dt


def test_run_loop_exits_on_quit_event():
    app = App((640, 480), seed=0)
    pygame.event.post(pygame.event.Event(pygame.QUIT))
    app.run()
    assert not pygame.get_init()


def test_cli_parses_arguments():
    args = build_parser().parse_args(["--size", "1024x768", "--seed", "7", "--max-planets", "10", "--sample"])
    assert args.size == (1024, 768)
    assert args.seed == 7 and args.max_planets == 10 and args.sample
    with pytest.raises(SystemExit):
        build_parser().parse_args(["--size", "big"])
    with pytest.raises(SystemExit):
        build_parser().parse_args(["--max-planets", "0"])


def test_sample_system_fits_the_window(app):
    app.world.config = PhysicsConfig()
    key(app, pygame.K_s)
    w, h = app.screen.get_size()
    for body in app.world.bodies:
        sx, sy = app.camera.to_screen(body.x, body.y)
        assert 0 <= sx <= w and 0 <= sy <= h


def test_second_press_without_release_keeps_first_planet(app):
    press(app, (100, 100))
    frames(app, 5)
    press(app, (400, 400))  # the first button-up was lost
    release(app, (400, 400))
    assert len(app.world.bodies) == 2
