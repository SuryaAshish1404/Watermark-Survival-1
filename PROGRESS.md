# Progress Log

Chronological log of what's actually been done. `ACTION_PLAN.md` is the plan;
this is the record of execution against it. Newest entries at the top.

---

## 2026-09-17

**Phase 0 — Gatekeeping: complete except sampling frame freeze**

- Initialized git repo (`D:\Watermark-Survival` was not a repo before today).
- Scaffolded directory structure: `docs/`, `catalogue/{measured,anticipatory}/`,
  `scripts/{recovery,mining}/`, `data/sampling/`, `results/{measured,anticipatory,composed}/`.
- Ran collision search (`docs/00-collision-search.md`). No direct collision. Closest
  adjacent work: arXiv:2603.02378 (image provenance/watermark desync, CVPR 2026 —
  different artifact type) and arXiv:2607.02774 (commit-provenance mining dataset —
  different question). Gap confirmed open.
- Drafted operational outcome definitions — retained / silently lost / spuriously
  gained, per-carrier presence tests (`docs/01-outcome-definitions.md`).
- Drafted substantially-human threshold rule: primary 90%, sensitivity range
  75-99%, reusing the census paper's (arXiv:2606.24429) labelling procedure rather
  than inventing a new one (`docs/02-substantially-human-rule.md`).
- Drafted before-state reconstruction procedure, including the exclusion-log path
  for unrecoverable pre-rewrite refs (`docs/03-before-state.md`).
- Drafted sampling frame (`docs/04-sampling-frame.md`), then resolved two of its
  open decisions with the user:
  - Sampling method: **fixed-corpus snapshot** (not live API query) — reproducibility.
  - Release definition: **GitHub Release is authoritative** over package-registry
    publish events; registry-only repos excluded with reason code.
- Opened `docs/DECISIONS.md` to track what's resolved vs. still blocking.
- Wrote `ACTION_PLAN.md` — the revised phase plan (previously only in chat), with
  checkboxes reflecting the above.
- Three commits made: scaffold + Phase 0 docs; sampling/release decisions;
  ACTION_PLAN.md.

**Still blocking Phase 2 build work** (see `docs/DECISIONS.md`):
- #7 — spurious-gain "small edit" task templates, not yet fixed
- #8 — exact repo count and fixed-corpus snapshot date, not yet fixed

**Not started:** Phase 1 (literature pass beyond the collision search), Phase 2
instrument build, all measurement.
