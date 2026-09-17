# Progress Log

Chronological log of what's actually been done. `ACTION_PLAN.md` is the plan;
this is the record of execution against it. Newest entries at the top.

---

## 2026-09-17 (cont'd 2) — Phase 1 literature sheet

Wrote `docs/05-literature-sheet.md` (Research Task #10): four category tables —
code watermarking (8 refs), trailer-based mining (3 refs), supply-chain provenance
(5 refs), reproducible builds (5 refs) — each with claim / strength-we-use /
weakness-we-address columns, plus the SIGSOFT Empirical Standards methodology
reference.

New sources found via search beyond the brief's own reference list, each checked
for collision against docs/00 and confirmed non-colliding:
- Kettle (arXiv:2605.08363) — TEE-attested builds; shows the field is hardening
  emission, not measuring survival, reinforcing that our question is unaddressed.
- S3C2 Industry Supply Chain Summit reports (4 arXiv entries, 2023-2025) —
  practitioner corroboration that attestation trust/adoption is a live, named
  industry problem; cited as corroboration, not peer-reviewed evidence.
- SLSA's own removal of hermetic/reproducible-build requirements from v1.0 —
  independent confirmation that rebuild-breaks-attestation-linkage has a
  documented structural cause.
- Reproducible Builds foundational framing (arXiv:2104.06020).

Left explicitly open in the sheet: forward-citation check on the census paper and
the Sept 2026 longitudinal study (arXiv:2609.05677), to be re-run immediately
before the related-work section is frozen since both are recent enough that
citations are still accumulating. Also flags that scheme selection (which 2-4 of
the 8 watermarking schemes covered) is still Decision #6, unresolved.

One commit: literature sheet + README/ACTION_PLAN/PROGRESS updates.

---

## 2026-09-17 (cont'd) — Phase 3 build started

**Unblocked #7 and #8** with explicit defaults (not final decisions, flagged for
sign-off): spurious-gain task templates (3 bounded templates, ≤20-line diff cap,
`docs/02`) and repo count/snapshot window (N=15, rolling most-recent-full-month,
`docs/04`). Neither blocks Phase 3, since recovery checks only depend on the
already-done outcome definitions and before-state procedure.

**Built `scripts/recovery/`:**
- `outcomes.py` — pure classification logic (Outcome enum, `classify()`,
  `classify_spurious_only()`) implementing docs/01's five outcomes.
- `trailer.py` — walks `git log` for trailers matching the census paper's
  vocabulary (Co-Authored-By / Assisted-By / Generated-By).
- `signature.py` — wraps `git verify-commit`, distinguishes surfaced-failure from
  silent absence.
- `attestation.py` — interface only, `NotImplementedError` stub. Needs a real
  attestation store (GitHub Attestations API / Sigstore-Rekor / registry-embedded)
  to build against; blocked on the sampling frame producing an actual sampled repo.

**Built `tests/`** per docs/03's validation requirement (hand-built fixtures,
confirm every carrier×outcome combination classifies correctly):
- `gitfixture.py` — minimal temp-repo builder.
- `test_outcomes.py` (9 tests) and `test_trailer.py` (4 tests) — all passing.
- `test_signature.py` — logic is correct against real git semantics, but the
  GPG-key fixture setup is currently **skipped in this Windows/Git-Bash session**:
  key generation fails because gpg mis-resolves a mixed MSYS/native temp path and
  can't reach its agent (`No such file or directory` / `No agent running`). Not a
  bug in `signature.py` — needs re-verification on Linux or in CI before the
  signature check is trusted against real sampled repos.

Two commits: recovery modules + tests + decision defaults.

**Still blocking full Phase 3:** attestation store integration; anticipatory-arm
scheme runners; actual sample assembly (needs the mining script, not yet built).

**Not started:** Phase 1 literature sheet (Research Task #10 in the brief — full
literature pass with strength/weakness columns), Phase 2 operation-catalogue mining
script, anticipatory-arm scheme selection.

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
