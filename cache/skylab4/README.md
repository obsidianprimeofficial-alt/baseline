# Skylab 4 crew sleep estimates

`sleep-estimates.csv`: one row per crew role and mission day, 84 days for each of three roles, 252 rows. Real NASA data, not simulated.

**What the numbers are:** crew log estimate: each crewman's own morning estimate of total sleep, split into light or medium sleep and heavy sleep, in hours. They are not measured values.

## Source

- Report: Skylab Sleep Monitoring Experiment (Experiment M133), Final Report, Contract NAS 9-12974, NASA CR-141886, January 1975.
- NTRS 19750019675: https://ntrs.nasa.gov/citations/19750019675 (opened 2 November 2026, HTTP 200). PDF: https://ntrs.nasa.gov/api/citations/19750019675/downloads/19750019675.pdf
- Tables, by PDF page number: Table VIII, CDR, pages 126 to 130. Table IX, PLT, pages 131 to 135. Table X, SPT, pages 136 to 141.

## Columns

`role`, `mission_day`, `total_sleep_h`, `light_h`, `heavy_h`, `note`. Hours are as printed on the page, so a value is usually a number but can be `≈3.0` or `?`, and a blank cell was blank on the page. Check for that before doing arithmetic.

Crew roles only, no names. Only the columns above were imported; no other column of the report's tables is in this file.

## How it was transcribed

Transcribed from the page images, not from text extracted from the scan, which misreads digits. There were two independent reads, compared on 31 October 2026, then a teammate checked 32 rows against the page images: the 7 rows that are incomplete or hard to read, and a random sample of 25. All 32 came back OK on 1 November 2026, with no corrections. The other rows had the two reads only. Written to this file on 2 November 2026.

## Rows with a note

Nothing was filled in or estimated. The note says what the page shows.

| Role | Day | Note |
|---|---|---|
| CDR | 84 | light and heavy blank; total only |
| PLT | 84 | light and heavy blank; total printed "≈3.0" |
| SPT | 3, 4 | light and heavy blank; total only |
| SPT | 84 | all three printed "?" |
| CDR | 10 | faint first digit (both reads: 0.0) |
| PLT | 18 | only PLT value not a whole/half hour (both reads: 1.8 / 7.8) |

CDR 10 and PLT 18 are complete rows, and their totals add up.
