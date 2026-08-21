# Suite: `hebisch`

10,335 randomly generated problems whose integrands are guaranteed to
have elementary antiderivatives, which makes this the sharpest available
test of a Risch implementation on exponential-logarithmic towers. FriCAS
solves 99.92% of them.

Waldek Hebisch generated them from a uniform distribution on unary-binary
trees with 15 nodes, with binary operations drawn from `+ - * /` and
unary operations from `log`, `exp` and squaring; leaves are the variable
with probability 1/2 and an integer 1-5 with probability 1/10 each. The
integrand is the *expanded derivative* of the generated expression, so
the expression itself is a known antiderivative.

## What it contains

One file, `hebisch.jsonl`, with all 10,335 cases. Every case is an
indefinite integral in `x` with no symbolic constants, and every case
carries its expected antiderivative — by construction, since the
integrand is the derivative of the recorded expression. The integrands
are pure exp-log towers: no algebraic functions, no trigonometry (which
is what makes the suite a direct measure of the transcendental Risch
algorithm rather than of heuristics).

Two cases are worth knowing about when benchmarking (see the top-level
CLAUDE.md): index 1692 is hash-seed-dependent in runtime, and index 274
trips an E-vs-`exp(1/2)` canonicalization bug in SymPy's Risch code.

## Where these came from

Announced in [this sci.math.symbolic thread](https://groups.google.com/g/sci.math.symbolic/c/f6zYWBa-Y-k)
and published as `http://www.math.uni.wroc.pl/~hebisch/fricas/rand3c.input`
in FriCAS `do_test(f, i)` syntax.

**That URL is dead and the file does not appear to survive anywhere
else.** Hebisch's entire university homepage went offline between
2023-10-03 and 2023-12-19; the file was never linked from his index page,
so the Wayback Machine never crawled it, and it is not in the FriCAS git
repository either.

The copy here is the SymPy-syntax translation from the Summer 2021 edition
of Nasser Abbasi's
[Computer Algebra Independent Integration Tests](https://www.12000.org/my_notes/CAS_integration_tests/),
imported by `importers/from_nasser_sympy.py`.

## License

**None stated, by anyone.** Hebisch attached no license to the original,
and Nasser Abbasi's site carries no copyright or license statement.

This suite is included pending Nasser's agreement (see the repository
README). If either author asks for removal, delete this directory; no
other suite depends on it.

Because the construction is fully documented above, an equivalent suite
of any size can be regenerated from scratch under a license of our
choosing. That is the intended fallback.
