# KDAB Go-Around Detection Pipeline

Detects and classifies **go-around** events in raw ADS-B arrival data
(OpenSky-style state vectors) for Daytona Beach International Airport (KDAB).
Built for the ERAU-fleet yearlong arrivals dataset. Every airport-specific
parameter lives in [`goaround_pipeline/config.py`](goaround_pipeline/config.py),
so the method can be transferred to other airports and datasets.

## Results at a glance

Dataset: ERAU fleet arrivals at KDAB, 2025-01-02 to 2025-12-23.

| | |
|---|---|
| Independent approaches | 87,092 |
| **Go-around events** | **1,888** |
| Ambiguous candidates (flagged, excluded from rate) | 265 |
| Go-around rate | **21.7 per 1,000 approaches** |

Full tables and figures: [`results/summary_report.md`](results/summary_report.md)
and [`results/summary_report.pdf`](results/summary_report.pdf).

## Method overview

1. **Load & clean** (`loading.py`) — daily parquet files; AGL computed from
   GNSS altitude minus field elevation (baro altitude is QNH-uncorrected and
   only used as a gap-filler after re-referencing to GNSS); altitude and
   vertical rate get a 7 s rolling-median smooth.
2. **Flight legs** (`loading.py`) — each aircraft-day is split into legs on
   20 min data gaps. Training aircraft fly several legs/day and several
   approaches/leg, so all detection is per approach, never per flight.
3. **Approach detection** (`approaches.py`) — contiguous intervals where the
   aircraft is on a runway's extended centerline (< 5 NM out, < 0.30 NM
   cross-track, track within 25° of runway heading, below 1,500 ft AGL,
   descending below 800 ft AGL at some point). Segments < 60 s apart merge;
   runway is a vote weighted toward low-altitude points (parallel-runway
   safe). A fallback catches arrivals whose final dips below the local ADS-B
   coverage floor (~50–250 ft AGL) before alignment is established.
4. **Outcome classification** (`classify.py`) — each approach becomes one of:

| Outcome | Meaning |
|---|---|
| `full_stop` | Touchdown (or data ends low/descending at leg end = landed below coverage floor) |
| `touch_and_go` | Touchdown evidence, then sustained climb |
| `go_around` | **No touchdown; V-shaped low point (plateau ≤ 20 s); sustained climb (≥ 300 fpm for ≥ 15 s within 120 s of the low point) regaining ≥ 250 ft; low point below 1,000 ft AGL** |
| `low_approach` | No touchdown, climb-out, but a level plateau ≥ 30 s at the low point (deliberate low pass) |
| `ga_ambiguous` | No touchdown + climb-out, plateau 20–30 s — kept, flagged, excluded from the strict count |
| `continued_approach` | Aligned fragment followed < 4 min later by another aligned segment on the same leg (S-turn/realignment) — not an independent attempt |
| `unresolved` | Outcome not classifiable (coverage loss, unusual maneuvering) |

Touchdown evidence is any of: `onground` flag, AGL ≤ 25 ft, plateau ≥ 20 s
below 120 ft AGL (GNSS bias makes “on the runway” read up to ~100 ft),
groundspeed ≤ 50 kt below 200 ft, or a > 12 s data gap below 150 ft (dip
below the coverage floor).

The **plateau duration** is the core shape metric. For climb-away events it
is measured from the last descent into the low band (min AGL + 60 ft) until
sustained climb start — anchoring on the climb makes it immune to slow
altitude drift across the band edge during a level segment. On this dataset
the metric separates the classes with an empty gap: go-arounds all fall at
0–25 s (flare + rotate), low approaches and landing rolls at 30 s and above —
the 20/30 s cutoffs sit inside the gap.

## Setup

Python 3.12+ recommended.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Place daily OpenSky-style parquet files in `daily_raw/`, named like:

```
ERU_KDAB_Arrivals_YYYYMMDD_raw.parquet
```

Required columns: `timestamp`, `icao24`, `callsign`, `latitude`, `longitude`,
`altitude`, `geoaltitude`, `vertical_rate`, `groundspeed`, `track`, `onground`.

Raw daily files are not in this repository (several GB). Summary outputs
under `results/` are included.

## Running it

```bash
# full dataset (writes results/all_approaches.csv, results/go_around_events.csv,
# per-event plots under results/plots/)
python -m goaround_pipeline.pipeline

# specific days
python -m goaround_pipeline.pipeline daily_raw/ERU_KDAB_Arrivals_20250102_raw.parquet

# summary report + figures (after the pipeline)
python -m goaround_pipeline.report

# PDF report
python -m goaround_pipeline.report_pdf

# threshold sensitivity analysis (samples every 14th day)
python -m goaround_pipeline.sensitivity

# cross-check against the traffic library's go-around detector
python -m goaround_pipeline.validate_traffic 20250108 20250115
```

## Outputs

| Path | Contents |
|---|---|
| `results/go_around_events.csv` | One row per go-around (strict + ambiguous, distinguished by `outcome`), with UTC/local time, callsign, icao24, runway, min AGL, climb-initiation altitude and distance from threshold, peak climb rate, altitude regained, plateau duration, and what followed (`next_action`: reapproach / leg_end) |
| `results/all_approaches.csv` | Every classified approach segment (the denominator for rates) |
| `results/plots/` | Per-event PNG (map + altitude / vertical-rate / groundspeed traces) for every `go_around` / `ga_ambiguous` / `low_approach` (generated locally; not committed) |
| `results/figures/` | Summary figures |
| `results/summary_report.md` / `.pdf` | Headline statistics |
| `results/sensitivity_analysis.csv` | Event counts under one-at-a-time threshold perturbations |

## Repository layout

```
goaround_pipeline/   detection, classification, reporting
config.py            all thresholds and airport geometry (KDAB)
daily_raw/           local ADS-B parquet inputs (not committed)
results/             classified tables, figures, and summary report
```

## Known limitations

State these in any publication:

- Intent is invisible: practice go-arounds, ATC-directed go-arounds, and
  pilot-initiated balked landings are indistinguishable in surveillance data.
- A go-around initiated *from* a sustained level-off is indistinguishable
  from a low approach; 20–30 s plateaus are therefore flagged ambiguous.
- Below the local ADS-B coverage floor, a very short touch cannot be
  distinguished from a low float; plateau + speed evidence decides.
- An aircraft whose entire final approach fell below the coverage floor and
  which reappears already climbing (no observed descent ≥ 150 ft before
  the low point) is classified `unresolved`, not `go_around` — the data
  cannot distinguish a go-around from a touch-and-go there. Go-arounds
  initiated fully below the coverage floor are therefore undetectable.
- Scope is go-arounds from established, runway-aligned approaches. Breakoffs
  from circling/power-off-180 maneuvers (never aligned) are out of scope and
  appear as `unresolved`.
- traffic's built-in `Flight.go_around` counts any re-approach (including
  after touch-and-goes) and requires a subsequent landing attempt; this
  pipeline's definition excludes touchdowns and keeps go-arounds followed by
  departures. Cross-check disagreements are definitional (see
  `validate_traffic.py`).
