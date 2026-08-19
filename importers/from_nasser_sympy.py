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
        with open(out_path, 'w', encoding='utf-8') as fh:
            for index, row in enumerate(rows):
                integrand = row[0]
                if not parses(integrand):
                    n_bad_integrand += 1
                    continue
                variable = str(row[1])
                num_steps = row[2] if len(row) > 2 else None
                answers = [a for a in row[3:] if isinstance(a, str)]
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
                         'answers_dropped_unparseable': n_bad_integral}
        print('%-10s %6d cases (%d integrands dropped, %d answers dropped)'
              % (suite, n_written, n_bad_integrand, n_bad_integral), flush=True)

    with open(os.path.join(data_dir, 'NASSER_IMPORT_REPORT.json'), 'w') as fh:
        json.dump(report, fh, indent=2)


if __name__ == '__main__':
    main()
