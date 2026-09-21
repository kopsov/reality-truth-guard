# Failure database — the ways engines have already lied

These cases are real. Each was found while auditing live trading engines, and each
carries its own numbers. There are no invented examples here.

System names have been removed on purpose: they add nothing to the lesson. In their
place is a short description of what the engine does, because the failure that
sticks to an engine depends on how it is built.

The cast:

- **the zone engine** — gold, imbalance zones on five higher timeframes, entry on a
  minute inversion, spread built into the setup rules;
- **the grid engine** — a grid drawn from an extremum confirmed by a three-candle
  fractal;
- **the add-on engine** — two limit orders with a short target, stop at the grid
  zero;
- **two engines with a short stop** — grids on the 15-minute and the 5-minute;
- **the executor** — whatever sits between the engine and the broker: a server that
  computes, an expert advisor inside the terminal that places orders.

Read this before any audit: a failure is almost never new.

**The cost, in summary.** Three findings in a row, over two weeks, moved the numbers
of three different engines from **+5874 R to −1016 R**, from **+1350 R to −423 R**
and from **+672 R to +205 R**. In none of them did the strategy change — only the
engine's arithmetic did.

---

## F01 — Days cut by GMT instead of broker server time

**Where.** The zone engine.

**What happened.** The engine cut the day by UTC; the broker cut it by its own
server (EET/EEST). The two Sunday opening hours became a separate daily candle. The
four-hour grid was pinned to UTC midnight while the broker pinned it to its own
days. Sessions were computed with a fixed offset and no daylight-saving switch at
all, so all four of them sat an hour wrong in winter.

**The cost.** 1229 daily candles against the broker's 1021 — 209 extra. 315 daily
imbalances against 239 real ones: 101 matched, 214 invented, 138 never seen. Over
five months **not one** four-hour candle out of 630 matched — meaning every 4h zone
stood on wrong boundaries. With the correct cut, 238 out of 239 matched. The engine
had been building zones on candles that never existed for over a year, and decisions
were being made on them.

**What matters here.** The minute data was clean: daily candles built from it with
the correct cut matched the broker across all 1019 days, with highs and lows
differing by exactly 0.00. **The failure was not in the data but in the markup.**
Clean data proves nothing until the grid has been reconciled.

**Root.** Period boundaries taken from a convenient calendar instead of the broker's.

**Rules.** R06, R08. **Test.** T-01.

---

## F02 — A seasonal offset taken from one candle and applied to four years

**Where.** The zone engine's display — the page where the owner looks at trades.

**What happened.** The page builder converted 15-minute timestamps into local time
with a single offset read off the very first bar of the series (winter, +2 hours),
and that offset stood for all four years. Summer needs +3, so every summer candle sat
an hour to the left of the truth, and higher timeframes — assembled from 15m by
"timestamp minus remainder" — were cut somewhere other than where the engine and the
terminal cut them.

**How it was found.** The owner looked at one trade with his own eyes and said the 4h
zone was not inside any gap. In the terminal the zone was marked up correctly. The
picture was lying.

**The cost.** Trade numbers untouched: the engine computes on its own candles. But
decisions were being made from the picture, and the picture showed a different
market. After the fix the reconciliation returned zero divergences across all five
timeframes: M15 88 122, M30 44 068, H1 22 046, H4 5 769, D1 962.

**Root.** An hourly offset treated as a constant where it is a function of time. The
display was considered "just a picture" and reconciled against nothing.

**Rules.** R07, R08. **Test.** T-02.

---

## F03 — A breakeven order the broker would not accept

**Where.** The zone engine.

**What happened.** Moving the stop to the entry price was done unconditionally,
without looking at the current price. If price stood worse than the entry, such a
stop ended up on the wrong side of the market. A broker rejects that order; in the
run it triggered in the same minute and was recorded as a flat zero.

**The cost.** 301 breakevens out of 2885 trades (10.4 %): 120 out of 521 on the
opposing zone (23.0 %), 163 out of 329 on one kind of rejection (49.5 %), 18 out of
562 on another. All closed in the same minute as the move. The market meanwhile stood
worse than the entry by 0.35 of risk on average, median 0.26, worst case 1.73. In
seven cases the move minute also touched the old stop — a zero was written instead of
a full loss.

After the fix: 2885 trades and +671.97 R at −15.35 drawdown and a 42.6 % win rate
became 2843 and **+574.46** at −18.35 and 40.3 %. The series lost 97.5 R of painted
profit.

**The symptom that works everywhere.** An order triggers in the very minute it is
placed.

**Root.** The engine computed an outcome from an order that is impossible in live.

**Rules.** R19, R16. **Test.** T-03.

---

## F04 — Orders filling inside the very minute whose close produced the signal

**Where.** The zone engine. Found by an audit the day after F03; it turned out to be
larger.

**What happened.** A signal is born at the close of a minute, and the executor sends
the command to the broker after it. The engine, however, filled its limit order on
the movement of that very minute. A market entry was computed at that minute's close,
although it fills at the open of the next one. A pending order lived up to two days in
the run; at the broker it lives until the end of the server day.

**The cost.** 928 entries out of 1570 (**+391.76 R**) were taken with hindsight. The
whole series: 2843 trades and +574.46 R at −18.35 drawdown and a 40.3 % win rate
became **2629 and +205.15** at −42.26 and 34.5 %, longest run of stops 11 → 15. For
the latest year: 685 and +219.22 at −14.02 → 638 and +135.80 at −13.88, profit factor
1.81 → 1.47. Half the profit of the series rested on orders the broker did not yet
have. The setup was rebuilt from the new numbers afterwards.

**Root.** The moment an order appears at the broker was never separated from the
moment the signal is born.

**Rules.** R17, R18. **Test.** T-04.

---

## F05 — The confirmation arrives on the next candle, and trading happens inside it

**Where.** The grid engine, while building its live layer for the executor.

**What happened.** The extremum is a three-candle fractal, so the grid zero is
confirmed by the **next** candle. The batch run created the grid with hindsight and
traded inside that confirming candle. A live bot cannot wait for it: the order has to
be placed before it closes.

**The cost.** Over a year, 1481 entries out of 1919 (77 %) happened inside the very
candle that confirms the zero. The live layer sees all 1919 grids of the run plus
another 2487 whose zero was never confirmed by the next candle — almost all of them
stops.

| | run's list | live engine |
|---|---:|---:|
| closed trades | 1596 | 4015 |
| target / stop | 623 / 973 | 666 / 3349 |
| share of targets | 39.0 % | 16.6 % |
| total R | **+1350.3** | **−423.0** |
| profit factor | 2.65 | 0.81 |
| drawdown | −10.5 | −423.1 |
| stops in a row | 9 | 25 |

The live engine takes almost the same number of targets (666 against 623) — the run
never lost those. **It does not see the stops: 973 against 3349.** The second reading
— wait for the confirming candle and trade only confirmed grids — leaves 438 grids out
of 1919 and +5.6 R, which is zero.

**Conclusion.** The reference numbers are not reproducible by live trading under
either reading.

**The symptom that works everywhere.** The run sees noticeably fewer stops than the
live layer at roughly the same number of targets.

**Root.** A confirmation that comes from the future relative to the entry.

**Rules.** R09, R10. **Test.** T-05.

---

## F06 — An order's fate decided once per candle instead of at the event

**Where.** The add-on engine. The most expensive finding of them all.

**What happened.** The engine decided a grid's fate once per candle, at its close. If
the candle went beyond the grid zero, it buried the grid together with the resting
limit order — no trade appeared in the numbers at all. At a broker that order rests
and fills: price reaches the zero by travelling through the limit price.

**The cost.** A minute-level breakdown of event ordering across the whole history:

- **4333 buried orders** — 17.6 % of the hourly limit orders placed and 19.9 % of the
  15-minute ones. By the minutes, 3331 would have exited at stop, 439 would have taken
  target, and for 563 the intra-minute ordering is unknown. There is not one case
  where price reached the zero without passing the limit.
- **1040 add-ons** taken after the first position had left: cancelling the add-on by
  the minute never saw the case where the first entered and left within one candle.
- **164 entries** where price went beyond one grid unit before touching the limit — by
  then the order had been withdrawn.

The result: **+5874.49 R** and 68.4 % targets became **−1016.05 R** and 44.6 %.
Drawdown −14.00 → −1078.13. One profitable year out of nine remained. On another
instrument under the same rules: +4881.80 → −1662.68.

**How the unknown ordering was resolved.** Against itself: a trade that might not have
happened is not counted; a stop that would have happened is. That caution touched 119
trades worth −116.22 R — meaning the minus comes from the hole, not from the caution.

**Root.** Intra-bar events collapsed into a single decision at the candle close.

**Rules.** R13, R14, R15. **Test.** T-06.

---

## F07 — The exit minute searched from the start of the candle instead of from the entry

**Where.** The add-on engine, setup audit.

**What happened.** The arbiter looked for the minute the first position left starting
from the beginning of the entry candle. An add-on that entered before the first
position actually left was discarded as "too late".

**The cost.** "Too late" on the 15-minute went 1126 → 163, on the hourly 144 → 90;
add-ons in the numbers 6420 → 7308; total **−1016.05 → +39.65 R**. An intra-bar timing
error took a thousand R in one direction and gave it back in the other.

**Found alongside, by the same audit.** 1354 surplus positions — duplicates inside one
stream (same timeframe, side, entry, stop, candle), 1145 of them from two
approximations coinciding. And 403 lone add-ons whose first order had been filtered
out, which a live bot would have placed: 139 targets, 261 stops, −94.50 R.

**Root.** Intra-bar time measured from the wrong event.

**Rules.** R13, R35. **Test.** T-07.

---

## F08 — A hole in the quote series that nobody saw

**Where.** The zone engine's series.

**What happened.** In a series of 1 401 956 minutes across 1233 trading days there is
not one minute for a little over a day — about 1500 of them — although those days
traded in full. Every other gap was examined and found lawful. It later turned out the
hole sits in the broker's own archive.

**Why it is a failure.** A missing trading day is invisible in a run: it does not break
anything and prints no warning. It simply changes the markup and the trades further
along the series. Every number of the project was computed on a series with that hole.

**Root.** Completeness of the series was never checked minute by minute against the
terminal.

**Rules.** R02, R01. **Test.** T-08.

---

## F09 — The quote source delivered emptiness for a day and the system showed "all good"

**Where.** The executor.

**What happened.** The source had the instrument name configured without the broker's
suffix. For a whole day it delivered empty batches, the server answered "accepted",
and nothing lit up anywhere. Later the source's own words "market closed" muted every
other rule of the watch and stayed silent for three and a half hours during a genuine
hole in the series.

**How it was fixed.** Two tiers: the reason is asked of whoever has it, and beyond that
we judge by the instrument's own habit — were bars arriving exactly a week ago at this
same instant? The words "market closed" are no longer believed unconditionally.

**Root.** Absence of data taken for absence of trouble.

**Rules.** R02. **Test.** T-08.

---

## F10 — In a run every stop costs exactly −1R; in live it does not

**Where.** Two engines with a short stop.

**What happened.** The grid's stop sits at the zero and the entry at 0.145 of its
width, so the stop is short by construction: the median stop on 15-minute gold is
2.9 $, and 0.8 $ happens. In an impulse such a stop fills with slippage.

**A live example.** Long 0.15 lots at 4307.96, stop at 4306.32 (1.64 $), filled at
4305.03. Slippage 1.29 $, loss **1.87 R instead of 1.00**.

**The price of the assumption, as a number.** At 0.2 $ of slippage on every stop the
first engine's total risk shares over eight years: +3090 with no allowance, +2282 at an
allowance of 0.3 and +1979 at 0.5; for the latest year +359, +325 and +307. The second
engine, on its trades for the year (1310 trades, 613 stops): +1024.7, +870.9 and
+794.4. Dearer for the second one because its stop is shorter: on the 5-minute it
averages 2.33 $, and half the trades are below 1.88 $.

**How it was solved.** Volume is computed from "distance to stop plus allowance"
instead of from the distance to the stop. Risk in money is unchanged, the lot comes out
smaller, and a stop with ordinary slippage returns to one R. The orders do not change by
a single number. The allowance lives in the executor; the engine knows nothing about it.

**Root.** Zero slippage taken as a fact instead of an assumption.

**Rules.** R28, R32. **Test.** T-09.

---

## F11 — The same market drawn at different heights by two brokers

**Where.** The executor.

**What happened.** The engine computes on the bid — the price the chart draws. The bid
is the middle of the market minus half the spread, so at a broker with a wider spread
the whole chart sits lower.

**The measurement.** 60 thousand minutes of gold: the spread at the quote broker 0.23 $,
at the broker where the advisor runs 0.32 $, difference 0.09 $, half of it 0.045 $, the
observed offset between the series 0.04 $ — it adds up. The low of a minute at the second
broker is lower than at the first **in 86 cases out of a hundred**. A long's stop placed
at exactly the number sent is knocked out there earlier than computed.

**A separate second thing.** A short is closed by buying, that is at the ask, which sits
above the bid by exactly one spread. A short's stop placed at exactly the number sent
triggers earlier than computed — and this is true at any broker.

**The important bit about double counting.** An engine for which spread is already part
of the setup rules — the stop leaves already moved by two spreads inside the engine
itself — must never get the second adjustment. Switching it on means moving the stop a
second time for the same spread.

**Root.** One broker's price scale taken for another's; the side of the market not
distinguished.

**Rules.** R25, R26, R27. **Test.** T-10.

---

## F12 — One spread for the whole history instead of the live one

**Where.** The executor and the zone engine.

**What happened.** The executor's quote series had no spread column at all, so it told
the engine one source spread, which the engine applied across the whole warm-up history.
And for that engine spread is part of the rules: the stop is moved by two spreads, the
short closes at the ask, and no entry is taken when the stop is already eight of that
minute's spreads away.

**The cost.** Reconciling the engine against the platform gave **+195.77 R for the year
against +205.46** on the engine's own page. The owner's words: "I need an honest estimate,
not a cautious lower bound."

**What matters here.** An understated number misleads exactly as much as an overstated
one. A truth guard is not looking for "less profit" but for "the right profit".

**Root.** A varying quantity replaced by a constant for storage convenience.

**Rules.** R05, R38. **Test.** T-11.

---

## F13 — An unclosed higher-series candle is already full inside a run

**Where.** The zone engine, the first measurement of a new rule.

**What happened.** The 3m, 5m, 15m and higher series are built across the whole history
at once, and in a run the last, still-unclosed candle already contains all of its minutes
— four minutes of the future. In live it is only filling up.

**The cost.** The first measurement gave the year **+212.81 R instead of an honest
+196.93**.

**How it was caught.** Not by eye and not by a look-ahead test, but by reconciling the
continued live account against a from-scratch recount: they disagreed by one trade. A
disagreement in that reconciliation is a reason to hunt for peeking, not to write off as
a detail.

**Root.** A derived series built in one pass where in live it accumulates.

**Rules.** R11, R33. **Test.** T-12.

---

## F14 — The bot layer never declared what the executor asks for

**Where.** The zone engine and the executor.

**What happened.** A rule moves the target onto the entry price. The executor asks the
bot layer for the current target, but the layer never declared it, so the question went
unanswered. **The target move failed to reach the broker for a day**: in the run the
target had moved, on the account it had not.

**Root.** The contract between engine and executor was never checked as a whole.

**Rules.** R21. **Test.** T-13.

---

## F15 — Volume: rounding, minimum lot and the account ceiling

**Where.** The executor.

**What exists, and why.**

- Tick value per lot, minimum volume, step and ceiling are reported by the terminal as an
  instrument spec. The server holds neither contract sizes nor exchange rates: a broker has
  its own units, and computing them yourself means disagreeing with the terminal by an order
  of magnitude one day.
- Rounding is **down** to the volume step: the stated risk may not be exceeded by even one
  step. The honest risk after rounding is recorded next to the intended one.
- Volume below the minimum lot is a failure with an explanation, not "let us place whatever
  fits".
- The whole-account risk ceiling used to be checked only when a binding was created. A
  binding on a fixed lot or a cash amount does not know its own share at creation time at all
  — a hole through which several such bindings, each within the per-trade ceiling, together
  pushed the account risk past the ceiling. Now the ceiling is computed at the moment of the
  signal.
- In the fraction 0.03 / 0.01 a machine returns 2.9999…, and without a tolerance an honest
  three steps would have become two.

**Root.** The instrument spec and the ceilings were treated as known in advance.

**Rules.** R30, R31, R32. **Test.** T-14.

---

## F16 — A disagreement with the terminal must never be corrected silently

**Where.** The executor.

**The rule.** Our view of a trade is a row in a database; the truth about it is the
terminal's report. If they disagree, that is not a reason to rewrite our row: a silent
correction would erase the trace of somebody touching the trade by hand, or of us drifting
apart from the broker. The full report goes to reconciliation first, which raises the alarm,
and only then is it handed to position management.

**The root it defends against.** An unnoticed state divergence: the server thinks the
position is open, the broker thinks it is closed, or the other way round.

**Rules.** R34. **Test.** T-15.

---

## F17 — The expired command

**Where.** The executor.

**What is being defended.** The advisor may go silent — the computer is off — commands pile
up, and twenty minutes later "enter at market" at a price that is long gone is a trade the
setup never intended. Hence the expiries: market entry until the close of the next bar, a
pending order and a stop move until the end of the day by broker server time, a close within
a day. An expired command does not execute; it is marked skipped with a reason, and an
expired close raises an alarm.

**Why this matters to a run.** A run that holds an order longer than it lives at the broker
trades trades that will not exist.

**Rules.** R18. **Test.** T-04.

---

## F18 — Time passes between the signal and the fill

**Where.** The executor, measured on a demo link.

**The measurement.** About **12 seconds** from bar close to a filled order; almost all of it
the advisor's polling step of 5 seconds. Not re-measured on a live account.

**Why it is in the database.** A run that treats execution as instant is obliged to state
that figure and show what it changes. On a one-minute stream 12 seconds is a fifth of a bar.

**Rules.** R22. **Test.** T-16.

---

## F19 — The entry commission never reaches the trade's total

**Where.** The executor. Noticed and **not fixed**: the fix would move every money figure in
the statistics and is made only with the owner's knowledge.

**What exists.** The advisor assembles a position's total from its closing deals, so the
commission the broker charged on entry does not enter it. Commission and swap meanwhile
arrive as separate fields and are counted across all deals of the position, entry included.

**Why it is in the database.** This is a live, known and recorded debt of truth in money.
Any money report is obliged to name it until it is closed.

**Rules.** R29, R40. **Test.** —

---

## F20 — The wrong environment: a training database messaged the owner, a self-test created a live bot

**Where.** The executor.

**What happened.** While the environments had no names, that namelessness cost two silent
failures: a "day's result" service on the development machine twice messaged the owner out of
the training database, and a self-test once created a live bot version in the working
database.

**How it was solved.** Not by labelling but by a lock: the environment decides which accounts
it works with. The live one does not run bindings on demo accounts, the sandbox does not issue
commands on live ones — not by a setting, but because it refuses to serve such an account at
all.

**Why it is in a truth guard's database.** Numbers taken in the wrong environment are exactly
as untrue as numbers taken on the wrong series.

**Rules.** R36. **Test.** T-17.

---

## F21 — The documentation promises what the code does not do

**Where.** The zone engine, found while assembling this skill.

**What exists.** The docstring at the top of the engine file, in its "deliberate
simplifications" section, still promises that daily, weekly and monthly periods are computed
in UTC and sessions by a fixed timezone offset. In the code this has been untrue for several
days: there sits a broker-server offset function, read off the terminal's hourly candles over
four years, with seven named switch dates, and the markup follows server time.

**Why it is in the database.** This is exactly the trap the rule "do not trust the
documentation" is written against. Anyone believing the docstring would start fixing what is
already fixed — or, worse, would believe its next clause about something else without checking.

**Rules.** R41. **Test.** T-18.

---

## F22 — A pretty number from a combination that almost never fires

**Where.** The zone engine, while sweeping one filter.

**What happened.** The best numbers in the sweep came from the reading "the stream dies when
even one opposing zone has been removed": a profit-to-drawdown ratio of 19.19 against the
reference's 17.22. On examining a live example it turned out to drop one signal a day and to
take the very trade the rule had been invented for.

**Conclusion.** A combination that almost never fires looks good in the numbers because it
changes almost nothing, not because it has been understood correctly.

**Alongside.** The same project records the rule that curve-fitting to the last year had been
caught before, so a change is measured across the whole history rather than on one year.

**Rules.** R39, R38. **Test.** —

---

## F23 — Nine entries at prices that did not exist in their minute

**Where.** The grid engine, its trade list for a year. Found by this repository's guard while
it was being built. **Not yet investigated.**

**What is visible.** Of the list's 1919 trades, nine have an entry price outside the range of
the minute their entry is stamped with, and further out than two spreads. Two were verified by
hand against the terminal's minutes:

- an entry stamped 16:18 at 5041.80, while the 16:18 minute ran 5034.73–5039.44. The price
  5041.80 existed in the previous minute, 16:17 (5038.45–5051.13) — the very minute the list
  names as the test minute;
- an entry stamped 04:49 at 5056.39, while the 04:49 minute ran 5056.85–5060.35. The price
  5056.39 existed in the 04:48 minute.

**What it looks like.** The limit order is touched in the test minute, and the fill is recorded
on the next minute at the limit price — although price never returned there during that next
minute. That is an order filled at a price that did not exist at the moment of filling. Nine
cases out of 1919 is not an engine rule but an edge: it shows up where price shot through the
limit inside a minute.

**Why it is in the database.** This engine's reference numbers are already known to be
irreproducible in live trading (F05), and these nine trades are a failure separate from F05:
this one is about price, not about the future. It must not be written off along with the first.

**Rules.** R20. **Test.** T-19.

---

## Knowledge gaps

What the database does not yet know is written down here rather than painted over.

1. **Real slippage on a live account has never been measured.** The 0.5 allowance on the two
   engines with a short stop is a starting number; the real one comes from live stops after a
   month of work, per instrument. The one-minute stream of one of them needs its own number:
   there the average stop is 1.12 $, and an allowance of 0.5 would eat more than a third of the
   risk shares. **The other engines have no allowance at all, and it shows in their numbers:**
   in the zone engine's snapshot 1251 trades out of 2629 (47.6 %) cost exactly −1.00 R; in the
   grid engine's list, 973 out of 1919 (50.7 %). Exactly −1 R happens only in a run; on an
   account half the trades will be worse, and by how much nobody has measured.
2. **Latency has not been re-measured on a live account.** The 12 seconds were measured on a
   demo link.
3. **There is no tick data.** Intra-minute event ordering cannot be proven anywhere: the minute
   is the smallest thing there is. Everything ambiguous inside it is resolved against ourselves
   and counted as unknown, not as fact.
4. **The entry commission does not reach the trade's total** (F19) — a debt of truth in money,
   left open knowingly.
5. **A one-day hole in the series is not closed** (F08) — it sits in the broker's archive.
6. **Broker refusals are not modelled in runs at all.** The executor knows them by name and
   handles them: "stop too close" — after which the refused stop is resent as a target — no
   connection, autotrading off, trading not allowed, broker refused, advisor ceiling. Some are
   treated as temporary and asked again on the next bar, some are final. No engine knows any of
   this: in a run every order is accepted first time. What it costs has not been measured.
7. **The broker's minimum stop distance is checked nowhere in any run.** A broker has a
   threshold below which stops and targets are not accepted. In runs a short stop always fills.
   An engine's own micro-stop filter is a setup rule, not a broker measure, and the two must not
   be confused.
8. **A partial fill has never been investigated.** The executor handles partial closes and trims
   volume to free margin, and takes the volume in a trade row from the terminal's report; but
   nobody has measured the case where a broker filled less than was requested on entry.
