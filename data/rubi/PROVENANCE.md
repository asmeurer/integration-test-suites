# Suite: `rubi`

Chapters 1-8 of the Rubi test suite: the integration problems Albert Rich
uses to test [Rubi](https://rulebasedintegration.org), each with the
antiderivative Rubi considers optimal and the number of steps it takes.

## Where these came from

Upstream: [RuleBasedIntegration/MathematicaSyntaxTestSuite](https://github.com/RuleBasedIntegration/MathematicaSyntaxTestSuite),
in Mathematica syntax.

Translated to SymPy by Francesco Bonazzi in
[Upabjojr/rubi-integration-test-suite](https://github.com/Upabjojr/rubi-integration-test-suite),
which stores the cases as generated Python modules. This directory was
produced from those modules by `importers/from_rubi_modules.py`; see
`IMPORT_REPORT.json` for the modules that failed to import and the cases
whose expressions did not survive the string round trip.

## License

MIT, twice over: Rubi's own test suite is MIT (Copyright (c) 2018
Rule-based Integration), and Francesco Bonazzi's translation is MIT
(Copyright (c) 2026 Francesco Bonazzi). Both texts are in
`../../licenses/`.
