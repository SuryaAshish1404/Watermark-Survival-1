# Sampling Frame (draft — needs a Decision, see DECISIONS.md)

## Population (proposed)
Public GitHub repositories that:
- Have ≥ 1 merged PR with an agent/co-authorship trailer in the last 12 months
  (ensures the measured arm has carriers to observe at all), AND
- Have ≥ 1 tagged release OR published package/build artifact in the same window
  (ensures a release-level unit of recovery exists), AND
- Are not forks (avoids double-counting history shared with an upstream).

## Strategy (proposed)
Stratified by primary language and by release-assembly style (squash-only vs.
merge-commit vs. rebase-merge branch protection setting, read from repo config) so
the operation catalogue's prevalence ranking is not dominated by one workflow style.
Target 10-20 repositories per the brief's Phase 2 sketch, drawn from within strata
rather than by raw popularity, to avoid the sample being all mega-projects with
atypical release engineering.

## Exclusion criteria (proposed)
- Repos that rewrite history in ways that make pre-rewrite refs categorically
  unrecoverable (e.g., squash-and-delete branch with no PR API access) are excluded
  *from the before-state-dependent measurements* but may still contribute to the
  operation-catalogue mining (presence of squash in config is still evidence of
  practice even if we can't recover the before-state for it).
- Archived/inactive repos (no commits in 6 months) excluded — the brief frames this
  as "active" repositories.

## What's still open
- Exact repo count and the popularity/activity thresholds that define "active."
- Whether to sample from a fixed list (e.g., GH Archive / GHTorrent-style corpus) or
  live API querying — affects reproducibility (a live query re-run later returns a
  different sample).
- Release definition for repos that ship via package registries (npm/PyPI) rather
  than GitHub Releases — needs a decision on which is authoritative when both exist.

This file stays in `docs/` as the *proposed* frame per the brief's Decision #3
("Propose the sampling frame... this one changes what the paper can claim about
practice, so it is not a purely technical choice"). Convert to
`data/sampling/frame.md` (frozen) only after the decision is made.
