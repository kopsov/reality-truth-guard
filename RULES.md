# Truth rules R01–R41

Every rule was born from a failure in [`FAILURE-DATABASE.md`](FAILURE-DATABASE.md)
or from a technical risk recorded while auditing real runs. There are no invented
rules here.

The **symptom** column is what the failure looks like from the outside, without
reading all the code. The **proven by** column is what closes the rule: a run, a
reconciliation, a test. The words "should match" and "presumably the same" cannot
appear in that column.

---

## Data — R01–R05

| Code | Rule | Symptom | Proven by | Born from |
|---|---|---|---|---|
| R01 | One series, reconciled against the terminal; the engine refuses a foreign file | several series with similar names in the project; a measurement made on "some" series | minute-by-minute reconciliation with the terminal; a whitelist of series inside the engine itself | F08 |
| R02 | The series is complete: every gap examined and declared lawful | a missing trading day neither breaks the run nor prints a warning | a list of gaps with a reason for each; a freshness watch based on the instrument's own habit | F08, F09 |
| R03 | Bars are intact: high above the body, low below it, timestamps strictly increasing, no duplicates | negative ranges, repeated timestamps, non-monotonic time | truth guard, series section | technical risk |
| R04 | Series depth is proven by measurement; the depth watchdog is never switched off | on a short series the higher-timeframe markup lands in a different phase — silently | a measured boundary: one engine needed two months, live depth was set six times larger | project memory |
| R05 | Spread is live and comes from the same terminal as the bars | one spread number applied to the whole history | a spread column next to each bar, reconciled with the terminal | F12 |

## Time — R06–R08

| Code | Rule | Symptom | Proven by | Born from |
|---|---|---|---|---|
| R06 | Day, week, month and higher-timeframe boundaries follow broker server time | more daily candles than the broker has; the Sunday opening hours as a separate daily candle | bar-by-bar reconciliation with the terminal on every timeframe | F01 |
| R07 | The seasonal offset is a function of time, not a constant | the offset taken from the first bar and applied to every year | DST dates read off the terminal's hourly candles, not guessed | F01, F02 |
| R08 | A human-facing label and a candle boundary are different things; the boundary is what gets reconciled | "the zone is not in any gap on the chart", while in the terminal it is | reconciliation of the display with the terminal by open time, high and low | F02 |

## The future — R09–R12

| Code | Rule | Symptom | Proven by | Born from |
|---|---|---|---|---|
| R09 | No knowledge from after the moment of decision | you cannot name the signal minute and list what was known in it | a signal-time audit of every entry | F05 |
| R10 | A confirmation that arrives on the next candle cannot be traded inside that candle | the run sees noticeably fewer stops than the live layer at the same number of targets | the live layer against the batch run on the same series | F05 |
| R11 | An unclosed bar of a derived series is already full in a run — keep it out of the rules | a rule reads the high and low of a candle that is still filling up in live | live account against a from-scratch recount; a single trade of disagreement means look for look-ahead | F13 |
| R12 | The past is not recomputed: fresh marks and calendars act forward only | yesterday recomputed with today's knowledge | the calendar never grows backwards; the run continues rather than restarts | project decision |

## Inside the bar — R13–R16

| Code | Rule | Symptom | Proven by | Born from |
|---|---|---|---|---|
| R13 | Intra-bar ordering is never invented: go down to minutes, otherwise call it unknown | a bar touched both stop and target and the convenient outcome was recorded | a minute-level breakdown; the share of undecidable cases stated as a number | F06, F07 |
| R14 | Unknown ordering is resolved against yourself | "the target probably came first" | a trade that might not have happened is not counted; a stop that might have happened is | F06 |
| R15 | An order's fate is decided at the moment of the event, not at the candle close | the order was buried with the candle; at a broker it would have filled | a minute-level recount; the number of buried orders stated | F06 |
| R16 | A moved stop or target never works retroactively | the move triggered on the high of the very minute it was placed in | it takes effect from the next minute | F03, F06 |

## Execution — R17–R24

| Code | Rule | Symptom | Proven by | Born from |
|---|---|---|---|---|
| R17 | The order lives at the broker, not in your head: no fill before the minute after the signal | fill timestamp equals signal timestamp | truth guard, "order does not fill in its own signal minute" | F04 |
| R18 | An order expires the way it does at the broker: market entry by the next bar close, pending order and stop move by the end of the server day, close within a day | a pending order lives longer than a day in the run | truth guard, broker-day check | F04, F17 |
| R19 | The broker must accept the order: a buy stop below price, a sell stop above; target the other way round | the order triggers in the very minute it was placed | truth guard, side and breakeven checks | F03 |
| R20 | The execution price existed: entry and exit inside their own bar, adjusted for the side of the market | an entry price above the high of its own candle | truth guard, prices-in-bar check | technical risk |
| R21 | The engine asks only for what the executor can do, and answers everything the executor asks | the change exists in the run and never reaches the broker | reconciliation of the contract with the executor; the command list | F14 |
| R22 | Latency is stated as a number; instant execution is an assumption | "signal — instant fill" in the run without a single figure | a measurement of the path: signal, decision, command, broker, fill | F18 |
| R23 | Stop and target are not closer than the broker minimum distance | any arbitrarily short stop fills in the run | the threshold taken from the terminal; the "stops too close" refusal accounted for | gap 7 |
| R24 | A broker refusal is a possible outcome of an order, not an impossibility | every order is accepted first time in the run | the executor's list of refusals; temporary ones separated from final | gap 6 |

## Spread and costs — R25–R29

| Code | Rule | Symptom | Proven by | Born from |
|---|---|---|---|---|
| R25 | Side of the market: buy at the ask, sell at the bid; a short's stop and target are measured at the ask | a short's stop triggers later than it does at the broker | a side measurement on live trades; the adjustment living in one place | F11 |
| R26 | Translating between the scales of a quote broker and a trading broker is a conversion, not a trading decision | a long's stop is knocked out at one broker and not at another | half the spread difference measured against the observed offset between series | F11 |
| R27 | Spread is never counted twice | an engine that already moved the stop internally gets an external adjustment on top | a named list of who the adjustment applies to, and a ban written into the contract | F11 |
| R28 | Slippage is measured, not assumed; zero is an assumption with a price of its own | every stop in the run costs exactly −1R | a measurement on live stops; the price of the assumption stated in R | F10 |
| R29 | Commission and swap are visible on their own line; whatever is not in the total is named | "there are no costs", while they are baked into the prices | costs arriving as separate fields, entry and exit kept apart | F19 |

## Position size and risk — R30–R32

| Code | Rule | Symptom | Proven by | Born from |
|---|---|---|---|---|
| R30 | Lot size comes from the instrument spec reported by the terminal; round down to the step; below the minimum lot is a failure, not "as much as fits" | contract sizes and tick values hard-coded as your own constants | the spec reported by the executor; the honest risk recorded next to the intended one | F15 |
| R31 | Risk ceilings are checked at the moment of the signal, not only when the binding is created | several bindings, each within its own limit, together push the account past the ceiling | occupied risk counted both from declarations and from open trades | F15 |
| R32 | One risk distance for every way of expressing risk | percentage, fixed lot and cash amount computed separately | a single distance function on all paths | F10, F15 |

## State — R33–R37

| Code | Rule | Symptom | Proven by | Born from |
|---|---|---|---|---|
| R33 | The continued live account agrees trade by trade with a from-scratch recount | a disagreement of "only one trade" | live against from-scratch; any disagreement is a reason to hunt for look-ahead | F13 |
| R34 | A disagreement with the terminal is an alarm, not a silent correction | the record quietly adjusted to match the report | the reconciliation raises the alarm before the report is taken as truth | F16 |
| R35 | One trade, one entry; duplicates are hunted separately | two positions with the same candle, side, entry and stop | a duplicate breakdown by key; a position identified by its grid and entry place | F07 |
| R36 | The environment is named: the sandbox never touches live accounts | a training database messages the owner; a self-test creates a live bot version | a lock by account, not a setting | F20 |
| R37 | A trade is managed by the rules of the version it entered on | management rules change mid-position | a shadow engine pinned to the trade's version | executor contract |

## Numbers and honesty — R38–R41

| Code | Rule | Symptom | Proven by | Born from |
|---|---|---|---|---|
| R38 | No number is served without its chain of origin | "where is this from?" — "from the run" | the chain: data, event, signal, order, execution, position, exit, money, metric | F12, F22 |
| R39 | Prettier does not mean truer; an understated number lies exactly as an overstated one does | a change accepted because the numbers improved | changes measured over the whole history; the best combination checked against a live example | F12, F22 |
| R40 | "I don't know" stays "I don't know" | uncertainty turned into "probably fine" | a knowledge gap recorded with three answers: what is missing, how many trades it touches, what would settle it | F19 |
| R41 | The source of truth is the executed code path, not the documentation | a rule proven by pointing at a README, a comment or a spec | the actual computation located in the code | F21 |

---

## How to add a rule

1. The failure goes into `FAILURE-DATABASE.md` with its own numbers and a
   reference to where it was found.
2. Extract the root — not "we forgot to check", but what exactly the engine took
   as fact without being entitled to.
3. Phrase the rule so that it can be **checked by a run**. If there is nothing to
   check it with, it is a wish, not a rule, and it belongs in the knowledge gaps.
4. Give the rule the next free number and a row in this table.
5. A test is born (`TESTS.md`), and only after that is the rule considered alive.
