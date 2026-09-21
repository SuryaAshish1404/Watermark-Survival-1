# STONE Mutation-Survival Pilot

A small, concrete pilot: pick one anticipatory-arm watermark scheme, embed it in
code placed inside a real repository, run it through a battery of real mutations,
and check whether the detector still fires after each one. Scoped down from the
full anticipatory arm (Phase 4 in ACTION_PLAN.md) — this is a single-scheme,
single-repo proof of the measurement method, not the pilot run Decision #11 still
calls for at full scale.

## Scheme: STONE

Chosen over the other 3 selected schemes (docs/06) for this pilot specifically
because:
- **Detection needs no model, only a tokenizer.** `detect_watermark` re-tokenizes
  the candidate text and computes a z-score from the green/red list structure —
  no GPU, no re-running a generation. SrcMarker needs its trained BiGRU
  encoder/decoder checkpoint (not available to us); CodeIP's grammar-guided
  logit manipulation and CodeMark's dataset-level detection are both heavier to
  stand up for a single-function pilot.
- **Embedding is generation-time**, via a `LogitsProcessor` that biases green-list
  tokens during decoding, restricted to non-syntax tokens (STONE's actual
  contribution) — this does mean we need a real causal LM to generate the
  watermarked function in the first place, unlike a purely post-hoc scheme.

Model used for generation: `bigcode/tiny_starcoder_py` (164M params, Python-only,
CPU-feasible) — a real, small, code-pretrained model, not a stand-in. Config:
`gamma=0.5, delta=4.0, hash_key=15485863, prefix_length=1, z_threshold=4.0,
language="python", skipping_rule="all_pl", watermark_on_pl="False"` (watermark
non-syntax tokens only, matching STONE's stated design; delta raised above the
paper's typical 0.5-2.0 range to compensate for tiny_starcoder_py's weaker,
noisier logits at 164M params — noted as a pilot-only deviation, not a
methodology recommendation for the full run).

## Repo: lutris/lutris

Reused from `data/sampling/candidates.md` — already hand-verified (agent trailers,
tagged releases, real Python project with real `ruff`/`black`/`.editorconfig`
config). Using an already-vetted repo avoids re-doing verification work and
means the mutation config (ruff.toml, pyproject.toml black settings) is real
project configuration, not invented.

## Procedure

1. Generate a watermarked Python function from a prompt shaped like real Lutris
   code (a docstring + signature in Lutris's style), using STONE + tiny_starcoder_py.
2. Sanity check: run `detect_watermark` on the raw generation. Must show
   `is_watermarked: True` before any mutation — otherwise the pilot proves nothing.
3. Write the generated function into a real Lutris checkout as a new module.
4. Apply mutations, individually and then composed, each producing a new version
   of the file. Chosen from the operation catalogue (docs/ACTION_PLAN, Figure 1)
   restricted to what's mechanically applicable to a single Python file:
   - **format** — `ruff format`, using Lutris's actual `ruff.toml` (checked CI:
     `.github/workflows/static.yml` runs `ruff format . --check`, not black —
     use the project's real formatter, not an assumed default)
   - **lint_autofix** — `ruff check --fix`, using Lutris's actual `ruff.toml`
   - **rename** — deterministic AST-based local-variable renaming (proxy for a
     human/agent refactor pass; also the exact transform class the base paper,
     Suresh et al., studies)
   - **minify** — `python-minifier` (strips comments/docstrings/blank lines,
     shortens names) — closest real-world equivalent to JS minification for a
     Python codebase
   - **ast_roundtrip** — parse then `ast.unparse`, a mechanical rewrite that
     normalizes formatting without any tool-specific intent (proxy for a
     transpile-class rewrite)
   - **composed** — format → lint_autofix → rename → minify, applied in sequence,
     matching the brief's requirement to test composed operations, not only
     single ones
5. Run `detect_watermark` after every step. Record z-score and boolean result.
6. Classify each result against `scripts/recovery/outcomes.py`'s taxonomy:
   retained (still above threshold), silently lost (below threshold, no error),
   or — if a mutation breaks the code's parseability — a note that this outcome
   sits outside the three-way taxonomy entirely (a build failure, not a
   provenance-loss event, though in a real pipeline it would still mean the
   watermark question never gets asked).

## What this pilot does and doesn't establish

**Does**: gives a concrete, reproducible answer for one scheme, one repo, one
generated function — proof that the measurement method in docs/01-03 works
end-to-end on a real watermark, real mutation tools, and a real host repo.

**Doesn't**: this is N=1 function, one scheme, one model backend — not
statistically representative of anything, and not a substitute for the full
Phase 4 anticipatory-arm run (which needs multiple repeated generations per
Decision #11's variance-reporting requirement). Treat results as a methodology
proof, not a headline number.
