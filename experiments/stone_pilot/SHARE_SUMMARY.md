# Do the Marks Survive the Pipeline? — Summary So Far

**Project:** FSE 2027 submission, "Do the Marks Survive the Pipeline?"
**Status:** Early-stage empirical results, methodology stable, scaling up next.

## The question

AI code-watermarking schemes embed a statistical signal into generated code that
lets you later prove "this was AI-written." All published evaluations of these
schemes check the watermark right after generation. Real code doesn't stay that
way — it gets renamed, reformatted, linted, merged, and packaged before anyone
looks at it again, and none of that is an attack, just normal engineering. We
test whether the watermark survives that ordinary pipeline.

## What we tested

- **9 published watermarking schemes** (STONE, KGW, SWEET, EWD, Unigram, Unbiased,
  DIP, SynthID, Permute-and-Flip), spanning several different design families.
- **Generation model:** `bigcode/tiny_starcoder_py`, 164M parameters, CPU-only —
  small by necessity so far (see "What's next").
- **22 individual operations** (rename, reformat, add type hints, extract a
  function, squash-merge, build a release package, etc.), each applied alone to
  freshly generated code.
- **A 9-step realistic pipeline** (AI adds type hints → adds a docstring →
  reviewer patches → reviewer renames → reviewer comments → CI formats → CI
  lints → squash-merge → release build), applied in sequence to the *same* code,
  checking the watermark after **every** step, not just at the end.

## What we found

1. **Only 2 of 9 schemes reliably produce a detectable watermark at all** on
   this small model — STONE and KGW. The other 7 mostly never embed a strong
   enough signal to test in the first place. This looks like a limitation of
   the small model, not of those schemes' designs.

2. **The main finding: it's *how* an edit is made, not *what* the edit is, that
   destroys the watermark.** Many of our editing operations were implemented by
   re-parsing and reprinting the entire file (a common approach for AST-based
   code tools). When we instead applied the identical edit as a small, in-place
   text change — same content, same random choices, provably the same resulting
   program — most of the "damage" disappeared:
   - KGW: watermark survived the full 9-step pipeline in only **4%** of runs
     when every step rewrote the whole file, vs. **65%** when the same edits
     were applied in place.
   - STONE: **84%** vs. **92%** — much less sensitive to this than KGW.

   So whole-file-rewriting tools are a much bigger threat to watermark survival
   than any specific kind of edit, and that sensitivity itself varies sharply
   by scheme.

3. **Watermark strength at generation time is the single best predictor of
   survival.** Longer/more confident generations kept their watermark far more
   reliably than short, borderline ones, regardless of scheme.

4. **We caught and fixed two of our own methodology bugs** along the way (a
   randomness seed that wasn't actually stable across runs, and a case where
   what looked like 25 independent test samples were mostly duplicates). Worth
   noting because it changed our numbers meaningfully and is an easy trap in
   this kind of study.

## What's next

The biggest lever right now is model size: 7 of 9 schemes can't even be
evaluated because the current 164M-parameter model doesn't generate code with
enough freedom for the watermark to take hold. With a 6 GB VRAM laptop now
available, the plan is:

- Switch generation to a larger model that fits in 6 GB VRAM — likely
  **StarCoder2-3B** or **DeepSeek-Coder-1.3B/6.7B-instruct** (quantized if
  needed to fit).
- Re-run the baseline-embedding check across all 9 schemes on the new model.
- Extend the reserialization-vs-in-place-edit finding to whichever schemes now
  produce a usable signal.
- Re-run the 9-step pipeline and the 22-operation battery at scale on the new
  model.

## Where the detail lives

- `report.md` — plain-language write-up.
- `BENCHMARK.md` — full methods + results, citable as-is.
- `RESULTS.md` — full session-by-session history, including corrections.
- `paper/main.tex` — LaTeX draft (currently a scratch outline; to be filled in
  once the larger-model run is done).
