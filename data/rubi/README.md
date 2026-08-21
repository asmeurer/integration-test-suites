# Suite: `rubi`

Chapters 1-8 of the Rubi test suite: the integration problems Albert Rich
uses to test [Rubi](https://rulebasedintegration.org), each with the
antiderivative Rubi considers optimal and the number of steps it takes.
This is the bulk of the corpus and the broadest coverage of elementary
integrands in existence.

## What it contains

64,740 indefinite integration problems in 186 JSONL files, one directory
per Rubi chapter, subdivided the way Rubi organizes its rules:

| Chapter | Cases |
| --- | ---: |
| `t_1_algebraic_functions` | 25,327 |
| `t_2_exponentials` | 963 |
| `t_3_logarithms` | 3,036 |
| `t_4_trig_functions` | 22,221 |
| `t_5_inverse_trig_functions` | 3,026 |
| `t_6_hyperbolic_functions` | 5,053 |
| `t_7_inverse_hyperbolic_functions` | 4,504 |
| `t_8_special_functions` | 610 |

Most problems are parametric (symbolic constants `a`, `b`, `m`, `n`, ...
besides the integration variable). Every case carries Rubi's `num_steps`;
most carry the expected antiderivative in `integral` — the exceptions are
the answers dropped at import time (Rubi's own no-result markers, and
expressions that do not survive a string round trip), recorded in
`IMPORT_REPORT.json`. A case's `source` is the upstream module path, so
`--source-prefix` can select a single chapter or section.

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
