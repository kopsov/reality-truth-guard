# Truth tests

> **One truth failure, one permanent test.**

The rule is simple: a failure found once may never pass unnoticed again. Not "we
will be more careful", but a run that fails.

---

## How a failure becomes a test

```
FAILURE ─► BREAKDOWN ─► ROOT ─► RULE ─► TEST ─► GUARD
```

1. **Failure.** Record it with numbers: how many trades affected, how much R, what
   happened to drawdown and win rate. Without numbers it is an impression, not a
   failure.
2. **Breakdown.** Walk the chain from data to metric and find the link where the
   truth ran out.
3. **Root.** State what exactly the engine took as fact without being entitled to.
   "We forgot to check" is not a root.
4. **Rule.** Write it into `RULES.md` so that it can be checked by a run.
5. **Test.** Write a check that fails on the old behaviour and passes on the new
   one. Verify that it **actually fails** on the old one: a test that is always
   green is not a test.
6. **Guard.** Add the check to the permanent set so it runs always, not from
   memory.

## Two kinds of test

**A test on a case.** Takes one concrete situation — that very trade, that very
candle — and demands the right outcome. Fast, precise, blind to the failure's
relatives.

**A test on an export.** Walks the whole trade snapshot and demands that not one
row breaks the rule. Slower, but it catches the whole family at once — that is how
the guard in this repository works.

Having both is best: the first explains, the second stands watch.

## What to run on every engine change

1. The truth guard — the general one or your own.
2. Reconciliation against the reference snapshot, field by field.
3. Reconciliation of the contract with the executor.
4. The continued live account against a from-scratch recount.
5. Comparison with the previous release: what changed beyond what the change
   itself does.

**If a single field moved beyond what the change does, the change is wrong. Fix
it, do not explain it.**

---

## Test register

The "by what" column is the run that closes the test. "Debt" means the test does
not exist yet, and that is recorded rather than forgotten.

| Code | What it catches | Rule | From failure | By what |
|---|---|---|---|---|
| T-01 | the candle grid diverged from the terminal on any timeframe | R06 | F01 | bar-by-bar reconciliation of engine candles with the terminal |
| T-02 | the seasonal offset stands as a constant for the whole series | R07 | F02 | reconciliation of the display with the terminal; DST dates read off hourly candles |
| T-03 | stop or target placed on the impossible side of price; an order triggering in the minute it was placed | R19 | F03 | this repository's guard; the project's own battle guard |
| T-04 | a fill inside its own signal minute; a pending order outliving the server day | R17, R18 | F04, F17 | this repository's guard; the project's own battle guard |
| T-05 | the run sees fewer stops than the live layer at the same number of targets | R10 | F05 | the live layer against the batch run's list |
| T-06 | an order's fate decided at the candle close instead of at the event; undecidable ordering resolved in your own favour | R13, R14, R15 | F06 | a minute-level breakdown; comparison of exact and coarse fill modes |
| T-07 | intra-bar time measured from the wrong event; duplicates inside a stream | R13, R35 | F07 | a minute-level setup audit; this repository's guard |
| T-08 | a hole in the series, duplicate timestamps, non-monotonic time, a broken bar | R02, R03 | F08, F09 | a series watchdog, a quote freshness watch, this repository's guard |
| T-09 | stops at exactly −1R for one hundred percent of trades | R28 | F10 | slippage-allowance tests; this repository's guard states the share |
| T-10 | the side of the market swapped; spread counted twice | R25, R27 | F11 | the executor's spread-adjustment tests |
| T-11 | spread substituted by one number for all history | R05 | F12 | spread stored next to each bar, reconciled with the terminal |
| T-12 | the continued live account diverged from a from-scratch recount by even one trade | R11, R33 | F13 | trade-by-trade reconciliation; reconciliation of derived candle assembly |
| T-13 | the bot layer failed to declare something the executor asks for | R21 | F14 | reconciliation of the contract with the executor |
| T-14 | volume off the lot step, below the minimum lot, above the ceiling; the account ceiling bypassed | R30, R31 | F15 | position-size tests; this repository's guard |
| T-15 | a disagreement with the terminal corrected silently | R34 | F16 | reconciliation tests |
| T-16 | the signal-to-fill latency is not stated as a number | R22 | F18 | **debt**: measured on a demo link only |
| T-17 | a live-account command arrived from the sandbox environment | R36 | F20 | environment locks |
| T-18 | documentation promises behaviour the code does not have | R41 | F21 | **debt**: no such check anywhere |
| T-19 | an entry or exit price outside its own bar beyond the spread | R20 | F23 | this repository's guard |
| T-20 | a bar hit both stop and target and the convenient outcome was recorded | R13 | F06 | this repository's guard |
| T-21 | a stop closer than the broker minimum distance | R23 | gap 7 | **debt** |
| T-22 | broker refusals not modelled at all | R24 | gap 6 | **debt** |

## Debts of the register

Four tests are unwritten — T-16, T-18, T-21, T-22 — and T-05 and T-07 live as
one-off investigations rather than permanent guards. This is not forgotten; it is
a recorded debt. Whoever steps on it must top up not only the failure database but
this list too.
