# Open Decisions

Tracks the "Decisions to make" from the action plan, plus ones surfaced while
drafting the Phase 0 docs. Nothing here is resolved yet — resolving these unblocks
the technical tasks noted.

| # | Decision | Blocks | Status |
|---|---|---|---|
| 1 | Measured vs. anticipatory arm space split in the paper | writing plan only, not build | Open |
| 2 | Which carriers enter the measured arm (trailers + signatures + attestations, or drop one) | scope of scripts/recovery/ | Open |
| 3 | Sampling frame — population, strategy, exclusions (docs/04-sampling-frame.md) | sample assembly, all measurement | Method decided (fixed corpus); repo count/snapshot date open |
| 4 | Substantially-human threshold + sensitivity range (docs/02-substantially-human-rule.md) | spurious-gain experiment | Draft primary=90%, range 75-99% proposed |
| 5 | Fallback if collision search finds the destruction question taken | — | Not needed (docs/00-collision-search.md: no collision found) |
| 6 | Venue fallback if scope doesn't reach submission shape | — | Open, not urgent |
| 7 | Task templates for the spurious-gain "small edit" (docs/02, step 3) | Phase 5 spurious-gain run | **Default proposed 2026-09-17: 3 bounded templates, ≤20 line diff cap** |
| 8 | Repo count and fixed-corpus snapshot date | experiments/data/sampling/frame.md freeze | **Default proposed 2026-09-17: N=15, rolling most-recent-full-month window** |
| 9 | Release definition: GitHub Release vs. package registry | sampling frame freeze | **Decided 2026-09-17: GitHub Release is authoritative; registry-only repos excluded** |
| 10 | Which 2-4 code/dataset watermark schemes for the anticipatory arm | anticipatory-arm scheme runner build | **Default proposed 2026-09-17: STONE, SrcMarker, CodeIP, CodeMark — see docs/06-scheme-selection.md** |
| 11 | Pin exact commit/version + generation settings for the 4 selected schemes | anticipatory-arm pilot run | Open, not yet started |

Items 7, 8, and 10 are defaults set to unblock the build, not user-confirmed final
decisions — call out all three explicitly for sign-off before the paper cites them
as methodology, and revisit if a pilot run shows any is impractical.

No remaining hard blockers on Phase 3 build work (recovery checks), which depends
only on the outcome definitions (#done) and before-state procedure (#done), not on
7/8.
