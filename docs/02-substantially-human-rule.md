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

## Open decision
Exact task templates for step 3 are not yet fixed — this determines how "small" the
edit is and therefore how defensible "still substantially human" remains post-edit.
Needs to be pinned before Phase 5 runs (see docs/DECISIONS.md).
