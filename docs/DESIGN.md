# Demo page design plan

Subject: one astronaut, tired, on a phone, months from Earth, doing the morning check. Judges read over their shoulder. The page's job: show in ten seconds whether today sits inside this person's own usual range, and if not, what moved, what study explains it and what step to follow.

## Palette

| Name | Hex | Use |
|---|---|---|
| Scrub | `#E6ECE8` | Page ground. Surgical green-grey: operating rooms use it to cut glare and afterimage, which suits tired eyes. |
| Band | `#C5D3CA` | The personal baseline band. A darker step of the ground, so "your usual" reads as ground, not as a figure. |
| Ink | `#16221E` | Text, the trace, primary buttons, focus ring. Green-black from the same hue family. |
| Quiet ink | `#52625B` | Secondary text and axis labels (5:1 on Scrub). |
| Rule | `#AEBDB5` | Axis lines and the outline of the reaction test field. Nothing else. |
| Flag | `#D4470C` | International orange, the aerospace colour for "look here". Used only where a rule fired. |
| Simulated | `#FFF1A8` | Light yellow behind the "Simulated data" label, so it reads in a screen recording. Nothing else. |
| Error | `#FCE1DE` | Light red behind the script-error line at the top of the page. Shown only when a script fails. |
| Paper | `#FFFFFF` | Ground of the "Real data: NASA MSL RAD and NOAA GOES" box only, so real data never sits on the simulated ground. |

## Type

One family: Source Sans 3 (Adobe, SIL OFL 1.1), bundled as one variable woff2 in `web/fonts/` with its licence in `web/fonts/OFL.txt`. A humanist sans with open shapes that stays readable small, a plain oval zero, and tabular lining figures by default, so columns of numbers line up. No other font is loaded; the fallback is the system sans.

Changed after review (third pass below): the first build used Atkinson Hyperlegible Next, chosen for low-vision legibility. Its slashed zero made "30" read like "3θ", which costs more than it gains on a screen full of numbers.

Scale (from the classical sequence): 12 axis ticks, 14 meta, 18 body, 24 screen titles, 36 the single readout on a screen. The chart key uses the 14 px meta size; on phones it sits in two rows (the band, then "Flagged" with "Watching"), on wider screens in one. Weights 400 and 600. Body line height 1.45; titles 1.2. Tabular figures wherever numbers line up.

## Layout

Single column, left aligned, 16 px gutters, designed at 390 px, max width 480 px centred on desktop. One screen at a time. A sticky top line carries the day and "Simulated data" on every screen. The framed objects are the first-open guide card, the reaction test field, because it is the part you touch, and the real-data box ("Real data: NASA MSL RAD and NOAA GOES"), because it holds the real readings on the page. On the evidence card, "Back to list" and "Queue for flight surgeon" sit in a bar fixed to the bottom of the screen, above the iPhone home indicator (`env(safe-area-inset-bottom)`). Headings stand on their own, with no rule or bar beside them. The page scrolls without a visible scrollbar track.

```
Day 29                 Simulated data     <- 16 px bold ink on light yellow, sticky
Health status                             <- title (Gate 1 label)
Your last 29 days                         <- 20 px; "Your last 7 days" in the 7-day view
▬ Usual range (from day 15, ±2 SD)        <- 14 px quiet key, row 1 on phones
● Flagged  ○ Watching                     <- row 2; one row on wider screens
4 readings are outside your usual range.  <- 18 px, the answer first
[   7 days   |  30 days  ]                <- switch, 30 days pressed by default

Heart rate             62 beats a minute   <- channel name / today's value
Heart rate variability          42.0 ms
░░░░░░░░░░░░░░▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒             <- band from day 15
───────────────────────────●●●            <- ink trace, orange marks on flagged days
Sleep                            4.7 h
...
Reaction time                   338 ms
...
1          10          20           29    <- one shared day axis (every day in the 7-day view)

[ See what changed ]                      <- the one action, ink filled
```

Console is seven stacked channel strips (heart rate, HRV, blood oxygen, core temperature, sleep, mood, reaction time) sharing one day axis, the way a polysomnography or Holter printout is read, so drift in two signals at once is visible without a legend.

## Principles

1. The chart is the only loud thing. Everything else is text on the ground.
2. Orange means a rule fired: chart marks and the bar on each flag row, nothing else. Headings, buttons, links and focus are ink.
3. Every number is the astronaut's own: "your usual", never a population norm.
4. Say what was measured, never what it means medically.
5. One action per screen, named for what it does.

## Review against the brief

Parts of the first draft that were defaults, and what changed:

- A segmented toggle to switch one chart between HRV, sleep and reaction time. That is the SaaS default and hides the story (signals drifting together). Replaced with stacked strips.
- A row of vital-sign tiles (big number, small label) above the chart. Cut: the brief makes the chart the hero, and tiles are a card grid.
- Green "normal" and red "alert" status colours. Cut: unflagged is plain ink; there is no "good" colour, only the absence of a flag.
- Chevrons on flag rows. Cut (decorative icon); each row said "Open evidence". Restored on 10 Oct 2026: rows now carry two lines only, so a quiet chevron is the sign that a row opens.
- A pure white ground. Replaced with Scrub for glare.

## Self-critique notes

Screenshots in `web/screenshots/` (390 x 844 and 1280 x 800), taken with an automated test browser against `python -m http.server -d web 8000`. Retaken on 10 Oct 2026 against `python -m baseline.serve`: all screens at 390 x 844 with touch emulation, plus the four 1280 x 800 shots without it; state: recorded day-29 reaction, 5 hours of sleep with a note, sleep quality 2, mood 4, near vision clear.

First pass:

- The y axes started at zero, so HRV and sleep drew as flat lines and the drift was invisible. Each strip now fits its data in whole steps, three ticks, never below zero.
- The band was too faint for a phone in bright light. Darkened one step (`#CCD9D1` to `#C5D3CA`).
- The console legend ran to four lines. Cut to what the marks mean.
- The rule id broke mid-word on the evidence card. It now wraps only after an underscore.
- The evidence title did not show which flag it came from. It got the same orange bar as its row in the list. (Removed in the third pass.)
- The sleep and mood questions ran into each other. More space between fieldsets.

Second pass:

- Uneven y ticks (9, 5, 4). Now exactly three evenly spaced ticks.
- On day 30 the answer ("Nothing is outside your usual range today") sat below the fold. The one-line summary now sits under the title on the console, so the answer comes before the chart that supports it.
- A slow automated run (1364 ms) pushed the reaction axis to -100 ms. Axes are clamped at zero.

- At the time, the slashed zero of Atkinson Hyperlegible Next was kept on purpose as a legibility feature. (Reversed in the third pass.)

Third pass (team review of the screenshots):

- The slashed zero made "30" read like "3θ". Replaced the typeface with Source Sans 3 (plain oval zero), with no fallback to the old font. Checked at 4x zoom that "Day 30", "Your last 30 days" and the 70/50/30 axis labels show a plain zero.
- The orange bar beside the evidence card heading came out. Headings stand on their own; orange stays on the chart marks and the flag rows.
- A grey scrollbar track showed in screenshots. Hidden with `scrollbar-width: none` and `::-webkit-scrollbar`; scrolling works as before.

Motion: none. Chart.js animation is off and nothing moves unless a tap changes the screen, so prefers-reduced-motion has nothing to reduce.

Offline: the page sets a Content-Security-Policy of `default-src 'self'`, and the browser's request log for a full run shows only `localhost:8000` (page, font, Chart.js, two scripts, two JSON files).
