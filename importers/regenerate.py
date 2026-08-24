# -*- coding: utf-8 -*-
"""Regenerate the entire corpus from its upstream sources, one command.

Runs every importer and then the duplicate finder, so that an upstream
update (a new Rubi release, say) needs no manual work: the importers
carry their own correction tables and each correction is verified at
import time — a source that shifts under a table fails the run loudly
instead of emitting bad data.

The Rubi/independent suites come from a checkout of Bonazzi's
rubi-integration-test-suite; the Hebisch/Blake suites from Nasser
Abbasi's frozen Summer 2021 SYMPY_syntax.zip, downloaded automatically
when no extracted directory is given (the site needs a browser user
agent); the MIT Bee suites are embedded in their importers.

After regenerating, run the answer audit
(``python -m integration_test_suites.validate``) and the tests
(``pytest``): the audit is how a translation bug in new upstream data
shows up, as a crop of unproven answers rather than wrong test data.

Usage:
    python importers/regenerate.py --rubi <rubi-test-suite-checkout> \\
        [--nasser <extracted-SYMPY-dir>]
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
import urllib.request

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMPORTERS = os.path.join(HERE, 'importers')

NASSER_ZIP_URL = ('https://www.12000.org/my_notes/CAS_integration_tests/'
                  'reports/summer_2021/input/SYMPY_syntax.zip')


def run(script: str, *args: str) -> None:
    cmd = [sys.executable, os.path.join(IMPORTERS, script), *args]
    print('==> %s' % ' '.join(cmd[1:]), flush=True)
    subprocess.run(cmd, check=True, cwd=HERE)


def fetch_nasser(dest: str) -> str:
    """Download and extract SYMPY_syntax.zip; the SYMPY dir path."""
    import zipfile

    zip_path = os.path.join(dest, 'SYMPY_syntax.zip')
    print('==> downloading %s' % NASSER_ZIP_URL, flush=True)
    request = urllib.request.Request(NASSER_ZIP_URL,
                                     headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(request) as resp, open(zip_path, 'wb') as fh:
        fh.write(resp.read())
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(dest)
    return os.path.join(dest, 'SYMPY')


def main() -> int:
    parser = argparse.ArgumentParser(
        prog='python importers/regenerate.py',
        description=__doc__.split('\n\n')[0])
    parser.add_argument('--rubi', required=True, metavar='DIR',
                        help='checkout of rubi-integration-test-suite')
    parser.add_argument('--nasser', metavar='DIR',
                        help='extracted SYMPY_syntax.zip directory '
                             '(downloaded automatically if omitted)')
    args = parser.parse_args()

    with tempfile.TemporaryDirectory() as tmp:
        nasser = args.nasser or fetch_nasser(tmp)
        run('from_rubi_modules.py', os.path.abspath(args.rubi))
        run('from_nasser_sympy.py', os.path.abspath(nasser))
        run('mit_bee.py')
        run('mit_bee_official.py')

    print('==> dedupe', flush=True)
    subprocess.run([sys.executable, '-m', 'integration_test_suites.dedupe'],
                   check=True, cwd=HERE)
    print('\nDone. Now audit the answers (validate) and run pytest.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
