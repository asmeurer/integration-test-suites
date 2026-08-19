# -*- coding: utf-8 -*-
"""Numerical oracle deciding whether an antiderivative is correct.

The primary verdict is numerical and never trusts symbolic zero-testing
of radical identities: it differentiates the answer under test and
compares against the integrand pointwise, at points chosen to cover both
signs of every factor appearing under a radical (a branch error is
invisible if you only sample where the radicands are positive).  The
suite's expected antiderivative is used only for secondary taxonomy, so
a mistranslated or unevaluatable expected answer cannot corrupt the
verdict on the answer under test.

Per-instantiation verdicts:

  DERIV-OK         D(ours) == f at every usable sample point, and
                   ours - expected is one constant across all regions
  DERIV-OK-SPLIT   D(ours) == f everywhere, but ours - expected is a
                   different constant on different connected regions
                   (form or branch-convention difference; both
                   antiderivatives correct where checked)
  DERIV-OK-EXP-BAD D(ours) == f everywhere, and D(expected) != f at
                   some usable point (the suite's answer itself looks
                   wrong there)
  DERIV-OK-EXP-NC  D(ours) == f everywhere; expected could not be
                   compared (failed to evaluate, or not closed form)
  WRONG            D(ours) != f at a sample point, confirmed at double
                   precision -- the answer under test is wrong there
  UNDECIDED-*      not enough usable sample points, or numerics were
                   inconclusive

For parametric cases the check runs once per instantiation round
(positive / mixed-sign / negative / irrational / complex constants) and
the aggregate verdict is the worst per-round outcome, where
WRONG > UNDECIDED-* > DERIV-OK-EXP-BAD > DERIV-OK-SPLIT > ... .
"""
import signal
from bisect import bisect

from sympy import (I, Integral, Mul, Pow, Rational, S, im, nan, oo, re,
                   sqrt, zoo)
from sympy.core.symbol import Symbol

__all__ = ['check_case', 'prove_derivative']

#: relative tolerance at working precision for "equal"
EQ_TOL = Rational(1, 10)**25
#: relative tolerance at double precision below which a first-pass
#: mismatch is written off as a precision artifact
EQ_TOL2 = Rational(1, 10)**40
#: relative tolerance above which a double-precision recheck confirms
#: a genuine mismatch
NEQ_TOL = Rational(1, 10)**12
#: relative movement between the two precisions above which the
#: evaluation itself is untrustworthy
STAB_TOL = Rational(1, 10)**6
PREC = 60

# Verdict severity, worst first, for aggregating instantiation rounds.
# TIMEOUT outranks the OK verdicts: an OK aggregate must mean every
# applicable round was actually checked.  DEGENERATE stays at the
# bottom (a round skipped as inapplicable does not taint an OK case).
SEVERITY = ['LEAKED-SYMBOLS', 'WRONG', 'UNDECIDED-NUMERICS',
            'UNDECIDED-COVERAGE', 'TIMEOUT', 'DERIV-OK-EXP-BAD',
            'DERIV-OK-SPLIT', 'DERIV-OK-EXP-NC', 'DERIV-OK',
            'DERIV-OK-PROVEN', 'DEGENERATE']


def _radicand_bases(f, x):
    """x-dependent bases raised to non-integer rational powers in f."""
    bases = []
    for p in f.atoms(Pow):
        if (p.exp.is_Rational and not p.exp.is_Integer and p.base.has(x)
                and not p.base.is_Symbol):
            bases.append(p.base)
        elif p.exp.is_Rational and not p.exp.is_Integer and p.base == x:
            bases.append(p.base)
    return bases


def _dyadic(v, bits=24):
    """A nearby dyadic rational (never exactly a nondyadic root)."""
    return Rational(int(round(v * 2**bits)), 2**bits)


def _real_breakpoints(bases, x):
    """Sorted real roots/poles of the radicand bases, as floats."""
    from sympy import Poly, together
    pts = set()
    for b in bases:
        b = together(b)
        n, d = b.as_numer_denom()
        for part in (n, d):
            if not part.has(x):
                continue
            try:
                p = Poly(part, x)
            except Exception:
                continue
            if p.degree() < 1 or not p.domain.is_Exact or \
                    not (p.domain.is_QQ or p.domain.is_ZZ):
                try:
                    rts = [r for r in p.nroots() if abs(im(r)) < 1e-12]
                    pts.update(float(re(r)) for r in rts)
                except Exception:
                    pass
                continue
            try:
                for r in p.real_roots():
                    pts.add(float(r.evalf(30)))
            except Exception:
                continue
    return sorted(pts)


def _sample_points(breaks):
    """Real dyadic sample points around the breakpoints, plus a default
    grid and a few complex points."""
    real = set()
    default = [Rational(p, 64) for p in
               (-333, -173, -87, -29, 23, 91, 169, 351)]
    if breaks:
        ext = [breaks[0] - 2.0] + breaks + [breaks[-1] + 2.0]
        for a, b in zip(ext, ext[1:]):
            if b - a > 1e-9:
                real.add(_dyadic((a + b) / 2))
        for r in breaks:
            gap = min(x for x in
                      [1.0] + [abs(r - s) for s in breaks if s != r])
            d = gap / 4
            real.add(_dyadic(r - d))
            real.add(_dyadic(r + d))
    real.update(default)
    # real parts on odd 64ths: breakpoints are usually simple
    # rationals, and the jump-correction factor (x - r)/sqrt((x - r)**2)
    # is discontinuous exactly on the vertical line Re(x) == r
    cx = [Rational(33, 64) + 3*I/4, Rational(-79, 64) + I/3,
          Rational(129, 64) - I/2, Rational(-47, 64) - 5*I/4]
    return sorted(real), cx


def _eval_at(expr, x, pt, prec=PREC):
    """expr at x=pt as an (re, im) pair of Floats, or None."""
    try:
        v = expr.subs(x, pt).evalf(prec)
    except Exception:
        return None
    if v.has(nan, oo, zoo, Integral):
        return None
    if v.free_symbols:
        return None
    try:
        vr, vi = v.as_real_imag()
        vr, vi = vr.evalf(prec), vi.evalf(prec)
        if not (vr.is_Number and vi.is_Number):
            return None
        float(vr), float(vi)  # reject non-finite
    except (TypeError, ValueError, OverflowError, Exception):
        return None
    return (vr, vi)


def _absval(v):
    return (v[0]**2 + v[1]**2)


def _reldiff2(a, b):
    """Squared relative difference of two (re, im) pairs."""
    d2 = (a[0] - b[0])**2 + (a[1] - b[1])**2
    scale = max(S.One, _absval(a), _absval(b))
    return d2 / scale


def _match_at(e1, e2, x, pt, prec=PREC):
    """'eq' / 'neq' / 'skip' / 'undecided' for e1 == e2 at x=pt."""
    a, b = _eval_at(e1, x, pt, prec), _eval_at(e2, x, pt, prec)
    if a is None or b is None:
        return 'skip'
    if _reldiff2(a, b) < EQ_TOL**2:
        return 'eq'
    a2, b2 = _eval_at(e1, x, pt, 2*prec), _eval_at(e2, x, pt, 2*prec)
    if a2 is None or b2 is None:
        return 'undecided'
    # an evaluation that moves between precisions is numerically
    # unstable at this point (heavy cancellation of branch-sensitive
    # pieces, typically) and cannot confirm a mismatch
    if (_reldiff2(a, a2) > STAB_TOL**2 or
            _reldiff2(b, b2) > STAB_TOL**2):
        return 'undecided'
    r2 = _reldiff2(a2, b2)
    if r2 < EQ_TOL2**2:
        return 'eq'
    if r2 > NEQ_TOL**2:
        # confirm with an independent engine before convicting: evalf
        # has been caught returning a stable wrong value at high
        # precision (correct below 60 digits and under mpmath at any
        # precision), so a mismatch it reports alone is not enough
        try:
            import mpmath
            from sympy import lambdify
            f1, f2 = lambdify(x, e1, 'mpmath'), lambdify(x, e2, 'mpmath')
            mpmath.mp.dps = prec
            v1, v2 = complex(f1(complex(pt))), complex(f2(complex(pt)))
        except Exception:
            return 'undecided'
        scale = max(1.0, abs(v1), abs(v2))
        if abs(v1 - v2) / scale > float(NEQ_TOL):
            return 'neq'
        return 'undecided'
    return 'undecided'


def prove_derivative(f, x, F, deep=True):
    """Try to *prove* D(F) == f symbolically.

    Returns the name of the step that settled it, or None if none did.
    ``cancel`` alone decides the large majority of cases and is fast; the
    trigonometric simplifier is tried only when the difference actually
    contains trigonometric functions, and ``simplify`` only as a last
    resort, since it is by far the expensive one -- pass ``deep=False``
    to stop before it and keep the check cheap over a whole corpus.

    A None result is "not proven", never "proven different": these
    rewriters are one-sided.  Callers fall back on the numerical ladder,
    which is the part that can actually convict a wrong answer.
    """
    from sympy import cancel, diff, expand, simplify
    from sympy.functions.elementary.trigonometric import TrigonometricFunction
    from sympy.functions.elementary.hyperbolic import HyperbolicFunction
    from sympy.simplify.fu import fu

    difference = diff(F, x) - f
    if difference.is_zero:
        return 'zero'
    for name, rewrite in (('cancel', cancel),
                          ('expand', lambda e: cancel(expand(e)))):
        try:
            if rewrite(difference).is_zero:
                return name
        except Exception:
            continue
    if difference.has(TrigonometricFunction, HyperbolicFunction):
        try:
            if cancel(fu(difference)).is_zero:
                return 'fu'
        except Exception:
            pass
    if deep:
        try:
            if simplify(difference).is_zero:
                return 'simplify'
        except Exception:
            pass
    return None


def check_answer(f, x, ours, expected, prove=True):
    """Decide one (already concrete) case.

    A symbolic proof that D(ours) == f is tried first: it is both faster
    and stronger than sampling, and settles the great majority of cases.
    The numerical ladder below runs only when no proof was found, and it
    is the only part that can convict a wrong answer.

    Returns a dict with 'verdict' and supporting detail.
    """
    from sympy import Derivative, diff, sign

    if prove:
        step = prove_derivative(f, x, ours)
        if step is not None:
            return {'verdict': 'DERIV-OK-PROVEN', 'step': step}
    dours = diff(ours, x)
    if ours.has(sign):
        # sign() is locally constant on the real line: its derivative
        # is zero away from the breakpoints, which the sample points
        # avoid.  Freeze it (naive differentiation leaves unevaluatable
        # Derivative(sign(...)) nodes), and skip the complex sample
        # points -- sign-corrected answers are real-line oriented.
        dours = dours.replace(
            lambda e: isinstance(e, Derivative) and e.has(sign),
            lambda e: S.Zero)
        cx_ok = False
    else:
        cx_ok = True
    bases = _radicand_bases(f, x)
    breaks = _real_breakpoints(bases, x)
    real_pts, cx_pts = _sample_points(breaks)
    if not cx_ok:
        cx_pts = []

    used, undecided = [], []
    for pt in real_pts + cx_pts:
        m = _match_at(dours, f, x, pt)
        if m == 'skip':
            continue
        if m == 'neq':
            return {'verdict': 'WRONG', 'point': str(pt),
                    'breaks': [round(b, 6) for b in breaks]}
        if m == 'undecided':
            undecided.append(pt)
            continue
        used.append(pt)

    # Coverage: every radicand with real roots/poles must have been
    # checked on both sides of at least one of them (the branch-bug
    # class flips sign at those points and is untested otherwise).
    cover_ok = True
    real_used = [p for p in used if p.is_real]
    for b in bases:
        bks = _real_breakpoints([b], x)
        if not bks:
            continue
        if not any(any(float(p) < r for p in real_used) and
                   any(float(p) > r for p in real_used) for r in bks):
            cover_ok = False

    if len(used) < 4 or not cover_ok:
        return {'verdict': 'UNDECIDED-COVERAGE', 'used': len(used),
                'undecided': len(undecided)}
    if undecided:
        return {'verdict': 'UNDECIDED-NUMERICS', 'used': len(used),
                'undecided': len(undecided)}

    # ours is right; classify against expected (real points only --
    # region structure in C is not an interval partition).
    if expected is None or expected.has(Integral):
        return {'verdict': 'DERIV-OK-EXP-NC', 'used': len(used)}
    consts = {}
    for pt in real_used:
        a = _eval_at(ours, x, pt)
        b = _eval_at(expected, x, pt)
        if a is None or b is None:
            continue
        region = bisect(breaks, float(pt))
        consts.setdefault(region, []).append(
            (a[0] - b[0], a[1] - b[1]))
    if not consts:
        return {'verdict': 'DERIV-OK-EXP-NC', 'used': len(used)}

    def _cdiff(u, v):
        d2 = (u[0] - v[0])**2 + (u[1] - v[1])**2
        scale = max(S.One, u[0]**2 + u[1]**2, v[0]**2 + v[1]**2)
        return d2 / scale

    local_const = True
    reps = []
    for region, vals in sorted(consts.items()):
        for v in vals[1:]:
            if _cdiff(vals[0], v) > EQ_TOL2:
                local_const = False
        reps.append(vals[0])
    if not local_const:
        # ours - expected is not constant within a region.  Either the
        # corpus answer is wrong there, or the region structure above
        # (radicand breakpoints only) is too coarse for expected's own
        # jumps (atan/log arguments).  Discriminate rigorously: check
        # D(expected) against f directly.
        dexp = diff(expected, x)
        for pt in real_used:
            m = _match_at(dexp, f, x, pt)
            if m == 'neq':
                return {'verdict': 'DERIV-OK-EXP-BAD', 'point': str(pt),
                        'used': len(used)}
        return {'verdict': 'DERIV-OK-SPLIT', 'used': len(used),
                'coarse': True}
    for v in reps[1:]:
        if _cdiff(reps[0], v) > EQ_TOL2:
            return {'verdict': 'DERIV-OK-SPLIT', 'used': len(used),
                    'nregions': len(reps)}
    return {'verdict': 'DERIV-OK', 'used': len(used)}


#: instantiation pools, cycled over the sorted constant symbols
ROUNDS = [
    ('pos', [2, 3, 5, 7, 11]),
    ('mixed', [-2, 3, Rational(-1, 2), 5, Rational(-7, 3)]),
    ('neg', [-3, Rational(-5, 2), -7, -2, Rational(-1, 3)]),
    ('irr', [sqrt(2), -sqrt(3), 1 + sqrt(2), 2, Rational(1, 2)]),
    ('cx', [1 + I/2, 2, -1 + I, 3, I/3]),
]


def _decide_numeric_relationals(e):
    """Decide Eq/Ne conditions whose sides are numbers.

    Piecewise conditions like Ne(<exact complex arithmetic>, 0) do not
    auto-evaluate in sympy, so an instantiated Piecewise answer stays
    a Piecewise and every point evaluation fails.  Deciding zero-ness
    exactly (is_zero on the difference) collapses them.
    """
    from sympy import Eq, Ne

    def dec(rel):
        z = rel.lhs - rel.rhs
        if not z.is_number:
            return rel
        zz = z.is_zero
        if zz is None:
            zz = z.expand().is_zero
        if zz is None:
            zz = z.equals(0)
        if zz is None:
            return rel
        truth = zz == isinstance(rel, Eq)
        return S.true if truth else S.false

    return e.replace(lambda sub: isinstance(sub, (Eq, Ne)), dec)


def _degenerate(f_i):
    from sympy import together
    if f_i.has(nan, oo, zoo):
        return True
    try:
        return together(f_i).is_zero is True
    except Exception:
        return True


def check_case(f, x, ours, expected, timeout=60):
    """Check one corpus case; instantiate symbolic constants if present.

    Returns {'verdict': aggregate, 'rounds': {name: perround}} where
    perround are check_answer() dicts.  A per-round signal.alarm(...)
    guards each instantiation; TimeoutError is recorded, not raised
    (a SIGALRM handler raising TimeoutError must already be installed
    when timeout is nonzero).
    """
    # a symbol in our answer that is not in the problem is an internal
    # symbol that leaked past the back-substitutions -- the answer is
    # unusable, and no amount of numerics can evaluate it anyway
    if ours.free_symbols - f.free_symbols - {x}:
        return {'verdict': 'LEAKED-SYMBOLS',
                'rounds': {'static': {'verdict': 'LEAKED-SYMBOLS',
                    'symbols': sorted(str(s) for s in
                        ours.free_symbols - f.free_symbols - {x})}}}
    consts = sorted(f.free_symbols - {x}, key=lambda s: s.name)
    if not consts:
        plan = [('concrete', {})]
    else:
        plan = []
        for name, pool in ROUNDS:
            sub = {s: pool[i % len(pool)] for i, s in enumerate(consts)}
            plan.append((name, sub))
    rounds = {}
    for name, sub in plan:
        if timeout:
            signal.alarm(timeout)
        try:
            f_i = f.subs(sub) if sub else f
            if sub and _degenerate(f_i):
                rounds[name] = {'verdict': 'DEGENERATE'}
                continue
            ours_i = _decide_numeric_relationals(ours.subs(sub)) \
                if sub else ours
            exp_i = _decide_numeric_relationals(expected.subs(sub)) \
                if (sub and expected is not None) else expected
            if sub and (ours_i.has(nan, oo, zoo) or
                        exp_i is not None and exp_i.has(nan, oo, zoo)):
                rounds[name] = {'verdict': 'DEGENERATE'}
                continue
            rounds[name] = check_answer(f_i, x, ours_i, exp_i)
        except TimeoutError:
            rounds[name] = {'verdict': 'TIMEOUT'}
        except Exception as e:
            rounds[name] = {'verdict': 'UNDECIDED-NUMERICS',
                            'error': type(e).__name__}
        finally:
            if timeout:
                signal.alarm(0)
    agg = min((r['verdict'] for r in rounds.values()),
              key=lambda v: SEVERITY.index(v) if v in SEVERITY else 99)
    return {'verdict': agg, 'rounds': rounds}
