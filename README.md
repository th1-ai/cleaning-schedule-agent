# Cleaning Schedule Agent

A Claude Code skill for hotel and small-property operators. It pulls reservations from your PMS, reads every booking note, and builds a month-long, day-by-day cleaning schedule with staffing, linen, and ironing rules already applied. Then it drafts the per-staff emails so each person gets their schedule in their language.

Built on the **WAT framework** (Workflows, Agents, Tools): probabilistic AI handles reasoning, deterministic scripts handle execution.

---

## What it does

- **Pulls reservations and notes** for the target month from your PMS — checkouts, stayovers, check-ins, bed setups, dietary needs, late checkouts, mid-stay cleans
- **Applies staffing rules** — fixed days, flex days, priority order (rooms → ironing → gardening / common areas), backup-cleaner triggers for heavy days
- **Manages linen stock** — counts sheet sets through the month, schedules ironing sessions before stock dips, prefers light days for ironing
- **Handles whole-property rental weeks** — different rules apply: 3-staff changeovers, hours caps, in-rental tidies driven by the booking notes
- **Reads ad-hoc adjustments** from `schedule-adjustments.md` — whole-villa rentals with paid housekeeping add-ons, staff holidays, equipment days, events
- **Drafts per-staff emails** in HTML with a colour-coded table showing each person's days, tasks, and ironing sessions

---

## What you need

- [Claude Code](https://claude.ai/code) installed
- A PMS with API access — the agent calls a `lookup`-style tool, an `api`-style tool for reservation lists, and a `notes`-style tool for appending notes. The reference setup uses Cloudbeds, but any PMS with reservation lookup + reservation-notes endpoints works.
- A Google Sheet for the published schedule (with `Schedule` and `System` tabs)
- A Gmail-compatible outbound account that can create drafts

---

## Quick start

1. **Clone the repo** into a Claude Code project:

   ```bash
   git clone https://github.com/th1-ai/cleaning-schedule-agent.git
   cd cleaning-schedule-agent
   ```

2. **Copy the env template** and fill it in:

   ```bash
   cp .env.example .env
   ```

3. **Edit [`.claude/skills/cleaning-schedule/SKILL.md`](.claude/skills/cleaning-schedule/SKILL.md)** — replace placeholders described in [Customising](#customising) and rewrite the example staff section to match your team.

4. **Open in Claude Code** from the project root:

   ```bash
   claude
   ```

5. **Invoke the skill**:

   > "Fill out the cleaning schedule for May."

   Claude Code will pick up the `cleaning-schedule` skill automatically.

---

## File structure

```
cleaning-schedule-agent/
├── README.md                                              # This file
├── .env.example                                           # PMS auth, sheet IDs, staff contacts
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

The skill file uses placeholders so it can be adapted to any PMS + sheet stack. Replace the following before first run:

| Placeholder | What to put | Example |
|---|---|---|
| `{{PMS_LOOKUP_TOOL}}` | Script that looks up reservations | `tools/lookup_guest.py` |
| `{{PMS_API_TOOL}}` | Script/library that wraps your PMS API | `tools/cloudbeds_api.py` |
| `{{PMS_NOTES_TOOL}}` | Script that appends a note to a reservation | `tools/cloudbeds_notes.py` |
| `{{PMS_PROPERTY_ID}}` | Property ID in your PMS | `123456789` |
| `{{SHEET_ID_TASKS}}` | Google Sheet ID for the cleaning schedule | `1AbCdEf...` |
| `{{EMAIL_CLI}}` | Command-line wrapper for email + sheets | `gws` |
| `{{NUM_ROOMS}}` | Number of cleanable rooms | `6` |
| `{{INBOX_PRIMARY}}` | Account that owns the schedule sheet | `info@yourhotel.com` |

Reference example tool paths from a Cloudbeds-based reference setup: `tools/lookup_guest.py`, `tools/cloudbeds_api.py`, `tools/cloudbeds_notes.py`. Yours will differ.

The example staff section (`<Staff A>`, `<Staff B>`) in `SKILL.md` is a starting point — rewrite the days, hours, and priorities to match your team. The structure (priority order, flex day, backup logic, whole-property cap) generalises well.

---

## How memory works

This is a skill-only repo, so there's no per-skill memory folder by default. If you want persistent learnings (e.g. "always check stayover bed setup for `<RoomType>` because it can split"), add a `.claude/agent-memory/cleaning-schedule/` folder and write short notes there — Claude Code will pick them up automatically.

---

## Related agents

This skill works well alongside:

- [`morning-routine-agent`](https://github.com/th1-ai/morning-routine-agent) — uses today's row of the schedule in the daily briefing
- [`fb-shopping-list-agent`](https://github.com/th1-ai/fb-shopping-list-agent) — pulls the same guest counts to drive the grocery list
- [`pre-arrival-outreach-agent`](https://github.com/th1-ai/pre-arrival-outreach-agent) — surfaces bed-setup and dietary requests that this skill then writes into the schedule
- [`email-triage-agent`](https://github.com/th1-ai/email-triage-agent) — captures the guest preferences (bed setup, late checkout) that flow into reservation notes

---

## License

MIT — see [LICENSE](LICENSE).
