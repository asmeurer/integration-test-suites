# Suite: `mit_bee_official`

Problems from the MIT Integration Bee, transcribed directly from the
official PDFs posted at
[math.mit.edu/~yyao1/integrationbee.html](https://math.mit.edu/~yyao1/integrationbee.html),
together with their official answers.

## What it contains

544 problems in one file, `mit_bee_official.jsonl`: 262 definite
integrals (using the `lower`/`upper`/`value` fields — this is the
corpus' definite-integral section) and 282 indefinite ones carrying the
boxed antiderivative in `integral`. All but 4 cases have an answer; the
4 exceptions are problems whose printed answer belongs to something the
schema cannot express (a floor of the whole integral, say), which keep
the integrand and carry no answer.

A case's `source` names the round and printed problem number
(`MIT Integration Bee 2023 qualifier, problem 8`), so `--source-prefix`
selects a year or a round. Two kinds of source files are covered:

- **Qualifier tests** (2010–2020 and 2022–2026; no 2021 qualifier is
  posted), each a 20–25 problem written exam with an answer sheet.
  Many qualifier problems are definite, and some are only meaningful as
  definite integrals (floor functions, infinite products,
  symmetric-interval tricks).
- **Bee rounds** (regular season, quarterfinals, semifinals, finals;
  posted for 2022–2026), one integral per page with the answer on the
  following page. Only the integrals actually used on stage appear in
  these files. Bee rounds from earlier years are not posted on the
  site.

38 posted problems could not be transcribed into a sympy integrand
(infinitely nested radicals and continued fractions, limits of
parameterized integrals, a 2023-deep nest of absolute values, ...);
`IMPORT_REPORT.json` lists each with its reason and, where the schema
simply cannot hold it, the official answer in the reason text.

Unlike the `mit_bee` suite — Nasser Abbasi's selection of Bee
integrands that SymPy 1.11.1 could not integrate — nearly every case
here carries its official answer, so the corpus audit (`validate.py`)
can prove the transcription against itself: indefinite answers by
symbolically differentiating them, definite values by numerical
quadrature of the integrand. A handful of printed answers are provably
wrong on the official sheet (sign typos and the like); the importer
keeps the printed text and corrects the emitted case through its
`ANSWER_OVERRIDES` table, listed in `IMPORT_REPORT.json`. The two
suites overlap on some integrands; `../DUPLICATES.json` records the
clusters and neither suite depends on the other.

## How the transcription was made

The PDFs are typeset LaTeX. They were transcribed to SymPy syntax by
Claude (Anthropic's model, reading the rendered pages) as part of this
repository's AI-assisted tooling — see the disclosure section in the
top-level README. The transcription lives verbatim in
`importers/mit_bee_official.py`, one tuple per problem in printed
order, which is what makes it auditable against the PDFs. Per-file
problem counts are asserted by the importer so a silently omitted
problem cannot pass unnoticed.

`log` in the PDFs is the natural logarithm and is transcribed as
SymPy's `log`. A printed real odd root over an interval containing
negative values is transcribed as `real_root(x, 3)`, since SymPy's
`x**(1/3)` is the complex principal branch there.

## License

None stated. The MIT Integration Bee publishes its problem sets and
answers as course material without a license. The underlying
integrands are mathematical facts.
