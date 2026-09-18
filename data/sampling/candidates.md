# Sampling Candidates (starter set — not the frozen frame)

Per Decision #8, the real frame should be drawn from a fixed-corpus snapshot. The
**AIDev dataset** (Hugging Face: `hao-li/AIDev`, arXiv:2602.09185, the same data
underlying the census paper in docs/05) is the right source: 2,807 repos with
agent-authored PR data already extracted and validated, joinable against GitHub
Release presence to apply the population criteria in docs/04 systematically. This
session doesn't have Hugging Face dataset access, so this file is a **hand-verified
starter set** — real repos, individually confirmed against the criteria, used to
prove the pipeline works end-to-end and to unblock a first real measurement while
the full frame gets built from AIDev.

## Verified

### lutris/lutris
- **Agent trailer**: confirmed live. `scripts/recovery/trailer.py` against a real
  clone found 193 commits with `Co-Authored-By: Claude Opus 4.6
  <noreply@anthropic.com>` in reachable history (checked 2026-09-18).
- **GitHub Release**: confirmed. 88 version tags (`v0.5.7` ... current), consistent
  with an active tagged-release practice.
- **Not a fork**: confirmed (primary Lutris repo).
- **Operation catalogue signals found** (real scan, not hypothetical):
  format (`.editorconfig`, `publish-ppa.yml`, `static.yml`), lint_autofix
  (`ruff.toml`, `pyproject.toml`), rebuild (4 workflow files + `Makefile`),
  repackage (`publish-lutris-ppa.yml`, `publish-ppa.yml`), republish
  (`publish-ppa.yml` via `dput` — a Debian-upload publish path the detector
  didn't originally cover; added after finding it here, see PROGRESS.md).
- No squash/rebase/cherry-pick/fork-sync, transpile/bundle/minify signals found —
  consistent with a Python/GTK desktop app with no JS build pipeline and no
  detected repo-settings file governing merge strategy (branch protection API
  query would be needed to check squash-only policy directly; not available in
  this session).

## Not yet checked
Nothing else has been individually verified yet. Do not treat this file as
sufficient for N=15 — it's 1 confirmed repo. Next: either pull the AIDev dataset
directly (best) or repeat this same clone-and-check procedure for more candidates
by hand (slower, same verification bar).
