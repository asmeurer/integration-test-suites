# Suite: `blake`

3,154 algebraic integration problems — pseudo-elliptic, hyperelliptic and
nested-radical integrands — from Sam Blake's work on `IntegrateAlgebraic`.
This is the natural test set for the algebraic case of the
Risch-Trager-Bronstein algorithm.

## Where these came from

Upstream: [stblake/algebraic_integration](https://github.com/stblake/algebraic_integration)
(`BlakeProblems.m`, `IntegrateAlgebraicTests.m`), in Mathematica syntax,
supporting the paper *A Simple Method for Computing Some Pseudo-Elliptic
Integrals in Terms of Elementary Functions* ([arXiv:2004.04910](https://arxiv.org/abs/2004.04910)).

The copy here is the SymPy-syntax translation from the Summer 2021 edition
of Nasser Abbasi's
[Computer Algebra Independent Integration Tests](https://www.12000.org/my_notes/CAS_integration_tests/),
imported by `importers/from_nasser_sympy.py`.

701 of the expected antiderivatives use Maple's
`RootSum(_Z1 -> ..., _Z1 -> ...)` lambda syntax, which is not Python and
does not sympify. Those answers were dropped; their problems are kept
without an expected antiderivative.

## License

The problems are MIT upstream (Copyright (c) 2020 stblake). **The
translation used here is Nasser Abbasi's and carries no stated license.**

This suite is therefore included pending Nasser's agreement, like
`hebisch`. Unlike `hebisch`, it has a clean replacement path that does not
depend on anyone's permission: re-translate `BlakeProblems.m` from the
MIT upstream with the same generator that produced the `rubi` suite.
