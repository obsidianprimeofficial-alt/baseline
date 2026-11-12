# References

Every source, dataset, library and font Baseline uses or shows. All links were opened on 10 Nov 2026.

## The challenge

- NASA Space Apps Challenge 2026: [Create Health Monitoring Software for Astronauts on Space Missions](https://www.spaceappschallenge.org/2026/challenges/health-monitoring-software/)

## Real data the app runs on

- **NASA MSL RAD**, Curiosity rover, dataset MSL_RAD_OBS-L2: Mars surface radiation, 29 days (11 Oct to 8 Nov 2026), cached 10 Nov 2026. [CDAWeb notes](https://cdaweb.gsfc.nasa.gov/misc/NotesM.html#MSL_RAD_OBS-L2) · [DOI 10.48322/20qb-4e17](https://doi.org/10.48322/20qb-4e17) · [PDS archive](https://pds-ppi.igpp.ucla.edu/data/MSL-M-RAD-3-RDR-V1.0/)
- **NASA MSL RAD, 20 April to 25 May 2024** (3,138 readings): the Mars radiation surge replay. [Data request](https://cdaweb.gsfc.nasa.gov/WS/cdasr/1/dataviews/sp_phys/datasets/MSL_RAD_OBS-L2/data/20240420T000000Z,20240526T000000Z/DOSIMETRY_TOTAL_f?format=json)
- **NOAA GOES** proton flux, 7 days, cached 10 Nov 2026: the solar storm alert. [SWPC data](https://services.swpc.noaa.gov/json/goes/primary/integral-protons-7-day.json)
- **Solar proton event of 9 Sep 2024** (34 pfu at 22:50 UTC): the solar storm replay. [NCEI event list](https://www.ngdc.noaa.gov/stp/space-weather/interplanetary-data/solar-proton-events/SEP%20page%20code.html) · SWPC SPE.txt, line 383 · [Australian Bureau of Meteorology alert](https://listserver.ips.gov.au/pipermail/ips-proton-alert/2024-September/000530.html)
- **Skylab 4 crew sleep estimates**, NASA CR-141886, Tables VIII to X (84 nights, roles only): the real crew record. [NTRS 19750019675](https://ntrs.nasa.gov/citations/19750019675)
- **NASA OSDR and NTRS search results**, cached 30 Sep to 10 Oct 2026: how we found the study behind each flag. [osdr.nasa.gov](https://osdr.nasa.gov) · [ntrs.nasa.gov](https://ntrs.nasa.gov)

The vital signs are simulated (`data/fixtures`). Blood pressure and blood sugar are not covered.

## Studies on the evidence cards

| Study | Used for |
|---|---|
| [NTRS 20040087874](https://ntrs.nasa.gov/citations/20040087874): heart rate variability in 4 crew, 16-day flight | Heart rate variability and heart rate flags |
| [NTRS 20140002864](https://ntrs.nasa.gov/citations/20140002864): exercise countermeasures (conference abstract) | Heart rate variability step |
| [NTRS 20240002094](https://ntrs.nasa.gov/citations/20240002094): sleep shifting on the ISS, 19 crew | Sleep flag, reaction step |
| [NTRS 20190002002](https://ntrs.nasa.gov/citations/20190002002): sleep environment recommendations | Sleep step |
| [NTRS 20240012108](https://ntrs.nasa.gov/citations/20240012108): cognitive performance in 25 ISS astronauts | Reaction time flag |
| [NTRS 20140012988](https://ntrs.nasa.gov/citations/20140012988): ISS lighting (conference abstract) | Reaction step |
| [NTRS 20150021491](https://ntrs.nasa.gov/citations/20150021491): hypobaric hypoxia evidence report (no blood oxygen readings) | Blood oxygen flag |
| [NTRS 20000104233](https://ntrs.nasa.gov/citations/20000104233): temperature regulation, 2 crew, before and after flight | Core temperature flag |
| [OSD-140](https://osdr.nasa.gov/bio/repo/data/studies/OSD-140) ([DOI 10.26030/pybz-6s43](https://doi.org/10.26030/pybz-6s43)): Mars-500 ground isolation, 6 crew, not spaceflight | Mood and 48-hour flags |

## NASA standards and briefs

- [NASA-STD-3001 Vol 1 Rev C](https://standards.nasa.gov/sites/default/files/standards/NASA/C//nasa-std-3001-vol-1-rev-c-signature.pdf): [V1 3004] for five steps, [V1 4029] for the Mars caution step.
- [NASA-STD-3001 Vol 2 Rev C](https://www.nasa.gov/wp-content/uploads/2020/10/2022-04-08_nasa-std-3001_vol_2_rev_c_final.pdf): [V2 6100] for the solar storm alert, [V2 6099] for the Mars caution step, [V2 7102] for space adaptation syndrome.
- [NASA OCHMO-TB-016 Rev B](https://www.nasa.gov/wp-content/uploads/2023/12/ochmo-tb-016-behavioral-health.pdf): the mood step.
- [NASA OCHMO-TB-020 Rev E](https://www.nasa.gov/wp-content/uploads/2023/03/radiation-protection-technical-brief-ochmo.pdf): the step "Go to the storm shelter."
- [NOAA SWPC, Solar Radiation Storm](https://www.swpc.noaa.gov/phenomena/solar-radiation-storm): the S1 level (10 pfu or more at 10 MeV or more).

## Mission-phase risks and event sources

- NASA Human Research Program hazard pages: [5 Hazards](https://www.nasa.gov/hrp/hazards/) · [Isolation and Confinement](https://www.nasa.gov/hrp/hazard-isolation-and-confinement/) · [Distance From Earth](https://www.nasa.gov/hrp/hazard-distance-from-earth/) (also the reply delay on the queue screen) · [Gravity Fields](https://www.nasa.gov/hrp/hazard-gravity-fields/) · [Hostile/Closed Environments](https://www.nasa.gov/hrp/hazard-hostile-closed-environments/)
- [NTRS 20180000936](https://ntrs.nasa.gov/citations/20180000936), SANS evidence report, pp.69 to 70: headward fluid shift.
- [NTRS 20140003729](https://ntrs.nasa.gov/citations/20140003729), decompression sickness evidence report, p.11: fluid shift "ongoing".
- [NASA osteoporosis evidence report](https://humanresearchroadmap.nasa.gov/evidence/reports/Osteo.pdf), p.21: bone loss with ARED.
- [NASA, To Protect Artemis II Astronauts, NASA Experts Keep Eyes on Sun](https://science.nasa.gov/missions/artemis/artemis-2/to-protect-artemis-ii-astronauts-nasa-experts-keep-eyes-on-sun/): the Mars caution practice.
- 20 May 2024 Mars surge: [NASA article](https://www.nasa.gov/solar-system/planets/mars/nasa-watches-mars-light-up-during-epic-solar-storm/) · [MSL RAD team slides, p.17](https://wrmiss.org/workshops/twentyseventh/Hassler.pdf) · [Posner, Richardson and Zeitlin, Solar Physics 300, 102 (2025)](https://doi.org/10.1007/s11207-025-02482-4)

## Software and fonts

| Item | Licence |
|---|---|
| [Chart.js](https://www.chartjs.org) 4.5.1, in `web/vendor/` | MIT |
| [Source Sans 3](https://github.com/adobe-fonts/source-sans) by Adobe | SIL Open Font License 1.1 |
| [JetBrains Mono](https://github.com/JetBrains/JetBrainsMono) 2.304 | SIL Open Font License 1.1 |
| Python, numpy, requests, pytest, Node.js | PSF, BSD-3-Clause, Apache-2.0, MIT, MIT |
| [Playwright](https://playwright.dev), for layout checks and screenshots | Apache-2.0 |

The AI tools and models we used are listed in [docs/AI_USE.md](AI_USE.md).

## This project

Apache-2.0. See [LICENSE](../LICENSE).