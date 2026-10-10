Prescreening prototype – concept demo

# Baseline

Baseline is a phone app that lets an astronaut check their health each day against their own normal, from a wearable record (simulated here) and a 2-minute self-check. When a reading moves outside that person's usual range, it shows the numbers, the NASA study behind the change and a step to consider, and it never diagnoses.

Evidence status: four rules cite an NTRS report reviewed by the team, two cite an OSDR study still to be reviewed, and the SpO2 and core temperature cards have a step but no study yet (see [Evidence cards](#evidence-cards)).

> **All telemetry in this repository is simulated.** No real crew data exists here. We generated the vitals in `data/fixtures` and labelled them "simulated", and the demo page shows "Simulated data" on every screen.

**Pre-screening prototype.** Everything here was written between 30 September and 10 October 2026, before the hackathon. The hackathon build starts on 14 November 2026 at 9:00 a.m. local time and will be committed from that date, so hackathon work can be told apart from this prototype by its commit dates.

## How to run offline

You need Python 3.11 or later. No `make`, no Node, no account. Install once while online. After that, everything runs with wifi off.

Open a terminal in this folder and run the lines one at a time.

**Windows (PowerShell)**

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
pytest -q
python -m baseline.demo
python -m baseline.serve
```

**Mac**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
python -m baseline.demo
python -m baseline.serve
```

**Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
python -m baseline.demo
python -m baseline.serve
```

What each step does. The first two lines create and enter a private Python environment. `pip install` fetches the two dependencies (numpy, requests) plus pytest. `pytest -q` should print `36 passed`. `python -m baseline.demo` prints the flags for the simulated fixtures and ends with "clean fixture: 2 watch items, 0 confirmed flags". The last line starts a local web server, opens the page in your default browser and keeps running.

If the page does not open by itself, open the address the server prints, usually http://localhost:8000. It moves to 8001 to 8010 if 8000 is busy. Press Ctrl+C in the terminal to stop the server. If `pip install` fails, check that `python --version` (Windows) or `python3 --version` (Mac, Linux) shows 3.11 or later.

To test on a phone: `python -m baseline.serve --lan`, then open the second address on a phone on the same wifi. Windows may ask to allow Python through the firewall; allow it for private networks.

To run offline with `OFFLINE=1` (Mac, Linux):

```bash
OFFLINE=1 python -m baseline.serve
```

Windows (PowerShell):

```powershell
$env:OFFLINE = "1"; python -m baseline.serve
```

The demo never requests anything outside localhost, so it behaves the same with or without the flag; with `OFFLINE=1` the fetch scripts in `scripts/` also refuse to run, so nothing can reach the network by accident.

If you have `make`, the same four commands are `make install`, `make test`, `make demo` and `make serve`.

The page loads files only from `web/`, which holds the fonts, Chart.js, the rules, the fixture and the radiation summary. A Content-Security-Policy blocks every other host, and the page makes no network request outside localhost. "Start the demo again" on day 30 resets the demo in memory, without reloading, so a phone that has loaded the page once can run it again offline. The server sends `Cache-Control: no-store`, so a reload always gets the latest files.

## The 90-second demo

For a repeatable demo, use the 'Use recorded day-29 self-check' button.

1. **Morning check.** A guide card opens first; "Start self-check" or "Skip" leads to the check. A five-round reaction test, sleep hours (typed, or in half hours with − and +) with an optional note, questions on sleep quality and mood, and a near-vision line to mark "Clear" or "Blurred". In the reaction test, a circle appears after a random 1 to 3 second delay, and the median time counts. "Use recorded day-29 self-check (simulated)" loads the simulated record's day-29 reaction time instead (338 ms, labelled "Recorded, simulated"), so the reaction flag fires in every demo. "Save and compare" turns the answers into today's row (day 29).
2. **Console.** The 30-day chart of heart rate variability (HRV), sleep and reaction time. A key under the title explains the marks: the grey band is the usual range (the average of earlier days, plus or minus 2 standard deviations), an orange dot is flagged and an orange ring is being watched. Today's check is the last point.
3. **Flag list.** What moved outside the usual range today, each in two lines: today's value against your usual, then a plain status such as "Well outside your usual range, third day running."
4. **Evidence card.** Tap a flag to see what changed and by how much, in plain words. Then the numbers (today, your usual, usual spread, how far in multiples of the usual spread, status), "Why it matters" with the study's key finding in bold and a link to the source, and "Step to consider" with links to its sources. The rule's internal name sits in small type at the bottom, and "Back to list" and "Queue for flight surgeon" stay at the bottom of the screen. Every line passes the same wording check as `src/baseline/compute/wording.py` before it appears.
5. **Queue for flight surgeon.** Shows the summary and "Sent to the queue. Earliest reply in 44 minutes (22 minutes each way at Mars distance)." Display only; nothing is sent.
6. **Show next day.** Day 30 from the simulated record, with each of yesterday's flagged readings compared with today. "Start the demo again" goes back to the guide card.

Wifi stays off for the whole demo.

<img src="web/screenshots/2-console-390.png" width="300" alt="Console: 29 days of heart rate variability, sleep and reaction time with the usual-range band and its key; days 27 to 29 flagged in orange; the latest NOAA proton reading below"> <img src="web/screenshots/4-evidence-390.png" width="300" alt="Evidence card for reaction time: the change in plain words, the numbers, why it matters with the NTRS source link, and the Back to list and Queue for flight surgeon buttons">

## What is real and what is simulated

Real:

- Search results from NASA's Open Science Data Repository (OSDR) for 7 keywords, cached in `cache/osdr/` on 30 September 2026. Each file keeps its source URL and fetch time.
- Search results from the NASA Technical Reports Server (NTRS) for the same 7 keywords, cached in `cache/ntrs/` on 3 October 2026 (UTC). Each file keeps its source URL and fetch time.
- NOAA GOES integral proton flux for 7 days, cached in `cache/noaa/` on 30 September 2026 with its source URL and fetch time. `src/baseline/compute/radiation.py` raises a solar particle event flag at the NOAA S1 level (flux at 10 MeV or more, at or above 10 pfu), with tests. `scripts/build_radiation_summary.py` turns the cache into `web/data/radiation.json`, and the console shows the latest reading in its own box titled "Real data: NOAA GOES".
- Your answers in the demo's morning check. They replace day 29's reaction time (unless you use the recorded day-29 self-check, which is simulated), sleep and mood, stay in your browser and are gone on reload. The optional sleep note is shown on the sleep card and in the flight-surgeon summary; no rule reads it.

Simulated:

- All telemetry for one crew member over 30 days: heart rate, HRV, blood oxygen (SpO2), core temperature, sleep, exercise minutes, reaction time and mood.
- `src/baseline/fixtures.py` generates it as Gaussian noise around fixed per-person means, with random seed 7.
- `crew_a_anomaly.json` lowers HRV, sleep and mood and slows reaction time on days 27 to 29, then at half strength on day 30. `crew_a_clean.json` is noise only.

The card text is fixed wording, filled in with the rule output.

## How the rules flag a reading

- The personal baseline is the mean and standard deviation of the person's previous days, up to 30. The current day is never part of its own baseline.
- A 14-day warm-up means no flag can fire before day 15, so every baseline has at least 14 days behind it.
- A reading 2 or more standard deviations from the usual becomes a watch item on its first day. Only the direction that matters counts, such as low HRV or slow reaction time.
- The reading is confirmed if it is 3 or more standard deviations out. It is also confirmed if the same signal was 2 or more out the day before.
- Two or more confirmed signals within 48 hours also raise `two_signals_in_48h`.

The Python in `src/baseline/compute` is the reference. The page runs a small JavaScript port of it in `web/rules.js`, and `tests/test_web.py` checks that both give the same flags on both fixtures.

### How often the rules fire on pure noise

The false-alarm test uses 50 clean 30-day records (seeds 1 to 50, 7 signals each). On average, the rules raise 0.64 confirmed flags per record: 0.60 from single signals and 0.04 from two signals together. They also raise about 3.1 watch items per record. Of the 50 records, 26 have no confirmed flag. The clean fixture in the tests (seed 7) has 0 confirmed flags and 2 watch items.

## Evidence cards

Six rules cite a source in `docs/evidence_map.json`; the first four were reviewed by the team, the mood and 48-hour entries still need review:

| Rule | Source |
|---|---|
| `hrv_below_personal_baseline` | [NTRS 20040087874](https://ntrs.nasa.gov/citations/20040087874), Microgravity alters respiratory sinus arrhythmia and short-term heart rate variability in humans; countermeasure step (ARED or T2 session) from [NTRS 20140002864](https://ntrs.nasa.gov/citations/20140002864), Benefits, Consequences, and Uncertainties of Conventional (Exercise) Countermeasure Approaches |
| `heart_rate_above_personal_baseline` | [NTRS 20040087874](https://ntrs.nasa.gov/citations/20040087874), the same study; countermeasure step (repeat the reading at rest, report if still high), source to be confirmed by the research lead |
| `sleep_below_personal_baseline` | [NTRS 20240002094](https://ntrs.nasa.gov/citations/20240002094), Impact of Sleep Shifting Strategies on the International Space Station; countermeasure step from [NTRS 20190002002](https://ntrs.nasa.gov/citations/20190002002), Sleep Environment Recommendations for Future Spaceflight Vehicles |
| `reaction_above_personal_baseline` | [NTRS 20240012108](https://ntrs.nasa.gov/citations/20240012108), Cognitive Performance in ISS Astronauts on 6-Month Low Earth Orbit Missions; countermeasure step (sleep window and circadian lighting) from [NTRS 20240002094](https://ntrs.nasa.gov/citations/20240002094) and [NTRS 20140012988](https://ntrs.nasa.gov/citations/20140012988), Addressing Challenges to the Design & Test of Operational Lighting Environments for the International Space Station |
| `mood_below_personal_baseline` | [OSD-140](https://osdr.nasa.gov/bio/repo/data/studies/OSD-140), Dynamic nature of epigenetic patterns observed during the Mars 520-d mission simulation (a ground isolation study, not spaceflight); countermeasure step (private conference or crew journal), source to be confirmed by the research lead |
| `two_signals_in_48h` | [OSD-140](https://osdr.nasa.gov/bio/repo/data/studies/OSD-140), the same study; countermeasure step (ARED or T2 session) from [NTRS 20140002864](https://ntrs.nasa.gov/citations/20140002864) |
| `spo2_below_personal_baseline` | No study yet; countermeasure step (check the sensor fit, repeat, report if still low), source to be confirmed by the research lead |
| `core_temp_above_personal_baseline` | No study yet; countermeasure step (lighter exercise, scheduled fluid intake, repeat later today), source to be confirmed by the research lead |

Every rule has a countermeasure step, and a test checks this. SpO2 and core temperature still show "No matching study cached". Nothing counts as evidence until the research lead has read a source and copied it in by hand.

**Not yet reviewed by the research lead.** This list matches `docs/evidence_map.json`; everything else in the map was reviewed by the team.

- Three new sources, picked on 10 Oct 2026, with the card text written from them:
  - [OSD-140](https://osdr.nasa.gov/bio/repo/data/studies/OSD-140): the study on the mood and 48-hour cards.
  - [NTRS 20140002864](https://ntrs.nasa.gov/citations/20140002864): the source of the ARED or T2 step on the heart rate variability and 48-hour cards.
  - [NTRS 20140012988](https://ntrs.nasa.gov/citations/20140012988): the second source of the reaction-time step; the first, NTRS 20240002094, is the sleep study the team reviewed.
- Four steps whose source reads "to be confirmed by research lead":
  - Mood, written by the team. NTRS 20130011053 was checked and covers autogenic-feedback training, not this step.
  - Heart rate, added on 10 Oct 2026 so that every card has a step.
  - SpO2, written by the team. No pulse-oximetry or cabin-oxygen reference is in the cached searches.
  - Core temperature, written by the team. The NASA core-temperature study by Stahn et al. is not in the cached searches.

The seven cached OSDR searches returned 57 studies, none reviewed yet. Twelve list the organism as Homo sapiens, and five of those come from human crew members (OSD-316, OSD-575, OSD-656, OSD-903, OSD-943). The rest are mouse, rat, fly or cell studies.

Each entry is keyed by rule id, for example `reaction_above_personal_baseline`. It has `source_type` (`osdr` or `ntrs`), `source_id`, `title` and `url`, and optionally `plain_words`, `key_finding`, `countermeasure` and `countermeasure_source`. `key_finding` is the phrase the card shows in bold; it must appear word for word in `plain_words`, and a test checks this. A study without an id and URL is not shown, and neither is a countermeasure without `countermeasure_source`. Where a step's source is not yet known, that field says so in words (for example "to be confirmed by research lead") and the card shows it as plain text, not a link. After editing the map, copy it to `web/data/evidence_map.json`. A test fails if the two differ.

## Data sources

| Source | Agency | Used for | Where | Status |
|---|---|---|---|---|
| OSDR / GeneLab | NASA | Study id and URL behind every flag | [osdr.nasa.gov](https://osdr.nasa.gov) (REST, no key) | search results cached; no study reviewed yet |
| NASA Technical Reports Server (NTRS), Human Research Program reports | NASA | Reference numbers, countermeasure protocols | [ntrs.nasa.gov](https://ntrs.nasa.gov) | search results cached; four reports reviewed and cited on evidence cards |
| MSL RAD (Curiosity rover) | NASA PDS | Real Mars radiation dose for the radiation indicator | [pds.nasa.gov](https://pds.nasa.gov), search "MSL RAD" | planned, access not verified |
| GOES proton flux | NOAA | Solar particle event alert | [SWPC 7-day integral protons](https://services.swpc.noaa.gov/json/goes/primary/integral-protons-7-day.json) | cached; rule and tests done; latest reading on the console |
| Vitals telemetry | ours, simulated | Daily heart rate, HRV, SpO2, core temperature, sleep, exercise minutes, reaction time, mood | `data/fixtures` | built (clean and anomaly fixtures) |

## Challenge

[Create Health Monitoring Software for Astronauts on Space Missions](https://www.spaceappschallenge.org/2026/challenges/create-health-monitoring-software-for-astronauts-on-space-missions/), NASA Space Apps Challenge 2026.

## Team

Obsidian Prime, Bangladesh.

## License

Apache-2.0. See [LICENSE](LICENSE).

Third-party files in `web/`:

- Chart.js 4.5.1: MIT, `web/vendor/chart.umd.js`, licence header kept.
- Source Sans 3 by Adobe: SIL Open Font License 1.1, `web/fonts/OFL.txt`.