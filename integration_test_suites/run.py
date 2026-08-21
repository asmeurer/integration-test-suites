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

Definite cases (those with bounds) are dispatched to the engine's
``call_definite`` entry point and their solved values are checked
against the suite's stated value, falling back to numerical quadrature.
Cases the engine has no entry point for are skipped and counted, not
failed.

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
    p.add_argument('--definite-only', action='store_true',
                   help='attempt only definite cases')
    p.add_argument('--indefinite-only', action='store_true',
                   help='attempt only indefinite cases')
    p.add_argument('--filter', action='append', dest='filters', default=[],
                   help='named case filter or preset; repeatable, combined '
                        'with and. See --list-filters')
    p.add_argument('--list-filters', action='store_true',
                   help='list the available filters and presets and exit')
    p.add_argument('--check', action='store_true',
                   help='verify solved answers with the numerical oracle')
    p.add_argument('--check-timeout', type=int, default=60,
                   help='per-instantiation limit for --check (default: 60)')
    p.add_argument('--results',
                   help='append one JSON record per case to this file')
    p.add_argument('--sympy-path',
                   help='a sympy checkout to test instead of the installed one')
    p.add_argument('--isolate', action='store_true',
                   help='run each case in a forked child process so that the '
                        'time limit is enforced even when the work is inside '
                        'an uninterruptible C call')
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


def evaluate(engine, case, args, deps) -> dict:
    """Run one case and classify it; the unit of work --isolate forks."""
    Integral, Piecewise, NonElementaryIntegral, checkers = deps
    f, x = case.f, case.x
    out: dict = {'reason': '', 'result': None, 'check': None,
                 'degenerate': False}
    t_case = time.time()
    signal.alarm(args.timeout)
    try:
        if case.is_definite:
            a, b = case.bounds
            result = engine.call_definite(f, x, a, b)
        else:
            result = engine.call(f, x)
        out['cls'], out['degenerate'] = classify(
            result, Integral, Piecewise, NonElementaryIntegral)
        out['result'] = str(result)
    except TimeoutError:
        result, out['cls'] = None, 'timeout'
    except NotImplementedError as e:
        result, out['cls'] = None, 'NIE'
        out['reason'] = str(e)[:160].replace('\n', ' ')
    except Exception as e:
        result, out['cls'] = None, 'error:' + type(e).__name__
        out['reason'] = str(e)[:160].replace('\n', ' ')
    finally:
        signal.alarm(0)

    if checkers is not None and out['cls'] == 'SOLVED':
        check_case, check_value = checkers
        signal.alarm(args.check_timeout)
        try:
            if case.is_definite:
                a, b = case.bounds
                out['check'] = check_value(f, x, a, b, result,
                                           case.expected_value)
            else:
                out['check'] = check_case(f, x, result, case.expected,
                                          timeout=args.check_timeout)
        except TimeoutError:
            out['check'] = {'verdict': 'TIMEOUT'}
        except Exception as e:
            out['check'] = {'verdict': 'CHECK-ERROR', 'error': type(e).__name__}
        finally:
            signal.alarm(0)
    out['secs'] = round(time.time() - t_case, 3)
    return out


def evaluate_isolated(engine, case, args, deps) -> dict:
    """evaluate() in a forked child, killed if it overruns its budget.

    A SIGALRM only lands between bytecodes, so a case that disappears
    into a long C-level computation -- an astronomically large evalf, for
    instance -- ignores the in-process time limit entirely.  Running the
    case in a child and killing it is the only hard bound.
    """
    import multiprocessing as mp

    ctx = mp.get_context('fork')
    queue = ctx.Queue()

    def worker():
        signal.signal(signal.SIGALRM,
                      lambda s, fr: (_ for _ in ()).throw(TimeoutError()))
        queue.put(evaluate(engine, case, args, deps))

    proc = ctx.Process(target=worker)
    budget = args.timeout + (args.check_timeout if deps[3] is not None else 0)
    t0 = time.time()
    proc.start()
    proc.join(budget + 5)
    if proc.is_alive():
        proc.terminate()
        proc.join(5)
        if proc.is_alive():
            proc.kill()
            proc.join()
        return {'cls': 'timeout', 'reason': 'hard timeout (child killed)',
                'result': None, 'check': None, 'degenerate': False,
                'secs': round(time.time() - t0, 3)}
    if queue.empty():
        return {'cls': 'error:ChildDied', 'reason': 'child produced no result',
                'result': None, 'check': None, 'degenerate': False,
                'secs': round(time.time() - t0, 3)}
    return queue.get()


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.sympy_path:
        sys.path.insert(0, args.sympy_path)

    from . import corpus, engines, filters

    if args.list_filters:
        print('filters:')
        for name in sorted(filters.FILTERS):
            print('  %s' % name)
        print('presets:')
        for name, expansion in sorted(filters.PRESETS.items()):
            print('  %-22s %s' % (name, ' + '.join(expansion)))
        return 0

    if args.list_engines:
        for name, engine in sorted(engines.registry().items()):
            status = 'ok' if engine.available \
                else 'UNAVAILABLE: ' + engine.unavailable_reason
            print('%-18s %-45s %s' % (name, engine.description, status))
        return 0

    engine = engines.get(args.engine)
    active_filters = filters.expand(args.filters)

    import sympy
    from sympy import Integral, Piecewise, latex
    from sympy.integrals.risch import NonElementaryIntegral

    checkers = None
    if args.check:
        from .verify import check_case, check_value
        checkers = (check_case, check_value)
    deps = (Integral, Piecewise, NonElementaryIntegral, checkers)
    runner = evaluate_isolated if args.isolate else evaluate

    signal.signal(signal.SIGALRM,
                  lambda s, fr: (_ for _ in ()).throw(TimeoutError()))

    print('engine: %s (%s)' % (engine.name, engine.description))
    if active_filters:
        print('filters: %s' % ', '.join(active_filters))
    print('sympy:  %s from %s' % (sympy.__version__,
                                  sympy.__file__.rsplit('/', 2)[0]))

    stats: Counter = Counter()
    checks: Counter = Counter()
    n_seen = n_tried = n_filtered = n_unsupported = 0
    t0 = time.time()
    results_fh = open(args.results, 'a', encoding='utf-8') \
        if args.results else None

    try:
        for case in corpus.load(args.suites, args.source_prefix):
            n_seen += 1
            if (args.definite_only and not case.is_definite) or \
                    (args.indefinite_only and case.is_definite):
                continue
            supported = engine.call_definite if case.is_definite \
                else engine.call
            if supported is None:
                n_unsupported += 1
                continue
            f, x = case.f, case.x
            if args.concrete_only and f.free_symbols - {x}:
                continue
            if active_filters and not filters.accepts(active_filters, f, x):
                n_filtered += 1
                continue
            if args.limit is not None and n_tried >= args.limit:
                break
            n_tried += 1

            outcome = runner(engine, case, args, deps)
            cls = outcome['cls']
            secs = outcome['secs']
            reason = outcome['reason']
            degenerate = outcome['degenerate']
            result = outcome['result']
            check = outcome['check']
            stats[cls] += 1
            if check is not None:
                checks[check['verdict']] += 1
                if check['verdict'] == 'WRONG':
                    print('  WRONG %s[%d] | %s'
                          % (case.suite, case.index, case.integrand[:120]),
                          flush=True)

            if results_fh:
                record = {'suite': case.suite, 'source': case.source,
                          'index': case.index, 'engine': engine.name,
                          'integrand': case.integrand, 'latex': latex(f),
                          'cls': cls, 'reason': reason, 'secs': secs}
                if case.is_definite:
                    record['lower'] = case.lower
                    record['upper'] = case.upper
                if degenerate:
                    record['degenerate_unevaluated'] = True
                if result is not None:
                    record['result'] = result
                if case.integral is not None:
                    record['expected'] = case.integral
                if case.value is not None:
                    record['expected_value'] = case.value
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
    print('\ncases seen %d, filtered out %d, attempted %d, %.0f s'
          % (n_seen, n_filtered, n_tried, dt))
    if n_unsupported:
        print('skipped %d cases the engine has no entry point for '
              '(definite vs. indefinite)' % n_unsupported)
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
