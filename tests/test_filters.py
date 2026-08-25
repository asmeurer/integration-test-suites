# -*- coding: utf-8 -*-
"""The named case filters select what they claim to."""
from __future__ import annotations

import pytest
from sympy import Symbol, cos, exp, sin, sqrt, symbols, tan

from integration_test_suites.filters import FILTERS

x = Symbol('x')
a, b, c = symbols('a b c')


@pytest.mark.parametrize('f', [
    1/(sin(x) + cos(x + 1) + 2),
    1/(a + b*sin(x)),
    sin(x)/sin(4*x),
    tan(x)*tan(a - x),
    1/(sin(x)*cos(3.14159*x) + 2),  # incommensurable, still in scope
    cos(c + b*x)**4/(a + b*sin(c + b*x))**8,
])
def test_trig_rational_accepts(f):
    assert FILTERS['trig-rational'](f, x)


@pytest.mark.parametrize('f', [
    x*sin(x),                # x outside the trig terms
    sin(x**2),               # argument not affine
    sqrt(sin(x)),            # not a rational function of the trig terms
    sin(x)**a,               # symbolic exponent
    exp(x)*sin(x),           # non-trig tower
    sin(sin(x)),             # nested trig
    1/(x + 1),               # no trig at all
    sin(a),                  # trig, but not in the variable
])
def test_trig_rational_rejects(f):
    assert not FILTERS['trig-rational'](f, x)
