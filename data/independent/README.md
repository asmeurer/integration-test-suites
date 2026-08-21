# Suite: `independent`

The twelve independent problem sets distributed with the Rubi test suite
as its chapter 0. They are small but historically significant, and
several of them are the standard reference problems for symbolic
integration.

## What it contains

1,780 indefinite problems in twelve JSONL files, one per source set;
1,765 carry an expected antiderivative, and every case carries Rubi's
`num_steps` for it.

| File | Cases | Problems from |
| --- | ---: | --- |
| `apostol_problems` | 175 | Tom M. Apostol, *Calculus*, Volume I, 2nd ed. (1967) |
| `bondarenko_problems` | 34 | Vladimir Bondarenko, sci.math.symbolic posts (2010) |
| `bronstein_problems` | 14 | Manuel Bronstein, *Symbolic Integration Tutorial* (1998) |
| `charlwood_problems` | 43 | Kevin Charlwood, *Integration on Computer Algebra Systems* (2008) |
| `hearn_problems` | 284 | Anthony Hearn, REDUCE Integration Test Package |
| `hebisch_problems` | 7 | Waldek Hebisch, email May 2013 (distinct from the `hebisch` suite) |
| `jeffrey_problems` | 9 | David Jeffrey, *Rectifying Transformations for Trig Integration* (1997) |
| `moses_problems` | 111 | Joel Moses, *Symbolic Integration* Ph.D. thesis (1967) |
| `stewart_problems` | 375 | James Stewart, *Calculus* (1987) |
| `timofeev_problems` | 629 | A. F. Timofeev, *Integration of Functions* (1948) |
| `welz_problems` | 92 | Martin Welz, sci.math.symbolic posts |
| `wester_problems` | 7 | Michael Wester |

## Where these came from

The same route as the `rubi` suite: chapter 0 of
[RuleBasedIntegration/MathematicaSyntaxTestSuite](https://github.com/RuleBasedIntegration/MathematicaSyntaxTestSuite),
through Francesco Bonazzi's SymPy translation. They are kept in their
own suite because their provenance is not Rubi's.

## License

MIT, as part of the Rubi test suite; Francesco Bonazzi's translation is
also MIT.

Several of these sets transcribe exercises from books and papers still in
copyright. Individual integrals are mathematical facts and not
copyrightable; only the selection and arrangement of a compilation could
attach, and these sets are reorganized rather than reproduced. Rubi has
distributed them under MIT since 2018, including in its
[JOSS publication](https://joss.theoj.org/papers/10.21105/joss.01073).
This repository relies on that grant rather than re-transcribing from the
original books.
