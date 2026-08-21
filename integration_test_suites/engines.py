# -*- coding: utf-8 -*-
"""The integration routines the corpus can be run against.

Each engine is a name, a one-line description and a callable taking
``(integrand, variable)`` and returning a sympy expression.  Engines
whose backing package is not installed report ``available = False``
instead of raising, so that ``--engine rubi`` fails with a clear message
rather than an import traceback from deep inside a worker.

``call_definite`` takes ``(integrand, variable, lower, upper)`` and is
the entry point for definite cases; engines without one (the
antiderivative-only routines) simply skip those cases.  Evaluating an
engine's antiderivative at the bounds is deliberately not offered as a
fallback: an antiderivative with a branch jump inside the interval is
correct as an antiderivative and wrong as a definite value, and the two
measurements must not be conflated.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass
class Engine:
    name: str
    description: str
    call: Callable
    available: bool = True
    unavailable_reason: str = ''
    call_definite: Callable | None = None


def _sympy_engines() -> list[Engine]:
    from sympy import integrate
    from sympy.integrals.heurisch import heurisch
    from sympy.integrals.manualintegrate import manualintegrate
    from sympy.integrals.risch import risch_integrate

    def heurisch_call(f, x):
        result = heurisch(f, x)
        if result is None:
            from sympy import Integral
            return Integral(f, x)
        return result

    def meijerint_call(f, x, a, b):
        from sympy import Integral
        from sympy.integrals.meijerint import meijerint_definite
        result = meijerint_definite(f, x, a, b)
        if result is None:
            return Integral(f, (x, a, b))
        value, _cond = result
        return value

    return [
        Engine('integrate', "sympy's integrate()",
               lambda f, x: integrate(f, x),
               call_definite=lambda f, x, a, b: integrate(f, (x, a, b))),
        Engine('integrate_norisch',
               "sympy's integrate() with risch=False",
               lambda f, x: integrate(f, x, risch=False),
               call_definite=lambda f, x, a, b:
                   integrate(f, (x, a, b), risch=False)),
        Engine('manualintegrate', 'sympy.integrals.manualintegrate',
               lambda f, x: manualintegrate(f, x)),
        Engine('heurisch', 'sympy.integrals.heurisch (None as Integral)',
               heurisch_call),
        Engine('risch', 'sympy.integrals.risch.risch_integrate',
               lambda f, x: risch_integrate(f, x)),
        Engine('meijerint',
               'sympy.integrals.meijerint (definite cases only)',
               None, call_definite=meijerint_call),
    ]


def _risch_algebraic_engine() -> Engine:
    """risch_integrate(algebraic=True), where the sympy under test has it."""
    import inspect

    from sympy.integrals.risch import risch_integrate

    if 'algebraic' in inspect.signature(risch_integrate).parameters:
        return Engine('risch_algebraic',
                      'risch_integrate(algebraic=True)',
                      lambda f, x: risch_integrate(f, x, algebraic=True))
    return Engine('risch_algebraic', 'risch_integrate(algebraic=True)',
                  None, available=False,
                  unavailable_reason='this sympy has no algebraic= parameter')


def _rubi_engine() -> Engine:
    """Francesco Bonazzi's rubi-integrate, if it is installed."""
    try:
        from rubi_integrate import rubi_integrate
    except ImportError as e:
        return Engine('rubi', 'rubi-integrate (Rubi rule set on sympy)',
                      None, available=False,
                      unavailable_reason='%s (pip install rubi-integrate)' % e)
    return Engine('rubi', 'rubi-integrate (Rubi rule set on sympy)',
                  lambda f, x: rubi_integrate(f, x))


def registry() -> dict[str, Engine]:
    engines = _sympy_engines()
    engines.append(_risch_algebraic_engine())
    engines.append(_rubi_engine())
    return {e.name: e for e in engines}


def get(name: str) -> Engine:
    reg = registry()
    if name not in reg:
        raise ValueError('unknown engine %r (have: %s)'
                         % (name, ', '.join(sorted(reg))))
    engine = reg[name]
    if not engine.available:
        raise RuntimeError('engine %r is unavailable: %s'
                           % (name, engine.unavailable_reason))
    return engine
