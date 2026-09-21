# Fixture — the guard's self-check

Ten trades, nine of them deliberately wrong, and eight minutes of bars beneath them.
Every wrongness comes from `FAILURE-DATABASE.md`, which means it happened for real
once.

The fixture exists for one reason: **a guard that is always green is not a guard.**
After any change to `truth-guard.py`, run it against this fixture and confirm it still
fails and still finds all ten.

## What is hidden in it

| Row | What is wrong | Rule |
|---|---|---|
| 1 | nothing — a healthy trade; the guard must stay silent on it | — |
| 2 | fill inside the very minute whose close produced the signal | R17 |
| 3 | a long's stop placed above the entry price — a broker rejects that order | R19 |
| 4 | an entry price that did not exist in its bar | R20 |
| 5 | an exit recorded earlier than the entry | — |
| 6 | a duplicate of row 3 inside the same stream | R35 |
| 7 | a bar hit both stop and target, and the outcome was recorded as a target | R13, R14 |
| 8 | a pending order that lived for two server days | R18 |
| 9 | volume that is not a multiple of the lot step | R30 |
| 10 | an R result that does not agree with the entry, exit and stop prices | R38 |

Plus two gaps the guard must name rather than swallow: some trades have a stop at
exactly −1.00 R (no slippage at all), and one entry finds no bar of its own in the
series.

## Expected result

Ten findings and exit code 1.

```bash
python3 ../truth-guard.py \
  --trades trades-broken.csv \
  --bars bars.csv \
  --broker-day eet-us --lot-step 0.01 --min-lot 0.01
```

Fewer than ten — the guard has gone blind. More than ten — a false alarm has appeared,
and it must be investigated as strictly as a missed failure.
