# Collision Search

Checked: 2026-09-17.

## Question
Has anyone already measured, on real repository history, whether release-assembly
operations (squash, rebase, cherry-pick, rebuild, republish) destroy or manufacture
provenance carriers (commit trailers, signatures, build attestations/SBOMs) at the
level of a shipped release, treating carriers jointly rather than one at a time?

## Search performed
- "commit trailer signature attestation survival squash rebase rebuild provenance loss 2026"
- "'provenance carrier' software release survival watermark trailer attestation empirical study FSE 2027"
- Follow-up check on the closest hit: "Authenticated Contradictions from Desynchronized
  Provenance and Watermarking" (arXiv:2603.02378, CVPR 2026 Workshop APAI)

## Findings
1. **No direct collision.** Nothing found measures release-level survival of software
   provenance carriers (trailers/signatures/attestations) across ordinary git/build
   operations as a joint, non-adversarial phenomenon.
2. **Closest adjacent work is a different domain.** arXiv:2603.02378 formalizes the
   "Integrity Clash" — a C2PA manifest and a pixel watermark disagreeing on authorship
   of an *image*, both passing verification in isolation. Same shape of argument
   (independent provenance layers can desynchronize), wrong artifact type (media, not
   code) and no release-assembly operations. Useful as a related-work citation for the
   "layers don't compose" framing, not a collision.
3. **Adjacent, not overlapping: commit-provenance mining.** arXiv:2607.02774 ("Was It
   Never Collected, or Rewritten Away?") separates ingestion gaps from upstream history
   edits in a mining dataset (World of Code). It's about *measurement artifacts in
   mining tools*, not about whether the underlying carriers survive release assembly.
   Cite as related work; does not close the gap.
4. **Live but narrower engineering activity.** Several 2026 GitHub issues (harness/CI
   projects) show teams independently trying to make provenance trailers survive squash
   merges via ad hoc trailer-preservation logic. This is evidence the problem is real
   and unsolved in practice, not a competing study — no measurement, no paper, no
   composed-operation results.

## Verdict
No pivot required. Proceed with the plan as scoped in the brief.

## Recheck policy
Re-run this search before the related-work section is finalized (the brief notes the
field moves in months) and again immediately before submission.
