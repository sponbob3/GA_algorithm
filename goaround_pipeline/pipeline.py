"""
Stage 4: run the full pipeline over daily files and build the event tables.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from . import config
from .approaches import detect_approaches, truncated_final
from .classify import ClassifiedApproach, classify_approach
from .loading import load_day, split_into_legs


def _chain_postprocess(leg_results: list[ClassifiedApproach]) -> None:
    """Link consecutive approaches on the same leg: tag what followed each
    one, and fold 'unresolved' fragments followed shortly by another aligned
    segment into a single continued approach."""
    leg_results.sort(key=lambda r: r.approach.start)
    for i, r in enumerate(leg_results):
        if i + 1 < len(leg_results):
            nxt = leg_results[i + 1]
            gap = (nxt.approach.start - r.approach.end).total_seconds()
            r.next_gap_s = gap
            r.next_action = "reapproach"
            if (r.outcome == "unresolved"
                    and gap <= config.CONTINUED_APPROACH_MAX_GAP_S):
                r.outcome = "continued_approach"
        else:
            r.next_action = "leg_end"


def process_day(path: Path) -> list[ClassifiedApproach]:
    df = load_day(path)
    results: list[ClassifiedApproach] = []
    for leg in split_into_legs(df):
        apps = detect_approaches(leg)
        fallback = truncated_final(leg, apps)
        if fallback is not None:
            apps.append(fallback)
        leg_results = [classify_approach(app) for app in apps]
        _chain_postprocess(leg_results)
        results.extend(leg_results)
    return results


def results_to_frame(results: list[ClassifiedApproach]) -> pd.DataFrame:
    rows = []
    for r in results:
        a = r.approach
        rows.append({
            "leg_id": a.leg_id,
            "icao24": a.icao24,
            "callsign": a.callsign,
            "runway": a.runway,
            "approach_start_utc": a.start,
            "approach_end_utc": a.end,
            "outcome": r.outcome,
            "touchdown": r.touchdown,
            "coverage_truncated": r.coverage_truncated,
            "min_agl_ft": round(r.min_agl_ft, 1),
            "t_low_utc": r.t_low,
            "lat_low": round(r.lat_low, 6),
            "lon_low": round(r.lon_low, 6),
            "level_low_duration_s": round(r.level_low_duration_s, 1),
            "climb_start_utc": r.climb_start,
            "init_agl_ft": round(r.init_agl_ft, 1),
            "init_dist_thr_nm": round(r.init_dist_thr_nm, 3),
            "peak_climb_fpm": round(r.peak_climb_fpm, 0),
            "alt_regain_ft": round(r.alt_regain_ft, 1),
            "next_action": r.next_action,
            "next_gap_s": r.next_gap_s,
        })
    df = pd.DataFrame(rows)
    if len(df):
        df["t_local"] = (
            pd.to_datetime(df["t_low_utc"], utc=True)
            .dt.tz_convert(config.LOCAL_TZ)
        )
    return df


PLOTTED_OUTCOMES = ("go_around", "ga_ambiguous", "low_approach")


def main(paths: list[str] | None = None, plots: bool = True) -> None:
    files = (
        [Path(p) for p in paths]
        if paths
        else sorted(config.DATA_DIR.glob("*.parquet"))
    )
    config.OUTPUT_DIR.mkdir(exist_ok=True)
    plot_dir = config.OUTPUT_DIR / "plots"
    if plots:
        from .viz import plot_event
        plot_dir.mkdir(exist_ok=True)
    # accumulate table rows only - ClassifiedApproach objects hold their
    # leg's full trajectory (for plotting), which must not outlive the day
    day_frames: list[pd.DataFrame] = []
    for i, f in enumerate(files):
        day_results = process_day(f)
        if plots:
            for r in day_results:
                if r.outcome in PLOTTED_OUTCOMES:
                    name = (f"{r.outcome}_{r.t_low:%Y%m%d_%H%M%S}Z_"
                            f"{r.approach.callsign}_{r.approach.runway}.png")
                    if (plot_dir / name).exists():
                        continue
                    try:
                        plot_event(r, plot_dir / name)
                    except Exception as e:
                        print(f"  plot failed {name}: {e}", flush=True)
        print(f"[{i + 1}/{len(files)}] {f.name}: "
              f"{len(day_results)} approaches", flush=True)
        frame = results_to_frame(day_results)
        if len(frame):
            day_frames.append(frame)
        del day_results
        # checkpoint the tables after every day so an interrupted run still
        # leaves complete outputs for the days processed so far
        df = pd.concat(day_frames, ignore_index=True)
        df.to_csv(config.OUTPUT_DIR / "all_approaches.csv", index=False)
        ga = df[df["outcome"].isin(["go_around", "ga_ambiguous"])]
        ga.to_csv(config.OUTPUT_DIR / "go_around_events.csv", index=False)
    print(f"\nTotal approaches: {len(df)}")
    print(df["outcome"].value_counts().to_string())
    print(f"\nWrote {config.OUTPUT_DIR / 'all_approaches.csv'}")
    print(f"Wrote {config.OUTPUT_DIR / 'go_around_events.csv'}")


if __name__ == "__main__":
    main(sys.argv[1:] if len(sys.argv) > 1 else None)
