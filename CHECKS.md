# Checks by area

The order is not accidental: a failure at the top makes every check below it
meaningless. If the series has not been reconciled, there is no point auditing
execution — the execution was computed on an invented market.

Every item ends with the same question: **what proves it?** The answer is "this
run", "this reconciliation", "this measurement, with this number". The answer
"you can see it in the code" does not count — unless the file and line are named
and the computation itself is quoted.

---

## 1. Data

- Where the series came from, who reconciled it, when, and against what.
- Is there exactly one series in the project? If several, which one went into the
  measurement, and why that one.
- Timestamps: timezone, step, monotonicity, duplicates.
- Bar integrity: high above both open and close, low below both, high above low.
- Gaps: are they all listed, does each have a stated reason, is a weekend told
  apart from a nightly break and from a hole?
- Spread: is it in the series at all, is it live or one number for all history,
  which terminal is it from?
- Volume and tick volume: present, used in the rules, reconciled?
- **The question that rules this area:** was this data available to the bot at
  the moment it is being used to make a decision?

Rules: R01, R02, R03, R04, R05.

## 2. Time

- Whose clock cuts days, weeks, months and four-hour candles: GMT, the broker
  server, local time?
- Where do the daylight-saving dates come from — read off the terminal or guessed
  from a country's rules? A broker server may switch on a different date than the
  country it sits in.
- Sessions: computed with a fixed offset? Do they account for weekdays?
- Market boundaries: open, close, breaks, shortened holiday sessions.
- Are human-facing labels kept apart from candle boundaries?
- **The question that rules this area:** does the candle grid match the terminal
  bar for bar, on every timeframe the rules touch?

Rules: R06, R07, R08.

## 3. Knowledge of the future

- For every signal, name the **moment of decision** and list what was known at
  that instant.
- Confirmations that arrive later — fractals, structure points, "the candle
  closed above" — when do they become known, and when does trading act on them?
- Derived series: built all at once over the whole history, or accumulated? The
  last candle of such a series is already full inside a run.
- Indicators: are they recomputed retroactively, is there repainting?
- News calendars and marks: do they grow backwards?
- **The trick that catches look-ahead better than anything:** run the same series
  through the live layer one bar at a time and compare with the batch run's list.
  A run that sees fewer stops at the same number of targets is peeking.

Rules: R09, R10, R11, R12.

## 4. Inside the bar

A historical candle shows open, high, low, close. It does **not** show the order
in which price visited them.

- Are there bars that touched both stop and target? How many, how was the outcome
  decided?
- Was a descent to minutes actually made, or was the order assigned by
  convenience?
- Is the share of undecidable cases stated as a number?
- Is the unknown resolved against yourself: a trade that might not have happened
  is not counted, a stop that might have happened is?
- Is an order's fate decided at the moment of the event or at the candle close?
- Do stop and target moves take effect from the next minute?
- Is intra-bar time measured from the right event, not from the start of the
  candle?

Rules: R13, R14, R15, R16.

## 5. Order execution

- The moment the order appears at the broker is separated from the moment the
  signal is born.
- Market entry: at the close of the signal candle, or at the open of the next one?
- Pending order: from which minute can it fill, and how long does it live?
- Cancellation: when is an unfilled order withdrawn, what happens to it when the
  server day rolls over?
- The broker will accept it: a buy stop below price, a sell stop above; minimum
  distance respected.
- The execution price existed: entry and exit inside their own bar, adjusted for
  the side of the market.
- Refusals: are they modelled at all? Temporary told apart from final?
- Latency: is the path signal — decision — command — broker — fill named, with a
  time for each step?
- Contract: the engine asks only for what the executor can do; the bot layer
  answers everything the executor asks.

Rules: R17, R18, R19, R20, R21, R22, R23, R24.

## 6. Spread

Spread is the one lawful source of divergence that is allowed to change. That
does not mean it can be left out of the count.

- Is it accounted for at all, and on which side of the market?
- Buy at the ask, sell at the bid; a short's stop and target measured at the ask.
- The quote broker's spread and the trading broker's spread are different numbers;
  is the scale translated between them, and is that kept apart from trading
  decisions?
- Is spread counted twice — once inside the engine and once by an outside
  adjustment?
- Is the historical spread live, or substituted by a single number?
- If spread affects the outcome, the effect is measured in R, not described in
  words.

Forbidden answer: "well, in live the spread will just be a bit different".

Rules: R25, R26, R27.

## 7. Stop and target

For every position:

- when the stop was placed, when the target, at what price;
- could such an order have existed at the broker at that moment;
- the order of execution if a bar touched both;
- price gaps: what happens when the open is already beyond the stop;
- moves: how many, when each took effect;
- partial close: what volume the share is taken from, what happens to rounding,
  what if the remainder is below the minimum lot.

Bars whose high is above the target and whose low is below the stop at the same
time get the strictest treatment. The convenient outcome is never assumed.

Rules: R16, R19, R23.

## 8. Position size and risk

- Balance and equity: where they come from, how fresh they are.
- Risk share, distance to stop, tick value, contract size.
- Minimum lot, lot step, ceiling; rounding down.
- Leverage, margin, free margin, currency conversion.
- Ceilings: per trade and for the whole account, checked at the moment of the
  signal.
- Slippage allowance: is there one, for whom, what number, where did the number
  come from?
- The risk formula is proven not only by arithmetic but by the broker's behaviour:
  the instrument spec comes from the terminal, not from constants in the code.

Rules: R30, R32, R31.

## 9. State

List the states and reconcile them between the run and the live layer: flat,
waiting, triggered, position open, stop moved, share taken, target reached,
closing, closed, rejected, cancelled.

- The continued live account against a from-scratch recount, trade by trade.
- Hunt for cases where the run thinks a position is open and the live layer thinks
  it is closed, and the other way round.
- Duplicates: two positions with the same key.
- A disagreement with the terminal raises an alarm instead of being quietly fixed.
- An open trade is managed by the rules of its own version.

Rules: R33, R34, R35, R37.

---

## The history-versus-live matrix

Filled in completely. An empty cell means "not proven", not "fine".

States: **proven**, **partly proven**, **not proven**, **failed**, **not
applicable**.

| Link | In history | In live | State | Proven by |
|---|---|---|---|---|
| Bar series | | | | |
| Bid | | | | |
| Ask | | | | |
| Spread | | | | |
| Candle markup | | | | |
| Moment of signal | | | | |
| Moment the order reaches the broker | | | | |
| Entry price | | | | |
| Stop | | | | |
| Target | | | | |
| Stop moves | | | | |
| Volume | | | | |
| Risk | | | | |
| Commission and swap | | | | |
| Slippage | | | | |
| Latency | | | | |
| Position state | | | | |
| Exit | | | | |
| Trade result | | | | |
| Balance | | | | |
| Equity | | | | |
| Drawdown | | | | |

---

## Number audit

Find **every** number the engine shows to the outside world and walk each one
back along its chain of origin:

```
DATA ─► EVENT ─► SIGNAL ─► ORDER ─► EXECUTION ─► POSITION ─► EXIT ─► MONEY ─► METRIC
```

Numbers that must pass the audit: number of trades, entry and exit points and
prices, stop, target, volume, risk, profit, loss, reward-to-risk, commission,
spread, slippage, maximum drawdown, longest run of stops and of targets, win rate,
profit factor, average win and average loss, time in position, order of trades,
order in which stop and target were hit, final balance and equity.

**The propagation rule.** An error at any link makes every number downstream
untrustworthy. Not "slightly off" — untrustworthy: they cannot be shown until the
chain has been recomputed.

**A plausibility check before sending.** A column where every value is the same.
Suspiciously round numbers. A win rate that does not move when the rules change.
Account growth impossible at the stated risk. An implausible pile of flat zeros.
Stops at exactly −1.00 R one hundred percent of the time. Any of these is a reason
to stop and dig, not to send.

---

## The live mirror

If a live or demo account is available, put the same situation through both roads
and compare stage by stage:

```
MARKET STATE ─► SIGNAL ─► ORDER ─► EXECUTION ─► POSITION ─► EXIT ─► MONEY
```

Compare not the bottom line but every link: signal timestamp, command timestamp,
fill timestamp, price, volume, stop, target, every move, reason for exit. A
disagreement at any link is traced to its root, even if the bottom line happened
to match.

**Keep two kinds of divergence apart.** An entry at 2650.00 in the run and at
2651.20 in live because bid and ask were swapped is an engine error. The same gap
caused by an unexpected news spike is a market event. The first gets fixed, the
second gets a number and stays. Writing the first off as the second is forbidden.
