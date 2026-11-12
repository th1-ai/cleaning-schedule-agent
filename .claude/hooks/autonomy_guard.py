#!/usr/bin/env python3
"""PreToolUse guard for unattended runs of the cleaning-schedule skill.

Claude Code sends the pending tool call as JSON on stdin. This script reads
the level from AUTONOMY.md and blocks a Bash command that the level does not
permit. Exit 0 = no objection (the normal permission rules still apply).
Exit 2 = block; the text on stderr goes back to Claude as the reason.

Wire it only into the settings file you pass to scheduled runs with
--settings. Do not put it in .claude/settings.json: at Level 0 or PAUSED it blocks
every Bash command, which would also stop your on-request sessions.

It matches command TEXT, so it is a second layer, not a security boundary.
The allowlist in the settings file is the first layer.
"""
import json
import os
import re
import sys

# ---------------------------------------------------------------------------
# EXAMPLE patterns for a gws-style Google Workspace CLI.
# Edit them to match the commands of your own tools.
# ---------------------------------------------------------------------------

# Blocked at every level.
NEVER_PATTERNS = [
    r"\b(messages|drafts)\s+send\b",          # sending an email
    r"\bsendmail\b",
    r"(^|[\s;&|('\"/])rm\s",                  # deleting files
    r"\bvalues\s+(clear|batchClear)\b",       # clearing sheet cells
    r"\b(deleteDimension|deleteSheet|deleteRange)\b",
]
# Blocked at every level, plain text match. The PMS note writer goes here.
NEVER_SUBSTRINGS = [
    "{{PMS_NOTES_TOOL}}",
]
# A write to the Google Sheet.
SHEET_WRITE_PATTERN = r"\bvalues\s+(update|append|batchUpdate)\b|\bspreadsheets\s+batchUpdate\b"
# Creating or changing an email draft.
DRAFT_WRITE_PATTERN = r"\bdrafts\s+(create|update)\b"
# Tab names as they appear in a range, e.g. Proposed!A2:L40
PROPOSED_TAB = "Proposed!"
PUBLISHED_TAB = "Schedule!"


def block(reason):
    sys.stderr.write("autonomy guard: " + reason + "\n")
    sys.exit(2)


def read_level(project_dir):
    """Return (level, reason). level is 0-3, or None for PAUSED.

    AUTONOMY.md has exactly one line "Level: <value>", value 0, 1, 2, 3 or
    PAUSED. A missing file, a missing line, more than one line or an unknown
    value all mean PAUSED.
    """
    try:
        with open(os.path.join(project_dir, "AUTONOMY.md"), encoding="utf-8") as fh:
            text = fh.read()
    except OSError:
        return None, "AUTONOMY.md is missing or unreadable"
    values = re.findall(r"^Level:[ \t]*(.*?)[ \t]*$", text, re.MULTILINE)
    if not values:
        return None, "AUTONOMY.md has no 'Level:' line"
    if len(values) > 1:
        return None, "AUTONOMY.md has more than one 'Level:' line"
    if values[0] == "PAUSED":
        return None, "AUTONOMY.md says Level: PAUSED"
    if values[0] in ("0", "1", "2", "3"):
        return int(values[0]), ""
    return None, "AUTONOMY.md has an unknown level value"


def main():
    try:
        data = json.load(sys.stdin)
    except ValueError:
        block("could not read the hook input, so the call is blocked.")
    if not isinstance(data, dict) or data.get("tool_name") != "Bash":
        sys.exit(0)
    command = (data.get("tool_input") or {}).get("command") or ""
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or "."
    level, reason = read_level(project_dir)

    if level is None:
        block(reason + ", which means PAUSED. Scheduled runs do nothing. Log why and stop now.")
    if level == 0:
        block("AUTONOMY.md says Level: 0. Scheduled runs do nothing. Log why and stop now.")

    for pattern in NEVER_PATTERNS:
        if re.search(pattern, command):
            block("this command is never autonomous at any level. Put it under 'Needs you'.")
    for text in NEVER_SUBSTRINGS:
        if text and not text.startswith("{{") and text in command:
            block("this tool is never autonomous at any level. Put it under 'Needs you'.")

    needed = 1
    what = ""
    if re.search(SHEET_WRITE_PATTERN, command):
        if PROPOSED_TAB in command and PUBLISHED_TAB not in command:
            needed, what = 2, "a write to the Proposed tab"
        else:
            needed, what = 3, "a write to the Schedule tab"
    elif re.search(DRAFT_WRITE_PATTERN, command):
        needed, what = 2, "creating an email draft"

    if level < needed:
        block("%s needs Level %d. AUTONOMY.md says Level %d. Record it as proposed instead." % (what, needed, level))
    sys.exit(0)


if __name__ == "__main__":
    main()
