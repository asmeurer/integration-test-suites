# -*- coding: utf-8 -*-
"""Convert Nasser Abbasi's sympy-syntax problem files into JSONL.

Source: the ``SYMPY_syntax.zip`` of the Summer 2021 edition of the
Computer Algebra Independent Integration Tests,
https://www.12000.org/my_notes/CAS_integration_tests/ .

Only the two suites that exist nowhere else are taken: Waldek Hebisch's
random exp-log problems and Sam Blake's algebraic problems.  Nasser's
copies of the Rubi chapters and of the twelve independent problem sets
are deliberately skipped -- those come from Francesco Bonazzi's MIT
translation instead, so that the licensing exposure of this repository
is confined to as few problems as possible.

Each source file is a Python fragment declaring ``symbols`` and then a
list of ``[integrand, variable, num_steps, antiderivative, ...]`` rows
whose expressions are strings, so it is executed with ``symbols`` bound
and the rows read off directly.

An antiderivative that does not sympify (Blake's answers use Maple's
``RootSum(_Z1 -> ..., _Z1 -> ...)`` lambda syntax, which is not Python)
is dropped while the problem is kept: the integrand is the test, and the
expected answer is a bonus the runner can do without.

A handful of Hebisch expected answers are corrected on import (see
``LOG_EXP_UNWRAP`` and ``ANSWER_OVERRIDES``): the suite's integrands are
expanded derivatives of generated expressions in which ``log(exp(u))``
counts as ``u``, but the transcribed answers keep the unsimplified
``log(exp(u)**k)`` towers, which differ from ``k*u`` by a locally
constant offset off the principal strip and so are wrong as
antiderivatives there.  The corrected forms prove exactly:
``cancel(diff(F) - f) == 0``.

The source zip is frozen upstream (the Summer 2021 edition; Hebisch's
original site is gone), so these suites regenerate byte-identically.
The site refuses non-browser user agents; download with:

    curl -A "Mozilla/5.0" -O https://www.12000.org/my_notes/\
CAS_integration_tests/reports/summer_2021/input/SYMPY_syntax.zip

Usage:
    python importers/from_nasser_sympy.py <path-to-extracted-SYMPY-dir>
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

from integration_test_suites.case import IntegrationTestCase  # noqa: E402

#: (suite name, path under the SYMPY directory, upstream description)
SOURCES = [
    ('hebisch', '10_Hebisch/Hebisch_Problems.py',
     'Hebisch rand3c.input, via 12000.org SYMPY_syntax.zip (Summer 2021)'),
    ('blake', '9_Blake_problems/BlakeProblems.py',
     'Blake IntegrateAlgebraic problems, via 12000.org SYMPY_syntax.zip'
     ' (Summer 2021)'),
]


#: Hebisch cases whose expected answers are rewritten with
#: ``log(exp(u)**k) -> k*u`` on import.  The audit's numerical oracle
#: convicted all of these (2026-08-24): the unsimplified tower is only a
#: valid antiderivative where ``k*u`` stays in the principal strip, and
#: each of these answers feeds the tower into a larger expression
#: nonlinearly, so the offset differentiates into a real error.  The
#: rewritten answers prove exactly against their integrands.
LOG_EXP_UNWRAP = frozenset({
    1411, 1770, 2364, 2878, 3241, 3319, 3862, 3954, 4674, 4706,
    6767, 6966, 9136, 9373, 10048, 10277,
})

#: Hebisch answers replaced outright.  8737's transcription flips the
#: sign of the imaginary part in a constant: the integrand contains
#: ``log(-log(2) - I*pi)`` but the answer was written with
#: ``log(-log(2) + I*pi)``.  The corrected form proves exactly.
ANSWER_OVERRIDES = {
    8737: 'x*(3-(x-24+ln(-ln(2)-I*pi))*x)',
}


def check_correction(integrand: str, variable: str, answers: list,
                     index: int) -> None:
    """Prove a corrected answer before letting it into the corpus.

    Every correction table entry must yield an answer with
    ``cancel(diff(F) - f) == 0`` exactly; anything else means the
    upstream source shifted under the table (or a correction is wrong),
    and the import fails loudly instead of emitting bad test data.
    """
    from sympy import Symbol, cancel, diff, sympify

    x = Symbol(variable)
    f = sympify(integrand)
    for text in answers:
        residual = cancel(diff(sympify(text), x) - f)
        if not residual.is_zero:
            raise RuntimeError(
                'corrected hebisch answer %d does not prove: '
                'cancel(diff(F) - f) = %s' % (index, str(residual)[:120]))


def unwrap_log_exp(text: str) -> str:
    """``text`` with ``log(exp(v)) -> v`` and ``log(exp(v)**k) -> k*v``,
    applied bottom-up until fixed point, as a round-trippable string."""
    from sympy import Pow, exp, log, sympify

    def rule(s):
        a = s.args[0]
        if isinstance(a, exp):
            return a.args[0]
        if isinstance(a, Pow) and isinstance(a.base, exp):
            return a.exp * a.base.args[0]
        return s

    e = sympify(text)
    prev = None
    while prev != e:
        prev = e
        e = e.replace(lambda s: isinstance(s, log), rule)
    return str(e)


def read_rows(path: str) -> list:
    """The ``lst`` rows of one of Nasser's sympy-syntax files."""
    from sympy import symbols

    namespace: dict = {'symbols': symbols}
    with open(path, encoding='utf-8') as fh:
        exec(compile(fh.read(), path, 'exec'), namespace)
    return namespace['lst']


def parses(text: str) -> bool:
    from sympy import sympify

    try:
        sympify(text)
    except Exception:
        return False
    return True


def main() -> None:
    sympy_dir = os.path.abspath(sys.argv[1])
    data_dir = os.path.join(HERE, 'data')
    report = {}

    for suite, relpath, description in SOURCES:
        rows = read_rows(os.path.join(sympy_dir, relpath))
        out_dir = os.path.join(data_dir, suite)
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, suite + '.jsonl')

        n_written = n_bad_integrand = n_bad_integral = 0
        n_corrected = 0
        with open(out_path, 'w', encoding='utf-8') as fh:
            for index, row in enumerate(rows):
                integrand = row[0]
                if not parses(integrand):
                    n_bad_integrand += 1
                    continue
                variable = str(row[1])
                num_steps = row[2] if len(row) > 2 else None
                answers = [a for a in row[3:] if isinstance(a, str)]
                if suite == 'hebisch' and index in ANSWER_OVERRIDES:
                    answers = [ANSWER_OVERRIDES[index]]
                    check_correction(integrand, str(row[1]), answers, index)
                    n_corrected += 1
                elif suite == 'hebisch' and index in LOG_EXP_UNWRAP:
                    unwrapped = [unwrap_log_exp(a) for a in answers]
                    if unwrapped == answers:
                        raise RuntimeError(
                            'LOG_EXP_UNWRAP entry %d changed nothing; the '
                            'upstream source no longer matches the table'
                            % index)
                    answers = unwrapped
                    check_correction(integrand, str(row[1]), answers, index)
                    n_corrected += 1
                good = [a for a in answers if parses(a)]
                n_bad_integral += len(answers) - len(good)
                record = IntegrationTestCase(
                    integrand=integrand,
                    variable=variable,
                    suite=suite,
                    source=description,
                    index=index,
                    integral=good[0] if good else None,
                    num_steps=num_steps if isinstance(num_steps, int) else None,
                    alt_integrals=good[1:],
                )
                fh.write(record.to_json() + '\n')
                n_written += 1

        report[suite] = {'source_file': relpath, 'upstream': description,
                         'rows_in_source': len(rows),
                         'cases_written': n_written,
                         'dropped_unparseable_integrand': n_bad_integrand,
                         'answers_dropped_unparseable': n_bad_integral,
                         'answers_corrected': n_corrected}
        print('%-10s %6d cases (%d integrands dropped, %d answers dropped,'
              ' %d answers corrected)'
              % (suite, n_written, n_bad_integrand, n_bad_integral,
                 n_corrected), flush=True)

    with open(os.path.join(data_dir, 'NASSER_IMPORT_REPORT.json'), 'w') as fh:
        json.dump(report, fh, indent=2)


if __name__ == '__main__':
    main()
