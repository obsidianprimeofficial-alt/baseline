# Usability test

## What we tested

Can people who have never seen Baseline do the daily self-check on a phone with no help? This test is about using the app. It says nothing about anyone's health, and all vital signs in the app are simulated.

## How

- **Date:** 6 Nov 2026.
- **People:** three adults outside the team, called Participant 1, 2 and 3. No names, ages, contact details, photos or recordings are kept.
- **Phones:** an Android phone and an iPhone, with the page served from a laptop over the local wifi (`python -m baseline.serve --lan`).
- **Task, read aloud:** "Imagine you are an astronaut on a long mission. It is morning, and this phone has an app you use every day to check on yourself. Please do today's check by yourself, from start to finish. Then find out what the app says about today, open one thing it points out, and find the reason behind it. I cannot help or answer questions until you are done. Please say out loud anything that confuses you."

## Results

- **All three finished the self-check with no help.**
- **None of them reported a problem**, so no wording or layout was changed.
- **Not measured:** time taken and wrong taps. We did not record them, so we cannot say whether the "2 min" on the first screen holds.

## Limits

- Three people find obvious problems. They do not give a rate.
- The participants are not astronauts, and the test was not run in mission conditions.
- The test covered the self-check. It did not cover "Show the maths", the flight surgeon queue, the next day, the solar alert, the replays, the Skylab 4 record, the laptop view or screen readers.
- The app is in English only.
- Whether the flags are right is a separate question, covered in [docs/VALIDATION.md](VALIDATION.md).