# Literature Sheet

Research Task #10 from the brief: exhaustive literature pass, columns are the
strength we can use and the weakness we can address, covering code watermarking,
trailer-based mining, supply-chain provenance, and reproducible builds. This sheet
is the working artifact; the paper's related-work section is written from it, not
the other way around. Re-run the collision-adjacent parts of this search before the
related-work section is finalized and again before submission (docs/00).

Checked: 2026-09-17.

## Code watermarking

| Ref | Venue/Year | Claim | Strength we use | Weakness we address |
|---|---|---|---|---|
| Suresh, Ugare, Singh, Misailovic — *Is Watermarking LLM-Generated Code Robust?* | ICLR 2024 Tiny Papers (2pg), expanded arXiv:2403.17983 | Semantics-preserving transforms (variable renaming, dead-code insertion) erase watermarks without changing behavior | The measurement pattern we port: apply a transformation, re-run the detector | Threat model is adversarial (evaluator models an attacker); unit is a snippet, not a release; each transform applied in isolation, not composed. We are a two-page Tiny Paper's full-study successor, not a rebuttal — cite as base paper, not as prior art we're correcting |
| STONE (syntax-aware, non-syntax-token embedding) | Findings of EACL 2026 | Embeds only in non-syntax tokens to preserve keywords/structure | Released, usable as-is; strong candidate for anticipatory-arm scheme #1 | Evaluated against transformations chosen by the evaluator, not against a release-assembly pipeline; single-artifact unit |
| SrcMarker (dual-channel via scalable code transformations) | IEEE S&P 2024 | Dual-channel embedding survives more transform classes than single-channel schemes | Released, strong candidate for anticipatory-arm scheme #2 | Same unit-of-analysis gap as STONE |
| Kirchenbauer et al. — *A Watermark for Large Language Models* | ICML 2023 | Foundational LLM-output watermarking (not code-specific) | Establishes the detection-statistics vocabulary (green/red list, z-score) we inherit for reporting variance across repeated runs | Text-generation watermark, not code-aware; cite as ancestor, not a candidate scheme itself |
| CLASP (training-free, semantic-preserving) | arXiv:2510.11251 | Training-free watermarking via semantic-preserving transformation | No training cost — cheapest to pin and reproduce for the anticipatory arm | Recency (2025) means less field validation than STONE/SrcMarker; candidate scheme #3 if we want 3-4 schemes |
| PromptMark (prompt-guided iterative feedback) | arXiv:2606.20835 | Prompt-guided iterative embedding | Very recent (2026), shows the space is still active | Least field-tested of the candidates; adds scheme-selection risk (brief's Decision #2 equivalent for schemes) |
| ACW, CodeMark, CodeIP | scattered venues, see brief's positioning note | Occupy the same embed-via-semantics-preserving-transformation space | Confirms the anticipatory arm has a saturated field of released, comparable schemes to choose 2-4 from | We are not proposing a new scheme; must state this early (brief's Research Task #9) so no reviewer reads the study as incomplete |
| *Can We Trust the Source? A Systematic Review of Watermarking and Attribution for AI-Generated Code* | Information and Software Technology, 2026 | Field favors accuracy/invisibility over long-term resilience | Names our exact gap from the scheme side — cite as the paper that motivates this study from the watermarking literature's own self-assessment | None for our purposes — this is a review, not competing empirical work |

## Trailer-based mining / agent detection

| Ref | Venue/Year | Claim | Strength we use | Weakness we address |
|---|---|---|---|---|
| *Detecting AI Coding Agents in Open Source: A Validated Multi-Method Census of 180 Million Repositories* | arXiv:2606.24429 | Separates agent-authored from agent-trailered commits; per-cell precision with CIs; relative-recall analysis of undercount | Closest work — adopt its validated labelling procedure rather than reinventing one (used directly in docs/02's substantially-human rule) | Characterizes the signal *as emitted*, at the commit, says nothing about what happens to the signal afterward — this is exactly the gap we fill. Must position against, not merely cite |
| *Beyond Simpson's Paradox: A Cascade of Confounders in AI Agent Pull-Request Co-Authorship* | arXiv:2606.24429-adjacent, arXiv:2606.24429 cf. brief's ref list — reports 1.2%-95% trailer-use variance across agents | Confirms trailer emission practice is wildly inconsistent across tools, not a stable signal even before any operation touches it | Strengthens our motivation: if emission is already this noisy, post-emission loss/gain makes downstream classification worse, not just noisy | Not itself a survival study |
| *Who Maintains Agent Skills? A Longitudinal Study of Human-Governed, AI-Assisted Skill Maintenance* | arXiv:2609.05677 | 62% of substantive edits carry a trailer; 4% false positive / 8% false negative from a small audit; states trailer-generation practice and squash workflows can't be disentangled | Names the exact gap this paper closes, independently and recently (Sept 2026) — the strongest "why it matters" citation available | States the problem, doesn't investigate it; also means we should check this didn't turn into a fuller study before we cite it as merely naming the gap (re-verify at related-work-finalization pass) |

## Supply-chain provenance

| Ref | Venue/Year | Claim | Strength we use | Weakness we address |
|---|---|---|---|---|
| in-toto (Torres-Arias et al.) | USENIX Security 2019 | Attestation formats + step-wise supply-chain model | Formal vocabulary for provenance-over-a-sequence-of-steps — candidate frame per brief's Research Task #7, though brief cautions it's vocabulary, not yet predictive | Specifies what *should* be recorded/verified, not what survives when ordinary teams (not adversaries) perform the steps |
| SLSA specification | slsa.dev | Step-wise supply chain levels, attestation requirements | Platform support moving toward default (per practitioner sources) — must confirm against platform docs before citing as fact (brief's Research Task flags this) | Reproducible/hermetic builds were explicitly *removed* from SLSA 1.0 because they're hard to implement in practice — this is independent corroboration that our rebuild-breaks-attestation-linkage claim has a documented cause, not just an observed effect |
| Kettle: Attested builds for verifiable software provenance (Asad & Arko) | arXiv:2605.08363, May 2026 | TEE-based attested builds bind provenance to hardware root of trust instead of build-infra operator | Shows the field's response to provenance trustworthiness is to harden *emission* (better attestation), not to measure *survival* through ordinary downstream operations — reinforces that our question (what happens after emission) is unaddressed even by the newest work | Different problem (attacker-resistant attestation generation) — cite as "the field is investing in making claims stronger, not in measuring whether they survive," not as a collision |
| *Authenticated Contradictions from Desynchronized Provenance and Watermarking* (Integrity Clash) | arXiv:2603.02378, CVPR 2026 Workshop APAI | Two independent provenance layers (C2PA manifest, pixel watermark) can validly disagree, both passing verification | Same shape of argument as our compositionality claim — "layers don't compose" — reusable framing, cross-domain corroboration | Image/C2PA domain, not software; no release-assembly operations; not a collision (see docs/00) but worth citing for the shared structural point |
| *Was It Never Collected, or Rewritten Away?* | arXiv:2607.02774 | Separates ingestion gaps from upstream history edits in a mining dataset (World of Code) | Directly relevant methodological cousin for our before-state reconstruction procedure (docs/03) — same "absence of signal vs. absence of evidence" distinction, different question | About mining-tool artifacts, not about whether carriers survive release assembly — cite as related method, not competing result |

## Reproducible builds

| Ref | Venue/Year | Claim | Strength we use | Weakness we address |
|---|---|---|---|---|
| *Reproducible Builds: Increasing the Integrity of Software Supply Chains* | arXiv:2104.06020 | Foundational framing of reproducible builds as a supply-chain integrity mechanism | Background citation for why rebuild is a release-assembly operation worth including in the operation catalogue at all | Predates the attestation/SLSA ecosystem's current form; use for framing only, not current-state claims |
| S3C2 Industry Summit reports (2023-11 through 2025-09) | arXiv:2408.16529, 2505.10538, 2510.24920, 2605.29226 | Practitioner-reported view: self-attestation can be misleading; trusted build/execution "remains an unresolved problem"; in-toto attestations "not yet being shipped to customers" in parts of industry | Practitioner corroboration that attestation breakage/non-adoption under real build pipelines is a live, named industry problem — supports the brief's motivation without over-claiming theory | Industry-summit reports, not peer-reviewed empirical studies — cite as motivation/corroboration, not as evidence with the same evidentiary weight as the census paper |

## SIGSOFT Empirical Standards
Ralph, Hoda, Treude — *ACM SIGSOFT Empirical Standards*, ACM 2020,
https://www2.sigsoft.org/EmpiricalStandards/ — governs the standards mapping already
in the brief (Repository Mining, Engineering Research, Benchmarking and Simulation,
Data and artifact standard, Sampling supplement). No claim to check; methodology
reference only.

## What this closes vs. leaves open (Research Task #10 checklist)
- [x] Code watermarking — 8 schemes/reviews covered, sufficient to pick 2-4 pinned
  schemes for the anticipatory arm (Decision #6 in docs/DECISIONS.md still open:
  which 2-4, and rejection reasons for the rest).
- [x] Trailer-based mining — positioned against the census paper and its
  contemporaries; confirms no collision (docs/00).
- [x] Supply-chain provenance — in-toto/SLSA as vocabulary per the brief's caution;
  Kettle and the Integrity Clash paper both checked and confirmed non-colliding.
- [x] Reproducible builds — practitioner corroboration found (S3C2 summits, SLSA's
  own removal of hermetic-build requirements); no dedicated academic study of
  attestation breakage under ordinary rebuild found, consistent with docs/00's
  verdict that the gap is open.
- [ ] Not yet done: forward-citation check on the census paper and the Sept 2026
  longitudinal study (arXiv:2609.05677) — who has cited them since, in case someone
  is already building on either. Brief's Research Task #10 note names this
  explicitly; do this pass again immediately before the related-work section is
  frozen, since both papers are recent enough that citations are still accumulating.
