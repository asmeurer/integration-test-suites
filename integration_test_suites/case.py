# -*- coding: utf-8 -*-
"""The canonical test-case record shared by every suite."""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from functools import cached_property

from sympy import Expr, Symbol, sympify

#: Names appearing in vendored suite sources that sympify does not map to
#: the intended sympy object on its own.
SYMPIFY_LOCALS = {}


@dataclass
class IntegrationTestCase:
    """One integration problem and its expected result.

    ``integrand``, ``integral`` and ``alt_integrals`` are stored as
    strings and sympified on demand: a corpus of this size is loaded far
    more often than it is evaluated, and most runs touch a slice of it.

    A case with ``lower`` and ``upper`` set is a *definite* integral
    over that interval; ``value`` is then the expected value of the
    definite integral.  ``integral`` always means an expected
    antiderivative and is normally absent on definite cases (a definite
    case may carry both when the source gives both).

    ``num_steps`` is Rubi's own step count for the case, passed through
    from the source suite verbatim; some suites record negative values
    and this package assigns them no meaning.
    """

    integrand: str
    variable: str
    suite: str
    source: str
    index: int
    integral: str | None = None
    num_steps: int | None = None
    alt_integrals: list[str] = field(default_factory=list)
    lower: str | None = None
    upper: str | None = None
    value: str | None = None

    @cached_property
    def x(self) -> Symbol:
        return Symbol(self.variable)

    @cached_property
    def f(self) -> Expr:
        """The integrand as a sympy expression."""
        return sympify(self.integrand, locals=SYMPIFY_LOCALS)

    @cached_property
    def expected(self) -> Expr | None:
        """The expected antiderivative, or None if the suite has none."""
        if self.integral is None:
            return None
        return sympify(self.integral, locals=SYMPIFY_LOCALS)

    @cached_property
    def alternatives(self) -> list[Expr]:
        """Further accepted antiderivatives given by the suite."""
        return [sympify(a, locals=SYMPIFY_LOCALS) for a in self.alt_integrals]

    @property
    def is_definite(self) -> bool:
        return self.lower is not None and self.upper is not None

    @cached_property
    def bounds(self) -> tuple[Expr, Expr] | None:
        """The integration interval of a definite case, or None."""
        if not self.is_definite:
            return None
        return (sympify(self.lower, locals=SYMPIFY_LOCALS),
                sympify(self.upper, locals=SYMPIFY_LOCALS))

    @cached_property
    def expected_value(self) -> Expr | None:
        """The expected value of a definite case, or None."""
        if self.value is None:
            return None
        return sympify(self.value, locals=SYMPIFY_LOCALS)

    def to_json(self) -> str:
        d = {k: v for k, v in asdict(self).items() if v not in (None, [])}
        return json.dumps(d, ensure_ascii=False, sort_keys=True)

    @classmethod
    def from_json(cls, line: str) -> IntegrationTestCase:
        return cls(**json.loads(line))
