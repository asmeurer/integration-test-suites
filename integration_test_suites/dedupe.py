# -*- coding: utf-8 -*-
"""Find problems that occur in more than one place in the corpus.

Deduplication here is deliberately non-destructive.  It writes a
manifest of duplicate clusters and never rewrites a suite: the same
integrand appearing in two suites usually carries two different expected
antiderivatives and two different step counts, both worth keeping, and a
suite has to stay removable by deleting its directory.

Two cases are considered the same problem when their integrands are
structurally identical after the integration variable is renamed to a
common symbol.  This is exact structural matching on the sympy
expression tree, so it collapses cases that differ only in the name of
the integration variable or in the automatic rewriting sympify already
does, and it does not collapse forms that are merely mathematically
equal.  A ``simplify``-based comparison would catch more, but is not
affordable over a corpus this size and would not be reproducible across
sympy versions.

Usage:
    python -m integration_test_suites.dedupe [output.json]
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from collections import Counter, defaultdict

from sympy import Symbol, srepr

from . import corpus
from .case import IntegrationTestCase

#: The integration variable is renamed to this before hashing so that
#: the same problem in u and in x compares equal.
CANONICAL_VAR = Symbol('_integration_variable')


def canonical_key(case: IntegrationTestCase) -> str:
    """A hash of the integrand, canonical in the integration variable.

    A definite case hashes its bounds too, so the same integrand as an
    indefinite problem and over an interval stay distinct problems.
    """
    normalized = case.f.xreplace({case.x: CANONICAL_VAR})
    text = srepr(normalized)
    if case.is_definite:
        a, b = case.bounds
        text += '|%s|%s' % (srepr(a), srepr(b))
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:32]


def build(progress_every: int = 5000) -> dict:
    """Group every case in the corpus by canonical key."""
    clusters: dict[str, list[IntegrationTestCase]] = defaultdict(list)
    n_failed = 0
    failures = []
    for n, case in enumerate(corpus.load(), 1):
        try:
            clusters[canonical_key(case)].append(case)
        except Exception as e:
            n_failed += 1
            failures.append({'suite': case.suite, 'source': case.source,
                             'index': case.index,
                             'error': '%s: %s' % (type(e).__name__,
                                                  str(e)[:120])})
        if progress_every and n % progress_every == 0:
            print('  ...%d cases, %d distinct' % (n, len(clusters)),
                  flush=True)
    return {'clusters': clusters, 'unhashable': failures,
            'n_unhashable': n_failed}


def report(built: dict) -> dict:
    """Summary statistics and the duplicate clusters themselves."""
    clusters = built['clusters']
    total = sum(len(v) for v in clusters.values())
    dup_clusters = {k: v for k, v in clusters.items() if len(v) > 1}

    within = Counter()
    across = Counter()
    for cases in dup_clusters.values():
        suites = sorted({c.suite for c in cases})
        if len(suites) == 1:
            within[suites[0]] += len(cases) - 1
        else:
            for i, a in enumerate(suites):
                for b in suites[i + 1:]:
                    across['%s & %s' % (a, b)] += 1

    listed = []
    for key, cases in sorted(dup_clusters.items(),
                             key=lambda kv: -len(kv[1])):
        listed.append({
            'key': key,
            'integrand': cases[0].integrand,
            'count': len(cases),
            'occurrences': [{'suite': c.suite, 'source': c.source,
                             'index': c.index} for c in cases],
        })

    return {
        'totals': {
            'cases': total,
            'distinct_problems': len(clusters),
            'redundant_cases': total - len(clusters),
            'clusters_with_duplicates': len(dup_clusters),
            'unhashable_cases': built['n_unhashable'],
        },
        'per_suite_case_counts': {s: n for s, n in
                                  sorted(Counter(
                                      c.suite for v in clusters.values()
                                      for c in v).items())},
        'duplicates_within_suite': dict(within.most_common()),
        'duplicates_across_suites': dict(across.most_common()),
        'unhashable': built['unhashable'],
        'clusters': listed,
    }


def main() -> None:
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        corpus.DATA_DIR, 'DUPLICATES.json')
    built = build()
    result = report(built)
    with open(out, 'w', encoding='utf-8') as fh:
        json.dump(result, fh, indent=2)
    print(json.dumps({k: v for k, v in result.items()
                      if k not in ('clusters', 'unhashable')}, indent=2))
    print('\nwrote %s' % out)


if __name__ == '__main__':
    main()
