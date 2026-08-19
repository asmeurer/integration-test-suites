# -*- coding: utf-8 -*-
"""The MIT Integration Bee problems Nasser Abbasi reported unsolved.

Source: https://github.com/sympy/sympy/discussions/24843 , where Nasser
Abbasi posted the integrands from the MIT Integration Bee
(https://math.mit.edu/~yyao1/integrationbee.html) that sympy 1.11.1
could not integrate.  All of them are stated there to have known
antiderivatives; the post lists only the integrands, so these cases
carry no expected answer and a runner can only report whether an engine
returns something closed form.

The problems are stored below exactly as posted, in Maple syntax, and
translated on import; keeping the posted text verbatim in the source is
what makes the translation auditable against the original.

Usage:
    python importers/mit_bee.py
"""
from __future__ import annotations

import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

from integration_test_suites.case import IntegrationTestCase  # noqa: E402

SOURCE = ('MIT Integration Bee, via sympy/sympy discussion 24843'
          ' (integrands unsolved by sympy 1.11.1)')

MAPLE_INTEGRANDS = """
sqrt(tan(x))
ln(x+1)/(x^2+1)
x^(1/2)/(x^(1/2)-x^(1/3))
1/(sin(x)+sec(x))
1/(1+exp(x)+exp(2*x))^(1/2)
(csc(x)-sin(x))^(1/2)
1/(9*cos(x)^2+4*sin(x)^2)
(x/(-x^3+1))^(1/2)
sin(101*x)*sin(x)^99
((1-x)/(x+1))^(1/2)
1/(1+x^(1/2))/(-x^2+x)^(1/2)
x^(1/2)/((2012-x)^(1/2)+x^(1/2))
(-1+x)/(x+1)/(x^3+x^2+x)^(1/2)
(csc(x)-sin(x))^(1/2)
sin(x)*(1+tan(x)^2)^(1/2)
x*sec(4*x)^2
1/(1-ln(1-x))
exp(sin(x))/tan(x)/csc(x)
(csc(x)-sin(x))^(1/2)
1/(sin(x)^4+cos(x)^4)
(1+2*x*exp(x^2))*cos(x)-(x+exp(x^2))*sin(x)
arccosh(x)
tanh(x)/exp(x)
(1+sin(x))^(1/2)
sin(x+1/4*Pi)^2/exp(x^2)
cos(x)/(1-cos(2*x))
(2018*x^2017+2017*x^2016)/(x^4036+2*x^4035+x^4034+1)
1/(x^(41/25)+x^(9/25))
1/(x^(3/2)-x^2)^(1/2)
exp(x+exp(x))+exp(x-exp(x))
(sin(20*x)+sin(19*x))/(cos(20*x)+cos(19*x))
(arctan(x)+arccot(x))/x
x/((-1+x)^(1/2)+(x+1)^(1/2))
sin(x+sin(x))-sin(x-sin(x))
1/(1+sin(x))+1/(1+cos(x))+1/(tan(x)+1)+1/(1+cot(x))+1/(1+sec(x))+1/(1+csc(x))
(x+exp(1)+1)*x^exp(x)*exp(x)
x^2/(-x^2+2)+2^(1/2)*(x/(x+1))^(1/2)
(2*x^2022+1)/(x^2023+x)
(1-(-1/2*pi+arcsin(sin(x)))^2)^(1/2)
(cos(x)-sin(x))/(2+sin(2*x))
(sec(1+ln(x))^2-tan(1+ln(x)))/x^2
(1/x*ln(1/x))^(1/2)
x*(exp(-x)+1)/(exp(x)-1)
ln(3^(1/2)+tan(x))
((sin(20*x)+3*sin(21*x)+sin(22*x))^2+(cos(20*x)+3*cos(21*x)+cos(22*x))^2)^(1/2)
exp(-2*x)*sin(3*x)/x
x*cot(x)
1/((x+1)^3*(-1+x))^(1/2)
x^(-ln(x))
exp(cos(x))*cos(2*x+sin(x))
sin(4*arctan(x))
tan(x)^(1/3)/(cos(x)+sin(x))^2
sin(2*x)^2*sin(3*x)^2*sin(5*x)^2*sin(30*x)^2/sin(x)^2/sin(6*x)^2/sin(10*x)^2/sin(15*x)^2
(1+x^2+(x^4+x^2+1)^(1/2))^(1/2)
"""

#: Maple spellings that differ from sympy's, longest name first so that
#: no replacement is a prefix of a later one.
RENAMES = [('arccosh', 'acosh'), ('arcsinh', 'asinh'), ('arctanh', 'atanh'),
           ('arcsin', 'asin'), ('arccos', 'acos'), ('arctan', 'atan'),
           ('arccot', 'acot'), ('arcsec', 'asec'), ('arccsc', 'acsc'),
           ('Pi', 'pi')]


def to_sympy_syntax(maple: str) -> str:
    text = maple.replace('^', '**')
    for old, new in RENAMES:
        text = re.sub(r'\b%s\b' % old, new, text)
    return text


def main() -> None:
    from sympy import sympify

    out_dir = os.path.join(HERE, 'data', 'mit_bee')
    os.makedirs(out_dir, exist_ok=True)
    lines = [ln.strip() for ln in MAPLE_INTEGRANDS.strip().splitlines()
             if ln.strip()]

    n = 0
    with open(os.path.join(out_dir, 'mit_bee.jsonl'), 'w',
              encoding='utf-8') as fh:
        for index, maple in enumerate(lines):
            integrand = to_sympy_syntax(maple)
            sympify(integrand)
            record = IntegrationTestCase(
                integrand=integrand, variable='x', suite='mit_bee',
                source=SOURCE, index=index)
            fh.write(record.to_json() + '\n')
            n += 1
    print('mit_bee    %6d cases' % n)


if __name__ == '__main__':
    main()
