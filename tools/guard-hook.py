# -*- coding: utf-8 -*-
"""GUARD HOOK — makes the truth guard run whether anyone remembers it or not.

A skill is a set of instructions, and instructions get skipped: the session
ends, the work did not look like engine work, somebody said "just fix it". This
script turns the guard from a habit into a gate.

Three modes, wired into Claude Code through `.claude/settings.json`:

    mark    PostToolUse on Write|Edit. Cheap. If the edited file matches the
            project's watch list, it drops a marker saying the engine changed.

    gate    Stop. Cheap. If a marker is newer than the last clean guard run, it
            blocks the turn from ending and says what to run.

    run     Invoked by Claude or by hand. Runs the project's guard commands and,
            only when every one of them passes, stamps the clean run and clears
            the marker — which is what opens the gate.

    status  Prints what the gate currently thinks. For humans.

The project declares what to watch and what to run in `.claude/reality-guard.json`:

    {
      "watch":  ["engine/**", "bot/**", "backtest/**"],
      "checks": [
        {"name": "battle guard",   "cmd": "python3 drafts/battle-guard.py"},
        {"name": "truth guard",    "cmd": "python3 ~/.claude/skills/reality-truth-guard/tools/truth-guard.py --trades ... --bars ..."}
      ]
    }

Nothing here ever raises into the session: a broken hook must not break the
work. Every mode exits 0 except `gate`, which exits 0 too and speaks through
its JSON, and `run`, which exits 1 when a check fails.
"""
from __future__ import annotations

import fnmatch
import json
import os
import subprocess
import sys
import time

MANIFEST = os.path.join(".claude", "reality-guard.json")
MARKER = os.path.join(".claude", ".reality-guard-dirty")
STAMP = os.path.join(".claude", ".reality-guard-pass")
LOOP = os.path.join(".claude", ".reality-guard-blocks")

# How many times in a row the gate may block before it lets go. A gate that can
# never be satisfied would trap the session, and a trap is worse than a missed
# check: the person stops trusting the guard and switches it off entirely.
MAX_BLOCKS = 3

DEFAULT_WATCH = [
    "*engine*", "*Движок*", "*bot/*", "*backtest*", "*Прогон*", "*runner*",
    "*strategy*", "*Стратег*", "*indicator*", "*Индикатор*",
]


def project_root():
    """Where the manifest lives. The hook runs from the project root."""
    return os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()


def load_manifest(root):
    path = os.path.join(root, MANIFEST)
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def watched(path, manifest):
    patterns = manifest.get("watch") or DEFAULT_WATCH
    norm = path.replace(os.sep, "/")
    for pattern in patterns:
        if fnmatch.fnmatch(norm, pattern) or fnmatch.fnmatch(norm, "*/" + pattern):
            return True
    return False


def read_stdin_json():
    try:
        raw = sys.stdin.read()
        return json.loads(raw) if raw.strip() else {}
    except (ValueError, OSError):
        return {}


def mtime(path):
    try:
        return os.path.getmtime(path)
    except OSError:
        return None


# ---------------------------------------------------------------- mark --- #

def do_mark(root, manifest):
    data = read_stdin_json()
    tool_input = data.get("tool_input") or {}
    response = data.get("tool_response") or {}
    path = response.get("filePath") or tool_input.get("file_path") or ""
    if not path or not watched(path, manifest):
        return 0

    marker = os.path.join(root, MARKER)
    os.makedirs(os.path.dirname(marker), exist_ok=True)
    try:
        touched = []
        if os.path.exists(marker):
            with open(marker, encoding="utf-8") as f:
                touched = [line.strip() for line in f if line.strip()]
        if path not in touched:
            touched.append(path)
        with open(marker, "w", encoding="utf-8") as f:
            f.write("\n".join(touched[-50:]))
    except OSError:
        return 0

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext":
                "REALITY TRUTH GUARD: this file can move a trading result. "
                "Before this turn ends the guard must run clean — "
                "`python3 <skill>/tools/guard-hook.py run` from the project root. "
                "Until it does, the numbers are not served and the change is not "
                "promoted.",
        }
    }, ensure_ascii=False))
    return 0


# ---------------------------------------------------------------- gate --- #

def do_gate(root, manifest):
    marker, stamp, loop = (os.path.join(root, MARKER), os.path.join(root, STAMP),
                           os.path.join(root, LOOP))
    dirty, passed = mtime(marker), mtime(stamp)
    if dirty is None or (passed is not None and passed >= dirty):
        try:
            if os.path.exists(loop):
                os.remove(loop)
        except OSError:
            pass
        return 0

    # The gate has already blocked several times: something is stuck. Let go,
    # but say so loudly rather than pretending everything is fine.
    blocks = 0
    try:
        if os.path.exists(loop):
            with open(loop, encoding="utf-8") as f:
                blocks = int((f.read() or "0").strip() or 0)
    except (OSError, ValueError):
        blocks = 0
    if blocks >= MAX_BLOCKS:
        print(json.dumps({
            "systemMessage":
                "REALITY TRUTH GUARD: the gate has blocked %d times and is "
                "letting go. The engine was changed and the guard has still not "
                "run clean — these numbers are NOT verified." % blocks,
        }, ensure_ascii=False))
        return 0

    try:
        with open(loop, "w", encoding="utf-8") as f:
            f.write(str(blocks + 1))
    except OSError:
        pass

    try:
        with open(marker, encoding="utf-8") as f:
            files = [line.strip() for line in f if line.strip()]
    except OSError:
        files = []

    checks = manifest.get("checks") or []
    names = ", ".join(c.get("name", "?") for c in checks) if checks else \
        "none declared in .claude/reality-guard.json"
    print(json.dumps({
        "decision": "block",
        "reason":
            "REALITY TRUTH GUARD has not run since the engine was changed.\n\n"
            "Changed: %s\n"
            "Checks for this project: %s\n\n"
            "Run `python3 <skill>/tools/guard-hook.py run` from the project root. "
            "If it finds something, fix the engine rather than explaining it away "
            "— a divergence is a computation error, not a modelling convention. "
            "If a check cannot be run right now, say so explicitly and say that "
            "the numbers are unverified; do not end the turn silently."
            % (", ".join(files[:10]) or "engine files", names),
    }, ensure_ascii=False))
    return 0


# ----------------------------------------------------------------- run --- #

def do_run(root, manifest):
    checks = manifest.get("checks") or []
    if not checks:
        print("REALITY TRUTH GUARD: this project declares no checks.")
        print("Create .claude/reality-guard.json with a \"checks\" list, or the "
              "gate has nothing to be satisfied by.")
        return 1

    print("REALITY TRUTH GUARD — running %d check(s)\n" % len(checks))
    failed = []
    for check in checks:
        name, cmd = check.get("name", "?"), check.get("cmd")
        if not cmd:
            continue
        print("--- %s" % name)
        print("    %s" % cmd)
        started = time.time()
        try:
            done = subprocess.run(cmd, shell=True, cwd=root,
                                  timeout=check.get("timeout", 1800))
            code = done.returncode
        except subprocess.TimeoutExpired:
            code = -1
            print("    timed out")
        except OSError as e:
            code = -1
            print("    could not run: %s" % e)
        print("    %s in %.1f s\n" % ("PASSED" if code == 0 else "FAILED", time.time() - started))
        if code != 0:
            failed.append(name)

    if failed:
        print("FAILED: %s" % ", ".join(failed))
        print("The gate stays shut. Fix the engine, then run this again.")
        return 1

    stamp, marker, loop = (os.path.join(root, STAMP), os.path.join(root, MARKER),
                           os.path.join(root, LOOP))
    try:
        os.makedirs(os.path.dirname(stamp), exist_ok=True)
        with open(stamp, "w", encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
        for path in (marker, loop):
            if os.path.exists(path):
                os.remove(path)
    except OSError as e:
        print("Checks passed but the stamp could not be written: %s" % e)
        return 1
    print("All checks passed. The gate is open.")
    return 0


# -------------------------------------------------------------- status --- #

def do_status(root, manifest):
    marker, stamp = os.path.join(root, MARKER), os.path.join(root, STAMP)
    dirty, passed = mtime(marker), mtime(stamp)
    print("Project: %s" % root)
    print("Manifest: %s" % ("found" if manifest else "missing — using defaults"))
    print("Checks: %d" % len(manifest.get("checks") or []))
    if dirty is None:
        print("State: clean — no engine change is waiting for the guard.")
    elif passed is not None and passed >= dirty:
        print("State: clean — the guard ran after the last engine change.")
    else:
        print("State: DIRTY — the engine changed and the guard has not run since.")
    return 0


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "status"
    root = project_root()
    manifest = load_manifest(root)
    try:
        if mode == "mark":
            return do_mark(root, manifest)
        if mode == "gate":
            return do_gate(root, manifest)
        if mode == "run":
            return do_run(root, manifest)
        return do_status(root, manifest)
    except Exception as e:                                    # noqa: BLE001
        # A broken hook must never break the session. Say it and step aside.
        if mode in ("mark", "gate"):
            print(json.dumps({"systemMessage":
                              "REALITY TRUTH GUARD hook error: %s" % e},
                             ensure_ascii=False))
            return 0
        print("guard-hook error: %s" % e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
