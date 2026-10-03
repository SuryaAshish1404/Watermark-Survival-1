# Substantially-Human Module Rule (fixed in advance)

Used only for the spurious-gain experiment (docs/01-outcome-definitions.md,
"Spuriously Gained"). Fixed before any module is scored, so the rule cannot be
tuned after seeing results.

## Primary rule
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
rather than inventing a new heuristic — this is a "port," not a new instrument.
