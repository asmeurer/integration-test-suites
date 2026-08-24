# -*- coding: utf-8 -*-
"""Convert Francesco Bonazzi's rubi-integration-test-suite into JSONL.

That package stores the Rubi MathematicaSyntaxTestSuite as generated
Python modules holding ``RubiTestSuiteCase`` objects.  This importer
walks them and writes the canonical records, one JSONL file per source
module, splitting the twelve independent problem sets out of chapter 0
into their own suite because their provenance differs from Rubi's own
chapters.

The generated modules leave some Mathematica heads untranslated, so
they arrive as undefined sympy ``Function``s: ``PolyLog``, ``Gamma``,
``EllipticPi`` and so on.  This importer maps them to their sympy
equivalents (the table is ``translate_heads``).  Rubi's markers for a
problem it could not do — ``Unintegrable``, ``CannotIntegrate`` and an
unevaluated ``Int`` — are not expressions at all, so an expected answer
containing one is dropped, leaving the problem in place without an
answer.  Heads with no sympy equivalent (the arbitrary functions ``F``
and ``F0``, Mathematica's generalized ``PolyGamma`` of negative order)
pass through unchanged and are tallied in the report.

Every expression is written with ``str()`` and read back with
``sympify`` to confirm it round-trips, rather than being written in a
form the loader would silently misread.  An integrand that does not
round-trip drops its case; an expected antiderivative that does not is
dropped on its own, leaving the problem in place without an answer.
All counts are recorded in ``data/rubi/IMPORT_REPORT.json``.

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

#: Rubi's ways of saying it has no antiderivative to offer.  An expected
#: answer containing any of these is not an expression and is dropped.
MARKER_HEADS = frozenset({'Unintegrable', 'CannotIntegrate', 'Int'})

#: Cases excluded from the corpus entirely, keyed by (jsonl basename,
#: upstream index).  The two Welz problems carry a literal ``0`` as
#: their upstream expected antiderivative — a placeholder like the
#: marker heads, but indistinguishable from a real answer once emitted
#: (the answer audit convicted both) — so the problems sit out until a
#: real reference antiderivative exists.  Skipping does not renumber:
#: ``index`` is the upstream enumeration position.  Each skip is
#: verified against the upstream case at import time, so an upstream
#: update that moves or fixes these cases fails the import loudly
#: instead of silently skipping the wrong problem; a zero answer on any
#: *other* case is dropped as a placeholder and counted in the report.
SKIP_CASES = frozenset({
    ('welz_problems.jsonl', 56),
    ('welz_problems.jsonl', 78),
})


def check_skip(case, skip_key: str, index: int) -> None:
    """Assert a SKIP_CASES entry still points at a zero-placeholder."""
    if str(case.integral) != '0':
        raise RuntimeError(
            'SKIP_CASES entry (%r, %d) no longer matches a literal-0 '
            'expected answer (found %r); the upstream suite changed -- '
            're-triage this case instead of skipping it'
            % (skip_key, index, str(case.integral)[:80]))

_HANDLERS = None


def _handlers():
    """Head name -> callable(applied undefined function) -> sympy expr."""
    global _HANDLERS
    if _HANDLERS is None:
        from sympy import (Chi, Ci, Ei, LambertW, Shi, Si, elliptic_pi, erf,
                           erfi, expand, fresnelc, fresnels, gamma, li,
                           loggamma, polygamma, polylog, uppergamma, zeta)

        def gamma_(e):
            # Mathematica: Gamma[z] is the gamma function, Gamma[a, z]
            # the upper incomplete one.
            fn = {1: gamma, 2: uppergamma}[len(e.args)]
            return fn(*e.args)

        def polygamma_(e):
            # PolyGamma of negative order is Mathematica's generalized
            # polygamma, which sympy does not have.
            n = e.args[0]
            if n.is_Integer and n.is_negative:
                return e
            return polygamma(*e.args)

        simple = {
            'PolyLog': polylog, 'EllipticPi': elliptic_pi,
            'ProductLog': LambertW, 'SinIntegral': Si, 'CosIntegral': Ci,
            'SinhIntegral': Shi, 'CoshIntegral': Chi, 'ExpIntegralEi': Ei,
            'LogIntegral': li, 'Erf': erf, 'Erfi': erfi,
            'FresnelS': fresnels, 'FresnelC': fresnelc, 'Zeta': zeta,
            'LogGamma': loggamma,
        }
        _HANDLERS = {name: (lambda e, fn=fn: fn(*e.args))
                     for name, fn in simple.items()}
        _HANDLERS['Gamma'] = gamma_
        _HANDLERS['PolyGamma'] = polygamma_
        # Expand[...] is an instruction to the CAS, not a function; its
        # meaning is the expanded argument.
        _HANDLERS['Expand'] = lambda e: expand(e.args[0])
    return _HANDLERS


def translate_heads(expr):
    """``expr`` with untranslated Mathematica heads mapped to sympy."""
    from sympy.core.function import AppliedUndef

    handlers = _handlers()
    return expr.replace(
        lambda e: isinstance(e, AppliedUndef) and type(e).__name__ in handlers,
        lambda e: handlers[type(e).__name__](e))


def undefined_heads(expr) -> set[str]:
    """Names of the undefined functions applied anywhere in ``expr``."""
    from sympy.core.function import AppliedUndef

    return {type(f).__name__ for f in expr.atoms(AppliedUndef)}


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


def convert(case, suite: str, source: str, index: int, stats):
    """A RubiTestSuiteCase as an IntegrationTestCase.

    Returns None only when the integrand itself does not survive the
    string round trip; an expected antiderivative that does not — or
    that contains one of Rubi's no-answer markers — is dropped on its
    own, since the integrand is the test and the expected answer is a
    bonus the runner can do without.  ``stats`` is a Counter of what
    happened along the way.
    """
    f = translate_heads(case.integrand)
    if f != case.integrand:
        stats['integrands_translated'] += 1
    integrand = round_trips(f)
    if integrand is None:
        stats['integrands_dropped_not_round_tripping'] += 1
        return None

    integral = None
    if case.integral is not None:
        if undefined_heads(case.integral) & MARKER_HEADS:
            stats['answers_dropped_unintegrable_marker'] += 1
        elif case.integral.is_zero and not case.integrand.is_zero:
            # a literal 0 "antiderivative" of a nonzero integrand is a
            # placeholder (SKIP_CASES excludes the known ones outright;
            # any new one from an upstream update is dropped here)
            stats['answers_dropped_zero_placeholder'] += 1
        else:
            expected = translate_heads(case.integral)
            if expected != case.integral:
                stats['answers_translated'] += 1
            integral = round_trips(expected)
            if integral is None:
                stats['answers_dropped_not_round_tripping'] += 1
            else:
                for name in undefined_heads(expected):
                    stats['leftover_head:' + name] += 1
    for name in undefined_heads(f):
        stats['leftover_head:' + name] += 1

    return IntegrationTestCase(
        integrand=integrand,
        variable=str(case.variable),
        suite=suite,
        source=source,
        index=index,
        integral=integral,
        num_steps=case.num_steps,
    )


def main() -> None:
    src_repo = os.path.abspath(sys.argv[1])
    sys.path.insert(0, src_repo)
    import rubi_integration_test_suite as corpus

    from collections import Counter

    data_dir = os.path.join(HERE, 'data')
    n_written = n_broken = n_modules = 0
    stats: Counter = Counter()
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
        skip_key = os.path.basename(relpath)
        with open(out_path, 'w', encoding='utf-8') as fh:
            for index, case in enumerate(cases):
                if (skip_key, index) in SKIP_CASES:
                    check_skip(case, skip_key, index)
                    stats['cases_skipped'] += 1
                    continue
                record = convert(case, suite, source, index, stats)
                if record is None:
                    continue
                fh.write(record.to_json() + '\n')
                written += 1
        n_written += written
        n_modules += 1
        print('  %-70s %5d' % (relpath, written), flush=True)
        del sys.modules[modinfo.name]

    leftover = {k.split(':', 1)[1]: n for k, n in sorted(stats.items())
                if k.startswith('leftover_head:')}
    report = {
        'modules_converted': n_modules,
        'cases_written': n_written,
        'cases_dropped_integrand_not_round_tripping':
            stats['integrands_dropped_not_round_tripping'],
        'answers_dropped_not_round_tripping':
            stats['answers_dropped_not_round_tripping'],
        'answers_dropped_unintegrable_marker':
            stats['answers_dropped_unintegrable_marker'],
        'answers_translated': stats['answers_translated'],
        'integrands_translated': stats['integrands_translated'],
        'untranslated_heads_remaining': leftover,
        'cases_skipped': stats['cases_skipped'],
        'answers_dropped_zero_placeholder':
            stats['answers_dropped_zero_placeholder'],
        'modules_broken_at_import': n_broken,
        'broken': broken,
    }
    with open(os.path.join(data_dir, 'rubi', 'IMPORT_REPORT.json'), 'w') as fh:
        json.dump(report, fh, indent=2)
    print('\nmodules %d, cases %d, integrands dropped %d, answers dropped %d'
          ' (%d marker), translated %d answers / %d integrands,'
          ' broken modules %d'
          % (n_modules, n_written,
             stats['integrands_dropped_not_round_tripping'],
             stats['answers_dropped_not_round_tripping'],
             stats['answers_dropped_unintegrable_marker'],
             stats['answers_translated'], stats['integrands_translated'],
             n_broken))
    if leftover:
        print('untranslated heads remaining: %s' % leftover)


if __name__ == '__main__':
    main()
