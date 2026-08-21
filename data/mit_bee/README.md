# Suite: `mit_bee`

54 integrands from the MIT Integration Bee that SymPy 1.11.1 could not
integrate, all of them stated to have known antiderivatives.

These are competition problems: they reward a clever substitution rather
than a decision procedure, so they measure the breadth of the heuristic
integrators (`manualintegrate`, `heurisch`) more than they test Risch.

## What it contains

One file, `mit_bee.jsonl`, with 54 indefinite integrands in `x` and no
expected answers — only the integrands were posted, so a runner can
report whether an engine returns something closed form, but the
numerical oracle can only check that the answer differentiates back to
the integrand. The list contains one integrand three times, exactly as
posted; the duplicates are kept rather than silently collapsed, and
`../DUPLICATES.json` records them.

The `mit_bee_official` suite covers the same competition from the
official PDFs, with answers; 26 of these 54 integrands reappear there
(see `../DUPLICATES.json`), while the rest likely came from bee rounds
whose problem sets are no longer posted.

## Where these came from

Posted by Nasser Abbasi in
[sympy/sympy discussion 24843](https://github.com/sympy/sympy/discussions/24843),
in Maple syntax, collected from the
[MIT Integration Bee](https://math.mit.edu/~yyao1/integrationbee.html).
The Maple text is embedded verbatim in `importers/mit_bee.py` and
translated on import, so the translation stays auditable against the
original post.

## License

None stated. The MIT Integration Bee publishes its qualifying-round tests
and answers as course material without a license; this transcription is
Nasser Abbasi's.

As with the other suites sourced from Nasser, this is included pending his
agreement. The underlying integrands are mathematical facts.
