# Sampling Frame

Decided 2026-09-17: fixed-corpus sampling, GitHub Releases as the authoritative
release unit. Repo count / activity threshold remain open — see DECISIONS.md.

## Population
Public GitHub repositories that:
- Have ≥ 1 merged PR with an agent/co-authorship trailer in the last 12 months
  (ensures the measured arm has carriers to observe at all), AND
- Have ≥ 1 tagged **GitHub Release** in the same window — this is the authoritative
  release unit (decided over package-registry publish events, since the goal is a
  reproducible, git-native unit of recovery; repos that ship only via npm/PyPI with
  no GitHub Release are excluded, logged with reason code `no-github-release`), AND
- Are not forks (avoids double-counting history shared with an upstream).

## Sampling method (decided)
Draw from a **fixed corpus snapshot** (GH Archive / GHTorrent-style dataset) taken at
a stated date, not live API querying. This is what makes the sample reproducible: a
reader re-running the pipeline against the same snapshot gets the same repo list,
independent of what has happened on GitHub since. The snapshot date and query become
part of the deposited artifact per the brief's "Data and artifact standard" row.

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
  (10-20 repos per the brief's Phase 2 sketch is a target range, not yet a fixed N.)
- Which fixed-corpus snapshot/date to use as the source dataset.

Once repo count and snapshot date are picked, this file freezes into
`data/sampling/frame.md` and the exclusion log starts populating
`data/sampling/exclusions.csv`.
