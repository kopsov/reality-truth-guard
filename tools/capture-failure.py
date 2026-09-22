# -*- coding: utf-8 -*-
"""CAPTURE-FAILURE — write a finding into the database before it is forgotten.

The most common way this skill loses knowledge is not disagreement. It is a
session that ends before anyone writes the case down. Hand-editing three files
in house style is enough friction to lose a finding; one command is not.

    python3 tools/capture-failure.py case.json
    python3 tools/capture-failure.py case.json --local
    python3 tools/capture-failure.py --template > case.json

It picks the next free F code, renders the case in the same shape as every other
one, inserts it above the knowledge gaps, and — when the case brings new ones —
adds a rule row and a test row with their own next free codes.

Both languages are written at once. A public case without its translation would
make the two halves drift, and the self-audit would go red at the next push, so
the tool refuses rather than leaving that behind. A private case (`--local`)
lives in `local/`, which git ignores, and needs one language only.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TEMPLATE = {
    "title": "What went wrong, in one line",
    "where": "Which engine or layer, and how it surfaced",
    "what": "What the engine did, and why that is not what happens at a broker",
    "cost": "The numbers. How many trades, how much R, what happened to drawdown "
            "and win rate. Without numbers this is an impression, not a failure.",
    "symptom": "How this failure looks from the outside, on any engine (optional)",
    "root": "What exactly the engine took as fact without being entitled to. "
            "'We forgot to check' is not a root.",
    "rules": ["R13"],
    "new_rule": {
        "section": "Execution",
        "text": "The rule, phrased so it can be checked by a run",
        "symptom": "What it looks like when broken",
        "proven_by": "Which run or reconciliation closes it",
    },
    "test": {"catches": "What the permanent test catches", "by": "Which run"},
    "ru": {
        "title": "То же по-русски",
        "where": "...",
        "what": "...",
        "cost": "...",
        "symptom": "...",
        "root": "...",
        "new_rule": {"text": "...", "symptom": "...", "proven_by": "..."},
        "test": {"catches": "...", "by": "..."},
    },
}

FILES = {
    "en": {"failures": "FAILURE-DATABASE.md", "rules": "RULES.md", "tests": "TESTS.md",
           "gaps": "## Knowledge gaps"},
    "ru": {"failures": "ru/БАЗА-ОТКАЗОВ.md", "rules": "ru/ПРАВИЛА.md",
           "tests": "ru/ТЕСТЫ.md", "gaps": "## Пробелы знания"},
}

WORDS = {
    "en": {"where": "Where", "what": "What happened", "cost": "The cost",
           "symptom": "The symptom that works everywhere", "root": "Root",
           "rules": "Rules", "test": "Test"},
    "ru": {"where": "Где", "what": "Что было", "cost": "Цена",
           "symptom": "Признак беды, который работает везде", "root": "Корень",
           "rules": "Правила", "test": "Тест"},
}

# Which table in RULES.md a new rule joins. The keys are matched against the
# section headings of both languages.
SECTIONS = {
    "data": ("## Data", "## Данные"),
    "time": ("## Time", "## Время"),
    "future": ("## The future", "## Будущее"),
    "intrabar": ("## Inside the bar", "## Внутри свечи"),
    "execution": ("## Execution", "## Исполнение"),
    "spread": ("## Spread and costs", "## Спред и издержки"),
    "size": ("## Position size and risk", "## Объём и риск"),
    "state": ("## State", "## Состояние"),
    "honesty": ("## Numbers and honesty", "## Числа и честность"),
}


def read(rel):
    path = os.path.join(ROOT, rel)
    with open(path, encoding="utf-8") as f:
        return f.read()


def write(rel, text):
    path = os.path.join(ROOT, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def next_code(text, pattern, prefix, width=2):
    # re.M matters: without it "^" only matches the start of the whole file and
    # every code looks free, so the tool would hand out F01 forever.
    found = [int(m) for m in re.findall(pattern, text, re.M)]
    return "%s%0*d" % (prefix, width, (max(found) + 1) if found else 1)


def render_case(code, case, lang):
    w = WORDS[lang]
    out = ["## %s — %s\n" % (code, case["title"])]
    out.append("**%s.** %s\n" % (w["where"], case["where"]))
    out.append("**%s.** %s\n" % (w["what"], case["what"]))
    out.append("**%s.** %s\n" % (w["cost"], case["cost"]))
    if case.get("symptom"):
        out.append("**%s.** %s\n" % (w["symptom"], case["symptom"]))
    out.append("**%s.** %s\n" % (w["root"], case["root"]))
    rules = ", ".join(case["rules"])
    test = case.get("test_code") or case.get("existing_test") or "—"
    out.append("**%s.** %s **%s.** %s\n" % (w["rules"], rules, w["test"], test))
    return "\n".join(out) + "\n---\n\n"


def insert_case(rel, marker, block):
    text = read(rel)
    at = text.find("\n" + marker)
    if at < 0:
        raise SystemExit("could not find %r in %s — insert the case by hand" % (marker, rel))
    return text[:at + 1] + block + text[at + 1:]


def add_rule_row(rel, code, rule, lang):
    text = read(rel)
    heads = SECTIONS.get((rule.get("section") or "execution").lower().strip(),
                         SECTIONS["execution"])
    head = heads[0] if lang == "en" else heads[1]
    start = text.find(head)
    if start < 0:
        raise SystemExit("section %r not found in %s" % (head, rel))
    nxt = text.find("\n## ", start + 1)
    nxt = len(text) if nxt < 0 else nxt
    block = text[start:nxt]
    rows = [m.start() for m in re.finditer(r"^\| R\d{2} \|", block, re.M)]
    if not rows:
        raise SystemExit("no rule rows in section %r of %s" % (head, rel))
    last = block.find("\n", rows[-1])
    row = "\n| %s | %s | %s | %s | %s |" % (
        code, rule["text"], rule["symptom"], rule["proven_by"], rule["from"])
    return text[:start + last] + row + text[start + last:]


def add_test_row(rel, code, test, lang):
    text = read(rel)
    rows = [m.start() for m in re.finditer(r"^\| T-\d{2} \|", text, re.M)]
    if not rows:
        raise SystemExit("no test rows in %s" % rel)
    last = text.find("\n", rows[-1])
    row = "\n| %s | %s | %s | %s | %s |" % (
        code, test["catches"], test["rules"], test["from"], test["by"])
    return text[:last] + row + text[last:]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("case", nargs="?", help="JSON file describing the failure")
    p.add_argument("--local", action="store_true",
                   help="write to local/ instead — a private case git ignores")
    p.add_argument("--template", action="store_true", help="print a blank case")
    a = p.parse_args()

    if a.template:
        print(json.dumps(TEMPLATE, ensure_ascii=False, indent=2))
        return 0
    if not a.case:
        p.error("give a case file, or --template to start one")

    with open(a.case, encoding="utf-8") as f:
        case = json.load(f)

    for field in ("title", "where", "what", "cost", "root", "rules"):
        if not case.get(field):
            raise SystemExit("the case needs a %r — a case without one is an "
                             "impression, not a failure" % field)

    if a.local:
        rel = os.path.join("local", "FAILURE-DATABASE.md")
        path = os.path.join(ROOT, rel)
        if not os.path.exists(path):
            write(rel, "# Private failure database\n\nCases that must not be "
                       "public. This folder is git-ignored.\n\n"
                       "## Knowledge gaps\n\n(none recorded yet)\n")
        text = read(rel)
        code = next_code(text, r"^## F(\d{2}) — ", "F")
        case["rules"] = case["rules"] if isinstance(case["rules"], list) else [case["rules"]]
        write(rel, insert_case(rel, "## Knowledge gaps",
                               render_case(code, case, "en")))
        print("Wrote %s into %s (private, not published)." % (code, rel))
        return 0

    if not case.get("ru"):
        raise SystemExit(
            "a public case needs its Russian half under \"ru\". Without it the "
            "two halves drift and the self-audit goes red at the next push. "
            "Add it, or use --local for a case that stays private.")

    en_text = read(FILES["en"]["failures"])
    code = next_code(en_text, r"^## F(\d{2}) — ", "F")

    rule_code = test_code = None
    if case.get("new_rule"):
        rule_code = next_code(read(FILES["en"]["rules"]), r"^\| R(\d{2}) \|", "R")
        case["rules"] = list(case["rules"]) + [rule_code]
    if case.get("test"):
        test_code = next_code(read(FILES["en"]["tests"]), r"^\| T-(\d{2}) \|", "T-")
        case["test_code"] = test_code

    for lang in ("en", "ru"):
        src = case if lang == "en" else {**case, **case["ru"]}
        src["rules"] = case["rules"]
        src["test_code"] = case.get("test_code")
        src["existing_test"] = case.get("existing_test")
        files = FILES[lang]
        write(files["failures"],
              insert_case(files["failures"], files["gaps"], render_case(code, src, lang)))
        if rule_code:
            rule = dict(case["new_rule"])
            if lang == "ru":
                rule.update(case["ru"].get("new_rule") or {})
            rule["from"] = code
            rule.setdefault("section", case["new_rule"].get("section", "execution"))
            write(files["rules"], add_rule_row(files["rules"], rule_code, rule, lang))
        if test_code:
            test = dict(case["test"])
            if lang == "ru":
                test.update(case["ru"].get("test") or {})
            test["rules"] = ", ".join(case["rules"])
            test["from"] = code
            write(files["tests"], add_test_row(files["tests"], test_code, test, lang))

    print("Wrote %s to both languages." % code)
    if rule_code:
        print("New rule %s added to the register." % rule_code)
    if test_code:
        print("New test %s added to the register — now write the test itself; "
              "until it exists it is a debt, not a guard." % test_code)
    print("\nRun `python3 tools/self-audit.py` before committing.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
