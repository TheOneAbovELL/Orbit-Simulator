"""Command-line entry point: ``python -m orbit_sim`` or ``orbit-sim``."""

from __future__ import annotations

import argparse
from dataclasses import replace

from . import __version__
from .config import PhysicsConfig


def _size(value: str) -> tuple[int, int]:
    try:
        w, h = (int(v) for v in value.lower().split("x"))
    except ValueError:
        raise argparse.ArgumentTypeError("size must look like 1280x800") from None
    if w < 320 or h < 240:
        raise argparse.ArgumentTypeError("size must be at least 320x240")
    return (w, h)


def _positive_int(value: str) -> int:
    n = int(value)
    if n < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return n


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="orbit-sim", description="Interactive 2D gravity sandbox.")
    parser.add_argument("--size", type=_size, help="window size, e.g. 1280x800 (default: fit screen)")
    parser.add_argument("--seed", type=int, help="random seed for planet colours and trails")
    parser.add_argument(
        "--max-planets",
        type=_positive_int,
        default=PhysicsConfig.max_bodies,
        help=f"maximum number of planets (default: {PhysicsConfig.max_bodies})",
    )
    parser.add_argument("--sample", action="store_true", help="start with the sample solar system")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    # Import pygame only after argument parsing so --help works without it.
    from .app import App, default_window_size

    physics = replace(PhysicsConfig(), max_bodies=args.max_planets)
    App(
        args.size or default_window_size(),
        seed=args.seed,
        physics_config=physics,
        sample=args.sample,
    ).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
