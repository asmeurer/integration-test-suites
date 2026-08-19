# -*- coding: utf-8 -*-
"""Discovery and loading of the vendored suites.

The corpus lives in ``data/<suite>/*.jsonl``, one JSON record per line in
the schema of :class:`~integration_test_suites.case.IntegrationTestCase`,
and one directory per suite so that a suite can be added or dropped
without touching any other.  Each suite directory carries a
``PROVENANCE.md`` recording where its problems came from and under what
license they are redistributed here.
"""
from __future__ import annotations

import os
from collections.abc import Iterator

from .case import IntegrationTestCase

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), 'data')


def suites() -> list[str]:
    """Names of the available suites, in directory order."""
    if not os.path.isdir(DATA_DIR):
        return []
    return sorted(d for d in os.listdir(DATA_DIR)
                  if os.path.isdir(os.path.join(DATA_DIR, d)))


def suite_files(suite: str) -> list[str]:
    """Absolute paths of the JSONL files making up ``suite``."""
    root = os.path.join(DATA_DIR, suite)
    if not os.path.isdir(root):
        raise ValueError('no such suite: %s (have: %s)'
                         % (suite, ', '.join(suites())))
    found = []
    for dirpath, _, filenames in os.walk(root):
        found.extend(os.path.join(dirpath, f) for f in filenames
                     if f.endswith('.jsonl'))
    return sorted(found)


def load_file(path: str) -> Iterator[IntegrationTestCase]:
    with open(path, encoding='utf-8') as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield IntegrationTestCase.from_json(line)


def load(suite_names: list[str] | None = None,
         source_prefix: str | None = None) -> Iterator[IntegrationTestCase]:
    """Iterate cases from the named suites (default: all of them).

    ``source_prefix`` further restricts to cases whose ``source`` starts
    with the given string, which is how a single chapter or problem file
    is selected.
    """
    for suite in (suite_names if suite_names is not None else suites()):
        for path in suite_files(suite):
            for case in load_file(path):
                if source_prefix and not case.source.startswith(source_prefix):
                    continue
                yield case


def counts() -> dict[str, int]:
    """Number of cases in each suite."""
    return {suite: sum(1 for _ in load([suite])) for suite in suites()}
