# -*- coding: utf-8 -*-
"""Print corpus cases selected by suite and index.

    python -m integration_test_suites.show hebisch 274 1692
    python -m integration_test_suites.show 'hebisch[274]' 'rubi[12]'
    python -m integration_test_suites.show hebisch:274 --format python
    python -m integration_test_suites.show rubi 12 --source-prefix '4 Trig'
    python -m integration_test_suites.show blake --grep '\*\*\(1/3\)' --limit 5

A selector is ``suite[index]``, ``suite:index`` (the same thing without
the shell-hostile brackets), or a suite name followed by indexes and
inclusive ranges like ``10-20``.  A suite name alone selects the whole
suite, which is the pipe-friendly way to stream it.

Indexes are unique within the ``hebisch``, ``blake`` and ``mit_bee*``
suites but only within a *source file* of ``rubi`` and ``independent``,
so a selector there can match several cases; every match is printed,
each headed by its source, and ``--source-prefix`` narrows to one.
"""
from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Iterator

FORMATS = ('text', 'pretty', 'latex', 'json', 'python')

_SPEC = re.compile(r'^(?P<suite>[A-Za-z_][\w]*)(?:\[(?P<a>\d+)\]|:(?P<b>\d+))$')
_RANGE = re.compile(r'^(?P<lo>\d+)(?:-(?P<hi>\d+))?$')


def parse_selectors(tokens: list[str]) -> dict[str, set[int] | None]:
    """Map each selected suite to its indexes, or None for "all of it"."""
    selected: dict[str, set[int]] = {}
    current = None
    for tok in tokens:
        m = _SPEC.match(tok)
        if m:
            current = m.group('suite')
            index = int(m.group('a') or m.group('b'))
            selected.setdefault(current, set()).add(index)
            continue
        m = _RANGE.match(tok)
        if m:
            if current is None:
                raise ValueError('index %r given before any suite name' % tok)
            lo = int(m.group('lo'))
            hi = int(m.group('hi') or lo)
            if hi < lo:
                raise ValueError('empty range %r' % tok)
            selected.setdefault(current, set()).update(range(lo, hi + 1))
            continue
        current = tok
        selected.setdefault(current, set())
    return {suite: indexes or None for suite, indexes in selected.items()}


def select(selected, source_prefix=None, grep=None, limit=None) -> Iterator:
    from . import corpus

    pattern = re.compile(grep) if grep else None
    n = 0
    for suite, indexes in selected.items():
        for case in corpus.load([suite], source_prefix):
            if indexes is not None and case.index not in indexes:
                continue
            if pattern and not pattern.search(case.integrand):
                continue
            yield case
            n += 1
            if limit is not None and n >= limit:
                return


def _integral(case):
    from sympy import Integral

    if case.is_definite:
        return Integral(case.f, (case.x, *case.bounds))
    return Integral(case.f, case.x)


def render(case, fmt: str) -> str:
    head = '%s[%d]  %s' % (case.suite, case.index, case.source)
    if fmt == 'json':
        return case.to_json()
    if fmt == 'text':
        lines = [head, '  integrand: %s' % case.integrand,
                 '  variable:  %s' % case.variable]
        if case.is_definite:
            lines.append('  bounds:    %s .. %s' % (case.lower, case.upper))
        if case.integral is not None:
            lines.append('  integral:  %s' % case.integral)
        for alt in case.alt_integrals:
            lines.append('  alt:       %s' % alt)
        if case.value is not None:
            lines.append('  value:     %s' % case.value)
        if case.num_steps is not None:
            lines.append('  num_steps: %d' % case.num_steps)
        return '\n'.join(lines)
    if fmt == 'pretty':
        from sympy import pretty

        parts = [head, pretty(_integral(case))]
        if case.expected is not None:
            parts += ['=', pretty(case.expected)]
        if case.expected_value is not None:
            parts += ['=', pretty(case.expected_value)]
        return '\n'.join(parts)
    if fmt == 'latex':
        from sympy import latex

        out = latex(_integral(case))
        if case.expected is not None:
            out += ' = ' + latex(case.expected)
        if case.expected_value is not None:
            out += ' = ' + latex(case.expected_value)
        return '%s\n%s' % (head, out)
    if fmt == 'python':
        # A self-contained snippet: sympify the stored strings (so that
        # `x` and any constants are the symbols the corpus means), then
        # integrate; the expected answer is attached as a comment.
        lines = ['# %s' % head,
                 'from sympy import *',
                 'x = Symbol(%r)' % case.variable,
                 'f = sympify(%r)' % case.integrand]
        if case.is_definite:
            lines.append('F = integrate(f, (x, sympify(%r), sympify(%r)))'
                         % (case.lower, case.upper))
        else:
            lines.append('F = integrate(f, x)')
        if case.integral is not None:
            lines.append('# expected: %s' % case.integral)
        if case.value is not None:
            lines.append('# expected value: %s' % case.value)
        return '\n'.join(lines)
    raise ValueError('unknown format %r' % fmt)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog='python -m integration_test_suites.show',
        description=__doc__.split('\n\n')[0],
        epilog='Selectors: SUITE, SUITE INDEX..., SUITE LO-HI, SUITE:INDEX, '
               'or SUITE[INDEX] (quote the brackets in zsh).')
    p.add_argument('selectors', nargs='+', metavar='SELECTOR',
                   help='a suite name, an index or LO-HI range of the '
                        'preceding suite, or suite[index] / suite:index')
    p.add_argument('--source-prefix',
                   help='restrict to cases whose source starts with this '
                        '(needed to pick one of several rubi/independent '
                        'cases sharing an index)')
    p.add_argument('--grep', metavar='REGEX',
                   help='restrict to cases whose integrand text matches')
    p.add_argument('--limit', type=int,
                   help='stop after this many cases')
    p.add_argument('--format', choices=FORMATS, default='text',
                   help='text (stored strings), pretty (sympy pprint), '
                        'latex, json (the corpus record), or python '
                        '(a self-contained reproduction snippet); '
                        'default: text')
    p.add_argument('--sympy-path',
                   help='a sympy checkout to use for pretty/latex output')
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.sympy_path:
        sys.path.insert(0, args.sympy_path)

    from . import corpus

    try:
        selected = parse_selectors(args.selectors)
    except ValueError as e:
        print('error: %s' % e, file=sys.stderr)
        return 2
    unknown = [s for s in selected if s not in corpus.suites()]
    if unknown:
        print('error: no such suite: %s (have: %s)'
              % (', '.join(unknown), ', '.join(corpus.suites())),
              file=sys.stderr)
        return 2

    seen: dict[str, set[int]] = {s: set() for s in selected}
    n = 0
    for case in select(selected, args.source_prefix, args.grep, args.limit):
        if n and args.format != 'json':
            print()
        print(render(case, args.format))
        seen[case.suite].add(case.index)
        n += 1

    missing = []
    for suite, indexes in selected.items():
        if indexes is None:
            continue
        missing += ['%s[%d]' % (suite, i)
                    for i in sorted(indexes - seen[suite])]
    if missing and args.limit is None:
        print('no case matched: %s' % ', '.join(missing), file=sys.stderr)
        return 1
    if n == 0:
        print('no case matched', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except BrokenPipeError:
        # The reader (``| head``) went away; exit quietly instead of
        # tracing back into a closed stdout.
        import os
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        sys.exit(1)
