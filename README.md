# Reality Truth Guard

**A Claude skill that audits your trading engine, not your strategy.**

A pretty backtest means nothing if its mechanism does not match real execution. A win
rate means nothing if some of the trades exist only because the engine looked into the
future. Profit means nothing if the entries could never have been obtained.

> Do not check whether the strategy works. Check whether the engine tells the truth.

*[Русская версия](ru/README.md) — полный перевод документации в папке [`ru/`](ru/).*

---

## Why it exists

This skill is not assembled from theory. It comes from auditing real live trading
engines. Three findings in a row, over two weeks, on three different systems:

| What was found | Before | After |
|---|---:|---:|
| an order's fate decided once per candle instead of at the event | **+5874 R** | **−1016 R** |
| a fractal confirmed by the next candle, while trading happened inside it | **+1350 R** | **−423 R** |
| a fill inside the very minute whose close produced the signal | **+672 R** | **+205 R** |

Not one strategy rule changed in any of them. Only the engine's arithmetic did.

All twenty-three cases, with numbers, roots and symptoms, are in
[`FAILURE-DATABASE.md`](FAILURE-DATABASE.md). System names are removed; the numbers are
real.

## What is inside

| File | What is in it |
|---|---|
| [`SKILL.md`](SKILL.md) | the procedure: when to engage, twelve questions of live execution, verdicts, divergence levels |
| [`FAILURE-DATABASE.md`](FAILURE-DATABASE.md) | 23 real failures with numbers — how engines actually lied |
| [`RULES.md`](RULES.md) | truth rules R01–R41: the symptom of each failure and what proves it |
| [`CHECKS.md`](CHECKS.md) | what to check in each area; the history-versus-live matrix; the number audit |
| [`EXECUTION-CONTRACT.md`](EXECUTION-CONTRACT.md) | what to check against: 14 questions for the executor, an example contract, a guard map |
| [`REPORT.md`](REPORT.md) | the report template: verdict, what is proven, what is not, what to do |
| [`TESTS.md`](TESTS.md) | how a failure becomes a permanent test; the register of tests and debts |
| [`tools/truth-guard.py`](tools/truth-guard.py) | a guard over a trade export and a bar series — works without Claude |
| [`tools/fixture/`](tools/fixture/) | the guard's self-check: ten trades, nine deliberately wrong |
| [`ru/`](ru/) | the full Russian translation |

## Installing the skill

A skill is just a folder of files. Claude picks it up on its own.

**For every project:**

```bash
git clone https://github.com/kopsov/reality-truth-guard.git ~/.claude/skills/reality-truth-guard
```

**For one project only** — put it in that project's `.claude/skills/`:

```bash
git clone https://github.com/kopsov/reality-truth-guard.git .claude/skills/reality-truth-guard
```

Update later:

```bash
cd ~/.claude/skills/reality-truth-guard && git pull
```

That is all. Claude engages the skill by itself as soon as the work touches an engine, a
run, execution, stop and target, position size, spread, time or a quote series. You can
also call it explicitly: "audit this with the truth guard".

## The guard also works without Claude

[`tools/truth-guard.py`](tools/truth-guard.py) is a plain Python script with no
dependencies. It knows nothing about your setup rules and does not want to: it checks
only what is true at any broker on any market.

```bash
python3 tools/truth-guard.py --trades trades.csv --bars minutes.csv
```

It recognises columns on its own — MetaTrader exports, English and Russian names, comma,
semicolon and tab. If your names are unusual, declare them with `--map map.json`.

| Option | What for |
|---|---|
| `--broker-day eet-us` | days by broker server time — checks pending-order lifetime |
| `--spreads 2` | how many bar spreads a price may sit outside its bar |
| `--point 0.01` | point size, when the series records spread in points |
| `--lot-step`, `--min-lot` | the broker's volume rules |
| `--min-stop` | the broker's minimum stop distance |

What it checks: series integrity and a census of gaps, fills that are not earlier than
and not inside their own signal minute, pending-order lifetime, the sides of stop and
target, whether the entry and exit prices existed in their own bars, bars that hit both
stop and target, duplicates inside a stream, whether the R result agrees with the prices,
lot-step compliance, the share of trades landing at exactly −1 R, and how many positions
were open at once.

The result is `FINDINGS: N` and exit code 1 if any check failed. Checks whose columns are
missing **do not stay silent**: they are printed as a separate list of knowledge gaps,
never as "all good".

## Self-check

A guard that is always green is not a guard. [`tools/fixture/`](tools/fixture/) holds ten
trades, nine of them deliberately wrong — one per failure from the database:

```bash
python3 tools/truth-guard.py \
  --trades tools/fixture/trades-broken.csv \
  --bars tools/fixture/bars.csv \
  --broker-day eet-us --lot-step 0.01 --min-lot 0.01
```

Expected: ten findings and exit code 1. Fewer means the guard has gone blind; more means a
false alarm has appeared, and it must be investigated as strictly as a missed failure.

## Limits

The skill says "I don't know" honestly and does not turn that into "probably fine". What
it cannot do today is recorded as knowledge gaps at the end of the failure database:
broker refusals, the minimum stop distance, partial fills, real slippage and live-account
latency. Those holes are named on purpose so nobody mistakes them for verified ground.

And the thing worth understanding up front: **numbers almost always get worse after an
honest audit.** That is the skill working, not breaking.

## Contributing

Found a truth failure that is not here? Send it to the failure database in the same shape
as the rest: what happened, what it cost in numbers, the root, the rule that follows, and
the run that proves it. A case without numbers is an impression, not a failure.

## License

MIT — see [LICENSE](LICENSE). Use it, change it, embed it.
