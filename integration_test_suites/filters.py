# -*- coding: utf-8 -*-
"""Named predicates for skipping cases an engine cannot usefully attempt.

Most of the corpus is irrelevant to any one engine, and running it anyway
buys nothing but wall-clock.  The Rubi chapters in particular are heavily
parameterized by *symbolic exponents* -- `(a + b*x)**m` with `m` a symbol
-- which no Risch-style method can attempt at all, so a Risch run over
the algebraic chapters should filter to `rational-exponents` first.

Filters are combined with "and": every named filter must accept a case
for it to be attempted.

    python -m integration_test_suites.run --engine risch \\
        --filter rational-exponents --filter no-radical

The `hebisch` suite needs none of these: it is exp-log by construction
and every case is attemptable.
"""
from __future__ import annotations

from typing import Callable


def _pow_exponents_are_rational(f, x) -> bool:
    from sympy import Pow, nan, oo, zoo

    if f.has(nan, oo, zoo):
        return False
    return all(p.exp.is_Rational for p in f.atoms(Pow))


def _has_radical(f, x) -> bool:
    """A fractional power of an x-dependent base that is not an exp.

    ``sqrt(exp(u))`` rewrites to ``exp(u/2)`` and a constant radical only
    extends the constant field, so neither makes the tower algebraic.
    """
    from sympy import Pow, exp

    return any(p.exp.is_Rational and not p.exp.is_Integer
               and p.base.has(x) and p.base.func is not exp
               for p in f.atoms(Pow))


def _is_concrete(f, x) -> bool:
    return not (f.free_symbols - {x})


def _has_special_functions(f, x) -> bool:
    from sympy.functions.special.error_functions import (
        Ei, erf, erfi, expint, fresnelc, fresnels, li, Si, Ci, Shi, Chi)
    from sympy.functions.special.gamma_functions import (
        gamma, lowergamma, uppergamma, polygamma)
    from sympy.functions.special.bessel import besseli, besselj, besselk, bessely
    from sympy.functions.special.hyper import hyper, meijerg
    from sympy.functions.special.zeta_functions import polylog, zeta

    return f.has(Ei, erf, erfi, expint, fresnelc, fresnels, li, Si, Ci, Shi,
                 Chi, gamma, lowergamma, uppergamma, polygamma, besseli,
                 besselj, besselk, bessely, hyper, meijerg, polylog, zeta)


def _is_trig_rational(f, x) -> bool:
    """A rational function of circular trig functions of affine arguments.

    The class attacked by Bioche/Weierstrass substitutions: every
    occurrence of ``x`` sits inside a sin/cos/tan/cot/sec/csc whose
    argument is affine in ``x``, and the integrand is a rational
    function of those trig subexpressions.  Frequencies need not be
    commensurable and coefficients may be symbolic; those subclasses are
    still worth attempting (or cleanly refusing).
    """
    from sympy import Dummy, cos, cot, csc, sec, sin, tan

    trigs = [t for t in f.atoms(sin, cos, tan, cot, sec, csc) if t.has(x)]
    if not trigs:
        return False
    if any(t.args[0].diff(x).has(x) for t in trigs):
        return False
    reps = {t: Dummy() for t in trigs}
    g = f.xreplace(reps)
    if g.has(x):
        return False
    return g.is_rational_function(*reps.values())


#: name -> predicate(integrand, variable) -> keep?
FILTERS: dict[str, Callable] = {
    'rational-exponents': _pow_exponents_are_rational,
    'symbolic-exponents': lambda f, x: not _pow_exponents_are_rational(f, x),
    'radical': _has_radical,
    'no-radical': lambda f, x: not _has_radical(f, x),
    'concrete': _is_concrete,
    'parametric': lambda f, x: not _is_concrete(f, x),
    'elementary': lambda f, x: not _has_special_functions(f, x),
    'special-functions': _has_special_functions,
    'trig-rational': _is_trig_rational,
}

#: shorthands expanding to several filters
PRESETS: dict[str, list[str]] = {
    'risch-attemptable': ['rational-exponents', 'elementary'],
    'risch-transcendental': ['rational-exponents', 'elementary', 'no-radical'],
    'risch-algebraic': ['rational-exponents', 'elementary', 'radical'],
}


def expand(names: list[str]) -> list[str]:
    """Resolve presets into their constituent filter names."""
    out: list[str] = []
    for name in names:
        if name in PRESETS:
            out.extend(PRESETS[name])
        elif name in FILTERS:
            out.append(name)
        else:
            raise ValueError(
                'unknown filter %r (filters: %s; presets: %s)'
                % (name, ', '.join(sorted(FILTERS)), ', '.join(sorted(PRESETS))))
    return list(dict.fromkeys(out))


def accepts(names: list[str], f, x) -> bool:
    return all(FILTERS[name](f, x) for name in names)
