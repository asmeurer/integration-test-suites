# -*- coding: utf-8 -*-
"""Checks that the vendored corpus loads and means what it says.

These are deliberately cheap: they sample each suite rather than
sympifying all of it, so that the suite stays runnable in CI while still
catching a suite whose expressions use a token sympify cannot read.
"""
from __future__ import annotations

import json

import pytest
from sympy import Expr, Symbol

from integration_test_suites import corpus
from integration_test_suites.case import IntegrationTestCase
from integration_test_suites.dedupe import canonical_key

SAMPLE = 20


def sample_cases(suite: str) -> list[IntegrationTestCase]:
    """Up to SAMPLE cases spread across the suite's files."""
    picked = []
    for path in corpus.suite_files(suite):
        for n, case in enumerate(corpus.load_file(path)):
            if n >= 3:
                break
            picked.append(case)
            if len(picked) >= SAMPLE:
                return picked
    return picked


def test_suites_exist():
    assert corpus.suites(), 'no suites found under data/'


@pytest.mark.parametrize('suite', corpus.suites())
def test_suite_has_cases(suite):
    assert corpus.suite_files(suite), 'suite %s has no jsonl files' % suite


@pytest.mark.parametrize('suite', corpus.suites())
def test_sample_sympifies(suite):
    cases = sample_cases(suite)
    assert cases, 'suite %s yielded no cases' % suite
    for case in cases:
        assert isinstance(case.f, Expr)
        assert isinstance(case.x, Symbol)
        assert case.x in case.f.free_symbols or not case.f.free_symbols
        if case.integral is not None:
            assert isinstance(case.expected, Expr)
        for alt in case.alternatives:
            assert isinstance(alt, Expr)


@pytest.mark.parametrize('suite', corpus.suites())
def test_sample_hashes(suite):
    for case in sample_cases(suite):
        assert len(canonical_key(case)) == 32


@pytest.mark.parametrize('suite', corpus.suites())
def test_records_round_trip(suite):
    for case in sample_cases(suite):
        assert IntegrationTestCase.from_json(case.to_json()) == case


@pytest.mark.parametrize('suite', corpus.suites())
def test_every_line_is_valid_json(suite):
    """Cheap enough to run over the whole suite, unlike sympify."""
    for path in corpus.suite_files(suite):
        with open(path, encoding='utf-8') as fh:
            for lineno, line in enumerate(fh, 1):
                if not line.strip():
                    continue
                record = json.loads(line)
                assert record['suite'] == suite, \
                    '%s:%d claims suite %r' % (path, lineno, record['suite'])
                assert 'integrand' in record and 'variable' in record


@pytest.mark.parametrize('suite', corpus.suites())
def test_provenance_present(suite):
    import os
    path = os.path.join(corpus.DATA_DIR, suite, 'PROVENANCE.md')
    assert os.path.exists(path), 'suite %s has no PROVENANCE.md' % suite
