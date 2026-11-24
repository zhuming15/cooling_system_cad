"""Repeat full-suite worker experiments and write raw logs, JUnit, JSON and a plot.

Run with the project's Python, e.g. uv run python tools/benchmark_tests.py.
Each trial is a fresh subprocess; trials run sequentially to avoid contention.
"""

import argparse
import json
import statistics
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def plot_results(destination, results, reported):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    workers = sorted({row["workers"] for row in results})
    groups = [[row["seconds"] for row in results if row["workers"] == w] for w in workers]
    medians = [statistics.median(group) for group in groups]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), layout="constrained")
    axes[0].bar(
        ["User reported\nbefore", "Measured\nafter (4 workers)"],
        [reported, medians[workers.index(4)]],
        color=["#9a9a9a", "#2379ad"],
    )
    axes[0].set_title("Full suite: reported before vs measured after")
    for i, value in enumerate([reported, medians[workers.index(4)]]):
        axes[0].text(i, value + 8, f"{value:.1f}s", ha="center")
    axes[0].set_ylim(0, reported * 1.15)
    axes[1].bar(range(len(workers)), medians, color="#2379ad", alpha=0.7)
    for i, group in enumerate(groups):
        axes[1].scatter([i] * len(group), group, color="#172b3a", zorder=3)
        axes[1].text(i, max(group) + 2, f"median {medians[i]:.1f}s", ha="center")
    axes[1].set_xticks(
        range(len(workers)), ["Serial" if w == 0 else f"{w} workers" for w in workers]
    )
    axes[1].set_title("Controlled experiment: identical optimized code")
    axes[1].set_ylim(0, max(max(g) for g in groups) * 1.2)
    for ax in axes:
        ax.set_ylabel("Wall-clock seconds (lower is better)")
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="y", alpha=0.15)
        ax.set_axisbelow(True)
    fig.supxlabel(
        "Dots = individual full-suite runs; bars = medians. Before value was reported, not rerun.",
        fontsize=10,
    )
    fig.savefig(destination / "runtime.png", dpi=180)
    fig.savefig(destination / "runtime.svg")
    plt.close(fig)


def plot_bounds(destination):
    """Plot the optional same-code cached/uncached stack profiles."""
    import matplotlib.pyplot as plt

    rows = [
        json.loads((destination / f"stack-{mode}.json").read_text())
        for mode in ("uncached", "cached")
    ]
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), layout="constrained")
    for ax, field, title, unit in zip(
        axes,
        ("seconds", "bounding_box_calls"),
        ("Stack check wall time", "Actual bounding-box calculations"),
        ("seconds", "calls"),
    ):
        values = [row[field] for row in rows]
        ax.bar(["Cache disabled", "Cache enabled"], values, color=["#9a9a9a", "#2379ad"])
        for i, value in enumerate(values):
            ax.text(
                i,
                value + max(values) * 0.03,
                f"{value:,.2f}" if field == "seconds" else f"{value:,}",
                ha="center",
            )
        ax.set_title(title)
        ax.set_ylabel(unit)
        ax.set_ylim(0, max(values) * 1.18)
        ax.spines[["top", "right"]].set_visible(False)
    fig.supxlabel(
        "Same code, geometry and limits; one instrumented run per mode; all 5 checks pass.",
        fontsize=10,
    )
    fig.savefig(destination / "bounds.png", dpi=180)
    fig.savefig(destination / "bounds.svg")
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", nargs="+", type=int, default=[0, 2, 4])
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--reported-before", type=float, default=742)
    parser.add_argument("--output", type=Path, default=ROOT / "benchmarks" / "test-runtime")
    parser.add_argument("--plot-only", action="store_true")
    args = parser.parse_args()
    if args.plot_only:
        saved = json.loads((args.output / "results.json").read_text())
        plot_results(args.output, saved["runs"], saved["reported_before_seconds"])
        if (args.output / "stack-cached.json").exists():
            plot_bounds(args.output)
        return
    if args.repeats < 1 or 4 not in args.workers or any(w < 0 for w in args.workers):
        parser.error("positive repeats and nonnegative workers including 4 are required")
    args.output.mkdir(parents=True, exist_ok=True)
    results = []
    for repeat in range(args.repeats):
        # Rotate order so each configuration gets an early and a late trial.
        order = (
            args.workers[repeat % len(args.workers) :] + args.workers[: repeat % len(args.workers)]
        )
        for workers in order:
            label = f"workers-{workers}-run-{repeat + 1}"
            xml = (args.output / f"{label}.xml").resolve()
            command = [
                sys.executable,
                "-m",
                "pytest",
                "-n",
                str(workers),
                "--durations=15",
                f"--junitxml={xml}",
            ]
            start = time.perf_counter()
            with (args.output / f"{label}.log").open("w") as log:
                run = subprocess.run(
                    command, check=False, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT
                )
            seconds = time.perf_counter() - start
            suite = ET.parse(xml).getroot().find("testsuite") if xml.exists() else None
            row = {
                "workers": workers,
                "repeat": repeat + 1,
                "seconds": seconds,
                "exit_code": run.returncode,
                "command": command,
                "tests": int(suite.attrib["tests"]) if suite is not None else None,
                "failures": int(suite.attrib["failures"]) if suite is not None else None,
                "errors": int(suite.attrib["errors"]) if suite is not None else None,
                "skipped": int(suite.attrib["skipped"]) if suite is not None else None,
            }
            results.append(row)
            (args.output / "results.json").write_text(
                json.dumps(
                    {
                        "reported_before_seconds": args.reported_before,
                        "python": sys.version,
                        "runs": results,
                    },
                    indent=2,
                )
                + "\n"
            )
            print(
                f"{label}: {seconds:.2f}s, exit {run.returncode}, {row['tests']} tests", flush=True
            )
            if run.returncode:
                raise SystemExit(f"Trial failed; inspect {args.output / (label + '.log')}")
    plot_results(args.output, results, args.reported_before)


if __name__ == "__main__":
    main()
