# CLAUDE.md

A corpus of 80,605 symbolic integration problems (Rubi, Hebisch, Blake,
independent classics, MIT Bee) with tooling to run SymPy's integrators over
it. The README covers the layout, format, and licensing; this file records
the invariants and operational knowledge that are easy to get wrong.

## Invariants

- **Every suite stays independently removable.** Each `data/<suite>/`
  directory is self-contained with its own `README.md`, so any suite can
  be dropped with one `git rm -r`. Never create cross-suite dependencies,
  never merge suites.
- **Deduplication is non-destructive.** `dedupe.py` writes
  `data/DUPLICATES.json` and never rewrites a suite. The same integrand in
  two suites carries different expected answers and step counts, both worth
  keeping.
- **Corpus changes go through `importers/`, never by hand-editing the
  JSONL.** The importers are the reproducible path from each upstream source
  to `data/`, and their import reports record what was dropped. A data fix
  belongs in the importer (rerun it), not in the data files.
- **Licensing is per-suite and delicate.** Three suites (`hebisch`, `blake`,
  `mit_bee`) are Nasser Abbasi's transcriptions with no stated license,
  included pending his agreement — that contact is the maintainer's to make,
  never an automated one. Read
  `licenses/README.md` before adding or removing any data.

## Running the corpus

The canonical benchmark invocation (measuring a SymPy development branch):

```console
python -m integration_test_suites.run --engine risch --sympy-path ../sympy \
    --suite hebisch --limit 2000 --timeout 5 --check --isolate \
    --results results.jsonl
```

- **Always pass `--isolate`.** The in-process timeout uses SIGALRM, which
  only lands between Python bytecodes; a case that disappears into C-level
  work (gmpy2, mpmath) ignores it entirely and hangs the whole run.
  `--isolate` forks a child per case and kills it on overrun.
- **Always pass `--check` when counting solves.** An engine can crash its
  way into a wrong answer; counting `SOLVED` without verification has hidden
  exactly that. The oracle (`verify.py`) tries a symbolic proof first
  (`cancel(diff(F) - f)`, then `fu()` for trig), falling back to numerical
  sampling that straddles every radicand's real roots — branch errors are
  invisible if you only sample where radicands are positive.
- **Compare runs by joining result files on `(suite, index)`**, not by
  comparing aggregate counts.
- Use `--filter` to keep an engine off problems it cannot attempt (e.g.
  symbolic exponents like `(a + b*x)**m` for Risch-style methods).

## Known corpus defects and flaky cases

- The Mathematica heads Bonazzi's generated modules leave untranslated
  (`PolyLog`, `Gamma`, `EllipticPi`, ...) are mapped to sympy equivalents by
  `translate_heads` in `importers/from_rubi_modules.py`; answers containing
  Rubi's no-result markers (`Unintegrable`, `CannotIntegrate`, unevaluated
  `Int`) are dropped to "no expected answer". The only undefined functions
  intentionally left in the corpus are the arbitrary `F`/`F0` some problems
  integrate against, and one `PolyGamma` of negative order (Mathematica's
  generalized polygamma, no sympy equivalent). Note that dropping
  `Unintegrable` answers discards Rubi's claim that the integral is
  non-elementary; a claims-NE field would be a separate feature.
- `hebisch[1692]` is **hash-seed-dependent**: some `PYTHONHASHSEED` values
  take >30 s, others <1 s, on any SymPy version. Treat it as a flaky
  timeout, never a regression.
- `hebisch[274]` fails on an E-vs-`exp(1/2)` constant-canonicalization bug
  in SymPy's Risch code, not a corpus problem.
- Known import-time drops (recorded in the import reports): 2,756 Rubi
  expected answers that are no-result markers, 964 that do not survive a
  `str()`/`sympify` round trip, 13 Rubi modules that fail to import
  upstream, 701 Blake answers in Maple `RootSum` lambda syntax. The only
  excluded integrands are the two Welz problems whose upstream answer is
  the literal `0` placeholder (`SKIP_CASES` in `from_rubi_modules.py`);
  everything else keeps its integrand.
- 17 Hebisch expected answers are corrected on import (`LOG_EXP_UNWRAP` /
  `ANSWER_OVERRIDES` in `from_nasser_sympy.py`): the transcription's
  `log(exp(u)**k)` towers are branch-wrong as antiderivatives, and 8737
  had a conjugate-flipped constant. The audit proves all 17 corrected
  forms. Skipped indexes stay stable — `index` is the upstream
  enumeration position, so joins on `(suite, index)` survive
  regeneration.
- `validate.py` is the answer audit: it proves the corpus' own expected
  antiderivatives (and, for definite cases, quadrature-checks the expected
  values), so a translation bug shows up as unproven or mismatched answers
  rather than silently wrong test data. Run it after touching an importer.

## The `mit_bee_official` suite and definite integrals

- Definite cases carry `lower`/`upper`/`value`; engines need a
  `call_definite` entry point (`integrate`, `meijerint`) or the runner
  skips the case. **Never add an F(b)-F(a) fallback** — an antiderivative
  with a branch jump inside the interval is a correct antiderivative and a
  wrong definite value; keeping the two measurements separate is
  deliberate.
- The suite is Claude's transcription of MIT's PDFs, embedded in
  `importers/mit_bee_official.py`. Printed answers the audit *proves* wrong
  (four so far, all verified by quadrature of the printed integrand) are
  corrected via `ANSWER_OVERRIDES` in that importer — the printed text
  stays in `PROBLEMS`, the correction is what's emitted. Add to the table
  only with quadrature-level proof; never edit a `PROBLEMS` tuple to "fix"
  an answer.
- A printed real odd root over an interval containing negatives is
  transcribed as `real_root(x, 3)`, not `x**(1/3)` (sympy's principal
  branch is complex there and the official answers assume the real root).
- Expect a residue of ~110 `unproven` cases in the audit: competition
  antiderivatives valid only on a subdomain (`2*sqrt(sin(x))` for
  `sqrt(csc(x) - sin(x))`), `log(Abs(...))` forms, and definite integrands
  quadrature cannot certify (dense `floor` jumps, infinite `Sum`s,
  oscillatory kernels). These were triaged one by one in Aug 2026; unproven
  there does not mean untrustworthy.
- The definite quadrature checker (`_quad_matches`) only issues a verdict
  when two different node layouts agree — a single tanh-sinh run
  confidently integrates a far-off Gaussian bump to 0 (its error estimate
  lies), and `exp`-argument critical points are added as split points for
  exactly that reason.

## Development

- Install: `pip install -e .[test]`; tests: `pytest` (they live in
  `tests/`).
- The `rubi` engine needs `pip install rubi-integrate`; `risch_algebraic`
  needs a SymPy checkout with the `risch-algebraic` branch (pass via
  `--sympy-path`).
- This repo is destined for the SymPy organization, whose AI-code policy
  requires the disclosure section in the README — keep it accurate when
  tooling changes.
