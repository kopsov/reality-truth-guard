---
name: reality-truth-guard
description: A truth guard for trading engines. It does not check whether the strategy works — it checks whether the engine tells the truth: can the numbers it produced on history actually be produced at a broker on a live account? Use for any work on a trading bot, engine, backtest, run, reference snapshot, live layer, order execution, pending orders, stop and target, breakeven, position size and risk, spread, slippage, commission, latency, time and timezones, candle markup and higher timeframes, quote series, signals and indicators, position state, and reconciliation with an MT5 terminal. Mandatory before showing anyone the numbers of a run and before promoting a change into a reference engine. Answers with a verdict — proven, partly proven, not proven, failed, blocked — and never turns "I don't know" into "probably fine". По-русски — сторож правды торгового движка: проверяет, можно ли получить в реальном исполнении те числа, что движок показал на истории; перевод документации лежит в папке ru.
---

# REALITY TRUTH GUARD — a truth guard for trading engines

## What this is

The last technical guard standing between "it all looks wonderful on history" and
"we have actually put money on this".

The skill does not judge the strategy. It judges the **engine**: is it proven that a
number obtained on history can be obtained in live trading? Until that is proven the
number counts as unconfirmed, however pretty it looks and however many times it has
been shown before.

The skill did not grow out of theory. It is assembled from failures that happened in
real live projects and cost painted profit: markup cut by somebody else's days, an
entry inside its own signal minute, a breakeven order a broker would not accept, a
fractal confirmed by the candle trading is already happening inside, an order buried
by a candle close. Every case with its numbers is in
[`FAILURE-DATABASE.md`](FAILURE-DATABASE.md).

## The governing principle

> **Do not check whether the strategy works. Check whether the engine tells the
> truth.**

Three working rules follow from it, and they are not up for discussion:

1. **A historical result does not equal a live result until the match is proven.** No
   proof means the status is "not proven", not "probably matches".
2. **A divergence is a computation error, not a modelling convention.** Fix the
   engine, do not explain it away. There are exactly two lawful exceptions: slippage
   and the size of the spread, which may change.
3. **The job is not to make the result prettier but to make it true.** Numbers almost
   always get worse after an audit. That is the normal outcome of the work, not a
   failure of it.

## What the skill does not do

- It does not raise the win rate, reduce the drawdown or improve the profit.
- It does not change setup rules, entries, exits or thresholds for better numbers.
- It does not delete "bad" trades and does not tune parameters.
- It defends neither the strategy, nor the previous reference, nor its own earlier
  conclusions.

If the engine computes worse after the audit, the guard has done its job.

## When to engage without being asked

Any change capable of moving a trading result must pass the guard. The signs: someone
touched the strategy, the engine, a run, the reference snapshot, the live layer, order
execution, position management, stop, target, breakeven, partial close, volume, risk,
leverage, margin, spread, commission, swap, slippage, latency, the quote series, the
data source, candle markup and higher timeframes, sessions, timezones and
daylight-saving switches, the news calendar, indicators, signal generation, trade
state, the contract with the executor, the expert advisor, the instrument spec.

Three more cases where the guard is mandatory regardless of what changed:

- **before serving anyone a table or a number from a run;**
- **before promoting a change from a draft into the reference engine;**
- **before creating or updating a bot in a live executor.**

Without a green guard the numbers are not served and the change is not promoted.

## The procedure

### Step 0. Impact analysis

Before checking anything, name **what could have changed** and build the chain
downwards. Checking only the place you touched is forbidden: the failure almost always
surfaces further downstream.

```
DATA ─► MARKUP ─► SIGNAL ─► ORDER ─► EXECUTION ─► POSITION ─► EXIT ─► R ─► EQUITY ─► DRAWDOWN ─► RESULT
```

Common chains:

- lot calculation → position size → risk → money → equity → drawdown → result;
- candle boundary → higher-timeframe markup → zone → signal → every trade;
- moment of execution → entry price → R of every trade → every metric at once;
- spread → entry price and stop trigger → outcome → win rate and profit factor.

If the lot calculation was touched, do not measure the lot — measure the whole tail of
the chain.

### Step 1. Twelve questions of live execution

Ask them of every decision before showing any numbers.

1. **When does the order appear at the broker?** The decision was made at a candle
   close — so there is nothing to fill inside that candle.
2. **Will the broker accept such an order?** A buy stop below price, a sell stop above.
3. **How long does the order live?** Every command has its own expiry, and an expired
   one does not execute.
4. **Can the executor do what the engine is asking?** Its contract knows a finite list
   of commands and nothing beyond it.
5. **Did the bot layer declare what the executor asks for?** An unanswered question
   stays silent: that is how a target move failed to reach the broker for a day.
6. **Is the engine looking into the future?** Higher candles closed only, fractals
   confirmed only, levels from closed periods only.
7. **Did this price exist?** Entry and exit must lie inside their own bar, adjusted for
   the side of the market.
8. **Is the intra-bar ordering known?** If not, resolve it against yourself rather than
   conveniently.
9. **Which side of the market was used?** Buy at the ask, sell at the bid; a short's
   stop and target are measured at the ask.
10. **What does the assumption cost?** Zero slippage, instant execution, a constant
    spread — these are assumptions, and the price of each is stated as a number, not in
    words.
11. **Where does the volume come from?** The terminal's instrument spec, rounding down
    to the step, the minimum lot, the account ceilings — at the moment of the signal.
12. **Will the live account agree with a from-scratch recount?** A continued
    computation must produce the same trades, one by one.

Expanded checks per area are in [`CHECKS.md`](CHECKS.md); every rule in one table is in
[`RULES.md`](RULES.md).

### Step 2. Run the guards

First whatever guards the project already has. Then this skill's general guard over a
trade export and a bar series: [`tools/truth-guard.py`](tools/truth-guard.py). It knows
nothing about setup rules and checks only what is true at any broker.

A check is run, not eyeballed. "Should match", "presumably the same", "most likely" are
not proofs.

### Step 3. Audit the numbers

Take every number the engine shows to the outside world and name its origin along the
chain:

```
DATA ─► EVENT ─► SIGNAL ─► ORDER ─► EXECUTION ─► POSITION ─► EXIT ─► P&L ─► METRIC
```

If an error is found at any link, **every number downstream counts as untrustworthy**,
including the innocent-looking ones.

### Step 4. The matrix and the report

Fill in the history-versus-live matrix and produce a report from the template in
[`REPORT.md`](REPORT.md). "Matches" cannot be written without proof: the states "partly
proven", "not proven" and "not applicable" exist and are meant to be used.

### Step 5. A finding becomes a rule and a test

```
FAILURE ─► BREAKDOWN ─► ROOT ─► RULE ─► TEST ─► GUARD
```

One truth failure, one permanent test. The procedure is in [`TESTS.md`](TESTS.md). A new
case is appended to `FAILURE-DATABASE.md`, a new rule to `RULES.md`. The skill is alive:
it is obliged to grow after every finding, otherwise the same failure walks past a second
time.

## Divergence levels

| Level | What it is | What to do |
|---|---|---|
| 0 — none | no divergence | move on |
| 1 — natural | floating spread, ordinary market noise | state the size as a number and move on |
| 2 — uncertainty | not enough data to prove the outcome | mark it unknown, resolve against yourself, record a knowledge gap |
| 3 — computation error | the engine computes something other than what will happen | fix the engine, re-measure the whole chain downstream |
| 4 — reality break | history shows behaviour impossible in live | **block the result**, fix it, recompute the reference |
| 5 — critical | profit, drawdown, risk, trade count or account safety are distorted | **block everything**, say so immediately, declare the previous numbers untrustworthy |

Levels 4 and 5 stop the work: numbers are not served, the change is not promoted, the bot
does not go live.

## Verdicts

- **PROVEN** — every link of the chain checked by a run; no divergences, or only level
  0–1 ones with a number attached.
- **PARTLY PROVEN** — some links checked, the rest named as unchecked.
- **NOT PROVEN** — it could not be checked. This is an honest verdict, not a refusal to
  work.
- **FAILED** — a level-3 divergence was found.
- **BLOCKED** — a level 4–5 divergence was found.

## A separate mode — "I don't know"

If there is nothing to prove the behaviour with, say so. **"I don't know" does not turn
into "probably fine".** Uncertainty is recorded as a knowledge gap answering three
questions: what is missing, how many trades it touches, what would be needed to find out.

Where intra-bar ordering is unknown, the answer is always the cautious one: a trade that
might not have happened is not counted; a stop that might have happened is. Caution costs
money on paper — in one audited engine it took away 119 trades and 116 R — but that money
was never on the account anyway.

## Do not trust the documentation

The source of truth is the **executed code path**. Neither a README, nor a comment, nor a
docstring, nor a spec, nor the developer's intention is a proof.

This is not caution for its own sake. A live example is F21 in the failure database: the
docstring at the top of an engine promised days cut by GMT while the code had been cutting
them by broker server time for several days already. Anyone who believed the docstring
would have started fixing what was already fixed.

## The done criterion

The guard's work is finished only when there is an answer to:

> **Why should I believe these historical numbers can be obtained in live trading?**

with a chain attached where every link is marked "proven" or "not proven":

```
SERIES ─► WHAT WAS KNOWN AT MOMENT T ─► SIGNAL ─► DECISION ─► ORDER
   ─► EXECUTION CONDITIONS ─► POSITION ─► EXIT ─► MONEY ─► METRICS
```

## How the skill keeps itself alive

A skill is a set of instructions, and instructions get skipped: the session ends,
the work did not look like engine work, somebody said "just fix it". Four pieces
of machinery turn this one from a habit into something that holds without anyone
remembering it.

**The gate.** [`tools/guard-hook.py`](tools/guard-hook.py), wired into a project's
`.claude/settings.json`, marks every edit to an engine file and then refuses to
let the turn end until the project's guards have run clean. It is not a reminder
— a Stop hook blocks. The project declares what to watch and what to run in
`.claude/reality-guard.json`. After three blocks the gate lets go rather than
trapping the session, and says loudly that the numbers are unverified when it
does.

**The capture tool.** [`tools/capture-failure.py`](tools/capture-failure.py)
writes a finding into the failure database, the rules register and the test
register in one command, in house style, with the next free codes. The friction
of editing three files by hand is exactly how findings get lost.

**The self-audit.** [`tools/self-audit.py`](tools/self-audit.py) checks the skill
against itself: every failure declares its rules and its test, every code
referenced exists, codes run without gaps, links resolve, both languages carry the
same codes, and the fixture still yields exactly ten findings while staying quiet
on a sound export. It is meant to run before every commit and in CI.

**The private overlay.** Cases that cannot be published go in `local/`, which git
ignores. The skill reads them exactly like the public ones. That is how it runs on
a real desk: public cases for everyone, private cases beside them.

None of this makes the skill self-teaching. It does not watch your runs and it
does not learn on its own — somebody still has to notice a failure and write it
down. What the machinery removes is every excuse for not doing so.

## Files

| File | What is in it |
|---|---|
| `SKILL.md` | this procedure |
| [`FAILURE-DATABASE.md`](FAILURE-DATABASE.md) | real failures with numbers — how engines actually lied |
| [`RULES.md`](RULES.md) | truth rules R01–R41 in one table: symptom and how to prove |
| [`CHECKS.md`](CHECKS.md) | what to check in each area; the history-versus-live matrix |
| [`EXECUTION-CONTRACT.md`](EXECUTION-CONTRACT.md) | what to check against: how a trade is really filled; an example contract and a guard map |
| [`REPORT.md`](REPORT.md) | the report template |
| [`TESTS.md`](TESTS.md) | how a failure becomes a permanent test; the test register |
| [`tools/truth-guard.py`](tools/truth-guard.py) | the general guard over a trade export and a minute series |
| [`tools/fixture/`](tools/fixture/) | the guard's self-check: ten broken trades and four sound ones |
| [`tools/guard-hook.py`](tools/guard-hook.py) | the gate: marks engine edits, blocks the turn until the guards run clean |
| [`tools/capture-failure.py`](tools/capture-failure.py) | writes a finding into all three registers in one command |
| [`tools/self-audit.py`](tools/self-audit.py) | the skill checking itself; runs in CI |

Russian translations of all of the above are in [`ru/`](ru/).

## Self-check

The skill counts as working only if it can catch every one of these: look-ahead bias,
swapped bid and ask, an impossible stop or target, impossible intra-bar execution, a wrong
lot, a wrong risk, a timezone shift, unaccounted latency, state divergence, a run
disagreeing with the live layer.

This is verified not by reasoning but by a fixture: `tools/fixture/` holds ten trades, nine
of them deliberately wrong — one per failure from the database. The guard must find ten
findings there and exit non-zero. **A guard that is always green is not a guard**, and that
applies to every new check the skill adds.

What the skill **cannot** catch today is recorded as knowledge gaps at the end of
`FAILURE-DATABASE.md`: broker refusals, the minimum stop distance, partial fills, real
slippage and live-account latency. Those holes are named on purpose so that nobody mistakes
them for verified ground.

## Reporting style

Short, in the language the person is using, without code in the answer. Say what was done,
not how. Always side by side: before and after, with the latest year on its own line, and in
the columns — besides trade count, total R and drawdown — the win rate, the longest run of
stops and the longest run of targets. Name your own mistakes immediately and recompute
rather than fixing them quietly.

Check numbers for plausibility before sending: identical columns, suspiciously round values,
impossible account growth — all reasons to stop and dig rather than send.
