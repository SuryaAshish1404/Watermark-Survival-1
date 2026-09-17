# Substantially-Human Module Rule (fixed in advance)

Used only for the spurious-gain experiment (docs/01-outcome-definitions.md,
"Spuriously Gained"). Fixed before any module is scored, per the brief's explicit
requirement that this rule not be tuned after seeing results.

## Candidate primary rule
A module (file or logically cohesive commit-sized unit) is **substantially human**
if, across its full authored history prior to the experiment:
- ≥ **90%** of surviving lines (by `git blame` line attribution at the pre-experiment
  HEAD) trace to commits with no agent trailer, no agent-pattern commit message, and
  no CI/bot author identity, AND
- The module has **zero** prior commits carrying an agent/co-authorship trailer.

Rationale for 90%: high enough that a module which received one small AI-assisted
edit in its distant past still qualifies (avoids penalizing normal incremental
history), low enough to exclude anything with a substantial AI-authored block.

## Sensitivity range (must be reported alongside the headline number, not instead of it)
Re-run the classification and the resulting spurious-gain rate at:
- 75%, 80%, 85%, 90% (primary), 95%, 99%

Report the spurious-gain rate as a curve over this range, not a single point. A rate
that collapses to ~0 only at 99% and is high at 90% is itself a finding.

## What counts as an "agent-pattern commit message / bot identity"
Reuse the validated labelling procedure from the census paper (arXiv:2606.24429)
rather than inventing a new heuristic — this is a "port," not a new instrument. Any
place this rule departs from the census procedure must be stated explicitly in the
paper (per the brief's "Why should we believe it?" section).

## Procedure for the experiment
1. Classify modules as substantially-human at the chosen threshold (report all
   thresholds in the sensitivity range).
2. Sample N substantially-human modules per repository (N and sampling method set
   once the pilot in docs/04-sampling-frame.md is run).
3. Pass each to an assistant for a small, realistic task-team-style edit (task
   templates TBD in Phase 5 build step — kept small and bounded so "substantially
   human" plausibly still holds after the edit).
4. Record whether the resulting commit and/or release carries any carrier claim
   attributing the work to a model, using the same per-carrier presence test as
   docs/01-outcome-definitions.md.
5. Spurious-gain rate = (# modules with a manufactured attribution) / (# modules
   tested), reported per threshold.

## Task templates for step 3 (proposed default, 2026-09-17)
Three bounded, realistic small-task-team-delegation templates, applied to a sampled
substantially-human module:
1. **Bug fix from a linked issue** — give the assistant an existing, unresolved issue
   referencing the module and ask for a minimal fix. Bounded by the issue's scope.
2. **Add/extend a unit test** — ask for one test covering an existing, uncovered
   branch in the module. Bounded to test files/functions only, no production-code edit.
3. **Docstring/comment pass** — ask for accurate docstrings on undocumented public
   functions in the module. Bounded to comments/docstrings, zero logic change.

Each template caps the diff at **≤ 20 changed lines** — chosen so the post-edit
module still plausibly clears the 90% (or even 95%) substantially-human line-blame
threshold from the rule above; a module that fails to still qualify post-edit under
its own rule is excluded from the spurious-gain denominator and logged, not scored.
Run all three templates per sampled module where applicable (a module with no open
issues skips template 1) so the spurious-gain rate isn't an artifact of task choice.

Flagged as a **default, not a final decision** — revisit if the 20-line cap turns
out to exclude too many candidate modules during the Phase 5 pilot.
