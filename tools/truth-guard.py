# -*- coding: utf-8 -*-
"""TRUTH GUARD — a broker-agnostic audit of a trade export and its bar series.

It knows nothing about your setup rules and does not want to. It checks only
what is true at any broker on any market: that the price existed, that the
order could have been placed and accepted, that the intra-bar ordering was not
invented, that the series is intact.

Usage:

    python3 truth-guard.py --trades <file.csv> [--bars <file.csv>] [options]

Options:
    --map <file.json>     your own column names instead of the guessed ones
    --spreads <N>         how many bar spreads a price may sit outside the bar
                          (default 1: a long fills at the ask and legitimately
                          sits above the bar high)
    --tolerance <price>   flat price tolerance when the series carries no spread
    --broker-day <...>    "eet-us" — server days with DST switched by US rules
                          (measured on one broker's hourly candles, 2022-2026),
                          or a plain number of hours. Omitted: the pending-order
                          lifetime check is skipped
    --point <price>       point size, when the series records spread in points
                          (MetaTrader exports). Omitted: such a spread is
                          discarded rather than used, so the tolerance built
                          from it cannot wave every price through
    --lot-step <N>        broker volume step
    --min-lot <N>         broker minimum volume
    --min-stop <price>    broker minimum stop distance
    --examples <N>        how many examples to print per finding (default 3)

Result: "FINDINGS: N" and exit code 1 if any check failed. Checks whose columns
are missing do not stay silent: they are listed separately as knowledge gaps,
never as "all good".

Self-check lives in `fixture/` next to this file: ten trades, nine of them
deliberately wrong. The guard must find ten findings there and exit 1. A guard
that is always green has gone blind.

Column names are recognised in English and in Russian, so exports from either
world are read without a map.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone

# ------------------------------------------------------------- columns --- #

# How columns are named across exports, ours and other people's. First match
# wins; your own name can always be supplied through a map file.
COLUMN_ALIASES = {
    "side":        ["dir", "direction", "side", "сторона", "направление"],
    "kind":        ["kind", "type", "order_type", "вид"],
    "outcome":     ["outcome", "result", "исход"],
    "signal_ts":   ["signalTs", "signal_ts", "signal_time", "метка_сигнала",
                    "сигнал_время", "время_сигнала"],
    "fill_ts":     ["fillTs", "fill_ts", "entryTs", "entry_time", "метка_входа",
                    "вход_время", "время_входа"],
    "exit_ts":     ["exitTs", "exit_ts", "exit_time", "метка_выхода",
                    "выход_время", "время_выхода"],
    "entry":       ["entryP", "entry", "entry_price", "price_in", "вход"],
    "stop":        ["slInit", "sl_init", "stop_init", "стоп_нач"],
    "stop_now":    ["sl", "stop", "стоп"],
    "target":      ["tp", "take", "target", "цель"],
    "exit":        ["exitP", "exit", "exit_price", "price_out", "выход"],
    "result_r":    ["rResult", "r_result", "resultR", "R", "итог_r"],
    "breakeven_ts": ["beTs", "be_ts", "метка_бу"],
    "volume":      ["lots", "volume", "vol", "объём", "лоты"],
    "stream":      ["tf", "timeframe", "stream", "тф", "поток", "таймфрейм"],
}

BAR_ALIASES = {
    "time":   ["time", "timestamp", "ts", "время", "метка", "<TIME>", "datetime"],
    "date":   ["<DATE>", "date", "дата"],
    "open":   ["open", "o", "откр", "<OPEN>"],
    "high":   ["high", "h", "верх", "<HIGH>"],
    "low":    ["low", "l", "низ", "<LOW>"],
    "close":  ["close", "c", "закр", "<CLOSE>"],
    "spread": ["spread_avg", "spread", "спред", "<SPREAD>"],
}

# ---------------------------------------------------------------- time --- #

_TIME_FORMATS = ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S",
                 "%Y-%m-%d %H:%M", "%Y.%m.%d %H:%M:%S", "%Y.%m.%d %H:%M")


def to_ts(value):
    """Timestamp in seconds. Understands epochs and ordinary date strings."""
    if value in ("", None):
        return None
    s = str(value).strip()
    if not s:
        return None
    try:
        n = float(s)
        return int(n / 1000) if n > 1e11 else int(n)
    except ValueError:
        pass
    for fmt in _TIME_FORMATS:
        try:
            return int(datetime.strptime(s, fmt).replace(tzinfo=timezone.utc).timestamp())
        except ValueError:
            continue
    return None


def to_num(value):
    if value in ("", None):
        return None
    try:
        return float(str(value).replace(",", "."))
    except ValueError:
        return None


def is_long(value):
    """1, buy, long — long; -1, sell, short — short; anything else unknown."""
    if value in ("", None):
        return None
    s = str(value).strip().lower()
    if s in ("1", "1.0", "buy", "long", "b", "+1", "покупка", "лонг"):
        return True
    if s in ("-1", "-1.0", "sell", "short", "s", "0", "продажа", "шорт"):
        return False
    return None


def fmt_ts(ts):
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d %H:%M") if ts else "—"


def _sunday(year, month, nth):
    d = datetime(year, month, 1, tzinfo=timezone.utc)
    shift = (6 - d.weekday()) % 7
    return d.replace(day=1 + shift + 7 * (nth - 1))


_DST_CACHE = {}


def eet_us_offset(ts):
    """Hours the broker server runs ahead of UTC.

    UTC+2 in winter, UTC+3 in summer; switched by US rules. The rule was
    measured on one particular broker's hourly candles over 2022-2026 and holds
    for that broker. Do not assume it for another one — measure it again.
    """
    year = datetime.fromtimestamp(ts, timezone.utc).year
    edges = _DST_CACHE.get(year)
    if edges is None:
        spring, autumn = _sunday(year, 3, 2), _sunday(year, 11, 1)
        edges = _DST_CACHE[year] = (int(spring.replace(hour=7).timestamp()),
                                    int(autumn.replace(hour=6).timestamp()))
    return 3 if edges[0] <= ts < edges[1] else 2


# -------------------------------------------------------------- output --- #

class Report:
    def __init__(self, examples):
        self.findings = []
        self.gaps = []
        self.examples = examples

    def check(self, name, ok, detail="", examples=()):
        print("  %-8s %s%s" % ("ok" if ok else "FINDING", name,
                               ("   " + detail) if detail else ""))
        if not ok:
            self.findings.append(name)
            for line in list(examples)[:self.examples]:
                print("             · %s" % line)

    def gap(self, name, why):
        print("  %-8s %s   %s" % ("unknown", name, why))
        self.gaps.append((name, why))


# -------------------------------------------------------------- input ---- #

def find_columns(headers, aliases, mapping):
    found, lower = {}, {h.lower(): h for h in headers}
    for key, variants in aliases.items():
        given = mapping.get(key)
        if given:
            found[key] = given if given in headers else None
            continue
        for v in variants:
            if v in headers:
                found[key] = v
                break
            if v.lower() in lower:
                found[key] = lower[v.lower()]
                break
        else:
            found[key] = None
    return found


def read_table(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        sample = f.read(8192)
        f.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
        except csv.Error:
            dialect = csv.excel
        reader = csv.DictReader(f, dialect=dialect)
        return reader.fieldnames or [], list(reader)


# --------------------------------------------------------------- bars ---- #

class Bars:
    def __init__(self, path, mapping, point=None):
        headers, rows = read_table(path)
        c = find_columns(headers, BAR_ALIASES, mapping)
        get = lambda r, k: r.get(c[k]) if c.get(k) else None
        # MetaTrader exports keep date and time apart — glue them back.
        split_time = bool(c.get("date")) and bool(c.get("time"))
        self.ts, self.high, self.low = [], [], []
        self.open, self.close, self.spread = [], [], []
        self.point = point
        for r in rows:
            if split_time:
                d, t = get(r, "date"), get(r, "time")
                stamp = to_ts("%s %s" % (str(d).replace(".", "-").strip(), str(t).strip()))
            else:
                stamp = to_ts(get(r, "time"))
            if stamp is None:
                continue
            self.ts.append(stamp)
            self.open.append(to_num(get(r, "open")))
            self.high.append(to_num(get(r, "high")))
            self.low.append(to_num(get(r, "low")))
            self.close.append(to_num(get(r, "close")))
            sp = to_num(get(r, "spread"))
            self.spread.append(sp * point if (sp is not None and point) else sp)
        self.has_spread = c.get("spread") is not None
        self.spread_in_points = False
        # MetaTrader records spread in points, not in price. With no point size
        # given it is two orders of magnitude too large, and a tolerance built
        # from it would wave any price through. Better to have no spread at all.
        if self.has_spread and not point:
            values = [s for s in self.spread if s is not None]
            whole = sum(1 for s in values if abs(s - round(s)) < 1e-9)
            if values and whole > 0.9 * len(values) and max(values) >= 5:
                self.has_spread = False
                self.spread_in_points = True
        self.index = {t: i for i, t in enumerate(self.ts)}
        step = Counter(b - a for a, b in zip(self.ts, self.ts[1:])).most_common(1)
        self.step = step[0][0] if step else None

    def __len__(self):
        return len(self.ts)

    def at(self, ts):
        """The bar a timestamp falls into, found on the series own grid."""
        i = self.index.get(ts)
        if i is not None:
            return i
        if not self.step:
            return None
        return self.index.get(ts - (ts % self.step))


# ------------------------------------------------------------- checks ---- #

def check_bars(bars, report):
    print("\nBar series (%d bars, step %s s):" % (len(bars), bars.step))
    if not len(bars):
        report.check("series parsed", False, "not a single bar")
        return

    pairs = list(zip(bars.ts, bars.ts[1:]))
    backwards = [(a, b) for a, b in pairs if b <= a]
    report.check("timestamps strictly increase, no duplicates", not backwards,
                 "" if not backwards else "cases %d" % len(backwards),
                 ["%s → %s" % (fmt_ts(a), fmt_ts(b)) for a, b in backwards])

    broken = []
    for i in range(len(bars)):
        h, l, o, c = bars.high[i], bars.low[i], bars.open[i], bars.close[i]
        if None in (h, l, o, c):
            continue
        if h < l or h < max(o, c) - 1e-9 or l > min(o, c) + 1e-9:
            broken.append(i)
    report.check("bars intact: high above the body, low below it", not broken,
                 "" if not broken else "broken bars %d" % len(broken),
                 [fmt_ts(bars.ts[i]) for i in broken])

    if bars.step:
        # A census of gaps. The guard does NOT judge them: a minute bar is not
        # born where there were no ticks, so a short gap in a quiet hour is
        # ordinary, while a long one may be a holiday or a genuine hole. A
        # human judges, and the verdict is recorded in the project. The guard's
        # job is to show what must be looked at, and never to let a whole
        # trading day slip through unnoticed.
        gaps = [(a, b - a) for a, b in pairs if b - a > bars.step]
        short = [g for g in gaps if g[1] < 55 * 60]
        medium = [g for g in gaps if 55 * 60 <= g[1] <= 12 * 3600]
        long_ = [g for g in gaps if g[1] > 12 * 3600]
        print("             gaps in total %d: under 55 min — %d, 55 min to 12 h "
              "— %d, over 12 h — %d" % (len(gaps), len(short), len(medium), len(long_)))

        # The usual weekend day is the one most long gaps start on. Any other
        # long gap is suspicious: that is what a lost trading day looks like.
        if long_:
            days = Counter(datetime.fromtimestamp(a, timezone.utc).weekday()
                           for a, _ in long_)
            usual = days.most_common(1)[0][0]
            odd = [(a, d) for a, d in long_
                   if datetime.fromtimestamp(a, timezone.utc).weekday() != usual]
            if odd:
                report.gap(
                    "long gaps on an unusual weekday",
                    "%d of them — look at each and record whether it is a holiday "
                    "or a hole: %s"
                    % (len(odd), "; ".join("%s (%.0f h)" % (fmt_ts(a), d / 3600.0)
                                           for a, d in odd[:8])))
        if short:
            report.gap("short gaps inside a session",
                       "%d of them — a minute bar is not born without ticks, but "
                       "look at them once and record the verdict" % len(short))

    if bars.has_spread:
        values = [s for s in bars.spread if s is not None]
        zeros = sum(1 for s in values if s <= 0)
        report.check("spread in the series is live", bool(values) and zeros * 20 < len(values),
                     "bars with spread %d of %d, zero ones %d, mean %.4f"
                     % (len(values), len(bars), zeros,
                        sum(values) / len(values) if values else 0.0))
    elif bars.spread_in_points:
        report.gap("spread in the series",
                   "it is recorded in points, not in price: give the point size "
                   "with --point, otherwise a spread tolerance waves any price through")
    else:
        report.gap("spread in the series", "no spread column — rule R05 unchecked")


def check_trades(trades, c, bars, opt, report):
    print("\nTrades (%d):" % len(trades))
    v = lambda r, k: r.get(c[k]) if c.get(k) else None

    # --- 1. A fill never lands in its own signal minute (R17) ---------------
    if c["signal_ts"] and c["fill_ts"]:
        same_minute, before = [], []
        for r in trades:
            sig, fill = to_ts(v(r, "signal_ts")), to_ts(v(r, "fill_ts"))
            if sig is None or fill is None:
                continue
            if fill == sig:
                same_minute.append(sig)
            elif fill < sig:
                before.append((sig, fill))
        report.check("order does not fill in its own signal minute", not same_minute,
                     "" if not same_minute else "such trades %d" % len(same_minute),
                     [fmt_ts(t) for t in same_minute])
        report.check("fill is never earlier than the signal", not before,
                     "" if not before else "such trades %d" % len(before),
                     ["signal %s, fill %s" % (fmt_ts(a), fmt_ts(b)) for a, b in before])
    else:
        missing = "signal" if not c["signal_ts"] else "fill"
        report.gap("moment of execution",
                   "the export carries no %s timestamp — R17 unchecked. This is "
                   "not a detail: without it you cannot see entries taken with "
                   "hindsight" % missing)

    # --- 2. A pending order does not outlive the broker day (R18) ----------
    if opt["broker_day"] and c["signal_ts"] and c["fill_ts"]:
        overdue = []
        for r in trades:
            sig, fill = to_ts(v(r, "signal_ts")), to_ts(v(r, "fill_ts"))
            kind = (str(v(r, "kind") or "")).upper()
            if sig is None or fill is None:
                continue
            if "LIMIT" not in kind and "STOP" not in kind and "ОТЛОЖ" not in kind:
                continue
            if opt["broker_day"](fill) != opt["broker_day"](sig):
                overdue.append((sig, fill))
        report.check("pending order does not outlive the broker day", not overdue,
                     "" if not overdue else "such trades %d" % len(overdue),
                     ["signal %s, fill %s" % (fmt_ts(a), fmt_ts(b)) for a, b in overdue])
    elif not opt["broker_day"]:
        report.gap("broker day", "--broker-day not given — R18 unchecked")
    else:
        report.gap("broker day", "no signal and fill timestamps together — R18 unchecked")

    # --- 3. Stop and target on the side a broker accepts (R19) -------------
    if c["entry"] and c["stop"] and c["side"]:
        bad_stop, bad_target = [], []
        for r in trades:
            long_ = is_long(v(r, "side"))
            entry, stop = to_num(v(r, "entry")), to_num(v(r, "stop"))
            target = to_num(v(r, "target")) if c["target"] else None
            if long_ is None or entry is None or stop is None:
                continue
            if abs(stop - entry) > 1e-9 and ((stop > entry) if long_ else (stop < entry)):
                bad_stop.append((entry, stop))
            if target is not None and abs(target - entry) > 1e-9 and \
                    ((target < entry) if long_ else (target > entry)):
                bad_target.append((entry, target))
        report.check("stop sits where a broker would accept it", not bad_stop,
                     "" if not bad_stop else "such trades %d" % len(bad_stop),
                     ["entry %.5f, stop %.5f" % (a, b) for a, b in bad_stop])
        report.check("target sits where a broker would accept it", not bad_target,
                     "" if not bad_target else "such trades %d (a target moved onto "
                     "the entry price is not counted here)" % len(bad_target),
                     ["entry %.5f, target %.5f" % (a, b) for a, b in bad_target])
    else:
        report.gap("order sides", "no entry, stop or side — R19 unchecked")

    # --- 4. Broker minimum stop distance (R23) ------------------------------
    if opt["min_stop"] and c["entry"] and c["stop"]:
        too_close = []
        for r in trades:
            entry, stop = to_num(v(r, "entry")), to_num(v(r, "stop"))
            if entry is None or stop is None:
                continue
            if abs(entry - stop) < opt["min_stop"] - 1e-9:
                too_close.append(abs(entry - stop))
        report.check("stop is not closer than the broker minimum", not too_close,
                     "" if not too_close else "such trades %d, shortest %.5f"
                     % (len(too_close), min(too_close)))
    else:
        report.gap("broker minimum stop distance", "--min-stop not given — R23 unchecked")

    # --- 5. An exit never precedes its entry --------------------------------
    if c["fill_ts"] and c["exit_ts"]:
        reversed_ = []
        for r in trades:
            fill, out = to_ts(v(r, "fill_ts")), to_ts(v(r, "exit_ts"))
            if fill is None or out is None:
                continue
            if out < fill:
                reversed_.append((fill, out))
        report.check("exit is never earlier than entry", not reversed_,
                     "" if not reversed_ else "such trades %d" % len(reversed_),
                     ["entry %s, exit %s" % (fmt_ts(a), fmt_ts(b)) for a, b in reversed_])

    # --- 6. The entry price existed (R20) -----------------------------------
    if bars and c["fill_ts"] and c["entry"]:
        outside, no_bar = [], 0
        for r in trades:
            t, price = to_ts(v(r, "fill_ts")), to_num(v(r, "entry"))
            long_ = is_long(v(r, "side")) if c["side"] else None
            if t is None or price is None:
                continue
            i = bars.at(t)
            if i is None:
                no_bar += 1
                continue
            hi, lo = bars.high[i], bars.low[i]
            if hi is None or lo is None:
                continue
            sp = (bars.spread[i] or 0.0) if bars.has_spread else 0.0
            allowance = max(opt["tolerance"], sp * opt["spreads"])
            above, below = price - hi, lo - price
            # A long fills at the ask and legitimately sits above the bar high
            # by a spread; a short fills at the bid and sits below the low.
            # Side unknown — the allowance is granted both ways.
            limit_up = allowance if long_ is not False else opt["tolerance"]
            limit_down = allowance if long_ is not True else opt["tolerance"]
            if above > limit_up + 1e-9 or below > limit_down + 1e-9:
                outside.append((t, price, lo, hi, allowance))
        report.check("entry price lies inside its own bar", not outside,
                     "" if not outside else "such trades %d" % len(outside),
                     ["%s: entry %.5f against bar %.5f–%.5f, allowance %.5f"
                      % (t, p, lo, hi, a) for t, p, lo, hi, a in
                      [(fmt_ts(x[0]),) + x[1:] for x in outside]])
        if no_bar:
            report.gap("entry bar found",
                       "%d trades found no bar of their own in the series" % no_bar)

    # --- 7. The exit price existed ------------------------------------------
    if bars and c["exit_ts"] and c["exit"]:
        outside = []
        for r in trades:
            t, price = to_ts(v(r, "exit_ts")), to_num(v(r, "exit"))
            if t is None or price is None:
                continue
            i = bars.at(t)
            if i is None:
                continue
            hi, lo = bars.high[i], bars.low[i]
            if hi is None or lo is None:
                continue
            sp = (bars.spread[i] or 0.0) if bars.has_spread else 0.0
            allowance = max(opt["tolerance"], sp * opt["spreads"])
            if price - hi > allowance + 1e-9 or lo - price > allowance + 1e-9:
                outside.append((t, price, lo, hi))
        report.check("exit price lies inside its own bar", not outside,
                     "" if not outside else "such trades %d" % len(outside),
                     ["%s: exit %.5f against bar %.5f–%.5f"
                      % (fmt_ts(t), p, lo, hi) for t, p, lo, hi in outside])
    elif c["exit_ts"]:
        report.gap("exit price", "the export carries no exit price — R20 half-checked")

    # --- 8. Undecidable bars: stop and target in one bar (R13) --------------
    if bars and c["fill_ts"] and c["exit_ts"] and c["stop"] and c["target"]:
        undecidable, called_target = 0, []
        for r in trades:
            fill, out = to_ts(v(r, "fill_ts")), to_ts(v(r, "exit_ts"))
            stop, target = to_num(v(r, "stop")), to_num(v(r, "target"))
            long_ = is_long(v(r, "side")) if c["side"] else None
            outcome = str(v(r, "outcome") or "").upper()
            if None in (fill, out, stop, target) or long_ is None:
                continue
            i, j = bars.at(fill), bars.at(out)
            if i is None or j is None or j < i:
                continue
            for k in range(i, j + 1):
                hi, lo = bars.high[k], bars.low[k]
                if hi is None or lo is None:
                    continue
                hit_target = (hi >= target) if long_ else (lo <= target)
                hit_stop = (lo <= stop) if long_ else (hi >= stop)
                if hit_target and hit_stop:
                    undecidable += 1
                    if "TP" in outcome or "TAKE" in outcome or "ЦЕЛ" in outcome:
                        called_target.append((fmt_ts(bars.ts[k]), outcome))
                    break
        share = 100.0 * undecidable / len(trades) if trades else 0.0
        report.check("a bar that hit both stop and target is not called a target",
                     not called_target,
                     "undecidable bars %d (%.1f %% of trades), of them called a "
                     "target %d" % (undecidable, share, len(called_target)),
                     ["%s, outcome %s" % p for p in called_target])

    # --- 9. Duplicates (R35) -------------------------------------------------
    # A duplicate key must carry time: without it identical prices recur on
    # their own and the check would turn into a false alarm.
    time_key = ("signal_ts" if c["signal_ts"] else
                ("fill_ts" if c["fill_ts"] else None))
    keys = ([time_key] if time_key else []) + \
           [k for k in ("side", "entry", "stop") if c[k]]
    if not time_key:
        report.gap("duplicate trades",
                   "the export carries neither a signal nor a fill timestamp — "
                   "on prices alone a duplicate cannot be told from a level that "
                   "simply recurred")
    elif len(keys) >= 3:
        # Inside one stream an identical trade is a duplicate and a finding
        # (1354 surplus positions were found this way in one audit). The same
        # trade in DIFFERENT streams is a question for the setup, not a broken
        # count: the guard names it but does not judge.
        with_stream = keys + (["stream"] if c["stream"] else [])
        counted = Counter(tuple(str(v(r, k)) for k in with_stream) for r in trades)
        dupes = [(k, n) for k, n in counted.items() if n > 1]
        report.check("no duplicates inside a stream", not dupes,
                     "" if not dupes else "repeated keys %d, surplus rows %d"
                     % (len(dupes), sum(n - 1 for _, n in dupes)),
                     ["%s — %d times" % (" · ".join(k), n) for k, n in dupes])
        if c["stream"]:
            across = Counter(tuple(str(v(r, k)) for k in keys) for r in trades)
            shared = [(k, n) for k, n in across.items() if n > 1]
            if shared:
                report.gap(
                    "one trade in several streams",
                    "%d such coincidences (%d surplus rows): in live trading this "
                    "is one price and one market — decide whether these are two "
                    "positions or one" % (len(shared), sum(n - 1 for _, n in shared)))

    # --- 10. The R result agrees with the prices ----------------------------
    if c["result_r"] and c["entry"] and c["stop"] and c["exit"] and c["side"]:
        disagree = []
        for r in trades:
            entry, stop, out = (to_num(v(r, "entry")), to_num(v(r, "stop")),
                                to_num(v(r, "exit")))
            stated, long_ = to_num(v(r, "result_r")), is_long(v(r, "side"))
            if None in (entry, stop, out, stated) or long_ is None:
                continue
            risk = abs(entry - stop)
            if risk < 1e-9:
                continue
            own = ((out - entry) if long_ else (entry - out)) / risk
            if abs(own - stated) > 0.02:
                disagree.append((stated, own))
        report.check("R result agrees with entry, exit and stop prices", not disagree,
                     "" if not disagree else "such trades %d" % len(disagree),
                     ["export says %.3f R, prices say %.3f R" % p for p in disagree])
    else:
        report.gap("R result against prices",
                   "no exit price or no R result — the chain of numbers cannot be closed")

    # --- 11. Suspiciously smooth outcomes ------------------------------------
    if c["result_r"]:
        values = [to_num(v(r, "result_r")) for r in trades]
        values = [x for x in values if x is not None]
        if values:
            zeros = sum(1 for x in values if abs(x) < 1e-9)
            exact = sum(1 for x in values if abs(x + 1.0) < 1e-9)
            top = Counter(round(x, 4) for x in values).most_common(1)[0]
            print("             outcomes: trades %d, flat zeros %d (%.1f %%), "
                  "exactly −1.00 R %d (%.1f %%), most frequent value %.4f — %d times"
                  % (len(values), zeros, 100.0 * zeros / len(values),
                     exact, 100.0 * exact / len(values), top[0], top[1]))
            if exact and exact >= 0.15 * len(values):
                report.gap("stops at exactly −1.00 R",
                           "%d of them (%.1f %%): this run carries no slippage at "
                           "all — put a number on that assumption (R28)"
                           % (exact, 100.0 * exact / len(values)))

    # --- 12. Volume against the broker rules (R30) --------------------------
    if c["volume"] and (opt["lot_step"] or opt["min_lot"]):
        off_step, too_small = [], []
        for r in trades:
            lots = to_num(v(r, "volume"))
            if lots is None:
                continue
            if opt["lot_step"]:
                steps = lots / opt["lot_step"]
                if abs(steps - round(steps)) > 1e-6:
                    off_step.append(lots)
            if opt["min_lot"] and lots < opt["min_lot"] - 1e-9:
                too_small.append(lots)
        if opt["lot_step"]:
            report.check("volume is a multiple of the lot step", not off_step,
                         "" if not off_step else "such trades %d" % len(off_step))
        if opt["min_lot"]:
            report.check("volume is not below the minimum lot", not too_small,
                         "" if not too_small else "such trades %d" % len(too_small))
    elif not c["volume"]:
        report.gap("volume", "the export carries no volume — R30 unchecked")

    # --- 13. How many positions were open at once ---------------------------
    if c["fill_ts"] and c["exit_ts"]:
        events = []
        for r in trades:
            fill, out = to_ts(v(r, "fill_ts")), to_ts(v(r, "exit_ts"))
            if fill is None or out is None:
                continue
            events.append((fill, 1))
            events.append((out, -1))
        events.sort()
        now = peak = 0
        when = None
        for t, d in events:
            now += d
            if now > peak:
                peak, when = now, t
        print("             positions open at once: most %d, %s" % (peak, fmt_ts(when)))


# ---------------------------------------------------------------- main --- #

def main():
    p = argparse.ArgumentParser(add_help=True)
    p.add_argument("--trades", required=True)
    p.add_argument("--bars")
    p.add_argument("--map")
    p.add_argument("--spreads", type=float, default=1.0)
    p.add_argument("--tolerance", type=float, default=0.0)
    p.add_argument("--broker-day", dest="broker_day")
    p.add_argument("--point", type=float,
                   help="point size, when the series records spread in points")
    p.add_argument("--lot-step", dest="lot_step", type=float)
    p.add_argument("--min-lot", dest="min_lot", type=float)
    p.add_argument("--min-stop", dest="min_stop", type=float)
    p.add_argument("--examples", type=int, default=3)
    a = p.parse_args()

    mapping = {}
    if a.map:
        mapping = json.load(open(a.map, encoding="utf-8"))

    print("TRUTH GUARD — auditing a trade export for live executability\n")
    print("Trades: %s" % os.path.basename(a.trades))

    headers, trades = read_table(a.trades)
    c = find_columns(headers, COLUMN_ALIASES, mapping.get("trades", mapping))
    # The initial stop may be absent altogether — then the current one stands in,
    # which is more honest than skipping the side checks outright.
    if not c["stop"] and c["stop_now"]:
        c["stop"] = c["stop_now"]
        print("No initial stop in the export — using the current one (\"%s\"): "
              "side checks run against it." % c["stop"])
    known = [k for k, val in c.items() if val]
    print("Columns recognised: %s" % (", ".join(known) if known else "none"))

    broker_day = None
    if a.broker_day:
        if a.broker_day.strip().lower() == "eet-us":
            broker_day = lambda ts: (ts + eet_us_offset(ts) * 3600) // 86400
        else:
            hours = float(a.broker_day)
            broker_day = lambda ts: int(ts + hours * 3600) // 86400

    opt = {"tolerance": a.tolerance, "spreads": a.spreads, "broker_day": broker_day,
           "lot_step": a.lot_step, "min_lot": a.min_lot, "min_stop": a.min_stop}

    report = Report(a.examples)
    bars = None
    if a.bars:
        print("Bars: %s" % os.path.basename(a.bars))
        bars = Bars(a.bars, mapping.get("bars", {}), a.point)
        check_bars(bars, report)
    else:
        report.gap("bar series", "no series given — prices and gaps unchecked")

    check_trades(trades, c, bars, opt, report)

    print()
    if report.gaps:
        print("UNCHECKED — %d. These are knowledge gaps, not \"all good\":"
              % len(report.gaps))
        for name, why in report.gaps:
            print("  · %s — %s" % (name, why))
        print()
    if report.findings:
        print("FINDINGS: %d — the run disagrees with live execution. Fix the "
              "engine, do not explain it away." % len(report.findings))
        return 1
    print("No findings. That does not mean \"the numbers are right\": this guard "
          "checks only what is true at any broker.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
