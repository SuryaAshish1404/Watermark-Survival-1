# Do the Marks Survive the Pipeline?

Empirical study of provenance carrier survival across software release assembly.
Target: FSE 2027. See `FSE2027_05_Do_The_Marks_Survive_Brief (1).pdf` for the brief.

## Status
Phase 0 (gatekeeping) drafted. See `ACTION_PLAN.md` for the phase plan,
`PROGRESS.md` for the execution log, and `docs/DECISIONS.md` for what's still open
before Phase 2+ can be built.

## Pilot
`experiments/stone_pilot/` — a scoped-down, single-scheme/single-repo proof that
the measurement method works end-to-end against a real watermark (STONE), a real
model (`bigcode/tiny_starcoder_py`), and real mutation tooling on a real repo
(lutris/lutris). See its `PLAN.md` and `RESULTS.md`.

## Layout
- `docs/` — instrument design docs (outcome definitions, sampling frame, rules),
  fixed *before* measurement per the brief's dependency graph.
- `catalogue/measured/`, `catalogue/anticipatory/` — mined operation catalogues
  (populated by `scripts/mining/`, not hand-written).
- `scripts/recovery/` — per-carrier presence/verification checks.
- `scripts/mining/` — operation-catalogue and sampling-frame derivation from repo
  configs.
- `data/sampling/` — frozen repo/release list + exclusion log, once docs/04 is
  resolved.
- `results/measured/`, `results/anticipatory/`, `results/composed/` — retention
  tables, per arm.

## Reading order for Phase 0
1. `docs/00-collision-search.md` — no collision found, gap is open (checked 2026-09-17)
2. `docs/01-outcome-definitions.md` — retained / silently lost / spuriously gained
3. `docs/02-substantially-human-rule.md` — spurious-gain threshold + sensitivity range
4. `docs/03-before-state.md` — how "emitted then destroyed" is established
5. `docs/04-sampling-frame.md` — proposed population/strategy/exclusions (open decision)
6. `docs/05-literature-sheet.md` — Phase 1 literature pass, strength/weakness per reference
7. `docs/DECISIONS.md` — what's still blocking Phase 2
