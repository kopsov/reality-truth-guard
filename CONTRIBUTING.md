# Contributing a failure

This skill only gets better one way: somebody's engine lies, somebody catches it,
and the case gets written down so it cannot pass unnoticed again.

> **One truth failure, one permanent test.**

## What belongs here

A case where a backtest, a run or a reference snapshot said something that live
execution would not have produced — and you can show it with numbers.

Good cases look like the ones already in
[`FAILURE-DATABASE.md`](FAILURE-DATABASE.md): what the engine did, what a broker
would have done instead, how many trades and how much R it was worth, and what
the engine took as fact without being entitled to.

**A case without numbers is an impression, not a failure.** "I think the fills
are optimistic" is a hypothesis; "4333 orders were buried by candle closes, and
fixing it moved the series from +5874 R to −1016 R" is a case. If you cannot
measure it yet, say so — it belongs in the knowledge gaps instead, and that is a
respectable place to be.

## What does not belong here

- Strategy ideas, parameters, or anything about whether a setup is any good. This
  skill audits engines, not strategies.
- Anything that only proves your own system is profitable.
- Cases whose numbers you cannot share. Anonymise the system — every case here
  already has — but keep the numbers real.

## How to send one

**The easy way.** Open an issue from the "Truth failure" template and fill it in.
The fields are the same ones the database uses.

**The precise way.** Use the capture tool, which writes the case in house style
and keeps both languages and all three registers in step:

```bash
python3 tools/capture-failure.py --template > case.json
# fill it in, including the "ru" half
python3 tools/capture-failure.py case.json
python3 tools/self-audit.py
```

Then open a pull request. Run the self-audit first — it refuses anything that
leaves the skill inconsistent: a failure with no rule, a rule with no test, a
translation left behind, a dangling code, a broken link, or a fixture the guard
no longer catches.

## If your case needs a new check in the guard

Add it to [`tools/truth-guard.py`](tools/truth-guard.py), and **plant the failure
in the fixture** (`tools/fixture/trades-broken.csv`) so the check has something to
catch. Then update the expected count in
[`tools/fixture/README.md`](tools/fixture/README.md), in the CI workflow, and in
`tools/self-audit.py`.

Before you send it, break your own check on purpose and confirm it goes red. **A
check that is always green is not a check** — that is the skill's own first rule
about itself, and it applies to contributions too.

## Keeping your own cases private

Not every failure can be published. Put those in `local/`, which git ignores:

```bash
python3 tools/capture-failure.py case.json --local
```

The skill reads them exactly like the public ones. This is the intended way to run
it on a real desk: public cases for everyone, private cases beside them.

## Language

The working language is English — file names, options, code and output — so that
people who do not read Russian can use this. Every document has a full Russian
translation in [`ru/`](ru/), and the two are checked against each other by the
self-audit. If you add a public case, add both halves; the capture tool will not
let you do otherwise.
