# -*- coding: utf-8 -*-
"""One pinned corpus case per proof step, and a soundness check.

Each positive case is a real corpus residual that only its step closes;
the negative cases confirm the prover refuses a perturbed answer.
"""
from __future__ import annotations

import pytest
from sympy import Symbol, sympify

from integration_test_suites.verify import prove_derivative

x = Symbol('x')

#: (step, integrand, antiderivative) -- from the named corpus cases.
CASES = [
    # rubi t_8_9[65] (LambertW): the defining identity W*exp(W) == z
    ('special',
     'LambertW(a*x)/x**2',
     'a*Ei(-LambertW(a*x)) - LambertW(a*x)/x'),
    # rubi t_2_3[30] (F**u vs exp): principal-power flattening
    ('powexp',
     'F**(a + b*x)*x**(5/2)',
     '-15*sqrt(pi)*F**a*erfi(sqrt(b)*sqrt(x)*sqrt(log(F)))'
     '/(8*b**(7/2)*log(F)**(7/2)) + F**(a + b*x)*x**(5/2)/(b*log(F))'
     ' - 5*F**(a + b*x)*x**(3/2)/(2*b**2*log(F)**2)'
     ' + 15*F**(a + b*x)*sqrt(x)/(4*b**3*log(F)**3)'),
    # rubi t_1[717] (2F1 tower + incomplete-beta relation)
    ('hyper2f1',
     'x**m/sqrt(3*x + 2)',
     'sqrt(2)*x**(m + 1)*hyper((1/2, m + 1), (m + 2,), -3*x/2)/(2*m + 2)'),
]


@pytest.mark.parametrize('step,f,F', CASES, ids=[c[0] for c in CASES])
def test_step_proves(step, f, F):
    assert prove_derivative(sympify(f), x, sympify(F), deep=False) == step


def test_argnorm_unifies_radicand_forms():
    # blake 980's blocker in miniature: the same radicand written two ways
    f = sympify('x/sqrt((1 - x**2)/(1 + x**2))')
    F = sympify('x**2/(2*sqrt(-x**2/(x**2 + 1) + 1/(x**2 + 1)))')
    # not equal antiderivatives; only the atoms must unify, so build the
    # exact-difference case instead
    d_f = sympify('sqrt((1 - x**2)/(1 + x**2)) '
                  '- sqrt(1/(1 + x**2) - x**2/(1 + x**2))')
    from integration_test_suites.proofsteps import argnorm
    from sympy import cancel
    assert cancel(argnorm(d_f)).is_zero


def test_numzero_kills_algebraic_coefficients():
    from integration_test_suites.proofsteps import numzero
    e = sympify('(sqrt(6) - sqrt(2)*sqrt(3))*x*sqrt(x**3 + 1)')
    assert numzero(e)


@pytest.mark.parametrize('step,f,F', CASES, ids=[c[0] for c in CASES])
def test_perturbed_answers_stay_unproven(step, f, F):
    F2 = 2 * sympify(F)
    assert prove_derivative(sympify(f), x, F2, deep=False) is None
