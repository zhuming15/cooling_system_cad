"""Measure stack checking and bounding-box work, with or without scoped caching.

Run each mode in its own process with no other CAD jobs running. The uncached
mode disables only GeometryQueries.box reuse; geometry and limits are identical.
"""

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from build123d import Shape

import assembly as A
from tools import checks as CK


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--uncached", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    parts = A.build()
    original = Shape.bounding_box
    calls = Counter()
    bounds_seconds = 0.0

    def measured(shape, *a, **kw):
        nonlocal bounds_seconds
        start = time.perf_counter()
        try:
            calls[id(shape)] += 1
            return original(shape, *a, **kw)
        finally:
            bounds_seconds += time.perf_counter() - start

    if args.uncached:

        class Uncached(CK.GeometryQueries):
            def box(self, shape):
                return shape.bounding_box()

        CK.GeometryQueries = Uncached
    Shape.bounding_box = measured
    report = CK.Report(echo=False)
    start = time.perf_counter()
    try:
        A.check_stack(parts, report)
    finally:
        Shape.bounding_box = original
    result = {
        "cached": not args.uncached,
        "seconds": time.perf_counter() - start,
        "bounding_box_calls": sum(calls.values()),
        "bounds_seconds": bounds_seconds,
        "checks": len(report.results),
        "failures": report.fails,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result), flush=True)
    if report.fails:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
