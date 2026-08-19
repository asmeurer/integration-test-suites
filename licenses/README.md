# Licensing of the corpus

The tooling in this repository is MIT (see the top-level `LICENSE`). The
problem sets under `data/` come from several places and are covered
separately, per suite. Each suite directory has its own `PROVENANCE.md`
with the full story; this is the summary.

| Suite | Problems | Origin | License |
| --- | ---: | --- | --- |
| `rubi` | ~64,000 | Rubi test suite, via Francesco Bonazzi's SymPy translation | MIT (`rubi-test-suite-MIT.txt`, `rubi-and-translation-MIT.txt`) |
| `independent` | ~1,800 | The 12 independent sets in Rubi's chapter 0, same route | MIT, as above |
| `blake` | 3,154 | Sam Blake's algebraic problems, via Nasser Abbasi's translation | Problems MIT (`blake-MIT.txt`); **translation unlicensed** |
| `hebisch` | 10,335 | Waldek Hebisch's random exp-log problems, via Nasser Abbasi | **Unlicensed** |
| `mit_bee` | 54 | MIT Integration Bee, via Nasser Abbasi's post | **Unlicensed** |

## What is and is not settled

Everything reached through Francesco Bonazzi's translation is cleanly
MIT at both layers, and that is the large majority of the corpus.

Three suites are transcriptions or translations by Nasser Abbasi, whose
site states no license. They are included here pending his agreement; he
is [@nasser1](https://github.com/nasser1) on GitHub and posts the `mit_bee`
problems in a SymPy discussion himself. If he asks for any of them to be
removed, `git rm -r` the suite directory: nothing else in the repository
depends on a suite's presence, and the tooling discovers whatever suites
exist.

Two of the three have replacement paths that need nobody's permission:

- `blake` can be re-translated from the MIT `BlakeProblems.m` upstream
  with the same generator that produced the `rubi` suite.
- `hebisch` can be regenerated from scratch — the construction is fully
  documented in `data/hebisch/PROVENANCE.md`, and the original file is
  gone from the web anyway.

## Problems taken from books and papers

Parts of the `independent` suite transcribe exercises from works still in
copyright, notably Apostol (1967), Stewart (1987) and Timofeev (1948).
Individual integrals are mathematical facts, which copyright does not
reach; only the selection and arrangement of a compilation could attach,
and these sets are reorganized rather than reproduced. Rubi has
distributed them under MIT since 2018. This repository relies on that
grant rather than re-transcribing from the originals.
