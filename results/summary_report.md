# KDAB go-around detection - summary report

Dataset: 2025-01-02 to 2025-12-23, ERAU fleet arrivals at KDAB.

## Headline numbers

- **1888 go-around events** (plus 265 ambiguous candidates, kept flagged)
- 87,092 independent approach attempts (91,810 aligned segments incl. continued fragments)
- go-around rate: **21.7 per 1,000 approaches** (strict definition, ambiguous excluded)

## Outcome breakdown

| outcome            |   count |
|:-------------------|--------:|
| full_stop          |   60090 |
| touch_and_go       |   19095 |
| continued_approach |    4718 |
| unresolved         |    4449 |
| go_around          |    1888 |
| low_approach       |    1305 |
| ga_ambiguous       |     265 |

## Monthly

| month   |   approaches |   ga |   rate |
|:--------|-------------:|-----:|-------:|
| 2025-01 |         6092 |  125 |  20.52 |
| 2025-02 |         7099 |  247 |  34.79 |
| 2025-03 |         7774 |  246 |  31.64 |
| 2025-04 |         9271 |  337 |  36.35 |
| 2025-05 |         5209 |  120 |  23.04 |
| 2025-06 |         7824 |  185 |  23.65 |
| 2025-07 |         7413 |  147 |  19.83 |
| 2025-08 |         5504 |  190 |  34.52 |
| 2025-09 |         7952 |  129 |  16.22 |
| 2025-10 |         8585 |  153 |  17.82 |
| 2025-11 |         9526 |  174 |  18.27 |
| 2025-12 |         4843 |  100 |  20.65 |

## By runway

| runway   |   approaches |   ga |   rate |
|:---------|-------------:|-----:|-------:|
| 07R      |        26324 |  385 |  14.63 |
| 07L      |        25503 | 1088 |  42.66 |
| 25L      |        11974 |  290 |  24.22 |
| 16       |         9182 |  251 |  27.34 |
| 25R      |         9050 |   73 |   8.07 |
| 34       |         4968 |   66 |  13.29 |

## Go-around event characteristics

|       |   min_agl_ft |   init_agl_ft |   peak_climb_fpm |   alt_regain_ft |   level_low_duration_s |
|:------|-------------:|--------------:|-----------------:|----------------:|-----------------------:|
| count |       1888   |        1888   |           1888   |          1888   |                 1888   |
| mean  |        179   |         204.1 |           1114.3 |          1485.3 |                   12   |
| std   |        152.4 |         156.2 |            233   |           568.2 |                    3.4 |
| min   |         41   |          16   |            320   |           250   |                    1   |
| 25%   |         91   |         116   |            960   |           875   |                   10   |
| 50%   |        116   |         141   |           1088   |          1700   |                   12   |
| 75%   |        241   |         266   |           1280   |          1875   |                   14   |
| max   |        791   |         941   |           2176   |          3000   |                   20   |

## What followed each go-around

| next_action   |   count |
|:--------------|--------:|
| reapproach    |    1815 |
| leg_end       |      73 |
