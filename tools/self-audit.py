# -*- coding: utf-8 -*-
"""SELF-AUDIT — the skill checking itself.

A skill that grows by hand drifts by hand: a failure gets written down and its
rule never does, a rule cites a test nobody wrote, the translation keeps the old
numbering, the fixture quietly stops catching things. None of that is visible by
reading, and all of it is trivial to check.

    python3 tools/self-audit.py [--skip-fixture]

Exit code 1 if anything is wrong. This runs in CI on every push, and it is worth
running by hand after adding a failure to the database.

What it checks:

  1. every failure declares its rules and its test
  2. every rule code referenced anywhere actually exists
  3. every test code referenced anywhere actually exists
  4. every rule says which failure it came from
  5. every test in the register cites a rule and a failure that exist
  6. failure, rule and test codes are contiguous — no silent gaps
  7. every markdown link resolves
  8. the Russian translation carries exactly the same codes as the English
  9. the knowledge gaps section exists and is not empty
 10. the fixture still yields exactly ten findings and a non-zero exit
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

EN = {
    "failures": "FAILURE-DATABASE.md",
    "rules": "RULES.md",
    "tests": "TESTS.md",
    "skill": "SKILL.md",
    "checks": "CHECKS.md",
    "report": "REPORT.md",
    "contract": "EXECUTION-CONTRACT.md",
    "readme": "README.md",
}
RU = {
    "failures": "ru/БАЗА-ОТКАЗОВ.md",
    "rules": "ru/ПРАВИЛА.md",
    "tests": "ru/ТЕСТЫ.md",
    "skill": "ru/НАВЫК.md",
    "checks": "ru/ПРОВЕРКИ.md",
    "report": "ru/ОТЧЁТ.md",
    "contract": "ru/ДОГОВОР-БОЯ.md",
    "readme": "ru/README.md",
}

FAILURE_HEAD = re.compile(r"^## (F\d{2}) — (.+)$", re.M)
RULE_ROW = re.compile(r"^\| (R\d{2}) \|", re.M)
TEST_ROW = re.compile(r"^\| (T-\d{2}) \|", re.M)
CODE_ANY = re.compile(r"\b(F\d{2}|R\d{2}|T-\d{2})\b")

problems = []
notes = []


def read(rel):
    path = os.path.join(ROOT, rel)
    if not os.path.exists(path):
        problems.append("file missing: %s" % rel)
        return ""
    with open(path, encoding="utf-8") as f:
        return f.read()


def check(name, ok, detail=""):
    print("  %-7s %s%s" % ("ok" if ok else "WRONG", name,
                           ("   " + detail) if detail else ""))
    if not ok:
        problems.append(name + ((" — " + detail) if detail else ""))


def contiguous(codes, prefix, width=2):
    """Codes must run 01, 02, 03… — a gap means something was deleted."""
    numbers = sorted(int(c.replace(prefix, "").lstrip("-")) for c in codes)
    if not numbers:
        return False, "none found"
    expected = list(range(1, len(numbers) + 1))
    if numbers != expected:
        missing = sorted(set(expected) - set(numbers))
        extra = sorted(set(numbers) - set(expected))
        return False, "gaps at %s, unexpected %s" % (missing or "-", extra or "-")
    return True, "%s01–%s%02d" % (prefix, prefix, numbers[-1])


def audit_language(tag, files):
    print("\n%s:" % tag)
    failures_text = read(files["failures"])
    rules_text = read(files["rules"])
    tests_text = read(files["tests"])

    failures = FAILURE_HEAD.findall(failures_text)
    failure_codes = [c for c, _ in failures]
    rule_codes = RULE_ROW.findall(rules_text)
    test_codes = TEST_ROW.findall(tests_text)

    ok, detail = contiguous(failure_codes, "F")
    check("failure codes run without gaps", ok, detail)
    ok, detail = contiguous(rule_codes, "R")
    check("rule codes run without gaps", ok, detail)
    ok, detail = contiguous(test_codes, "T-")
    check("test codes run without gaps", ok, detail)

    # 1. Every failure declares its rules and its test.
    sections = re.split(r"^## ", failures_text, flags=re.M)[1:]
    undeclared = []
    for section in sections:
        head = section.split("\n", 1)[0]
        code = head.split(" ")[0]
        if not code.startswith("F"):
            continue
        body = section.lower()
        if "rules." not in body and "правила." not in body:
            undeclared.append(code + " (no rules)")
        if "test." not in body and "тест." not in body:
            undeclared.append(code + " (no test)")
    check("every failure declares its rules and its test", not undeclared,
          ", ".join(undeclared))

    # 2-3. Every code referenced anywhere exists.
    known = set(failure_codes) | set(rule_codes) | set(test_codes)
    dangling = {}
    for key, rel in files.items():
        text = read(rel)
        for code in set(CODE_ANY.findall(text)):
            if code not in known:
                dangling.setdefault(code, []).append(rel)
    check("every code referenced exists", not dangling,
          ", ".join("%s in %s" % (c, ", ".join(w)) for c, w in dangling.items()))

    # 4. Every rule says where it came from.
    rows = [r for r in rules_text.splitlines() if RULE_ROW.match(r)]
    rootless = [r.split("|")[1].strip() for r in rows
                if not re.search(r"(F\d{2}|risk|риск|memory|памят|contract|договор|gap|пробел|decision|решени)",
                                 r.split("|")[-2], re.I)]
    check("every rule says which failure it came from", not rootless,
          ", ".join(rootless))

    # 5. Every register test cites a rule and a failure that exist.
    bad_tests = []
    for row in tests_text.splitlines():
        m = TEST_ROW.match(row)
        if not m:
            continue
        cells = [c.strip() for c in row.split("|")]
        cited = set(CODE_ANY.findall(" ".join(cells[3:5])))
        if not any(c.startswith("R") for c in cited):
            bad_tests.append(m.group(1) + " (no rule)")
        if not any(c.startswith("F") for c in cited) and "gap" not in row and "пробел" not in row:
            bad_tests.append(m.group(1) + " (no failure)")
    check("every test cites a rule and a failure", not bad_tests,
          ", ".join(bad_tests))

    # 9. Knowledge gaps exist and are not empty.
    gaps = re.search(r"^## (Knowledge gaps|Пробелы знания)\s*$(.+)", failures_text,
                     re.M | re.S)
    listed = len(re.findall(r"^\d+\. ", gaps.group(2), re.M)) if gaps else 0
    check("knowledge gaps are written down", listed > 0,
          "%d recorded" % listed if gaps else "section missing")

    return {"F": set(failure_codes), "R": set(rule_codes), "T-": set(test_codes)}


def audit_links():
    print("\nLinks:")
    broken = []
    for folder, _, names in os.walk(ROOT):
        if ".git" in folder:
            continue
        for name in names:
            if not name.endswith(".md"):
                continue
            path = os.path.join(folder, name)
            with open(path, encoding="utf-8") as f:
                text = f.read()
            for m in re.finditer(r"\]\(([^)#:]+)\)", text):
                target = m.group(1)
                if target.startswith("http"):
                    continue
                full = os.path.normpath(os.path.join(folder, target))
                if not os.path.exists(full):
                    broken.append("%s → %s" % (os.path.relpath(path, ROOT), target))
    check("every markdown link resolves", not broken, "; ".join(broken[:6]))


def audit_fixture():
    print("\nFixture:")
    guard = os.path.join(ROOT, "tools", "truth-guard.py")
    fixture = os.path.join(ROOT, "tools", "fixture")
    cmd = [sys.executable, guard,
           "--trades", os.path.join(fixture, "trades-broken.csv"),
           "--bars", os.path.join(fixture, "bars.csv"),
           "--broker-day", "eet-us", "--lot-step", "0.01", "--min-lot", "0.01"]
    try:
        done = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired) as e:
        check("the guard runs on the fixture", False, str(e))
        return
    found = len(re.findall(r"^  FINDING", done.stdout, re.M))
    check("the guard still finds exactly ten planted failures", found == 10,
          "found %d" % found)
    check("the guard exits non-zero when it finds something", done.returncode == 1,
          "exit code %d" % done.returncode)
    # A guard that is always green is not a guard — but one that is always red
    # is useless too. Prove it can also stay quiet on an export that is sound.
    clean_path = os.path.join(fixture, "trades-clean.csv")
    if os.path.exists(clean_path):
        clean = subprocess.run([sys.executable, guard, "--trades", clean_path,
                                "--bars", os.path.join(fixture, "bars.csv"),
                                "--broker-day", "eet-us"],
                               capture_output=True, text=True, timeout=120)
        check("the guard stays quiet on a sound export", clean.returncode == 0,
              "exit code %d, findings: %s" % (
                  clean.returncode,
                  "; ".join(re.findall(r"^  FINDING\s+(.+?)\s\s", clean.stdout, re.M)) or "-"))
    else:
        check("a sound-export fixture exists", False, "trades-clean.csv missing")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--skip-fixture", action="store_true")
    a = p.parse_args()

    print("SELF-AUDIT — the skill checking itself\n")
    en = audit_language("English", EN)
    ru = audit_language("Russian", RU)

    print("\nTranslation drift:")
    for kind in ("F", "R", "T-"):
        only_en = sorted(en[kind] - ru[kind])
        only_ru = sorted(ru[kind] - en[kind])
        check("%s codes match across languages" % kind,
              not only_en and not only_ru,
              "only in English: %s; only in Russian: %s"
              % (only_en or "-", only_ru or "-"))

    audit_links()
    if not a.skip_fixture:
        audit_fixture()

    print()
    if problems:
        print("WRONG: %d" % len(problems))
        for item in problems:
            print("  · %s" % item)
        return 1
    print("The skill is consistent with itself.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
