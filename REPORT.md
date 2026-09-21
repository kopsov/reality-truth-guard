# The truth guard report

Written after every audit. A short spoken part goes to the person; the full report
is filed with the project and gets a line in its journal.

An empty section means "not checked", not "all good". A section with genuinely
nothing to say is marked "not applicable" with a reason.

---

## Template

```
# TRUTH GUARD REPORT — <project>, <date>

## 1. Verdict
proven / partly proven / not proven / failed / blocked
One line: may these numbers be shown, and may the change be promoted?

## 2. What was checked
The trigger (which change, or whose request), which links of the chain it
touches, which runs and reconciliations were executed.

## 3. What was proven
Link by link, stating what proves each. No "presumably" and no "should".

## 4. What was not proven
By name. Each item with the reason it could not be proven.

## 5. Reality violations found
For each: what the engine computed, what would happen at the broker, and how
that is visible.

## 6. Which historical numbers are now in question
The numbers downstream of the finding — untrustworthy until recomputed. Say
plainly where those numbers have already been shown: pages, tables, journals.

## 7. History-versus-live divergences
The matrix from CHECKS.md, filled in completely.

## 8. Root cause
Not "we forgot to check", but what exactly the engine took as fact without
being entitled to.

## 9. Severity
Level 0–5 for each divergence, with the reasoning for the level.

## 10. Required action
Itemised, in the order it must be done. Separately: what blocks the numbers
from being shown.

## 11. Tests created
New permanent tests, with their codes and what exactly they catch.

## 12. Remaining uncertainty
Knowledge gaps: what is missing, how many trades it touches, what would settle
it.

## 13. Numbers: before and after
Latest year on the first line, whole series below. Columns: trades, total R,
drawdown, win rate, profit factor, longest run of stops, longest run of
targets.
```

---

## How to pick the verdict

| Verdict | When |
|---|---|
| **proven** | every link checked by a run; no divergences, or only level 0–1 ones with a number attached |
| **partly proven** | some links checked, the rest listed by name as unchecked; the decision to show the numbers belongs to the person, who now has that list |
| **not proven** | it could not be checked. The numbers are not served as fact: they may only be shown with the words "not verified" |
| **failed** | a level-3 divergence was found — the engine computes something other than what will happen |
| **blocked** | a level 4–5 divergence: numbers are not served, the change is not promoted, the bot does not go live |

A verdict of "proven" cannot be issued while a single cell of the matrix is empty.

## Divergence levels

| Level | What it is | Example from the failure database |
|---|---|---|
| 0 | no divergence | — |
| 1 | natural: floating spread, ordinary market noise | a 0.09 $ spread difference between brokers (F11) |
| 2 | uncertainty: not enough data | 563 orders with unknown intra-minute ordering (F06) |
| 3 | computation error | the exit minute searched from the start of the candle (F07) |
| 4 | reality break: behaviour impossible in live | a breakeven order a broker would reject (F03) |
| 5 | critical: profit, drawdown, risk, trade count or account safety distorted | an entry inside its own signal minute (F04), a fractal from the future (F05), an order buried by a candle (F06) |

## What to tell the person

Short, in plain words, no code. Always:

- whether the numbers they have already seen can be trusted;
- what exactly changed and by how much — before and after, side by side;
- which of it is their decision and which resolved itself;
- what we still do not know.

**Name your own mistakes immediately.** If an error is found in a check or a
script, say so and recompute — do not fix it quietly.

## What must never appear in a report

- "Probably matches", "should be the same", "presumably so".
- A verdict of "proven" with an unfilled matrix.
- A divergence explained away as a modelling convention. A divergence is a
  computation error; there are exactly two lawful exceptions, slippage and the
  size of the spread.
- A suggestion to "adjust" a setup rule for better numbers. The guard does not
  optimise. It verifies.
