# Anticipatory-Arm Scheme Selection (Decision #6)

Resolves `docs/DECISIONS.md` #6: argue scheme selection covering availability,
reproducibility, distinct embedding strategy, and rejection reasons. Checked
2026-09-17. Flagged as a **proposed default**, same status as #7/#8 — cheap to
revisit if a pilot run shows one of the four is impractical to pin/reproduce.

## Selected: 4 schemes, 3 distinct embedding strategies

| # | Scheme | Venue | Repo | Embedding strategy | Target carrier |
|---|---|---|---|---|---|
| 1 | **STONE** | Findings of EACL 2026 | `github.com/inistory/STONE-watermarking` (official) | Rule-based, post-hoc: embeds only in non-syntax tokens, deterministic, no training | Code watermark |
| 2 | **SrcMarker** | IEEE S&P 2024 | `github.com/YBRua/SrcMarker` (official) | Neural, post-hoc: BiGRU-trained encoder over variable-naming + AST transforms, 4-bit signature | Code watermark |
| 3 | **CodeIP** | arXiv:2404.15639 | `github.com/CGCL-codes/naturalcc/tree/main/examples/codeip` (official, hosted in the NaturalCC toolkit) | Generation-time, statistical: grammar-guided logit manipulation during LLM decoding (Kirchenbauer-family, code-aware) | Code watermark |
| 4 | **CodeMark** | (dataset watermarking venue, see docs/05) | `github.com/v587su/CodeMark` (official) | Dataset-level: watermark embedded into a training corpus via variable renaming + AST/GNN modeling, detected via a fine-tuned completion model's behavior | Dataset watermark |

## Why this set

- **Availability**: all four have an official, author-linked public repository —
  confirmed by direct search, not inferred from the paper text. This is the brief's
  explicit criterion ("strength is that several are released and usable as given").
- **Reproducibility**: repos exist with runnable code, which is what lets scheme
  version + settings be pinned per docs/04's "generation settings held fixed"
  requirement, rather than us reimplementing from a paper description (a
  reimplementation risk the brief explicitly warns against — outcomes would be
  attributable to our reimplementation, not the scheme).
- **Distinct embedding strategies, not near-duplicates**: STONE (rule-based,
  post-hoc, deterministic) vs. SrcMarker (neural, post-hoc, learned) vs. CodeIP
  (statistical, generation-time, requires LLM decoding access) are three genuinely
  different mechanisms for where and how the mark enters the artifact. Running all
  three against the same operation catalogue tests whether survival is a property
  of the *mechanism* or of the *operation* — the more interesting axis for the
  paper's contribution.
- **Covers the anticipatory arm's second carrier type**: CodeMark is not a
  code-watermark peer of the other three — it's a *dataset* watermark, which the
  brief's Figure 1 lists as a separate anticipatory-arm carrier ("Dataset watermark
  and data card"). Including it means the anticipatory arm isn't code-watermark-only,
  matching the brief's stated scope rather than narrowing it.

## Rejected, with reasons

| Scheme | Reason rejected |
|---|---|
| **CLASP** (arXiv:2510.11251) | No public repository found despite direct search (paper revised as recently as 2026-04-20). Training-free is otherwise attractive, but unreproducible without either a repo or a from-scratch reimplementation we'd have to defend as faithful — availability fails the brief's stated criterion. |
| **PromptMark** (arXiv:2606.20835) | Very recent (2026), no repository found, least field-tested of any candidate in docs/05. Same availability failure as CLASP, compounded by no independent validation yet existing. |
| **ACW** | No confirmed public repository found. Described as training-free/plug-and-play in secondary sources, but no official release located to pin a version against. |
| **Kirchenbauer et al. (2023)** | Foundational but not code-specific — a general LLM-text watermark, not a source-code scheme. Kept in the literature sheet as the statistical-watermarking ancestor CodeIP's family descends from, not as a candidate itself. |

## What's still open
- Model watermark and dataset-card-only carriers (as opposed to CodeMark's dataset
  watermark) are not yet covered — the brief lists these as "if available" for the
  anticipatory arm, lower priority than the four above.
- Pin exact commit/release versions and generation settings for all four repos once
  the pilot run (Phase 4, per the brief's technical task table) is scheduled —
  tracked as a new open item, not yet in `docs/DECISIONS.md`.
