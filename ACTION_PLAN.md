# Action Plan

Revised from the original draft to match the brief's actual scope: two arms
(measured: trailers/signatures/attestations on real history; anticipatory: code/
model/dataset watermarks on constructed releases), plus the spurious-gain direction.
See `docs/` for the Phase 0 artifacts this plan has already produced.

## Phase 0 — Gatekeeping (MUST, blocks everything) — done, see docs/
- [x] Collision search — `docs/00-collision-search.md` (no collision found, 2026-09-17)
- [x] Outcome definitions (retained / silently lost / spuriously gained) — `docs/01-outcome-definitions.md`
- [x] Substantially-human threshold rule + sensitivity range — `docs/02-substantially-human-rule.md`
- [x] Before-state reconstruction procedure — `docs/03-before-state.md`
- [~] Sampling frame — `docs/04-sampling-frame.md` (method + release definition decided; repo count/snapshot date open, see `docs/DECISIONS.md`)

## Phase 1 — Literature & Positioning
- Code watermarking robustness (Suresh et al. base paper, STONE, SrcMarker, CLASP, PromptMark)
- Trailer-based agent detection (180M-repo census) — position against, don't replicate
- Supply-chain provenance (in-toto/SLSA) as vocabulary, not a predictive theory
- AI Act Article 50 — cite as conditional motivation, not settled fact

## Phase 2 — Instrument Design
- Measured-arm carriers: agent trailers, commit signatures (GPG/sigstore), build attestations + SBOM (in-toto/SLSA)
- Anticipatory-arm carriers: 2-4 pinned code watermark schemes; model/dataset watermarks if feasible
- Mine the operation catalogue from real repo/workflow configs, with a prevalence ranking — not hand-picked
- Finalize sampling frame (repo count, snapshot date) — blocks sample assembly

## Phase 3 — Build the Measurement Framework
- Per-carrier recovery checks: trailer extraction, signature verification, attestation/SBOM resolution
- Anticipatory-arm scheme runners with pinned versions/settings
- Assemble the sampled repo/release list against the frozen frame, with an exclusion log

## Phase 4 — Measure
- Single-operation retention table, measured arm, over real history
- Single-operation retention table, anticipatory arm, over constructed releases, repeated runs with reported variance
- Pilot the anticipatory arm first to size the repeated-run count before the full matrix

## Phase 5 — Composition & Spurious Gain
- Compose operations in orders observed in real repos — composed retention, not just per-operation
- Fix the spurious-gain task templates (open decision, see `docs/DECISIONS.md` #7)
- Run the spurious-gain experiment against the fixed threshold + sensitivity range

## Phase 6 — Analysis & Paper
- Implied misclassification error for trailer-based mining studies
- Package catalogue, sampling frame, retention tables, and scripts as a reusable, regenerable artifact
- Write implications for disclosure obligations and empirical SE methodology

## Currently blocking
See `docs/DECISIONS.md` — repo count/snapshot date (#8) and spurious-gain task
templates (#7) are the two open items before Phase 2 build work can start in earnest.
