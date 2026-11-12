# Cleaning Schedule Agent

A Claude Code skill for hotel and small-property operators. It pulls reservations from your PMS, reads every booking note, and builds a month-long, day-by-day cleaning schedule with staffing, linen, and ironing rules already applied. Then it drafts the per-staff emails so each person gets their schedule in their language.

Built on the **WAT framework** (Workflows, Agents, Tools): the AI handles the reasoning, and deterministic scripts handle the execution. This repo is the workflow. It is a markdown template with no code in it: you bring the scripts that talk to your PMS, your Google Sheet and your mailbox.

Nothing goes out without you. When you run it yourself, the skill shows you the schedule before it writes to the sheet. It only creates email drafts, and it never changes a booking.

It can also run on its own on a schedule. [`AUTONOMY.md`](AUTONOMY.md) sets how much it may do then. The default is Level 1: it checks the published schedule against the PMS each day and reports what changed, and it writes nothing outside its own run log.

---

## What it does

- **Pulls reservations and notes** for the target month from your PMS — checkouts, stayovers, check-ins, bed setups, dietary needs, late checkouts, mid-stay cleans
- **Applies staffing rules** — fixed days, flex days, priority order (rooms → ironing → gardening / common areas), backup-cleaner triggers for heavy days
- **Manages linen stock** — counts sheet sets through the month, schedules ironing sessions before stock dips, prefers light days for ironing
- **Handles whole-property rental weeks** — different rules apply: 3-staff changeovers, hours caps, in-rental tidies driven by the booking notes
- **Reads ad-hoc adjustments** from `schedule-adjustments.md` — whole-villa rentals with paid housekeeping add-ons, staff holidays, equipment days, events
- **Drafts per-staff emails** in HTML with a colour-coded table showing each person's days, tasks, and ironing sessions. Drafts only: you review and send them
- **Runs unattended within limits you set** — a daily check that compares the sheet with the PMS, keeps a run log, and reports only what needs you (see [Run it on its own](#run-it-on-its-own))

---

## What you need

- [Claude Code](https://code.claude.com/docs/en/overview) installed
- A PMS with API access, and your own scripts that wrap it: one that lists reservations and reads reservation details and notes, and one that appends a note to a reservation. The reference setup uses Cloudbeds, but any PMS with those endpoints works.
- A Google Sheet for the published schedule, with a `Schedule` tab (columns A to K as listed in `SKILL.md`) and a `System` tab (one row per staff member: name, priority, contracted days, responsibilities, email, language). From autonomy Level 2 you also need a `Proposed` tab with the same columns plus column L
- A command-line tool that can read and write Google Sheets and create Gmail drafts, signed in to the account that owns the sheet

---

## Quick start

1. **Clone the repo** into a Claude Code project:

   ```bash
   git clone https://github.com/th1-ai/cleaning-schedule-agent.git
   cd cleaning-schedule-agent
   ```

2. **Add your tools.** Put your PMS wrapper scripts in the project (for example in `tools/`) and make sure your email + sheets CLI works from this folder. If your scripts need secrets, copy the env template and fill it in:

   ```bash
   cp .env.example .env
   ```

3. **Open Claude Code** from the project root:

   ```bash
   claude
   ```

4. **Set it up.** Paste this as your first prompt:

   > "Read the README and `.claude/skills/cleaning-schedule/SKILL.md`, then set this skill up with me. Ask me for each placeholder value one at a time, then ask about my staff: names, days, hours and priorities. Write my answers into `SKILL.md`. Do not call the PMS or the sheet yet. Leave `AUTONOMY.md` as it is."

   You can also edit [`SKILL.md`](.claude/skills/cleaning-schedule/SKILL.md) by hand: replace the placeholders described in [Customising](#customising) and rewrite the example staff section to match your team.

5. **Invoke the skill**:

   > "Fill out the cleaning schedule for May."

   Claude Code picks up the `cleaning-schedule` skill from its description. You can also call it directly with `/cleaning-schedule May`.

---

## Verify it works

Do a dry run before you trust it with a real month:

> "Build the cleaning schedule for next month, but do not write to the sheet and do not draft any emails. Show me the plan."

Check three things against your PMS: the checkouts on two or three days you know well, one booking with a note (late checkout, bed setup), and the weekly hours per staff member.

## Run it on its own

The skill has a scheduled mode: `/cleaning-schedule scheduled`. It reads [`AUTONOMY.md`](AUTONOMY.md), checks the published schedule against the PMS, acts only as far as the level permits, appends an entry to `runs/LOG.md`, writes a handoff file for the morning briefing, and ends with a report whose first section is "Needs you".

| Level | A scheduled run |
|---|---|
| 0 or PAUSED | does nothing |
| 1 (default) | reads and reports |
| 2 | also writes the `Proposed` tab and creates staff email drafts |
| 3 | also updates the fact columns of existing `Schedule` rows (10 rows per run) and fills empty staff columns 14 or more days ahead with fixed contracted days |

Never on its own, at any level: sending an email, any PMS write, a change to who works on a day that already has staff, a flex-day move or an hours change, booking a backup cleaner, deleting anything. The full table and the guard rails are in `AUTONOMY.md`.

### 1. Make the tools callable without you

An unattended run can only use commands that are on an allowlist. Your PMS wrapper must therefore work as one read-only command (for example `python3 tools/your_pms.py reservations --from ... --to ...`), and your sheets CLI must work without a login prompt.

Copy the example permissions and fill in the two placeholders (`{{PMS_API_TOOL}}`, `{{EMAIL_CLI}}`) with the same values as in `SKILL.md`. Change the command shapes to match your own tools:

```bash
cp .claude/settings.example.json .claude/settings.scheduled.json
```

The file is an example. It allows the PMS read command, the sheet read command and writes to `runs/`. It denies reading `.env`, editing `AUTONOMY.md` or anything in `.claude/`, `rm`, `curl`, `git push`, email send commands and web access. Claude Code does not load a file with this name by itself, so your normal sessions do not change. For Level 2, add an allow rule for your sheet write command and your draft-create command. Do not add a send command.

It also wires one hook, [`.claude/hooks/autonomy_guard.py`](.claude/hooks/autonomy_guard.py) (needs `python3`). Before each shell command it reads the level from `AUTONOMY.md` and blocks: every command at `Level: 0` or PAUSED, a draft or a `Proposed` tab write below Level 2, a `Schedule` tab write below Level 3, and send, clear, delete and `rm` commands at every level. The patterns at the top of the script are examples for one Google Workspace CLI; edit them for yours, and put your PMS note script in `NEVER_SUBSTRINGS`. The hook matches command text, so treat it as a second check behind the allowlist, not as a security boundary. It cannot count shadow runs or daily caps; the skill does that from the run log.

### 2. Run it once by hand

```bash
claude -p "/cleaning-schedule scheduled" \
  --settings .claude/settings.scheduled.json \
  --permission-mode dontAsk \
  --permission-prompts none
```

`-p` runs Claude Code without a conversation. `--permission-mode dontAsk` denies every tool call that is not on the allowlist instead of asking. `--permission-prompts none` tells Claude that nobody can approve a request (it needs Claude Code v2.1.259 or later; leave it out on an older version). Read the report and `runs/LOG.md`. A denied command shows up as an error in the report: add its read-only form to the allowlist, or fix the command shape in `SKILL.md`.

### 3. Schedule it

Example for cron on macOS or Linux, every day at 06:30. Cron has a short `PATH`, so use full paths (`command -v claude` prints the one for `claude`):

```
30 6 * * * cd /full/path/to/cleaning-schedule-agent && /full/path/to/claude -p "/cleaning-schedule scheduled" --settings .claude/settings.scheduled.json --permission-mode dontAsk --permission-prompts none >> runs/cron.log 2>&1
```

Cron does not run while the computer is asleep or off. The Claude Code desktop app also has local scheduled tasks; they run only while the app is open and the computer is awake. Cloud scheduled tasks start from a fresh clone without your local tools, so they do not fit this template as it is.

Unattended use of a personal Pro or Max plan is subject to Anthropic's usage policy; for a heavy or business-critical schedule, use an API key or a team plan.

### 4. Move up one level at a time

1. Run at the current level for at least 7 days.
2. Read `runs/LOG.md`. Check a few entries against the PMS and the sheet. The "Proposed" lines show what the next level would have done.
3. If they are right, change one line in `AUTONOMY.md` (`Level: 1` to `Level: 2`). For Level 2, add the `Proposed` tab and the two allow rules first.
4. The first 5 runs at the new level are shadow runs: the skill still acts at the old level and logs what it would have done.

To stop everything, set `Level: PAUSED`. It applies at the next run. A missing `AUTONOMY.md`, a missing `Level:` line or an unknown value also counts as PAUSED.

## Troubleshooting

- **The skill does not start.** Type `/` in Claude Code and look for `cleaning-schedule`. If it is missing, you probably started `claude` outside the repo folder. Skills load from `.claude/skills/` in the project you open.
- **Claude stops and asks for values.** `SKILL.md` still contains a placeholder in double curly braces. Run the setup prompt from step 4.
- **A PMS or sheet command fails.** The command shapes in `SKILL.md` are examples. Tell Claude to read your script or run your CLI's `--help`, then correct the examples in `SKILL.md` so the next run is right.
- **A scheduled run does nothing.** Check the level line in `AUTONOMY.md`, then the last entry in `runs/LOG.md` and the end of `runs/cron.log`. A message that starts with `autonomy guard:` comes from the hook and names the level that the command needs.
- **A stay is missing.** Check that the booking has a room assigned and a status your script returns. Stays that start before the month and end after it need the extra pull described in step 2 of `SKILL.md`.

---

## File structure

```
cleaning-schedule-agent/
├── README.md                                              # This file
├── AUTONOMY.md                                            # Level, action limits and guard rails for scheduled runs
├── .env.example                                           # Secrets for your own PMS / sheets tools
├── .gitignore
├── LICENSE
├── runs/
│   ├── README.md                                          # Format of the run log and the handoff file
│   └── .gitkeep                                           # LOG.md and handoff/ appear here; git ignores them
└── .claude/
    ├── settings.example.json                              # Example permissions + hook for scheduled runs
    ├── hooks/
    │   └── autonomy_guard.py                              # Blocks commands above the current level
    └── skills/
        └── cleaning-schedule/
            ├── SKILL.md                                   # The skill definition
            └── schedule-adjustments.md                    # One-off changes for specific weeks
```

---

## Customising

The skill file uses placeholders so it can be adapted to any PMS + sheet stack. Replace the following before first run (or let the setup prompt in [Quick start](#quick-start) do it). The skill stops and asks if it finds one still unfilled.

| Placeholder | What to put | Example |
|---|---|---|
| `{{PMS_API_TOOL}}` | Script/library that lists reservations and reads details and notes | `tools/cloudbeds_api.py` |
| `{{PMS_NOTES_TOOL}}` | Script that appends a note to a reservation | `tools/cloudbeds_notes.py` |
| `{{PMS_PROPERTY_ID}}` | Property ID in your PMS | `123456789` |
| `{{SHEET_ID_TASKS}}` | Google Sheet ID for the cleaning schedule | `1AbCdEf...` |
| `{{EMAIL_CLI}}` | Command-line tool for Sheets + Gmail drafts | `gws` |
| `{{NUM_ROOMS}}` | Number of cleanable rooms | `6` |
| `{{INBOX_PRIMARY}}` | Account that owns the schedule sheet | `info@yourhotel.com` |

The example tool paths come from a Cloudbeds-based reference setup. Those scripts are not in this repo; yours will differ. The code and command snippets in `SKILL.md` show the shape of each call, so adjust them to your own tools.

The example staff section (`<Staff A>`, `<Staff B>`) in `SKILL.md` is a starting point — rewrite the days, hours, and priorities to match your team. The structure (priority order, flex day, backup logic, whole-property cap) generalises well.

---

## How memory works

This is a skill-only repo, and a skill has no memory of its own. Three places hold what should persist:

- **Rules that always apply** (e.g. "always check stayover bed setup for `<RoomType>` because it can split") go into `SKILL.md` itself. Ask Claude to add the rule after a run where it mattered.
- **One-off changes for specific weeks** go into [`schedule-adjustments.md`](.claude/skills/cleaning-schedule/schedule-adjustments.md), which the skill reads at the start of every run.
- **What each run checked, did and proposed** goes into `runs/LOG.md` (format in [`runs/README.md`](runs/README.md)). The skill reads the last entries before it acts, so that it does not repeat a write, a draft or a warning. The file stays on your machine; git ignores it.

---

## Related agents

This skill has no hard dependency on another repo. It reads the same PMS reservations and notes as these agents, so they work well side by side:

- [`morning-routine-agent`](https://github.com/th1-ai/morning-routine-agent) — the daily briefing. Each scheduled run of this skill writes `runs/handoff/cleaning-schedule-agent.md` (today, tomorrow, flagged days, "Needs you") for it to read
- [`fb-shopping-list-agent`](https://github.com/th1-ai/fb-shopping-list-agent) — builds the grocery list from the same guest counts
- [`pre-arrival-outreach-agent`](https://github.com/th1-ai/pre-arrival-outreach-agent) — drafts welcome emails to upcoming guests; requests that come back and land in the reservation notes are picked up by this skill
- [`email-triage-agent`](https://github.com/th1-ai/email-triage-agent) — sorts the inbox where bed-setup and late-checkout requests arrive

The full set of 21 agents: [th1.ai/agent-stack](https://th1.ai/agent-stack).

---

## License

MIT — see [LICENSE](LICENSE).
