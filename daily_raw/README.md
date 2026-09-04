# Daily raw ADS-B arrivals

Put one OpenSky-style parquet file per day in this directory:

```
ERU_KDAB_Arrivals_YYYYMMDD_raw.parquet
```

Required columns: `timestamp`, `icao24`, `callsign`, `latitude`, `longitude`,
`altitude`, `geoaltitude`, `vertical_rate`, `groundspeed`, `track`, `onground`.

These files are large (several GB for a full year) and are gitignored.
The pipeline reads every `*.parquet` here when run with no arguments:

```bash
python -m goaround_pipeline.pipeline
```
