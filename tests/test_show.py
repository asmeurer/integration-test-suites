# -*- coding: utf-8 -*-
"""The show command finds the case a selector names and prints it."""
from __future__ import annotations

import json

import pytest

from integration_test_suites import show


def test_parse_selectors_forms():
    assert show.parse_selectors(['hebisch', '274', '1692']) == \
        {'hebisch': {274, 1692}}
    assert show.parse_selectors(['hebisch[274]', 'rubi:12']) == \
        {'hebisch': {274}, 'rubi': {12}}
    assert show.parse_selectors(['blake']) == {'blake': None}
    assert show.parse_selectors(['hebisch', '3-5', 'blake', '7']) == \
        {'hebisch': {3, 4, 5}, 'blake': {7}}


def test_parse_selectors_rejects_bare_index():
    with pytest.raises(ValueError):
        show.parse_selectors(['5'])


def test_show_by_index(capsys):
    assert show.main(['hebisch', '274']) == 0
    out = capsys.readouterr().out
    assert out.startswith('hebisch[274]  ')
    assert '  integrand: ' in out and '  integral:  ' in out


@pytest.mark.parametrize('fmt', show.FORMATS)
def test_formats(fmt, capsys):
    assert show.main(['mit_bee_official', '5', '--format', fmt]) == 0
    out = capsys.readouterr().out
    if fmt == 'json':
        record = json.loads(out)
        assert record['suite'] == 'mit_bee_official' and record['index'] == 5
    else:
        assert 'mit_bee_official[5]' in out
    if fmt == 'python':
        namespace = {}
        exec(out, namespace)
        assert 'F' in namespace


def test_definite_case_python_snippet(capsys):
    from integration_test_suites import corpus
    case = next(c for c in corpus.load(['mit_bee_official']) if c.is_definite)
    assert show.main(['mit_bee_official', str(case.index),
                      '--format', 'python']) == 0
    out = capsys.readouterr().out
    assert 'integrate(f, (x, ' in out


def test_rubi_index_matches_several_sources(capsys):
    """rubi indexes repeat per source file; every match is printed and
    --source-prefix narrows to one."""
    assert show.main(['rubi', '12', '--format', 'json']) == 0
    records = [json.loads(line) for line in
               capsys.readouterr().out.splitlines()]
    assert len(records) > 1
    assert all(r['index'] == 12 for r in records)
    assert len({r['source'] for r in records}) == len(records)
    prefix = records[0]['source'][:40]
    assert show.main(['rubi', '12', '--source-prefix', prefix,
                      '--format', 'json']) == 0
    narrowed = capsys.readouterr().out.splitlines()
    assert len(narrowed) < len(records)


def test_grep_and_limit(capsys):
    assert show.main(['blake', '--grep', r'\*\*\(1/3\)', '--limit', '2',
                      '--format', 'json']) == 0
    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == 2
    assert all('**(1/3)' in json.loads(l)['integrand'] for l in lines)


def test_missing_index_is_reported(capsys):
    assert show.main(['hebisch', '274', '999999']) == 1
    captured = capsys.readouterr()
    assert 'hebisch[274]' in captured.out
    assert 'hebisch[999999]' in captured.err


def test_unknown_suite(capsys):
    assert show.main(['nosuch', '1']) == 2
    assert 'no such suite' in capsys.readouterr().err
