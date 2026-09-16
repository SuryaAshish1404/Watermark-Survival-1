# Open Decisions

Tracks the "Decisions to make" from the action plan, plus ones surfaced while
drafting the Phase 0 docs. Nothing here is resolved yet — resolving these unblocks
the technical tasks noted.

| # | Decision | Blocks | Status |
|---|---|---|---|
| 1 | Measured vs. anticipatory arm space split in the paper | writing plan only, not build | Open |
| 2 | Which carriers enter the measured arm (trailers + signatures + attestations, or drop one) | scope of scripts/recovery/ | Open |
| 3 | Sampling frame — population, strategy, exclusions (docs/04-sampling-frame.md) | sample assembly, all measurement | Open — draft exists |
| 4 | Substantially-human threshold + sensitivity range (docs/02-substantially-human-rule.md) | spurious-gain experiment | Draft primary=90%, range 75-99% proposed |
| 5 | Fallback if collision search finds the destruction question taken | — | Not needed (docs/00-collision-search.md: no collision found) |
| 6 | Venue fallback if scope doesn't reach submission shape | — | Open, not urgent |
| 7 | Task templates for the spurious-gain "small edit" (docs/02, step 3) | Phase 5 spurious-gain run | Open |
| 8 | Repo count, activity threshold, live-query vs. fixed-corpus sampling | data/sampling/frame.md freeze | Open |
| 9 | Release definition for package-registry-only projects (npm/PyPI vs. GitHub Releases) | sampling frame freeze | Open |

Resolve in dependency order: 3 → 8/9 → sample assembly; 4 → 7 → spurious-gain build.
