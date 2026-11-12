# Cleaning Schedule Agent

A Claude Code skill for hotel and small-property operators. It pulls reservations from your PMS, reads every booking note, and builds a month-long, day-by-day cleaning schedule with staffing, linen, and ironing rules already applied. Then it drafts the per-staff emails so each person gets their schedule in their language.

Built on the **WAT framework** (Workflows, Agents, Tools): the AI handles the reasoning, and deterministic scripts handle the execution. This repo is the workflow. It is a markdown template with no code in it: you bring the scripts that talk to your PMS, your Google Sheet and your mailbox.

Nothing goes out without you. The skill shows you the schedule before it writes to the sheet, it only creates email drafts, and it never changes a booking.

---

## What it does

- **Pulls reservations and notes** for the target month from your PMS — checkouts, stayovers, check-ins, bed setups, dietary needs, late checkouts, mid-stay cleans
- **Applies staffing rules** — fixed days, flex days, priority order (rooms → ironing → gardening / common areas), backup-cleaner triggers for heavy days
- **Manages linen stock** — counts sheet sets through the month, schedules ironing sessions before stock dips, prefers light days for ironing
- **Handles whole-property rental weeks** — different rules apply: 3-staff changeovers, hours caps, in-rental tidies driven by the booking notes
- **Reads ad-hoc adjustments** from `schedule-adjustments.md` — whole-villa rentals with paid housekeeping add-ons, staff holidays, equipment days, events
- **Drafts per-staff emails** in HTML with a colour-coded table showing each person's days, tasks, and ironing sessions. Drafts only: you review and send them

---

## What you need

- [Claude Code](https://code.claude.com/docs/en/overview) installed
- A PMS with API access, and your own scripts that wrap it: one that lists reservations and reads reservation details and notes, and one that appends a note to a reservation. The reference setup uses Cloudbeds, but any PMS with those endpoints works.
- A Google Sheet for the published schedule, with a `Schedule` tab (columns A to K as listed in `SKILL.md`) and a `System` tab (one row per staff member: name, priority, contracted days, responsibilities, email, language)
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

   > "Read the README and `.claude/skills/cleaning-schedule/SKILL.md`, then set this skill up with me. Ask me for each placeholder value one at a time, then ask about my staff: names, days, hours and priorities. Write my answers into `SKILL.md`. Do not call the PMS or the sheet yet."

   You can also edit [`SKILL.md`](.claude/skills/cleaning-schedule/SKILL.md) by hand: replace the placeholders described in [Customising](#customising) and rewrite the example staff section to match your team.

5. **Invoke the skill**:

   > "Fill out the cleaning schedule for May."

   Claude Code picks up the `cleaning-schedule` skill from its description. You can also call it directly with `/cleaning-schedule May`.

---

## Verify it works

Do a dry run before you trust it with a real month:

> "Build the cleaning schedule for next month, but do not write to the sheet and do not draft any emails. Show me the plan."

Check three things against your PMS: the checkouts on two or three days you know well, one booking with a note (late checkout, bed setup), and the weekly hours per staff member.

## Troubleshooting

- **The skill does not start.** Type `/` in Claude Code and look for `cleaning-schedule`. If it is missing, you probably started `claude` outside the repo folder. Skills load from `.claude/skills/` in the project you open.
- **Claude stops and asks for values.** `SKILL.md` still contains a placeholder in double curly braces. Run the setup prompt from step 4.
- **A PMS or sheet command fails.** The command shapes in `SKILL.md` are examples. Tell Claude to read your script or run your CLI's `--help`, then correct the examples in `SKILL.md` so the next run is right.
- **A stay is missing.** Check that the booking has a room assigned and a status your script returns. Stays that start before the month and end after it need the extra pull described in step 2 of `SKILL.md`.

---

## File structure

```
cleaning-schedule-agent/
├── README.md                                              # This file
├── .env.example                                           # Secrets for your own PMS / sheets tools
├── .gitignore
├── LICENSE
└── .claude/
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

This is a skill-only repo, and a skill has no memory of its own. Two places hold what should persist:

- **Rules that always apply** (e.g. "always check stayover bed setup for `<RoomType>` because it can split") go into `SKILL.md` itself. Ask Claude to add the rule after a run where it mattered.
- **One-off changes for specific weeks** go into [`schedule-adjustments.md`](.claude/skills/cleaning-schedule/schedule-adjustments.md), which the skill reads at the start of every run.

---

## Related agents

This skill has no hard dependency on another repo. It reads the same PMS reservations and notes as these agents, so they work well side by side:

- [`morning-routine-agent`](https://github.com/th1-ai/morning-routine-agent) — the daily briefing; today's row of the schedule is a natural input
- [`fb-shopping-list-agent`](https://github.com/th1-ai/fb-shopping-list-agent) — builds the grocery list from the same guest counts
- [`pre-arrival-outreach-agent`](https://github.com/th1-ai/pre-arrival-outreach-agent) — drafts welcome emails to upcoming guests; requests that come back and land in the reservation notes are picked up by this skill
- [`email-triage-agent`](https://github.com/th1-ai/email-triage-agent) — sorts the inbox where bed-setup and late-checkout requests arrive

The full set of 21 agents: [th1.ai/agent-stack](https://th1.ai/agent-stack).

---

## License

MIT — see [LICENSE](LICENSE).
