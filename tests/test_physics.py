import math
from dataclasses import replace

import pytest

from orbit_sim.config import PhysicsConfig
from orbit_sim.physics import (
    World,
    WorldFullError,
    circular_orbit_speed,
    load_sample_system,
    mass_for_radius,
)


def run(world: World, seconds: float) -> None:
    for _ in range(round(seconds / world.config.dt)):
        world.step()


def test_mass_is_proportional_to_area():
    world = World()
    body = world.add_body(0, 0, 10)
    assert body.mass == pytest.approx(math.pi * 100)


def test_radius_is_capped_on_creation():
    world = World()
    body = world.add_body(0, 0, 500)
    assert body.radius == world.config.max_radius


@pytest.mark.parametrize(
    "kwargs",
    [
        {"radius": 0},
        {"radius": -1},
        {"radius": float("nan")},
        {"radius": 5, "vx": float("inf")},
        {"radius": 5, "mass": 0},
    ],
)
def test_add_body_rejects_invalid_values(kwargs):
    with pytest.raises(ValueError):
        World().add_body(0, 0, **kwargs)


def test_body_limit_is_enforced_without_deleting_existing_bodies():
    world = World(replace(PhysicsConfig(), max_bodies=3))
    for i in range(3):
        world.add_body(i * 100, 0, 5)
    assert world.is_full
    with pytest.raises(WorldFullError):
        world.add_body(1000, 0, 5)
    assert len(world.bodies) == 3


def test_ids_are_unique_and_remove_body_works():
    world = World()
    a = world.add_body(0, 0, 5)
    b = world.add_body(100, 0, 5)
    assert a.id != b.id
    assert world.remove_body(a.id) is True
    assert world.remove_body(a.id) is False
    assert [x.id for x in world.bodies] == [b.id]


def test_body_at_prefers_topmost_and_respects_padding():
    world = World()
    world.add_body(0, 0, 10)
    top = world.add_body(5, 0, 10)
    assert world.body_at(4, 0) is top
    assert world.body_at(30, 0) is None
    assert world.body_at(18, 0, padding=5) is top


def test_two_bodies_attract_symmetrically():
    world = World()
    a = world.add_body(-100, 0, 10)
    b = world.add_body(100, 0, 10)
    world.step()
    assert a.vx > 0 and b.vx < 0
    assert a.vx == pytest.approx(-b.vx)
    assert a.vy == pytest.approx(0) and b.vy == pytest.approx(0)


def test_acceleration_matches_newtonian_gravity():
    world = World(replace(PhysicsConfig(), softening=0.0))
    heavy = world.add_body(0, 0, 20)
    light = world.add_body(300, 0, 1)
    world._compute_accelerations()
    expected = world.config.gravity * heavy.mass / 300**2
    assert light.ax == pytest.approx(-expected)


def test_momentum_is_conserved_without_collisions():
    world = World()
    world.add_body(-200, 0, 10, vx=0, vy=40)
    world.add_body(200, 0, 14, vx=0, vy=-25)
    world.add_body(0, 300, 6, vx=30, vy=0)
    p0 = world.momentum()
    run(world, 3.0)
    assert len(world.bodies) == 3
    p1 = world.momentum()
    assert p1[0] == pytest.approx(p0[0], abs=1e-6)
    assert p1[1] == pytest.approx(p0[1], abs=1e-6)


def test_merge_conserves_mass_momentum_and_centre_of_mass():
    world = World()
    a = world.add_body(0, 0, 10, vx=50, vy=0)
    world.add_body(15, 0, 5, vx=-20, vy=10)
    mass = world.total_mass()
    momentum = world.momentum()
    com = world.center_of_mass()
    report = world.step(dt=1e-9)  # effectively no motion: isolate the merge
    assert report.merges == 1
    assert world.bodies == [a]
    assert a.mass == pytest.approx(mass)
    assert world.momentum()[0] == pytest.approx(momentum[0], rel=1e-6)
    assert world.momentum()[1] == pytest.approx(momentum[1], rel=1e-6)
    assert world.center_of_mass()[0] == pytest.approx(com[0], abs=1e-6)
    assert a.radius == pytest.approx(math.sqrt(a.mass / math.pi))


def test_equal_masses_merge_and_older_body_survives():
    """The prototype never merged equal-mass planets."""
    world = World()
    older = world.add_body(0, 0, 10)
    world.add_body(12, 0, 10)
    world.step()
    assert world.bodies == [older]


def test_merged_radius_is_capped_but_mass_is_kept():
    world = World()
    big = world.add_body(0, 0, 190)
    world.add_body(100, 0, 150)
    total = world.total_mass()
    world.step()
    assert big.radius == world.config.max_radius
    assert big.mass == pytest.approx(total)


def test_cascading_merges_leave_no_overlaps():
    world = World()
    for x in (0, 15, 30, 45, 200, 212):
        world.add_body(x, 0, 10)
    mass = world.total_mass()
    report = world.step()
    assert report.merges >= 3
    assert world.total_mass() == pytest.approx(mass)
    assert world._find_overlap() is None


def test_softening_keeps_near_coincident_bodies_finite_and_bounded():
    world = World()
    # Tiny radii so they do not merge; separation far below the softening length.
    world.add_body(0, 0, 1e-6, mass=10)
    world.add_body(1e-3, 0, 1e-6, mass=10)
    world.step()
    assert len(world.bodies) == 2
    for b in world.bodies:
        assert all(math.isfinite(v) for v in (b.x, b.y, b.vx, b.vy))
        assert b.speed < 1.0


def test_escaping_and_out_of_bounds_bodies_are_removed():
    """The prototype could call list.remove twice on one planet and crash."""
    world = World()
    far = world.add_body(60_000, 60_000, 5)  # out of bounds on both axes
    fast = world.add_body(0, 1000, 5, vx=100_000, vy=100_000)
    keep = world.add_body(0, -1000, 5)
    report = world.step()
    assert sorted(report.removed) == sorted([far.id, fast.id])
    assert world.bodies == [keep]


def test_clear_empties_the_world():
    world = World()
    world.add_body(0, 0, 5)
    world.clear()
    assert world.bodies == []
    world.step()  # stepping an empty world is a no-op


def test_circular_orbit_stays_circular():
    world = World()
    star = world.add_body(0, 0, 50)
    r = 400.0
    v = circular_orbit_speed(world.config.gravity, star.mass, r)
    planet = world.add_body(r, 0, 2, vx=0, vy=v)
    # Cancel total momentum so the star stays near the origin.
    star.vy = -planet.mass * v / star.mass
    period = 2 * math.pi * r / v
    distances = []
    for _ in range(round(period / world.config.dt)):
        world.step()
        distances.append(math.hypot(planet.x - star.x, planet.y - star.y))
    assert len(world.bodies) == 2
    assert min(distances) > r * 0.97
    assert max(distances) < r * 1.03


def test_energy_is_well_conserved_over_long_runs():
    world = World()
    load_sample_system(world)
    e0 = world.energy()
    run(world, 30.0)
    assert len(world.bodies) == 4
    assert abs((world.energy() - e0) / e0) < 1e-3


def test_sample_system_has_zero_net_momentum_and_stays_bound():
    world = World()
    load_sample_system(world, 100, -50)
    px, py = world.momentum()
    assert abs(px) < 1e-6 and abs(py) < 1e-6
    star = world.bodies[0]
    run(world, 20.0)
    assert len(world.bodies) == 4
    for planet in world.bodies[1:]:
        assert math.hypot(planet.x - star.x, planet.y - star.y) < 800


def test_mass_for_radius():
    assert mass_for_radius(2) == pytest.approx(4 * math.pi)
