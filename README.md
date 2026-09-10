# Go-Around Detection from ADS-B Data

A rule-based, airport-configurable pipeline that detects and classifies
**go-arounds** (and every other approach outcome: full-stop landings,
touch-and-goes, low approaches) in raw ADS-B trajectory data. Built and
validated on a year of arrivals at Daytona Beach Intl (KDAB); designed to
transfer to any airport via per-airport profiles.

Pure Python (pandas/NumPy geometry, no machine learning): every detection
is explainable, every threshold is a named, documented parameter.

## Quick start

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt

# put daily .parquet/.csv files in datasets/<ICAO>_<label>/   e.g. KDAB_2025
.venv/bin/python run_analysis.py KDAB_2025
```

That is the entire workflow. Each run writes a **fresh numbered folder**
`output/<dataset>/run_NN/` containing:

| file | content |
|---|---|
| `go_around_events.csv` | one row per go-around (time, aircraft, runway, low-point coordinates, min AGL, climb metrics, what followed) |
| `all_approaches.csv` | every classified approach segment (the denominator) |
| `summary.pdf` + `summary_outcomes.csv` | exact counts and percentages per outcome |
| `summary_by_runway.csv`, `summary_by_month.csv` | outcome counts and go-around rate per 1,000 by runway / month |
| `plots/` | per-event trajectory plot (map + AGL/vertical-rate/groundspeed) for every go-around, ambiguous case, and low approach |
| `run_config.txt` | full provenance: every resolved parameter of the run |

Flags: `--report` (figures + narrative report + PDF) · `--calibrate`
(plateau-duration histogram, see below) · `--no-plots` · `--limit N`.

## Datasets and airports

- **Dataset folder name = `<ICAO>_<label>`** — the prefix selects the
  airport profile `airports/<ICAO>.yaml`. Multiple datasets coexist;
  nothing is overwritten. See `datasets/README.md` for the required
  columns.
- **New airport:** `python run_analysis.py new-airport KBNA` generates the
  profile (runways, bearings, elevation) from the OurAirports database.
  Review it: set the timezone, the preset, terrain mode, and whether the
  dataset is arrivals-only.

### Airport profile settings

| setting | meaning |
|---|---|
| `preset` | `training_ga` (calibrated baseline, GA speeds) or `air_carrier` (jet speeds: touchdown gate 80 kt, 8 NM final window) |
| `terrain` | `flat` = AGL from field elevation (right for flat sites); `dem` = AGL from a terrain model sampled under every point (tiles auto-downloaded once, then cached — use at airports with terrain under the approaches) |
| `assume_arrivals_dataset` | `true` only when the data was queried as *arrivals*, so a flight leg ending low means "landed below the ADS-B coverage floor" |
| `overrides` | any parameter from `goaround_pipeline/config.py`, per airport |

## Method (one paragraph)

Each aircraft-day is split into flight legs on 20-minute gaps. An
*approach attempt* is a ≥20 s interval aligned with a runway extended
centerline (within 5 NM / 0.30 NM cross-track / 25° of runway heading,
descending below the AGL gates); parallel runways are resolved by a
low-altitude-weighted vote. Each attempt is classified by touchdown
evidence (on-ground flag, near-zero AGL, ≥20 s flat stretch below 120 ft,
taxi-speed groundspeed, or coverage dropout at flare height) and, when no
touchdown, by the shape of the profile low point: a **go-around** reverses
a ≥150 ft observed descent into a sustained climb (≥300 fpm for ≥15 s,
regaining ≥250 ft) with ≤20 s spent at the low point; ≥30 s level at the
bottom is a deliberate **low approach**; 20–30 s is flagged ambiguous.
Fragmented segments are chained so one continued approach never counts
twice.

## Transferring to a new airport — read this first

The thresholds above are **calibrated on KDAB training traffic**. At a new
airport (say Nashville, Class C, airline jets):

1. Generate and review the profile; pick the `air_carrier` preset.
2. Run once with `--calibrate` and inspect
   `calibration_plateau.png`: the go-around and landing-roll/low-approach
   populations must be separated by an empty gap, with the shaded cutoff
   band inside that gap. If not, adjust `LEVEL_GA_MAX_S` /
   `LEVEL_LOWAPP_MIN_S` in the profile's `overrides`.
3. Consider `terrain: dem` where there is real terrain under the finals.
4. Spot-check a sample of `plots/` before trusting the numbers.

Known limitations (state these in any publication): pilot intent is
invisible (practice, ATC-directed, and safety go-arounds count alike);
go-arounds initiated entirely below the local ADS-B coverage floor are
undetectable; a very short touch cannot be distinguished from a low float;
scope is runway-aligned finals (circling breakoffs are out of scope);
`flat` AGL assumes negligible terrain relief within ~5 NM of the field.

## Repository layout

```
run_analysis.py            <- the only file you run
airports/                  <- per-airport YAML profiles (+ cached DEM tiles)
datasets/                  <- your data (gitignored; see datasets/README.md)
output/                    <- one run_NN folder per run (gitignored)
goaround_pipeline/         <- the pipeline package
  config.py                   every threshold, documented
  loading.py / approaches.py / classify.py / pipeline.py   the four stages
  profiles.py / terrain.py    airport profiles, optional DEM AGL
  viz.py / report.py / report_pdf.py    plots and optional reports
  sensitivity.py / validate_traffic.py  robustness & cross-validation tools
results/                   <- frozen outputs of the original KDAB 2025 study
```

## Data policy

Raw ADS-B data (from the OpenSky Network) is **never committed**: it is
multi-GB and OpenSky's terms do not permit redistribution. The repo carries
code, airport profiles, and small derived products only; anyone can
reproduce the raw inputs with an OpenSky account and the query parameters
in the paper/README.
