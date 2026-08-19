# -*- coding: utf-8 -*-
"""Run an integration engine over the corpus and classify the results.

Each attempted case is classified as

  SOLVED     the engine returned a result with no unevaluated Integral
  partial    the result still contains an unevaluated Integral
  CLAIMS-NE  the result contains a NonElementaryIntegral
  NIE        the engine raised NotImplementedError
  timeout    the engine exceeded --timeout seconds
  error:*    the engine raised something else

A ``conds='piecewise'`` result carries an honestly unevaluated Integral
in its degenerate branch, so classification looks at the generic branch
and flags the case rather than counting it as a failure.

With ``--check`` every solved case is additionally verified with the
numerical oracle in :mod:`integration_test_suites.verify`, which decides
whether the answer really is an antiderivative of the integrand and,
where the suite supplies one, how it relates to the expected answer.

Usage:
    python -m integration_test_suites.run --engine integrate \\
        --suite mit_bee --timeout 20 --check
"""
from __future__ import annotations

import argparse
import json
import signal
import sys
import time
from collections import Counter


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog='python -m integration_test_suites.run',
        description=__doc__.split('\n\n')[0])
    p.add_argument('--engine', default='integrate',
                   help='integration routine to run (default: integrate)')
    p.add_argument('--suite', action='append', dest='suites',
                   help='restrict to this suite; repeatable')
    p.add_argument('--source-prefix',
                   help='restrict to cases whose source starts with this')
    p.add_argument('--limit', type=int,
                   help='stop after this many attempted cases')
    p.add_argument('--timeout', type=int, default=10,
                   help='per-case time limit in seconds (default: 10)')
    p.add_argument('--concrete-only', action='store_true',
                   help='skip cases with symbolic constants')
    p.add_argument('--check', action='store_true',
                   help='verify solved answers with the numerical oracle')
    p.add_argument('--check-timeout', type=int, default=60,
                   help='per-instantiation limit for --check (default: 60)')
    p.add_argument('--results',
                   help='append one JSON record per case to this file')
    p.add_argument('--sympy-path',
                   help='a sympy checkout to test instead of the installed one')
    p.add_argument('--list-engines', action='store_true',
                   help='list the available engines and exit')
    return p.parse_args(argv)


def classify(result, Integral, Piecewise, NonElementaryIntegral):
    """(classification, degenerate_branch_unevaluated) for a result."""
    if isinstance(result, NonElementaryIntegral) or \
            result.has(NonElementaryIntegral):
        return 'CLAIMS-NE', False
    generic = result
    if result.has(Piecewise):
        generic = result.replace(lambda e: isinstance(e, Piecewise),
                                 lambda e: e.args[0][0])
    degenerate = (generic is not result and result.has(Integral)
                  and not generic.has(Integral))
    if generic.has(Integral):
        return 'partial', degenerate
    return 'SOLVED', degenerate


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.sympy_path:
        sys.path.insert(0, args.sympy_path)

    from . import corpus, engines

    if args.list_engines:
        for name, engine in sorted(engines.registry().items()):
            status = 'ok' if engine.available \
                else 'UNAVAILABLE: ' + engine.unavailable_reason
            print('%-18s %-45s %s' % (name, engine.description, status))
        return 0

    engine = engines.get(args.engine)

    import sympy
    from sympy import Integral, Piecewise, latex
    from sympy.integrals.risch import NonElementaryIntegral

    if args.check:
        from .verify import check_case

    signal.signal(signal.SIGALRM,
                  lambda s, fr: (_ for _ in ()).throw(TimeoutError()))

    print('engine: %s (%s)' % (engine.name, engine.description))
    print('sympy:  %s from %s' % (sympy.__version__,
                                  sympy.__file__.rsplit('/', 2)[0]))

    stats: Counter = Counter()
    checks: Counter = Counter()
    n_seen = n_tried = 0
    t0 = time.time()
    results_fh = open(args.results, 'a', encoding='utf-8') \
        if args.results else None

    try:
        for case in corpus.load(args.suites, args.source_prefix):
            n_seen += 1
            f, x = case.f, case.x
            if args.concrete_only and f.free_symbols - {x}:
                continue
            if args.limit is not None and n_tried >= args.limit:
                break
            n_tried += 1

            t_case = time.time()
            reason = ''
            result = None
            signal.alarm(args.timeout)
            try:
                result = engine.call(f, x)
                cls, degenerate = classify(result, Integral, Piecewise,
                                           NonElementaryIntegral)
            except TimeoutError:
                cls, degenerate = 'timeout', False
            except NotImplementedError as e:
                cls, degenerate = 'NIE', False
                reason = str(e)[:160].replace('\n', ' ')
            except Exception as e:
                cls, degenerate = 'error:' + type(e).__name__, False
                reason = str(e)[:160].replace('\n', ' ')
            finally:
                signal.alarm(0)
            secs = round(time.time() - t_case, 3)
            stats[cls] += 1

            check = None
            if args.check and cls == 'SOLVED':
                try:
                    check = check_case(f, x, result, case.expected,
                                       timeout=args.check_timeout)
                except Exception as e:
                    check = {'verdict': 'CHECK-ERROR',
                             'error': type(e).__name__}
                checks[check['verdict']] += 1
                if check['verdict'] == 'WRONG':
                    print('  WRONG %s[%d] | %s' % (case.suite, case.index, f),
                          flush=True)

            if results_fh:
                record = {'suite': case.suite, 'source': case.source,
                          'index': case.index, 'engine': engine.name,
                          'integrand': case.integrand, 'latex': latex(f),
                          'cls': cls, 'reason': reason, 'secs': secs}
                if degenerate:
                    record['degenerate_unevaluated'] = True
                if result is not None:
                    record['result'] = str(result)
                if case.integral is not None:
                    record['expected'] = case.integral
                if check is not None:
                    record['check'] = check
                results_fh.write(json.dumps(record) + '\n')
                results_fh.flush()

            if n_tried % 100 == 0:
                print('  ...%d attempted, %.0f s' % (n_tried, time.time() - t0),
                      flush=True)
    finally:
        if results_fh:
            results_fh.close()

    dt = time.time() - t0
    print('\ncases seen %d, attempted %d, %.0f s' % (n_seen, n_tried, dt))
    total = sum(stats.values()) or 1
    for cls, n in stats.most_common():
        print('  %-22s %6d  %5.1f%%' % (cls, n, 100.0 * n / total))
    if checks:
        print('\nverification of solved cases:')
        for verdict, n in checks.most_common():
            print('  %-22s %6d' % (verdict, n))
    return 0


if __name__ == '__main__':
    sys.exit(main())
