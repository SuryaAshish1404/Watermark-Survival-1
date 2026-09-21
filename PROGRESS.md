# Progress Log

Chronological log of what's actually been done. `ACTION_PLAN.md` is the plan;
this is the record of execution against it. Newest entries at the top.

---

## 2026-09-21 — STONE mutation-survival pilot (single scheme, real repo, real mutations)

User asked for a concrete pivot: pick one watermark, pick a repo, mutate, see how
the mark fares. Built and ran this as `experiments/stone_pilot/`.

**Scheme chosen: STONE**, of the 4 from docs/06 — detection needs only a
tokenizer (no GPU/model at detect time), unlike SrcMarker (needs its trained
BiGRU checkpoint, unavailable) or CodeIP/CodeMark (heavier to stand up for a
single-function pilot). Documented the choice and its limits in
`experiments/stone_pilot/PLAN.md`.

**Vendored STONE's minimal import graph** (not the whole repo — that includes a
bigcode-evaluation-harness submodule and training scripts unrelated to this
pilot) into `experiments/stone_pilot/vendor/`, byte-for-byte from commit
`bb5d809` — cited in `vendor/VENDORED.md` — so the scheme under test is STONE as
released, matching docs/06's reproducibility requirement. Windows long-path
limits blocked a normal clone of the full STONE repo; worked around with
`--filter=blob:none --sparse` and `core.longpaths=true`.

**Generation model: `bigcode/tiny_starcoder_py`** (164M, CPU, real code-pretrained
model, network access to Hugging Face confirmed working in this session).

**Repo: lutris/lutris**, reused from `data/sampling/candidates.md` (already
hand-verified). Checked its actual CI config rather than assuming a formatter —
Lutris uses `ruff format`, not black, per `.github/workflows/static.yml`; the
pilot plan was corrected to match before running.

**Pipeline built and run**: generate watermarked function → sanity-check
detection on the raw generation (passed: z=4.91 vs. threshold 4.0) → write into
the real repo → run 6 mutations (format, lint_autofix, AST variable rename,
python-minifier, AST round-trip, and a composed pipeline of all four) → re-run
STONE's own detector after each.

**One real bug found and fixed while running**: the tiny model's capped
generation trailed off mid-statement, producing unparseable code that broke
every mutation tool. Fixed by trimming to the largest syntactically valid
prefix before mutating, rather than special-casing each tool's failure.

**Result: all 6 mutations retained detectability** (z-scores 4.91-7.25, all
above the 4.0 threshold). Full table and — importantly — the limitations (N=1,
very short scored sequence so z-scores are noisy, delta raised above the paper's
typical range to compensate for the tiny model, mutation order chosen by us
rather than mined) are in `experiments/stone_pilot/RESULTS.md`. Explicitly not a
survival-rate claim — a proof that the Phase 0-3 measurement method works
end-to-end against a real scheme, real repo, and real mutation tools.

One commit: pilot script, vendored STONE subset, plan, results, raw JSON output.

---

## 2026-09-18 — First real repo, real bugs found

Live network access confirmed working in this session, so instead of only
hand-picking candidate repo names from search results, cloned one for real and ran
the actual pipeline against it.

**lutris/lutris** (`--filter=blob:none` clone, checked out working tree):
- `scripts/recovery/trailer.py` found **193 real commits** with
  `Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>` trailers.
- Confirmed 88 version tags (release practice) — satisfies docs/04's population
  criteria (agent trailer + tagged releases, not a fork). First entry in
  `data/sampling/candidates.md`, a hand-verified starter set distinct from the real
  frozen frame.
- `scripts/mining/cli.py` ran against the real checkout and correctly detected
  format/lint_autofix/rebuild/repackage signals with real cited evidence files.

**Two real bugs found and fixed by testing against live data, not fixtures:**
1. `trailer.py` and `signature.py` called `subprocess.run(..., text=True)` without
   an explicit encoding. On this Windows session that defaults to cp1252, which
   crashed decoding Lutris's UTF-8 commit messages
   (`UnicodeDecodeError: 'charmap' codec can't decode byte 0x9d`). Fixed by passing
   `encoding="utf-8", errors="replace"` explicitly in both modules.
2. `republish` detector missed Lutris's actual publish mechanism entirely (`dput`,
   the Debian PPA upload tool) — it only recognized npm/PyPI/GitHub-Release/
   GoReleaser patterns. Extended `detectors.py`'s REPUBLISH content pattern and
   step keywords to include `dput`, `ppa`, `appimage` after finding the gap
   live, not by guessing what to add in advance.

**Found a concrete source for Decision #8's fixed corpus**: the AIDev dataset
(Hugging Face `hao-li/AIDev`, arXiv:2602.09185) — 2,807 repos with agent-PR data
already extracted, same data family as the census paper. Not pulled into this
session (no HF dataset access here), but documented in docs/04 as the right source
to build the real frame from, rather than continuing to hand-pick repos one at a
time via search.

All 18 tests still pass after the fixes (17 pass, 1 skipped — the known Windows/GPG
issue). Scratch clone deleted after use.

Two commits: bug fixes to recovery modules + detector extension; candidates.md +
docs/04 update.

---

## 2026-09-17 (cont'd 4) — Operation-catalogue mining script

Built `scripts/mining/` — the tool that derives the operation catalogue from real
repo/workflow configs rather than a hand-picked list, per the brief's explicit
requirement and the Technical Tasks acceptance criterion ("regenerates from the
repository list without manual editing, and every operation class in it traces to
a configuration file that is cited").

- `detectors.py` — 12 operation-class signals across the history (squash, rebase,
  cherry-pick, fork-sync), source (format, lint-autofix, transpile, bundle,
  minify), and packaging (rebuild, repackage, republish) layers from Figure 1.
  Each signal is either existence-sufficient (a `.prettierrc` file needs no content
  check) or requires a content-pattern match inside a generic multi-purpose file
  (package.json, workflow YAML, Makefile) — kept as two separate glob categories
  after the first test run showed conflating them under-detected dedicated config
  files.
- `scan.py` — walks a repo, returns evidence tuples that always cite the matching
  file path, so no catalogue entry is ever evidence-free.
- `workflow_order.py` — parses `.github/workflows/*.yml` job step sequences and
  classifies steps by keyword, producing the *observed* operation order per
  workflow/job — this is what Phase 5's "compose operations in orders real
  projects apply them" will draw from, rather than an invented order.
- `catalogue.py` + `cli.py` — aggregates per-repo scans into a prevalence-ranked,
  JSON-serializable catalogue (`python -m scripts.mining.cli <repo>... --out ...`).

Tests (`tests/test_mining.py`, 5 tests, all passing) use fixture repos with
realistic config files (prettier, webpack production mode, a release workflow with
lint→build→bundle→publish steps) and assert: correct detection, every hit citing a
real file, correct prevalence math across a 2-repo fixture, correct step-order
extraction, and JSON round-trip. Smoke-tested against this repo itself (correctly
all-zero, since it has no CI/build config yet).

One commit: mining module + tests + ACTION_PLAN/PROGRESS updates.

**Not yet run against real data** — needs the sampling frame frozen (repo
count/snapshot date, Decision #8) and an actual repo list to scan; that's the next
step toward unblocking Phase 3's sample-assembly task.

---

## 2026-09-17 (cont'd 3) — Anticipatory-arm scheme selection (Decision #6)

Wrote `docs/06-scheme-selection.md`. Searched for public repos on every code-
watermark candidate from the literature sheet rather than assuming availability
from the paper text alone:

- **Confirmed public, official repos**: STONE (`inistory/STONE-watermarking`),
  SrcMarker (`YBRua/SrcMarker`), CodeIP (`CGCL-codes/naturalcc`), CodeMark
  (`v587su/CodeMark`).
- **No public repo found** despite direct search: CLASP (arXiv:2510.11251, revised
  as recently as April 2026), PromptMark, ACW. All three rejected on availability
  grounds, not merit — documented per scheme in the sheet.

**Selected 4**: STONE (rule-based/post-hoc), SrcMarker (neural/post-hoc), CodeIP
(statistical/generation-time) — three genuinely different embedding mechanisms, so
the study can separate "survival depends on the operation" from "survival depends
on the mechanism" — plus CodeMark, which is a *dataset* watermark, not a code
watermark, chosen specifically to cover the anticipatory arm's second carrier type
per the brief's Figure 1 rather than narrowing to code-watermarks-only.

Flagged as a default like #7/#8, not a final decision. New open item added (#11):
pin exact commit/version + generation settings for all four before the pilot run —
not yet started.

One commit: scheme-selection doc + DECISIONS/ACTION_PLAN updates.

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
