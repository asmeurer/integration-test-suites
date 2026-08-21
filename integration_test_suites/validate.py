# -*- coding: utf-8 -*-
"""Check the corpus against itself: is every expected answer correct?

For each case that carries an expected antiderivative F, this tries to
prove D(F) == f symbolically.  For each definite case that carries an
expected value, it compares the value against numerical quadrature of
the integrand; a clear disagreement is reported as ``mismatch``.  It is
a one-time audit of the data rather than a measurement of any
integrator, and it is worth running after any change to the importers,
because a translation bug shows up here as a sudden crop of unproven
answers.

An unproven case is not necessarily wrong: the rewriters are one-sided,
quadrature can fail to converge, and a genuinely correct answer in an
awkward form can defeat them.  The output lists the unproven cases so
they can be examined; the numerical oracle in
:mod:`integration_test_suites.verify` is what settles those.

Usage:
    python -m integration_test_suites.validate [--suite blake] \\
        [--jobs 8] [--timeout 20] [--results unproven.jsonl]
"""
from __future__ import annotations

import argparse
import json
import signal
import sys
import time
from collections import Counter


def _raise_timeout(signum, frame):
    raise TimeoutError()


def _init_worker() -> None:
    signal.signal(signal.SIGALRM, _raise_timeout)


def _check_one(task):
    """(suite, index, integrand, variable, integral, bounds_value,
    timeout, deep) -> rec.

    ``integral`` drives the symbolic derivative proof;
    ``bounds_value`` is ``(lower, upper, value)`` for a definite case
    with a stated value, driving the quadrature comparison.  A case
    carrying both must pass both.
    """
    suite, index, integrand, variable, integral, bounds_value, \
        timeout, deep = task
    from sympy import Symbol, sympify

    from .verify import _quad_matches, prove_derivative

    signal.alarm(timeout)
    verdicts = []
    try:
        x = Symbol(variable)
        f = sympify(integrand)
        if integral is not None:
            F = sympify(integral)
            step = prove_derivative(f, x, F, deep=deep)
            verdicts.append('proven:' + step if step else 'unproven')
        if bounds_value is not None:
            lower, upper, value = bounds_value
            m = _quad_matches(f, x, sympify(lower), sympify(upper),
                              sympify(value))
            verdicts.append({'eq': 'proven:quad', 'neq': 'mismatch',
                             'undecided': 'unproven'}[m])
        for bad in ('mismatch', 'unproven'):
            if bad in verdicts:
                verdict = bad
                break
        else:
            verdict = verdicts[0]
    except TimeoutError:
        verdict = 'timeout'
    except Exception as e:
        verdict = 'error:' + type(e).__name__
    finally:
        signal.alarm(0)
    return {'suite': suite, 'index': index, 'verdict': verdict,
            'integrand': integrand, 'integral': integral,
            'bounds_value': bounds_value}


def _check_one_isolated(task):
    """_check_one in a forked child, killed if it overruns.

    A SIGALRM lands only between bytecodes, so a case that disappears
    into a long C-level computation ignores the in-process limit; killing
    a child is the only hard bound.
    """
    import multiprocessing as mp

    timeout = task[6]
    ctx = mp.get_context('fork')
    queue = ctx.Queue()

    def worker():
        _init_worker()
        queue.put(_check_one(task))

    proc = ctx.Process(target=worker)
    proc.start()
    proc.join(timeout + 5)
    if proc.is_alive():
        proc.terminate()
        proc.join(3)
        if proc.is_alive():
            proc.kill()
            proc.join()
        return {'suite': task[0], 'index': task[1], 'verdict': 'timeout',
                'integrand': task[2], 'integral': task[4],
                'bounds_value': task[5]}
    if queue.empty():
        return {'suite': task[0], 'index': task[1], 'verdict': 'error:ChildDied',
                'integrand': task[2], 'integral': task[4],
                'bounds_value': task[5]}
    return queue.get()


def parse_args(argv=None):
    p = argparse.ArgumentParser(
        prog='python -m integration_test_suites.validate',
        description=__doc__.split('\n\n')[0])
    p.add_argument('--suite', action='append', dest='suites',
                   help='restrict to this suite; repeatable')
    p.add_argument('--shard', default='0/1', metavar='I/N',
                   help='process only shard I of N, so that several '
                        'independent processes can split the work '
                        '(default: 0/1)')
    p.add_argument('--timeout', type=int, default=20,
                   help='per-case time limit in seconds (default: 20)')
    p.add_argument('--limit', type=int, help='stop after this many cases')
    p.add_argument('--results', help='write one JSON record per case here')
    p.add_argument('--deep', action='store_true',
                   help='also try simplify(), which is much slower but '
                        'settles cases cancel() and fu() cannot')
    p.add_argument('--no-isolate', action='store_true',
                   help='do not fork per case (faster, but a case stuck in a '
                        'C-level call will hang the run)')
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    from . import corpus

    shard_i, shard_n = (int(v) for v in args.shard.split('/'))
    _init_worker()

    tasks = []
    n_no_answer = Counter()
    for seen, case in enumerate(corpus.load(args.suites)):
        bounds_value = (case.lower, case.upper, case.value) \
            if case.is_definite and case.value is not None else None
        if case.integral is None and bounds_value is None:
            n_no_answer[case.suite] += 1
            continue
        if seen % shard_n != shard_i:
            continue
        tasks.append((case.suite, case.index, case.integrand, case.variable,
                      case.integral, bounds_value, args.timeout, args.deep))
        if args.limit and len(tasks) >= args.limit:
            break

    print('cases with an expected answer: %d' % len(tasks))
    print('cases without one (skipped):   %d %s'
          % (sum(n_no_answer.values()), dict(n_no_answer)))

    per_suite: dict[str, Counter] = {}
    overall: Counter = Counter()
    t0 = time.time()
    check = _check_one if args.no_isolate else _check_one_isolated
    fh = open(args.results, 'w', encoding='utf-8') if args.results else None
    try:
        for n, task in enumerate(tasks, 1):
            rec = check(task)
            bucket = rec['verdict'].split(':')[0]
            overall[rec['verdict']] += 1
            per_suite.setdefault(rec['suite'], Counter())[bucket] += 1
            if fh and bucket != 'proven':
                fh.write(json.dumps(rec) + '\n')
                fh.flush()
            if n % 200 == 0:
                ok = sum(v for k, v in overall.items()
                         if k.startswith('proven'))
                print('  ...%d checked, %d proven, %.0f s'
                      % (n, ok, time.time() - t0), flush=True)
    finally:
        if fh:
            fh.close()

    print('\nchecked %d answers in %.0f s\n' % (sum(overall.values()),
                                                time.time() - t0))
    print('| suite | proven | unproven | mismatch | timeout | error |')
    print('|---|---|---|---|---|---|')
    for suite in sorted(per_suite):
        c = per_suite[suite]
        print('| %s | %d | %d | %d | %d | %d |' % (suite, c['proven'],
              c['unproven'], c['mismatch'], c['timeout'], c['error']))
    print('\nby proof step:')
    for verdict, n in overall.most_common():
        print('  %-22s %6d' % (verdict, n))
    return 0


if __name__ == '__main__':
    sys.exit(main())
