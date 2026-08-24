# -*- coding: utf-8 -*-
"""Sound rewrite steps for the symbolic derivative proof.

Everything here proves at the same standard as ``cancel``: identities of
meromorphic functions under principal-branch semantics, indifferent to
removable singularities and to points where a denominator vanishes.  No
step uses a rewrite that can change a nonzero function into zero — each
is an exact identity at every point of the domain:

- ``B**(u + v) == B**u * B**v`` (both factors use the same ``log(B)``);
- ``(r*A)**q == r**q * A**q`` for positive rational ``r``;
- ``B**q == exp(q*log(B))`` (the definition of the principal power);
- ``polylog(1, z) == -log(1 - z)`` and ``LambertW(z)*exp(LambertW(z))
  == z`` (each holds on every branch);
- inverse trigonometric and hyperbolic functions rewritten to their
  principal logarithmic forms;
- normalizing a function's argument with ``cancel``;
- for 2F1, the contiguous-parameter operator algebra plus the
  hypergeometric ODE, and for ``2F1(a, b; a+1; z)`` the incomplete-beta
  relation ``H' == a*((1-z)**-b - H)/z``;
- deciding a numeric algebraic coefficient's zero-ness through its
  minimal polynomial.

The 2F1 reduction only *proves*: a residual is declared zero when every
collected coefficient of the opaque function symbols vanishes, which
requires no independence assumption; the shift-operator rewrites divide
by parameter expressions and so are generic in the parameters, the same
convention ``cancel`` applies to denominators.
"""
from __future__ import annotations

from sympy import (Add, Dummy, Function, Integer, LambertW, Mul, Pow,
                   cancel, exp, expand, fraction, log, polylog, together)


def powsplit(e):
    """Split ``Pow(B, u + v)`` into ``Pow(B, u)*Pow(B, v)``."""
    def split(s):
        return Mul(*[Pow(s.base, t) for t in s.exp.args])

    return e.replace(
        lambda s: isinstance(s, Pow) and isinstance(s.exp, Add),
        split)


def argnorm(e):
    """Normalize function arguments and power bases with ``cancel``, so
    the same mathematical argument written two ways becomes one atom.
    Positive rational content is pulled out of non-integer powers."""
    from sympy import Expr, Tuple

    def norm(s):
        if isinstance(s, Pow):
            b, q = cancel(s.base), s.exp
            if not q.is_Integer:
                c, p = b.as_content_primitive()
                if c.is_Rational and c.is_positive and c != 1:
                    return Pow(c, q) * Pow(p, q)
            return Pow(b, q)
        return s.func(*[cancel(a) if isinstance(a, Expr)
                        and not isinstance(a, Tuple) else a
                        for a in s.args])

    return e.replace(
        lambda s: isinstance(s, (Pow, Function)) and not s.is_Atom,
        norm)


def special_rewrites(e):
    """Apply ``polylog(1, z) -> -log(1 - z)`` and
    ``exp(n*LambertW(z)) -> (z/LambertW(z))**n`` for integer ``n``."""
    def do_polylog(s):
        if s.args[0] == 1:
            return -log(1 - s.args[1])
        return s

    def do_exp(s):
        coeff, rest = s.args[0].as_coeff_Mul()
        if isinstance(rest, LambertW) and coeff.is_Integer:
            z = rest.args[0]
            if coeff > 0:
                return (z / rest)**coeff
            return (rest / z)**(-coeff)
        return s

    e = e.replace(lambda s: isinstance(s, polylog), do_polylog)
    e = e.replace(lambda s: isinstance(s, exp), do_exp)
    return e


def powexp(e):
    """Rewrite inverse functions to their logarithmic forms and powers
    with symbolic exponents to ``exp(q*log(B))``, then push everything
    through ``exp``, normalize the ``exp`` arguments and expand, so that
    answers phrased with ``F**u`` atoms meet integrands phrased with
    ``exp`` atoms on common ground."""
    from sympy import (acos, acosh, acot, acoth, acsc, acsch, asec, asech,
                       asin, asinh, atan, atanh)
    inv = (acosh, acoth, asinh, atanh, acos, asin, atan, acot, asec, acsc,
           asech, acsch)
    e = e.replace(lambda s: isinstance(s, inv), lambda s: s.rewrite(log))

    def pow_to_exp(s):
        if s.exp.is_number or isinstance(s.base, exp):
            return s
        return exp(expand(s.exp * log(s.base)))
    e = e.replace(lambda s: isinstance(s, Pow) and not s.exp.is_number,
                  pow_to_exp)
    e = e.rewrite(exp)
    e = e.replace(lambda s: isinstance(s, exp),
                  lambda s: exp(expand(cancel(s.args[0]))))
    return expand(e, power_exp=True, mul=True, log=False)


def killzero(c) -> bool:
    """Whether ``c`` reduces to zero under the cheap sound rewrites."""
    from sympy import powsimp
    from sympy.functions.elementary.hyperbolic import HyperbolicFunction
    from sympy.functions.elementary.trigonometric import \
        TrigonometricFunction
    from sympy.simplify.fu import fu

    c = cancel(c)
    if c.is_zero:
        return True
    c = cancel(powsimp(c, combine='exp'))
    if c.is_zero:
        return True
    c = cancel(expand(powsplit(c), mul=True))
    if c.is_zero:
        return True
    c = cancel(argnorm(c))
    if c.is_zero:
        return True
    if not c.has(TrigonometricFunction, HyperbolicFunction):
        return False
    try:
        return cancel(fu(c)).is_zero is True
    except Exception:
        return False


def numzero(e) -> bool:
    """Whether ``e`` is zero because its numeric algebraic-number
    coefficients all are.  The numerator is collected over its symbols
    and irrational atoms as free generators — the proving direction
    needs no relations between them — and each purely numeric
    coefficient is decided exactly by its minimal polynomial."""
    from sympy import Poly, minimal_polynomial, preorder_traversal

    num, _ = fraction(together(e))
    num = expand(num)
    if num.is_zero:
        return True
    gens = set()
    for s in preorder_traversal(num):
        if not s.free_symbols:
            continue
        if isinstance(s, (Pow, Function)) and not s.is_Atom:
            if isinstance(s, Pow) and s.exp.is_Integer:
                continue
            gens.add(s)
    gens |= num.free_symbols
    try:
        p = Poly(num, *sorted(gens, key=str))
    except Exception:
        return False
    for c in p.coeffs():
        if not c.is_number or c.is_rational and not c.is_zero:
            return False
        if c.is_zero:
            continue
        try:
            mp = minimal_polynomial(c, Dummy())
            if not mp.is_Symbol:
                return False
        except Exception:
            return False
    return True


def hyperzero(e) -> bool:
    """Whether a residual containing 2F1 functions is provably zero.

    All 2F1 atoms sharing an argument whose parameters differ by
    integers are expressed through one opaque base ``H`` and its
    derivative ``H'``: uniform shifts through the derivative relation
    ``2F1(a+n, b+n; c+n; z) == (c)_n/((a)_n (b)_n) * H^(n)``, mixed
    shifts through the contiguous operators of
    :mod:`sympy.simplify.hyperexpand`, and orders above one through the
    hypergeometric ODE.  When the base matches ``2F1(a, b; a+1; z)``,
    the incomplete-beta relation eliminates ``H'`` as well.  The
    residual is zero when every collected coefficient of the opaque
    symbols is."""
    from sympy import Derivative, Poly, hyper, nsimplify, rf
    from sympy.core.sorting import default_sort_key
    from sympy.simplify.hyperexpand import (Hyper_Function, apply_operators,
                                            devise_plan)

    e = e.replace(
        lambda s: isinstance(s, hyper) and len(s.ap) == 2
        and list(s.ap) != sorted(s.ap, key=default_sort_key),
        lambda s: hyper(sorted(s.ap, key=default_sort_key), s.bq,
                        s.argument))

    hs = [s for s in e.atoms(hyper) if len(s.ap) == 2 and len(s.bq) == 1]
    if not hs:
        return False

    def int_shifts(h, h0):
        d = [cancel(h.ap[0] - h0.ap[0]), cancel(h.ap[1] - h0.ap[1]),
             cancel(h.bq[0] - h0.bq[0])]
        if all(v.is_Integer for v in d):
            return d, (h.ap[0], h.ap[1])
        d = [cancel(h.ap[0] - h0.ap[1]), cancel(h.ap[1] - h0.ap[0]),
             cancel(h.bq[0] - h0.bq[0])]
        if all(v.is_Integer for v in d):
            return d, (h.ap[1], h.ap[0])
        return None

    groups = []
    for h in hs:
        for members in groups:
            if (h.argument == members[0].argument
                    and int_shifts(h, members[0]) is not None):
                members.append(h)
                break
        else:
            groups.append([h])

    reps = {}
    dummies = []
    for members in groups:
        shifts = {h: int_shifts(h, members[0]) for h in members}
        base = min(members, key=lambda h: sum(shifts[h][0]))
        a, b = shifts[base][1]
        c = base.bq[0]
        z = base.argument
        H0, H1 = Dummy('H0'), Dummy('H1')
        dummies += [H0, H1]
        Z = Dummy('Z')
        Hf = Function('H')

        exprs = {}
        maxord = 0
        for h in members:
            (i, j, k), (pa, pb) = int_shifts(h, base)
            if i == j == k:
                if i < 0:
                    return False
                exprs[h] = (rf(c, i) / (rf(a, i) * rf(b, i))
                            * Derivative(Hf(Z), Z, i) if i else Hf(Z))
                maxord = max(maxord, i)
                continue
            try:
                ops = devise_plan(Hyper_Function((pa, pb), h.bq),
                                  Hyper_Function((a, b), base.bq), Z)
            except Exception:
                return False
            r = apply_operators(Hf(Z), ops, lambda f: Z * f.diff(Z))
            r = nsimplify(cancel(r), rational=True)
            exprs[h] = r
            for d_ in r.atoms(Derivative):
                maxord = max(maxord, d_.derivative_count)
        if maxord > 4:
            return False

        table = {0: (Integer(1), Integer(0)), 1: (Integer(0), Integer(1))}
        for k in range(1, max(maxord, 1)):
            p, q = table[k]
            dp = p.diff(Z) + q * a * b / (Z * (1 - Z))
            dq = q.diff(Z) + p - q * (c - (a + b + 1) * Z) / (Z * (1 - Z))
            table[k + 1] = (cancel(dp), cancel(dq))

        def flatten(r):
            r = r.replace(
                lambda s: isinstance(s, Derivative),
                lambda s: (table[s.derivative_count][0] * H0
                           + table[s.derivative_count][1] * H1))
            return r.subs(Hf(Z), H0).subs(Z, z)

        for h in members:
            reps[h] = flatten(exprs[h])

        omz = cancel(1 - z)
        if cancel(c - a - 1) == 0:
            h1val = a * (Pow(omz, -b) - H0) / z
        elif cancel(c - b - 1) == 0:
            h1val = b * (Pow(omz, -a) - H0) / z
        else:
            h1val = None
        if h1val is not None:
            reps = {h: v.subs(H1, h1val) for h, v in reps.items()}
            dummies.remove(H1)

    num, _ = fraction(together(e.xreplace(reps)))
    try:
        p = Poly(expand(num), *dummies)
    except Exception:
        return False
    return all(killzero(coeff) for coeff in p.coeffs())
