# integration-test-suites

A large corpus of symbolic integration problems, in one place and one
format, with tooling to run it against SymPy's integrators.

SymPy has several integration routines and no systematic way to measure
any of them. The Rubi test suite is the one most often reached for, but
it is not the only large collection in existence, and the interesting
ones are scattered across Mathematica sources, a dead university
homepage, and a mailing list post. This repository collects them,
converts them to a single JSON Lines schema, and provides a runner that
classifies and verifies what an engine does with each problem.

**Status: alpha.** The intention is to move this to the SymPy
organization once it has settled, so that SymPy has a comprehensive
integration test suite it maintains itself.

## The corpus

80,605 problems, most of them with a known answer.

| Suite | Cases | What it is |
| --- | ---: | --- |
| [`rubi`](data/rubi/README.md) | 64,740 | Albert Rich's Rubi test suite, chapters 1-8 |
| [`hebisch`](data/hebisch/README.md) | 10,335 | Random exp-log integrands guaranteed to be elementary |
| [`blake`](data/blake/README.md) | 3,154 | Algebraic: pseudo-elliptic, hyperelliptic, nested radicals |
| [`independent`](data/independent/README.md) | 1,778 | 12 classic sets: Timofeev, Apostol, Moses, Bronstein, ... |
| [`mit_bee_official`](data/mit_bee_official/README.md) | 544 | Every posted MIT Integration Bee problem, with official answers |
| [`mit_bee`](data/mit_bee/README.md) | 54 | MIT Integration Bee problems SymPy could not do |

`mit_bee_official` is the corpus' definite-integral section: 262 of its
cases are definite integrals — many only meaningful as such (floor
functions, infinite products, symmetric-interval tricks) — which is what
exercises SymPy's definite machinery (`meijerint`) rather than the
antiderivative engines.

Two of these are worth singling out, because they test things Rubi does
not. The `hebisch` suite is built so that every integrand is the expanded
derivative of a known expression, which makes it a direct measure of a
Risch implementation on exponential-logarithmic towers — FriCAS solves
99.92% of it. The `blake` suite is the corresponding test for the
algebraic case of Risch-Trager-Bronstein.

Each suite directory carries a `README.md` describing what the suite
contains, where its problems came from and under what license they are
redistributed here. Read
[`licenses/README.md`](licenses/README.md) before adding or removing
anything.

### Format

One JSON object per line, in `data/<suite>/**/*.jsonl`:

```json
{"index": 0, "integrand": "3/(5 - 4*cos(x))", "integral": "x + 2*atan(sin(x)/(2 - cos(x)))",
 "num_steps": 2, "source": "0 Independent test suites/Jeffrey Problems.m",
 "suite": "independent", "variable": "x"}
```

Expressions are stored as strings and sympified on demand, because the
corpus is loaded far more often than it is evaluated. `num_steps` is
Rubi's own step count, passed through verbatim. `integral` is absent when
the suite gives no answer, gave one that does not parse, or gave Rubi's
marker for a problem it could not do.

A *definite* case additionally carries `lower` and `upper` (sympy-syntax
bounds, e.g. `"0"`, `"pi/2"`, `"-oo"`) and `value`, the expected value of
the definite integral; `integral` keeps meaning an antiderivative and is
normally absent on such cases:

```json
{"index": 7, "integrand": "floor(2023*sin(x))", "lower": "0", "upper": "2*pi",
 "value": "-pi", "source": "MIT Integration Bee 2023 qualifier, problem 8",
 "suite": "mit_bee_official", "variable": "x"}
```

```python
from integration_test_suites import corpus

for case in corpus.load(['mit_bee']):
    print(case.f, case.x)          # sympy Expr, Symbol
```

## Running an engine over it

```console
$ python -m integration_test_suites.run --list-engines
heurisch           sympy.integrals.heurisch (None as Integral)   ok
integrate          sympy's integrate()                           ok
integrate_norisch  sympy's integrate() with risch=False          ok
manualintegrate    sympy.integrals.manualintegrate               ok
meijerint          sympy.integrals.meijerint (definite cases only) ok
risch              sympy.integrals.risch.risch_integrate         ok
risch_algebraic    risch_integrate(algebraic=True)               UNAVAILABLE: ...
rubi               rubi-integrate (Rubi rule set on sympy)       UNAVAILABLE: ...
```

Definite cases are dispatched to an engine's definite entry point
(`integrate` and `meijerint` have one); an engine without one skips them,
counted separately rather than failed. Deliberately, no engine falls back
to evaluating its antiderivative at the bounds: an antiderivative with a
branch jump inside the interval is correct as an antiderivative and wrong
as a definite value, and the two measurements must not be conflated.
`--definite-only` / `--indefinite-only` restrict a run to one kind.

```console
$ python -m integration_test_suites.run --engine integrate --suite mit_bee \
    --timeout 20 --check --results results.jsonl
```

Useful options: `--suite` (repeatable) and `--source-prefix` to select
problems, `--limit` and `--concrete-only` to cut the corpus down,
`--timeout` per case, `--results` for one JSON record per case, and
`--sympy-path` to test a SymPy checkout instead of the installed one —
which is how a development branch gets measured.

Results are classified as `SOLVED`, `partial` (an unevaluated `Integral`
remains), `CLAIMS-NE` (a `NonElementaryIntegral`), `NIE`, `timeout`, or
`error:*`.

`--check` additionally verifies each solved answer with the numerical
oracle in `integration_test_suites/verify.py`. It differentiates the
answer and compares against the integrand at sample points chosen to
straddle every radicand's real roots, because a branch error is invisible
if you only sample where the radicands are positive. Symbolic constants
are instantiated over several rounds (positive, mixed-sign, negative,
irrational, complex) and the worst verdict wins. The suite's expected
answer is used only for secondary classification, so a mistranslated
expected answer cannot produce a false `WRONG`. A solved definite case is
checked by comparing the returned constant against the suite's stated
value at two precisions, falling back to numerical quadrature of the
integrand when they disagree or no value is stated — so here too a wrong
stated value cannot convict a right answer.

`rubi` is [Francesco Bonazzi's `rubi-integrate`](https://github.com/Upabjojr/rubi-integrate),
the Rubi rule set running on SymPy; `pip install rubi-integrate` to enable it.

## Looking at a case

`show` prints the cases a selector names, which is how a line like
`WRONG hebisch[274]` in a run's output is followed up:

```console
$ python -m integration_test_suites.show hebisch 274 1692
$ python -m integration_test_suites.show hebisch:274 --format python
$ python -m integration_test_suites.show rubi 12 --source-prefix '4 Trig'
```

A selector is `suite[index]`, `suite:index`, or a suite name followed by
indexes and `LO-HI` ranges; a suite name alone streams the whole suite,
and `--grep REGEX` / `--limit N` cut that down. `--format` chooses `text`
(the stored strings), `pretty`, `latex`, `json` (the corpus record) or
`python` (a self-contained reproduction snippet). Indexes are unique
within `hebisch`, `blake` and the `mit_bee` suites but only within a
source file of `rubi` and `independent`, so a selector there can match
several cases; every match is printed under its source, and
`--source-prefix` narrows to one. The same holds for result files: the
unambiguous per-case key is `(suite, source, index)`.

`--results FILE` selects the cases recorded in a run's results file and
prints each run record (classification, check verdict, timing, answer)
under its case; `--cls` keeps only records with that classification or
check verdict, so the wrong answers of a run are

```console
$ python -m integration_test_suites.show --results results.jsonl --cls WRONG
```

and `--cls error` matches every `error:*`. Both flags repeat, and
selectors given alongside `--results` intersect with it.

## Duplicates

The suites overlap, and a problem can appear several times within one
suite. `data/DUPLICATES.json` records where:

```console
$ python -m integration_test_suites.dedupe
```

Deduplication is deliberately non-destructive — it writes a manifest and
never rewrites a suite. The same integrand in two suites usually carries
two different expected antiderivatives and two different step counts,
both worth keeping, and a suite has to stay removable by deleting its
directory. Matching is exact on the sympy expression tree after the
integration variable is renamed to a common symbol, so it collapses cases
that differ only in variable naming, and does not collapse forms that are
merely mathematically equal.

## Regenerating the corpus

The importers under `importers/` are the reproducible path from each
upstream source to `data/`, and record what they dropped:

The whole corpus regenerates with one command — no manual steps, so an
upstream update (a new Rubi release, say) is a rerun, not a re-audit:

```console
$ python importers/regenerate.py --rubi ../rubi-integration-test-suite
```

| Importer | Produces | Needs |
| --- | --- | --- |
| `from_rubi_modules.py` | `rubi`, `independent` | a checkout of [rubi-integration-test-suite](https://github.com/Upabjojr/rubi-integration-test-suite) |
| `from_nasser_sympy.py` | `hebisch`, `blake` | the extracted `SYMPY_syntax.zip` from [12000.org](https://www.12000.org/my_notes/CAS_integration_tests/) (frozen upstream; the driver downloads it) |
| `mit_bee.py` | `mit_bee` | nothing; the problems are embedded verbatim |
| `mit_bee_official.py` | `mit_bee_official` | nothing; the transcription is embedded verbatim |

The importers carry their own correction tables, and every correction is
verified at import time — a corrected antiderivative must prove
(`cancel(diff(F) - f) == 0`) and a skipped case must still match what
the skip was recorded for, so upstream data shifting under a table fails
the run loudly instead of emitting bad test data. After regenerating,
run `pytest` and the answer audit
(`python -m integration_test_suites.validate`).

`data/rubi/IMPORT_REPORT.json` and `data/NASSER_IMPORT_REPORT.json` record
the per-run counts. The Rubi import translates the Mathematica heads the
generated modules leave as undefined functions (`PolyLog`, `Gamma`,
`EllipticPi`, `ProductLog`, `SinIntegral`, ...) to their SymPy
equivalents, and drops the 2,756 expected answers that are not answers at
all but Rubi's own no-result markers (`Unintegrable`, `CannotIntegrate`).
It further drops 964 expected antiderivatives that do not survive a
`str()`/`sympify` round trip, and skips 13 generated modules that fail to
import upstream; the only excluded integrands are two Welz problems whose
upstream "answer" is the literal `0` placeholder (see `SKIP_CASES` in the
importer). The only untranslated heads remaining in the corpus are the
arbitrary functions `F` and `F0` that some problems integrate against,
and one `PolyGamma` of negative order, which has no SymPy equivalent.

The Nasser import corrects 17 Hebisch expected answers whose transcribed
`log(exp(u)**k)` towers are branch-wrong as antiderivatives (the suite's
generator counts `log(exp(u))` as `u`); the corrected forms prove exactly
against their integrands. See `LOG_EXP_UNWRAP` and `ANSWER_OVERRIDES` in
`from_nasser_sympy.py`.

## Licensing, in short

The tooling is MIT. Most of the corpus — everything reached through
Francesco Bonazzi's translation — is MIT at both layers.

Three suites (`hebisch`, `blake`, `mit_bee`) are transcriptions by Nasser
Abbasi, whose site states no license, and are included here pending his
agreement. If he asks for any of them to be removed, `git rm -r` that
suite directory; nothing else depends on it. `blake` and `hebisch` both
have replacement paths that need nobody's permission, described in their
provenance files.

`mit_bee_official` is this repository's own transcription of the problem
sets MIT publishes as course material without a stated license; it does
not depend on Nasser's transcriptions.

See [`licenses/README.md`](licenses/README.md) for the details, including
the position on problems transcribed from books still in copyright.

## AI generation disclosure

The tooling, importers, tests and documentation in this repository were
written with Claude Code (Claude Opus 5 and Claude Fable 5). The problem
data is not AI-generated: it is mechanically converted from the upstream
sources named in each suite's `README.md`, and `verify.py` is the
numerical oracle developed for SymPy's Risch work. One suite is an
exception in mechanism: `mit_bee_official` was transcribed by Claude
reading the rendered PDFs (there is no machine-readable upstream), with
the transcription embedded verbatim in its importer and audited by
`validate.py` — every expected answer is proved against its integrand
symbolically or by quadrature, so a mistranscription surfaces as an
unproven or mismatched case rather than silently wrong test data. This
note is here because the repository is intended for the SymPy
organization, whose
[policy on AI-generated code](https://docs.sympy.org/dev/contributing/ai-generated-code-policy.html)
requires it.

## Acknowledgements

Albert Rich for Rubi and its test suite; Francesco Bonazzi for the SymPy
translation and `rubi-integrate`; Nasser Abbasi for the Computer Algebra
Independent Integration Tests, which is where most of this was found;
Waldek Hebisch and Sam Blake for their problem sets.
