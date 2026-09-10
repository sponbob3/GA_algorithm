#!/usr/bin/env python
"""
Single entry point for the go-around detection pipeline.

Usage:
    python run_analysis.py                      # run the only/newest dataset
    python run_analysis.py KDAB_2025            # run a specific dataset
    python run_analysis.py KDAB_2025 --report   # + figures, report, PDF
    python run_analysis.py KDAB_2025 --calibrate  # + plateau histogram
    python run_analysis.py KDAB_2025 --no-plots --limit 5   # quick test
    python run_analysis.py new-airport KBNA     # generate an airport profile

Datasets live in datasets/<ICAO>_<label>/ (daily .parquet or .csv files);
the ICAO prefix of the folder name selects airports/<ICAO>.yaml. Every run
writes to a fresh folder: output/<dataset>/run_NN/.
"""

from __future__ import annotations

import argparse
import datetime
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATASETS_DIR = ROOT / "datasets"
OUTPUT_DIR = ROOT / "output"


def list_datasets() -> list[Path]:
    if not DATASETS_DIR.exists():
        return []
    return sorted(
        d for d in DATASETS_DIR.iterdir()
        if d.is_dir() and any(d.glob("*.parquet")) or any(d.glob("*.csv"))
    )


def resolve_dataset(name: str | None) -> Path:
    ds = list_datasets()
    if name:
        path = DATASETS_DIR / name
        if not path.is_dir():
            options = ", ".join(d.name for d in ds) or "(none)"
            sys.exit(f"error: no dataset folder '{name}' in datasets/. "
                     f"Available: {options}")
        return path
    if len(ds) == 1:
        return ds[0]
    if not ds:
        sys.exit("error: no datasets found. Create datasets/<ICAO>_<label>/ "
                 "and put daily .parquet/.csv files in it.")
    names = "\n  ".join(d.name for d in ds)
    sys.exit(f"multiple datasets found - pick one:\n  {names}\n"
             f"usage: python run_analysis.py <dataset_name>")


def next_run_dir(dataset_name: str) -> Path:
    base = OUTPUT_DIR / dataset_name
    base.mkdir(parents=True, exist_ok=True)
    nums = [
        int(p.name.split("_")[1])
        for p in base.glob("run_*") if p.name.split("_")[1].isdigit()
    ]
    run_dir = base / f"run_{(max(nums) + 1 if nums else 1):02d}"
    run_dir.mkdir()
    return run_dir


def dump_run_config(run_dir: Path, dataset: Path, n_files: int,
                    args: argparse.Namespace) -> None:
    """Full provenance record: every resolved parameter of this run."""
    from goaround_pipeline import config

    lines = [
        f"run_time: {datetime.datetime.now().isoformat(timespec='seconds')}",
        f"dataset: {dataset.name}  ({n_files} daily files)",
        f"command: {' '.join(sys.argv)}",
        "",
        "[resolved configuration]",
    ]
    for key in sorted(dir(config)):
        if key.isupper():
            lines.append(f"{key} = {getattr(config, key)!r}")
    (run_dir / "run_config.txt").write_text("\n".join(lines) + "\n")


def calibrate(df, run_dir: Path) -> None:
    """Plateau-duration distribution by outcome class: the check that the
    go-around / low-approach / landing-roll cutoffs separate cleanly on
    THIS dataset (look for an empty gap between the populations)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    from goaround_pipeline import config

    classes = ["go_around", "ga_ambiguous", "low_approach", "touch_and_go"]
    sub = df[df["outcome"].isin(classes)]
    sub[["outcome", "level_low_duration_s"]].to_csv(
        run_dir / "calibration_plateau.csv", index=False)

    fig, ax = plt.subplots(figsize=(8.5, 3.8))
    bins = np.arange(0, 90, 3)
    for outcome, color in zip(classes,
                              ["#eb6834", "#eda100", "#1baf7a", "#2a78d6"]):
        vals = sub[sub["outcome"] == outcome]["level_low_duration_s"]
        if len(vals):
            ax.hist(vals.clip(0, 87), bins=bins, histtype="step", lw=2,
                    color=color, label=f"{outcome} (n={len(vals)})",
                    density=True)
    ax.axvspan(config.LEVEL_GA_MAX_S, config.LEVEL_LOWAPP_MIN_S,
               color="0.9", zorder=0)
    ax.set_xlabel("plateau duration at profile low point (s)")
    ax.set_ylabel("density")
    ax.legend(frameon=False, fontsize=8)
    ax.set_title("Cutoff calibration - the shaded band should fall in an "
                 "empty gap", loc="left", fontsize=10)
    fig.tight_layout()
    fig.savefig(run_dir / "calibration_plateau.png", dpi=150)
    plt.close(fig)


def cmd_new_airport(icao: str) -> None:
    from goaround_pipeline import profiles

    path = profiles.create_profile(icao)
    print(f"wrote {path.relative_to(ROOT)}\n"
          "Review it before running: set timezone, preset "
          "(training_ga/air_carrier), terrain (flat/dem), and "
          "assume_arrivals_dataset.")


def main() -> None:
    if len(sys.argv) >= 3 and sys.argv[1] == "new-airport":
        cmd_new_airport(sys.argv[2])
        return

    ap = argparse.ArgumentParser(
        description="Run go-around detection on a dataset folder.")
    ap.add_argument("dataset", nargs="?",
                    help="folder name under datasets/ (e.g. KDAB_2025)")
    ap.add_argument("--no-plots", action="store_true",
                    help="skip per-event trajectory plots")
    ap.add_argument("--limit", type=int, metavar="N",
                    help="process only the first N daily files (testing)")
    ap.add_argument("--report", action="store_true",
                    help="also produce figures, summary report and PDF")
    ap.add_argument("--calibrate", action="store_true",
                    help="also output the plateau-duration calibration "
                         "histogram")
    args = ap.parse_args()

    dataset = resolve_dataset(args.dataset)
    icao = dataset.name.split("_")[0].upper()

    from goaround_pipeline import pipeline, profiles

    profiles.load_profile(icao)
    from goaround_pipeline import config
    config.OUTPUT_DIR = run_dir = next_run_dir(dataset.name)
    n_files = len(pipeline.data_files(dataset))
    print(f"dataset: {dataset.name}  airport: {icao}  "
          f"preset: {config.PRESET}  terrain: {config.TERRAIN_MODE}  "
          f"-> {run_dir.relative_to(ROOT)}")
    dump_run_config(run_dir, dataset, n_files, args)

    df = pipeline.run(dataset, run_dir, plots=not args.no_plots,
                      limit=args.limit)
    print()
    print(pipeline.write_summaries(df, run_dir))

    if args.calibrate:
        calibrate(df, run_dir)
        print(f"\ncalibration histogram: "
              f"{(run_dir / 'calibration_plateau.png').relative_to(ROOT)}")

    if args.report:
        from goaround_pipeline import report, report_pdf
        report.main(run_dir)
        report_pdf.main(run_dir)

    print(f"\noutputs in {run_dir.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
