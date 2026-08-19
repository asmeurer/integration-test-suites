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

80,063 problems, most of them with a known antiderivative.

| Suite | Cases | What it is |
| --- | ---: | --- |
| [`rubi`](data/rubi/PROVENANCE.md) | 64,740 | Albert Rich's Rubi test suite, chapters 1-8 |
| [`hebisch`](data/hebisch/PROVENANCE.md) | 10,335 | Random exp-log integrands guaranteed to be elementary |
| [`blake`](data/blake/PROVENANCE.md) | 3,154 | Algebraic: pseudo-elliptic, hyperelliptic, nested radicals |
| [`independent`](data/independent/PROVENANCE.md) | 1,780 | 12 classic sets: Timofeev, Apostol, Moses, Bronstein, ... |
| [`mit_bee`](data/mit_bee/PROVENANCE.md) | 54 | MIT Integration Bee problems SymPy could not do |

Two of these are worth singling out, because they test things Rubi does
not. The `hebisch` suite is built so that every integrand is the expanded
derivative of a known expression, which makes it a direct measure of a
Risch implementation on exponential-logarithmic towers — FriCAS solves
99.92% of it. The `blake` suite is the corresponding test for the
algebraic case of Risch-Trager-Bronstein.

Each suite directory carries a `PROVENANCE.md` saying where its problems
came from and under what license they are redistributed here. Read
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
the suite gives no answer, or gave one that does not parse.

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
risch              sympy.integrals.risch.risch_integrate         ok
risch_algebraic    risch_integrate(algebraic=True)               UNAVAILABLE: ...
rubi               rubi-integrate (Rubi rule set on sympy)       UNAVAILABLE: ...
```

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
expected answer cannot produce a false `WRONG`.

`rubi` is [Francesco Bonazzi's `rubi-integrate`](https://github.com/Upabjojr/rubi-integrate),
the Rubi rule set running on SymPy; `pip install rubi-integrate` to enable it.

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

| Importer | Produces | Needs |
| --- | --- | --- |
| `from_rubi_modules.py` | `rubi`, `independent` | a checkout of [rubi-integration-test-suite](https://github.com/Upabjojr/rubi-integration-test-suite) |
| `from_nasser_sympy.py` | `hebisch`, `blake` | the extracted `SYMPY_syntax.zip` from [12000.org](https://www.12000.org/my_notes/CAS_integration_tests/) |
| `mit_bee.py` | `mit_bee` | nothing; the problems are embedded verbatim |

`data/rubi/IMPORT_REPORT.json` and `data/NASSER_IMPORT_REPORT.json` record
the per-run counts. The Rubi import currently drops 968 expected
antiderivatives that do not survive a `str()`/`sympify` round trip, and
skips 13 generated modules that fail to import upstream; no integrand is
dropped.

## Licensing, in short

The tooling is MIT. Most of the corpus — everything reached through
Francesco Bonazzi's translation — is MIT at both layers.

Three suites (`hebisch`, `blake`, `mit_bee`) are transcriptions by Nasser
Abbasi, whose site states no license, and are included here pending his
agreement. If he asks for any of them to be removed, `git rm -r` that
suite directory; nothing else depends on it. `blake` and `hebisch` both
have replacement paths that need nobody's permission, described in their
provenance files.

See [`licenses/README.md`](licenses/README.md) for the details, including
the position on problems transcribed from books still in copyright.

## AI generation disclosure

The tooling, importers, tests and documentation in this repository were
written with Claude Code (Claude Opus 5). The problem data is not
AI-generated: it is mechanically converted from the upstream sources named
in each suite's `PROVENANCE.md`, and `verify.py` is the numerical oracle
developed for SymPy's Risch work. This note is here because the repository
is intended for the SymPy organization, whose
[policy on AI-generated code](https://docs.sympy.org/dev/contributing/ai-generated-code-policy.html)
requires it.

## Acknowledgements

Albert Rich for Rubi and its test suite; Francesco Bonazzi for the SymPy
translation and `rubi-integrate`; Nasser Abbasi for the Computer Algebra
Independent Integration Tests, which is where most of this was found;
Waldek Hebisch and Sam Blake for their problem sets.
