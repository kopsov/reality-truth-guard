# The execution contract — how a trade is really filled

The guard needs something to check against. This document is that something: **a
written answer to what happens to an order from the birth of a signal to the entry
in the journal**, taken off the executor's code rather than off its descriptions.

Without such a contract an audit turns into two opinions arguing. With it, it
becomes a reconciliation.

The contract is written once per engine–executor–broker triple, and it is
rewritten first as soon as the executor changes. Otherwise the guard starts
checking against the past and stays green when it should not.

---

## What the contract must state

Fourteen questions. A blank answer is not "unimportant" — it is the first hole the
run will fall into.

1. **The path of a trade.** Who computes, who sends, who places the order, who
   talks to the broker. Where the boundaries between them run.
2. **What the executor can do.** The exact list of commands. An engine asking for
   anything beyond that list is asking for the impossible.
3. **The moment an order may fill.** Not "on the signal", but to the precision of a
   bar or a minute.
4. **The price a market order fills at.** The close of its own candle and the open
   of the next one are different numbers, and the difference compounds across the
   whole series.
5. **How long each command lives.** Each has its own expiry, and an expired one
   does not execute.
6. **Where stop and target live.** As orders at the broker, or in the memory of
   whatever is computing. This decides what happens when the connection drops.
7. **When a stop move takes effect.** Until the command arrives, the broker still
   holds the old level.
8. **Which refusals exist**, and which of them are temporary and which final.
9. **How volume is computed.** Where contract size, lot step, minimum and maximum
   volume come from, how it is rounded, what happens when margin runs short.
10. **How spread is computed** and on which side of the market. Separately: the
    translation between the scales of two brokers, if quotes come from one and
    trading happens at another.
11. **How slippage is accounted for** and who knows about it — the engine or the
    executor.
12. **What the latency is** at each step of the path, measured rather than assumed.
13. **What happens when the rule version changes** mid-position.
14. **Who counts as the source of truth** about a trade when records disagree.

---

## An example contract

Below is a real contract of one live setup, taken off its code. Names have been
removed, but every decision and number is genuine. It is here not as a template to
copy but to show how detailed a contract has to be before it is of any use.

### The path of a trade

```
MINUTE SERIES ─► ENGINE ─► SERVER (command) ─► EXPERT ADVISOR IN THE TERMINAL ─► BROKER
```

Quotes arrive by a separate road: a source advisor on its own terminal sends bars
and spread. The brain sits on the server, the hands sit on the participant's
machine.

### Five commands, and nothing beyond them

The executor can do exactly five things with a position: **market entry**,
**pending order**, **stop move**, **close**, **close a share**.

### Command expiry

The advisor may go silent — the computer is off — and commands pile up. Hence an
expiry for each:

| Command | Lives |
|---|---|
| market entry | until the close of the next bar of the bot's timeframe |
| pending order | until the end of the day by broker server time |
| stop move | until the end of the day by broker server time |
| close | one day |
| close a share | one day |

An expired command **does not execute**: it is marked skipped with a reason. An
expired close raises an alarm.

A run that holds an order longer than this trades trades that will not exist.

### The moment an order may fill

The decision is made at the close of a minute. The executor sends the command
**after** it. Therefore:

- there is nothing to fill inside the signal minute itself;
- a market order enters **at the open of the next minute**, not at the close of its
  own;
- a pending order rests at the broker and may trigger from the next minute onward.

### Stop and target live at the broker

The levels travel as fields with the entry command and then stand as orders inside
the terminal itself. The broker will close on them even if the server is off and
the advisor is silent. The server does not watch price and never sends a close on a
level being reached.

Hence something important: **until the move command reaches the terminal, the move
exists only on paper — the broker will close at the old level.**

### Ordering and protection against repeats

The server assigns the command number: an integer, increasing. That same number
sets the execution order and the protection against double execution. Commands
travel to the advisor in ascending order and repeat until the server sees their
outcome in a report.

### Broker refusals

A refusal is a normal outcome of an order, not an impossibility.

| Refusal | What it means | What the executor does |
|---|---|---|
| stop too close | the broker will not take the level: too near price, or on the wrong side | the refused stop is resent **as a target** |
| no connection, autotrading off, trading not allowed, broker refused | trouble with the link or at the broker | asked again on the next bar |
| share too small, no position, command not understood, advisor ceiling | final | not asked again; the position is managed whole |

None of the engines audited models any of this: in a run every order is accepted
first time.

### Volume

- Tick value per lot, minimum volume, step and ceiling are reported by the
  **terminal** as an instrument spec. The server holds neither contract sizes nor
  exchange rates: computing them yourself means disagreeing with the terminal by an
  order of magnitude one day.
- Rounding is **down** to the volume step. The honest risk after rounding is
  recorded next to the intended one.
- Volume below the minimum lot is a failure with an explanation, not "let us place
  whatever fits". Above the instrument ceiling it is trimmed to the ceiling.
- Risk ceilings per trade and for the whole account are checked **at the moment of
  the signal**, for every way of expressing risk: a share of balance, a fixed lot,
  a cash amount.
- One risk distance for all three.
- On top of that the advisor will trim volume to free margin and the broker's own
  rules and report what actually happened. Quietly substituting the executed for
  the intended is not allowed: the journal records the difference.

### Spread

Two different adjustments, and they must not be confused.

**Scale translation.** The bid is the middle of the market minus half the spread.
At a broker with a wider spread the whole chart sits lower. This is not a trading
decision but a conversion of a number from one scale into another; it applies to
everyone and to both sides, and equals zero at the quote broker.

**The ask on a short.** A short is closed by buying, that is at the ask, which sits
above the bid by exactly one spread. The adjustment puts the trigger back where the
engine computed it, and it costs money: every losing short is dearer by exactly one
spread. It goes not to everyone but by name.

**Only the advisor sees its own broker's spread** — it alone talks to the broker and
takes the spread at the instant of placement. Two numbers travel to it: the source
spread (the scale the stop was computed in) and a shift ceiling — in news seconds
the spread blows out, and shifting by its full size would push the stop absurdly far.

**One exception: an engine for which spread is part of the setup rules.** If the
stop already leaves moved by two spreads and the short already closes at the ask
inside the engine itself, the second adjustment never applies to it. Switching it on
would move the stop a second time for the same spread.

**The minute's spread lies next to its bar**, not as one number for all history. The
source is the same terminal as the bars. The few minutes before the next catch-up
are computed at the last known spread — as they are in live.

### Slippage

The allowance lengthens the risk distance: volume is computed from "distance to
stop plus allowance". Risk in money stays the same, the lot comes out smaller, and a
stop with ordinary slippage returns to one R.

**The allowance never touches the orders:** entry price, stop and target go to the
broker exactly as the engine sent them. The engine knows nothing about the allowance
and must not.

The numbers are starting ones: 0.5 in instrument price on gold for two engines with
a short stop. The real ones are taken from live stops, per instrument. A stream whose
average stop is 1.12 $ needs a number of its own.

### Latency

Measured on a demo link: **about 12 seconds** from bar close to a filled order,
almost all of it the advisor's polling step of 5 seconds. Not re-measured on a live
account.

### The trade's version

Computation follows the current rule version and reconfigures itself as soon as it is
changed. But **an open trade is managed by the rules of its own version**: a shadow
engine is spun up with that version's parameters, warmed on the same window of bars.
It produces no signals — it is asked only where the stop is now and whether the share
has been taken.

Any change to the engine's code changes the release fingerprint, and the executor
creates a new bot version by itself. Trades before and after a change are trades of
different bots.

### The truth about a trade

Our view is a row in a database. The truth is the terminal's report. If they
disagree — alarm, not a silent correction: a silent one would erase the trace of
somebody touching the trade by hand. The full report goes to reconciliation first and
is taken as truth only afterwards.

### The environment

Two environments: live and sandbox. The environment decides which accounts it works
with. The sandbox does not issue commands to live accounts — not by a setting, but
because it refuses to serve a live account at all.

---

## The guard map

The second half of a contract is the list of **what checks each of its promises**.
It is written for your own project; below are the kinds of rows it should contain.

| What we check | By what |
|---|---|
| the run computes what will happen at the broker | the project's battle guard plus this repository's guard |
| an engine change moved nothing silently | reconciliation against the reference snapshot, field by field |
| the contract with the executor is intact | reconciliation of the command list and of the questions the executor asks the bot layer |
| the live layer computes what a from-scratch recount does | trade-by-trade reconciliation, stops included |
| the display's candles match the terminal | reconciliation by open time, high and low on every timeframe |
| how much series the engine needs | a depth measurement |
| a continued computation equals a single-pass one | reconciliation at several points in history |
| higher candles assembled from minutes equal the higher-candle file | a separate reconciliation: the live bot assembles them itself |
| the series is intact and fresh | a series watchdog and a quote freshness watch |

The rule is simple: **every clause of the contract must have a row in this map.** A
clause without a row is a promise nobody checks.
