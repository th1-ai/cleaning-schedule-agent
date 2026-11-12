---
name: cleaning-schedule
description: Builds or updates the monthly housekeeping schedule for a hotel or small property. Pulls reservations and booking notes from the PMS, applies staffing, linen and ironing rules, shows the plan for approval, writes it to the schedule Google Sheet, and drafts per-staff schedule emails. Use when the operator asks to fill out, build, redo or update the cleaning schedule, the cleaning sheet or the housekeeping rota for a month, or asks who cleans on which day.
argument-hint: "[month, e.g. May 2027]"
---

# Skill: Cleaning Schedule

Generate and update the monthly cleaning schedule by pulling reservations from the PMS and applying staffing, linen, and ironing rules.

## Before you start

- **Unfilled template.** If this file still contains a value in double curly braces, stop. Tell the operator which values are missing, ask for them (the README table explains each one), fill them in, then continue. Do not guess a sheet ID, property ID or tool path.
- **Target month.** If the operator did not name a month, ask. Do not assume.
- **Staff rules.** The staff section in step 4 is an example. If it still says `<Staff A>` / `<Staff B>` and the System tab lists real people, ask the operator to confirm days, hours and priorities before you build.

## Google Sheet

**Sheet:** Cleaning Schedule
**ID:** `{{SHEET_ID_TASKS}}`
**Account:** `{{INBOX_PRIMARY}}`

### Tabs

- **Schedule** — The monthly day-by-day schedule
- **System** — Staff reference data (priority, days, responsibilities, emails)

### Schedule Columns

| Column | Content |
|--------|---------|
| A | Date |
| B | Day of week |
| C | Check-ins (guest names) |
| D | Checkouts (guest names) |
| E | Rooms (detailed: `<RoomType>` CO (Name), `<RoomType>` stay, etc.) |
| F | Staff # |
| G | Staff 1 |
| H | Staff 2 |
| I | Flag (Heavy, Very heavy, Action, No staff!) |
| J | Notes |
| K | Linen (sheet changes, mid-stay cleans, ironing tasks, stock count) |

## Process

### 0. Read Schedule Adjustments

Before building the schedule, read [`schedule-adjustments.md`](./schedule-adjustments.md) in this skill folder. It lists one-off changes for specific weeks — whole-property rentals with paid housekeeping add-ons, staff holidays, broken-equipment days, events, etc.

- Apply every entry marked `confirmed`.
- For every entry marked `pending`, use placeholder hours and put a reminder in the Notes column for the affected week, so the operator chases it.

When a week's hours differ from contracted, net out the difference over adjacent weeks in the same calendar month. If netting is impossible within the month, flag it and propose carry-over.

After applying an entry, if the week has fully passed, move the entry to the `## Archive` section of that file.

### 1. Read System Tab

```bash
{{EMAIL_CLI}} sheets spreadsheets values get \
  --params '{"spreadsheetId": "{{SHEET_ID_TASKS}}", "range": "System!A1:F20"}'
```

Get staff names, priority, contracted days, responsibilities, and email addresses. Also read the Schedule tab rows for the target month, so you know what is already published (see Guardrails).

The command shape above is an example. Use the syntax of your own `{{EMAIL_CLI}}`.

### 2. Pull Reservations from the PMS

Use `{{PMS_API_TOOL}}` with property ID `{{PMS_PROPERTY_ID}}`. The calls below show the shape of what you need; method and field names depend on the operator's wrapper, so read the tool before you call it.

```python
# Illustrative only. Adapt to the interface of {{PMS_API_TOOL}}.
pid = "{{PMS_PROPERTY_ID}}"
statuses = "confirmed,checked_in,not_confirmed"

# Use the real first and last day of the target month.
res_checkins  = api.get_reservations(pid, checkInFrom=month_start,  checkInTo=month_end,  status=statuses)
res_checkouts = api.get_reservations(pid, checkOutFrom=month_start, checkOutTo=month_end, status=statuses)
```

Deduplicate by reservation ID. These two pulls miss a stay that starts before the month and ends after it. Also pull check-ins from the previous month (or in-house guests on day 1) and keep any stay that overlaps the target month.

Then get room assignments for each reservation:

```python
detail = api.get_reservation(reservation_id, pid)
rooms = [r.get('roomName') for r in detail.get('data', {}).get('assigned', [])]
```

Exclude cancelled and no-show reservations. A reservation with no room assigned still goes on the schedule, with an **Action** flag.

**If a PMS call fails or returns an error, stop and tell the operator.** A schedule built from a partial reservation list looks complete and leaves rooms uncleaned.

### 2b. Read Notes on EVERY Reservation

Notes carry the operational details that affect cleaning: late checkouts, early arrivals, bed setup (twin vs king, extra single beds, cots), dietary needs (relevant for breakfast prep), upgrades, room blocks for extensions, allergies, etc. **Always pull notes for every reservation overlapping the month, not just whole-property rentals.**

```python
for r in reservations:
    notes = api.get_reservation_notes(reservation_id=r['reservationID'], property_id=pid)
```

What to extract from notes and add to the schedule:

- **Late checkouts / early check-ins** — affects which rooms can be cleaned when
- **Stay extensions / room blocks** — OTA end date may be wrong if the guest extended directly (date will be blocked separately in the PMS). Cross-check the room block dates against the original end date.
- **Room moves** — a guest who changes room mid-stay creates a checkout clean in the room they leave.
- **Bed setup requests** — twin beds (premium room types may split), extra singles, cots. Surface in the Notes column so staff know before changeover.
- **Dietary requests** — surface for the staff member doing breakfast.
- **Concierge plans** affecting arrival/departure timing.

Copy what the notes say. Do not infer a bed setup, a checkout time or a guest request that is not written down. If a note is ambiguous, put it in the Notes column as a question for the operator.

**If a relevant detail is missing from the notes** (e.g. the operator tells you something that is not in the PMS), propose the exact note text and ask the operator to approve it. After approval, append it with `{{PMS_NOTES_TOOL}}` so future runs see it.

### 3. Build Daily Schedule

For each day, determine:

- **Checkouts** = rooms that need full clean (strip beds, full sheet change)
- **Stayovers** = rooms with guests staying (light clean: tidy, towels, bathroom)
- **Check-ins** = rooms that must be ready by check-in time. The operator typically handles check-ins themselves — these don't create staff workload for cleaning.

A room with a checkout and a check-in on the same day is a same-day turnaround. Put it first in that day's room order, and note any late checkout or early arrival that narrows the window.

### 4. Apply Staffing Rules

> The staffing rules below are an **example** — replace with your own staff, hours, and contracted days. Keep the structure.

#### High Season (April – September)

##### Staff Schedules (example)

- **<Staff A>:** 15 hours/week, 3 days x 5 hours (08:00-13:00).
  - **Fixed days:** Monday, Tuesday, **Thursday** (default 3rd day).
  - **Flex window:** Move 3rd day to Friday or Saturday based on demand. Available alternate Saturdays. Never available Wednesday or Sunday.
  - **Priority:** Rooms/cleaning first, then ironing, then common areas.
- **<Staff B>:** 30 hours/week, 5 days x 6 hours.
  - **Fixed days:** Wednesday, Thursday, Friday, Saturday, Sunday.
  - **Priority:** Rooms first (if needed), then ironing (only if urgent), then gardening.

##### Staffing Logic

1. **Staff A is priority 1 for rooms** — handles all room cleaning when on shift.
2. **Staff B defaults to gardening.** Only pull onto rooms if:
   - Heavy day (3+ checkouts, or 4+ total rooms needing work)
   - Sole staff on duty (Wed, Sun, and sometimes Thu/Sat depending on the flex day)
3. **Overlap days:** Staff A does rooms, Staff B does gardening. Unless heavy — then both on rooms.
4. **Operator handles check-ins.** Check-ins don't count as staff workload.
5. **Never want idle staff.** Task priority order:
   - Rooms (checkouts, stayovers)
   - Ironing (if stock is getting low or ironing is due — see Linen section)
   - Gardening (Staff B) / Common areas (Staff A)

##### Flexible 3rd-Day Logic

When building the schedule, check each week for the heaviest day Staff A can work (Thu, Fri, or Sat):

- If Fri or Sat has significantly more checkouts than Thu, move the 3rd day there. Saturday is only possible on Staff A's alternate Saturdays.
- If all three are similar, keep the default (Thu).
- If Mon or Tue has zero bookings (no rooms occupied at all), consider swapping that empty day for a busier Thu/Fri/Sat instead. Flag this as a recommendation for the operator; do not apply it without their agreement, because it changes a fixed day.

##### Backup / On-Call Rules

A roster of on-call backup cleaners is helpful when only one staff member is working and the day is too heavy for one person:

- **Wednesday / Sunday:** If 4+ checkouts, call backup to help Staff B.
- **Any day with 6+ occupied rooms:** Lone staff may need backup just for breakfast help, even without many checkouts.

Write "backup needed" in the schedule and flag it. Booking the backup cleaner is the operator's job; do not contact anyone.

**Cap at 2 staff for hotel days.** Even on 5-checkout days, 2 people is enough — never schedule 3 for hotel-only changeovers. The 3-staff rule only applies to whole-property changeover days (see below).

##### Whole-Property Rental Weeks

If a whole-property rental falls in the month, hotel rooms are blocked for those dates. Cleaning then follows the **whole-property rental rules**, not the hotel staffing rules above. Skip this section if the property is never rented as a whole.

1. **Check the PMS reservation notes for the property booking** before planning. Notes are the source of truth for the cleaning schedule during the rental.
2. **If notes specify a cleaning schedule** (daily tidies, specific hours, etc.), follow that exactly. Both hours and days come from the notes.
3. **If notes are silent on cleaning**, apply the default:
   - **1× mid-week deep clean (6h)** — Staff B, on a Tue/Wed/Thu in the middle of the rental.
   - **1× gardening day (6h)** — Staff B, separate day during the rental.
   - That's the entire in-rental cleaning workload.
4. **Changeover days are very heavy and need 3 staff** — both the check-in changeover (when the rental starts) AND the check-out changeover (when it ends).
   - Default crew: Staff A + Staff B + a backup cleaner.
   - If Staff A is unavailable: Staff B + two backup cleaners.
5. **Staff B caps at 15h during a property-rental week.** Dial back from 30h to ~15h for that calendar week (Mon–Sun). Reasons: less gardening is fine because guests are using the grounds, and you want a low staff footprint to give renters privacy. Mandatory inclusions inside the 15h: changeover days (6h each) and any daily tidies committed in the booking notes. Fill the rest with light gardening or grounds work. If a property-rental week also has hotel days at the start or end, normal hotel work on those non-rental days is on top of the 15h cap.
6. **Staff A hours during a property-rental week.** Staff A normally cleans hotel rooms; during a whole-property rental there are no hotel rooms, so they would otherwise be idle. Two ways to keep contracted hours:
   - **Option A (preferred when notes are silent):** skip Staff A the rental week and add the lost hours back across the other weeks of the month. This needs the staff member's agreement, so draft an email asking for it before the schedule is published.
   - **Option B (split):** Staff A does the in-rental interior work (mid-week clean + any tidies), Staff B does gardening. Both keep close to normal weekly hours. Use this when interior hours are high enough.
   - Ask the operator which option to use. Write the choice in the Notes column.

#### Low Season (October – March)

Staff schedule is flexible — assign based on need, not contracted days.

#### Flags

- **Heavy** — 3+ checkouts or 4+ total rooms needing work
- **Very heavy** — 4+ checkouts AND check-ins on the same day
- **Action** — Something needs attention (unassigned room, ambiguous note, backup needed, etc.)
- **No staff!** — Rooms need work but nobody is scheduled

### 5. Linen & Ironing Management

#### Inventory

- **2 sets of bedding per room** × `{{NUM_ROOMS}}` rooms = total bedding. One set is on each bed, so the clean spare stock is at most `{{NUM_ROOMS}}` sets. The stock count below tracks the spare sets.
- At the start of each month, ask the operator for the current count of clean, ironed spare sets. If they do not know, assume all spare sets are clean and say that you assumed it.

#### When to Change Sheets

1. **Every checkout** — strip beds, fresh set from clean stock.
2. **Mid-stay clean for stays of 6+ nights** — change sheets around day 3-4.
3. **Stays of 12+ nights** — two mid-stay cleans, roughly every 4 days.

#### Tracking Linen Stock

Track a running stock count through the month in the Linen column:

- Each CO or mid-stay clean = -1 set from stock.
- Each ironing session = +N sets back to stock.
- **Never let stock drop below 2.** If it would, schedule ironing earlier. If no ironing slot can prevent it, flag the day as **Action** and tell the operator.

#### Ironing Schedule

Ironing is slow — estimate ~3 sets per session for Staff A on a very light day with 3-4 hours free, ~2 sets for Staff B.

**Who irons:**

- **Staff A preferred** — schedule ironing on light days (1 stayover or less, no checkouts).
- **Staff B only if urgent** — if stock will run out before Staff A's next working day.

**When to schedule ironing:**

1. After building the room schedule, calculate cumulative linen usage day by day.
2. Identify days where stock drops below 4 — schedule ironing 1-2 days before that point.
3. Prefer Monday/Tuesday for Staff A ironing (their lightest days typically).
4. If Staff A has 1 CO + stayovers, they can do a small ironing session (1-2 sets). If they have 2+ CO, no ironing that day.

### 6. Show the Plan, Then Write to Sheet

Show the operator the schedule before you write anything. Give:

- The day-by-day table (same columns as the sheet).
- Weekly hours per staff member against contracted hours.
- Every flagged day (Heavy, Very heavy, Action, No staff!) with the reason.
- The linen stock low point and the planned ironing sessions.
- Assumptions you made and open questions (pending adjustments, ambiguous notes, recommended day swaps).
- On an update of an existing month: which rows change, and which rows you leave alone.

Write only after the operator approves.

```bash
{{EMAIL_CLI}} sheets spreadsheets values update \
  --params '{"spreadsheetId": "{{SHEET_ID_TASKS}}", "range": "Schedule!B{row}:K{row}", "valueInputOption": "USER_ENTERED"}' \
  --json '{"values": [[...]]}'
```

Write the whole month in as few calls as possible, to stay inside rate limits. After the write, read the range back and confirm that the row count and dates match.

### 7. Generate Staff Emails

After the sheet is written, offer to draft emails to staff with their individual schedules. Take each address and language from the System tab; if either is missing, ask the operator.

- **Staff A:** In their preferred language. Table with Date | Day | Tasks (Rooms / Ironing / Other). Off days greyed out. Checkout days highlighted. Include ironing days and estimated sets.
- **Staff B:** In their preferred language. Table with Date | Day | Focus (ROOMS / IRONING / GARDENING) | Details. Colour-coded: blue (rooms), orange (ironing), green (gardening).

Both emails should include:

- The caveat that the schedule may change with new bookings/cancellations
- That extra days may be added if large bookings come in
- Linen/ironing responsibilities clearly marked

Use HTML so the tables render. **Create drafts only. Never send.** The operator reviews and sends each one. Do not put guest surnames, dietary details or other guest personal data in a staff email beyond what the person needs to do the room.

## Guardrails

- **PMS is read-only.** The one permitted write is appending a reservation note with `{{PMS_NOTES_TOOL}}`, and only after the operator approves the exact text. Never change dates, rooms, rates, status or guest data.
- **Show before you write.** No write to the sheet without approval of the plan (step 6).
- **Past and published dates are locked.** Do not overwrite staff assignments for past dates or for dates already sent to staff. If a new booking or cancellation changes one of those days, show the operator the difference and let them decide; staff have planned around the published version.
- **Never invent data.** No made-up reservations, staff, hours, email addresses or stock counts. Missing data is a question for the operator or an **Action** flag.
- **Drafts only.** Never send an email and never contact staff, backup cleaners or guests directly.
