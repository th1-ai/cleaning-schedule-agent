# Schedule Adjustments — Cleaning Staff

Ad-hoc changes to the default housekeeping schedule for specific weeks or days. The cleaning-schedule skill reads this file before it builds a monthly schedule. Adjustments arise from whole-property rentals with paid housekeeping add-ons, staff holidays, one-off events, broken-equipment days, etc.

## How to use this file

- Each entry has a **status** (`pending` or `confirmed`) and a **date range** it affects.
- When an entry is `pending`, the monthly schedule should be built with placeholder hours and a flag note in the Schedule sheet — then re-run once confirmed.
- When a week's hours differ from the staff's contracted weekly hours, **net out** the difference over the adjacent weeks in the same calendar month so the monthly total stays on contract. Flag any month where netting is not possible and propose carry-over to the next month.
- After an entry is applied and its week has fully passed, move it to `## Archive` at the bottom.
- Keep entries short. Link to the triggering email/booking where relevant.

## Entry template

```
### [Guest/Event name] — [YYYY-MM-DD → YYYY-MM-DD]
- **Status:** pending | confirmed
- **Trigger:** booking ref / email link
- **Change:** what differs from default
- **Hours impact:** +X Staff B, +Y Staff A for that week
- **Netting plan:** how surrounding weeks adjust
- **Follow-ups:** what still needs a response, by when
```

---

## Active

_(No active adjustments. Add new entries here using the template above.)_

---

## Archive

_(Move entries here once the week has passed and netting is settled.)_
