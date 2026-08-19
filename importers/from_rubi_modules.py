# -*- coding: utf-8 -*-
"""Convert Francesco Bonazzi's rubi-integration-test-suite into JSONL.

That package stores the Rubi MathematicaSyntaxTestSuite as generated
Python modules holding ``RubiTestSuiteCase`` objects.  This importer
walks them and writes the canonical records, one JSONL file per source
module, splitting the twelve independent problem sets out of chapter 0
into their own suite because their provenance differs from Rubi's own
chapters.

Every expression is written with ``str()`` and read back with
``sympify`` to confirm it round-trips, rather than being written in a
form the loader would silently misread.  An integrand that does not
round-trip drops its case; an expected antiderivative that does not is
dropped on its own, leaving the problem in place without an answer.
Both counts are recorded in ``data/rubi/IMPORT_REPORT.json``.

Usage:
    python importers/from_rubi_modules.py <path-to-rubi-integration-test-suite>
"""
from __future__ import annotations

import importlib
import json
import os
import pkgutil
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

from integration_test_suites.case import IntegrationTestCase  # noqa: E402

INDEPENDENT_CHAPTER = 't_0_independent_test_suites'


def module_target(modname: str) -> tuple[str, str]:
    """(suite, relative jsonl path) for a generated module name."""
    parts = modname.split('.')[1:]
    if parts[0] == INDEPENDENT_CHAPTER:
        return 'independent', parts[-1] + '.jsonl'
    return 'rubi', os.path.join(*parts) + '.jsonl'


def round_trips(expr) -> str | None:
    """``str(expr)`` if sympify reads it back unchanged, else None."""
    from sympy import sympify

    try:
        text = str(expr)
        if sympify(text) == expr:
            return text
    except Exception:
        return None
    return None


def convert(case, suite: str, source: str, index: int):
    """A RubiTestSuiteCase as an IntegrationTestCase.

    Returns None only when the integrand itself does not survive the
    string round trip; an expected antiderivative that does not is
    dropped on its own, since the integrand is the test and the expected
    answer is a bonus the runner can do without.
    """
    integrand = round_trips(case.integrand)
    if integrand is None:
        return None
    return IntegrationTestCase(
        integrand=integrand,
        variable=str(case.variable),
        suite=suite,
        source=source,
        index=index,
        integral=round_trips(case.integral),
        num_steps=case.num_steps,
    )


def main() -> None:
    src_repo = os.path.abspath(sys.argv[1])
    sys.path.insert(0, src_repo)
    import rubi_integration_test_suite as corpus

    data_dir = os.path.join(HERE, 'data')
    n_written = n_dropped = n_broken = n_modules = 0
    n_answer_dropped = 0
    broken = []
    for modinfo in pkgutil.walk_packages(corpus.__path__,
                                         corpus.__name__ + '.'):
        if modinfo.ispkg:
            continue
        try:
            mod = importlib.import_module(modinfo.name)
        except Exception as e:
            n_broken += 1
            broken.append({'module': modinfo.name,
                           'error': '%s: %s' % (type(e).__name__, str(e)[:200])})
            print('  BROKEN-MODULE %s: %s: %s'
                  % (modinfo.name, type(e).__name__, str(e)[:120]), flush=True)
            continue
        cases = getattr(mod, 'TEST_CASES', [])
        if not cases:
            continue
        suite, relpath = module_target(modinfo.name)
        source = getattr(mod, 'SOURCE_FILE', modinfo.name)
        out_path = os.path.join(data_dir, suite, relpath)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        written = 0
        with open(out_path, 'w', encoding='utf-8') as fh:
            for index, case in enumerate(cases):
                record = convert(case, suite, source, index)
                if record is None:
                    n_dropped += 1
                    continue
                if record.integral is None:
                    n_answer_dropped += 1
                fh.write(record.to_json() + '\n')
                written += 1
        n_written += written
        n_modules += 1
        print('  %-70s %5d' % (relpath, written), flush=True)
        del sys.modules[modinfo.name]

    report = {'modules_converted': n_modules, 'cases_written': n_written,
              'cases_dropped_integrand_not_round_tripping': n_dropped,
              'answers_dropped_not_round_tripping': n_answer_dropped,
              'modules_broken_at_import': n_broken, 'broken': broken}
    with open(os.path.join(data_dir, 'rubi', 'IMPORT_REPORT.json'), 'w') as fh:
        json.dump(report, fh, indent=2)
    print('\nmodules %d, cases %d, integrands dropped %d, answers dropped %d,'
          ' broken modules %d'
          % (n_modules, n_written, n_dropped, n_answer_dropped, n_broken))


if __name__ == '__main__':
    main()
