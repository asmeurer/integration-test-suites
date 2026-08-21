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


@pytest.fixture
def results_file(tmp_path):
    records = [
        {'suite': 'hebisch', 'source': 'Hebisch rand3c.input, via 12000.org '
         'SYMPY_syntax.zip (Summer 2021)', 'index': 274, 'engine': 'risch',
         'cls': 'error:ValueError', 'reason': 'boom', 'secs': 0.1},
        {'suite': 'hebisch', 'source': 'Hebisch rand3c.input, via 12000.org '
         'SYMPY_syntax.zip (Summer 2021)', 'index': 3, 'engine': 'risch',
         'cls': 'SOLVED', 'reason': '', 'secs': 0.2, 'result': 'x**2',
         'check': {'verdict': 'WRONG'}},
        {'suite': 'hebisch', 'source': 'Hebisch rand3c.input, via 12000.org '
         'SYMPY_syntax.zip (Summer 2021)', 'index': 4, 'engine': 'risch',
         'cls': 'SOLVED', 'reason': '', 'secs': 0.3, 'result': 'x',
         'check': {'verdict': 'DERIV-OK'}},
    ]
    path = tmp_path / 'results.jsonl'
    path.write_text(''.join(json.dumps(r) + '\n' for r in records))
    return str(path)


def test_results_selects_recorded_cases(results_file, capsys):
    assert show.main(['--results', results_file, '--format', 'json']) == 0
    records = [json.loads(l) for l in capsys.readouterr().out.splitlines()]
    assert [r['index'] for r in records] == [3, 4, 274]
    assert records[0]['runs'][0]['check']['verdict'] == 'WRONG'
    assert records[0]['runs'][0]['file'] == 'results.jsonl'


def test_results_cls_matches_verdict_or_classification(results_file, capsys):
    assert show.main(['--results', results_file, '--cls', 'WRONG']) == 0
    out = capsys.readouterr().out
    assert out.startswith('hebisch[3]') and 'hebisch[4]' not in out
    assert '  run:       results.jsonl risch SOLVED WRONG 0.20s' in out
    assert '    result:  x**2' in out
    assert show.main(['--results', results_file, '--cls', 'error']) == 0
    out = capsys.readouterr().out
    assert out.startswith('hebisch[274]') and 'error:ValueError boom' in out


def test_results_intersects_with_selectors(results_file, capsys):
    assert show.main(['--results', results_file, 'hebisch', '4', '274']) == 0
    out = capsys.readouterr().out
    assert out.startswith('hebisch[4]') and 'hebisch[274]' in out
    assert 'hebisch[3]' not in out


def test_cls_requires_results(capsys):
    assert show.main(['hebisch', '3', '--cls', 'WRONG']) == 2
    assert show.main([]) == 2
