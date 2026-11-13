## Use of AI

Following the local organisers' prescreening rule, AI use was not named in this repository before the final submission. It is disclosed in full here. These tools were used :

* Claude (Anthropic; Claude Opus 4.8, Claude Opus 5.5): research, project planning, and inspiration for screen designs.
* Claude Code: code review and checking. It read the rules, tests and screens against the team's own requirements and flagged mismatches. The team decided what to fix and made the change.
* NotebookLM (Google): questions about the Participants Guide.
* Qwen3-4B, run once on the team's laptop, wrote an optional one-line explanation for 9 evidence cards. A person read the lines, found one not true, and the feature was removed on 11 Nov 2026. Nothing it wrote is in the app.

No language model runs in the app. The flags come from fixed rules with tests. Every line on screen passes a wording check with 76 blocked terms (`src/baseline/compute/wording.py`).
