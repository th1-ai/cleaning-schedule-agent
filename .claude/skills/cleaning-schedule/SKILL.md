# Skill: Cleaning Schedule

Generate and update the monthly cleaning schedule by pulling reservations from your PMS and applying staffing, linen, and ironing rules.

> **Template note:** Replace `{{PMS_*}}`, `{{SHEET_ID_TASKS}}`, `{{EMAIL_CLI}}`, `{{NUM_ROOMS}}` and the staff names/hours in this file with your own values. See the README for guidance.

## Trigger

User asks to "fill out the cleaning schedule", "do the schedule for [month]", "update the cleaning sheet", or similar.

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

Before building the schedule, read [`schedule-adjustments.md`](./schedule-adjustments.md) in this skill folder. It lists one-off changes for specific weeks — whole-property rentals with paid housekeeping add-ons, staff holidays, broken-equipment days, events, etc. Every entry marked `confirmed` must be applied to the schedule. Every entry marked `pending` must be noted in the Schedule sheet's Notes column for the affected week so the operator is reminded to chase it, and a placeholder must be used for hours until confirmed.

When a week's hours differ from contracted, net out the difference over adjacent weeks in the same calendar month. If netting is impossible within the month, flag it and propose carry-over.

After applying an entry, if the week has fully passed, move the entry to the `## Archive` section of that file.

### 1. Read System Tab

```bash
{{EMAIL_CLI}} sheets spreadsheets values get \
  --params '{"spreadsheetId": "{{SHEET_ID_TASKS}}", "range": "System!A1:F20"}'
```

Get staff names, priority, contracted days, and responsibilities.

### 2. Pull Reservations from the PMS

```python
from tools.pms_api import PMSAPI  # adapter around {{PMS_API_TOOL}}
api = PMSAPI()
pid = "{{PMS_PROPERTY_ID}}"

# Get all reservations that overlap the target month
res_checkins = api.get_reservations(pid, checkInFrom='YYYY-MM-01', checkInTo='YYYY-MM-31', status='confirmed,checked_in,not_confirmed')
res_checkouts = api.get_reservations(pid, checkOutFrom='YYYY-MM-01', checkOutTo='YYYY-MM-31', status='confirmed,checked_in,not_confirmed')
```

Deduplicate by reservation ID. Then get room assignments:

```python
detail = api.get_reservation(reservation_id, pid)
rooms = [r.get('roomName') for r in detail.get('data', {}).get('assigned', [])]
```

### 2b. Read Notes on EVERY Reservation

Notes carry the operational details that affect cleaning: late checkouts, early arrivals, bed setup (twin vs king, extra single beds, cots), dietary needs (relevant for breakfast prep), upgrades, room blocks for extensions, allergies, etc. **Always pull notes for every reservation overlapping the month, not just whole-property rentals.**

```python
for r in reservations:
    notes = api.get_reservation_notes(reservation_id=r['reservationID'], property_id=pid)
```

What to extract from notes and add to the schedule:

- **Late checkouts / early check-ins** — affects which rooms can be cleaned when
- **Stay extensions / room blocks** — OTA end date may be wrong if the guest extended directly (date will be blocked separately in the PMS). Cross-check the room block dates against the original endDate.
- **Bed setup requests** — twin beds (premium room types may split), extra singles, cots. Surface in the Notes column so staff know before changeover.
- **Dietary requests** — surface for the staff member doing breakfast.
- **Concierge plans** affecting arrival/departure timing.

**If a relevant detail is missing from the notes** (e.g. you learn something from email but it's not in the PMS), add it via `{{PMS_NOTES_TOOL}}` so future runs of the skill see it.

### 3. Build Daily Schedule

For each day, determine:

- **Checkouts** = rooms that need full clean (strip beds, full sheet change)
- **Stayovers** = rooms with guests staying (light clean: tidy, towels, bathroom)
- **Check-ins** = rooms that must be ready by ~15:00. The operator typically handles check-ins themselves — these don't create staff workload for cleaning.

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

- If Thu or Sat has significantly more checkouts than Fri, move the 3rd day there.
- If all three are similar, keep the default (Fri).
- If Mon or Tue has zero bookings (no rooms occupied at all), consider swapping that empty day for a busier Thu/Sat instead. Flag this as a recommendation for the operator.

##### Backup / On-Call Rules

A roster of on-call backup cleaners is helpful when only one staff member is working and the day is too heavy for one person:

- **Wednesday / Sunday:** If 4+ checkouts, call backup to help Staff B.
- **Any day with 6+ occupied rooms:** Lone staff may need backup just for breakfast help, even without many checkouts.

**Cap at 2 staff for hotel days.** Even on 5-checkout days, 2 people is enough — never schedule 3 for hotel-only changeovers. The 3-staff rule only applies to whole-property changeover days (see below).

##### Whole-Property Rental Weeks

If a whole-property rental falls in the month, hotel rooms are blocked for those dates. Cleaning then follows the **whole-property rental rules**, not the hotel staffing rules above.

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
   - **Option A (preferred when notes are silent):** skip Staff A the rental week and add the lost hours back across the other weeks of the month. Email the staff member asking agreement before publishing.
   - **Option B (split):** Staff A does the in-rental interior work (mid-week clean + any tidies), Staff B does gardening. Both keep close to normal weekly hours. Use this when interior hours are high enough.
   - Whichever option is chosen, write the assumption in the Notes column and confirm by email before sending the staff schedule.

#### Low Season (October – March)

Staff schedule is flexible — assign based on need, not contracted days.

#### Flags

- **Heavy** — 3+ checkouts or 4+ total rooms needing work
- **Very heavy** — 4+ checkouts AND check-ins on the same day
- **Action** — Something needs attention (unassigned room, etc.)
- **No staff!** — Rooms need work but nobody is scheduled

### 5. Linen & Ironing Management

#### Inventory

- **2 sets of bedding per room** × `{{NUM_ROOMS}}` rooms = total bedding stock.
- At the start of each month, assume all sets are clean and ironed (verify if unsure).

#### When to Change Sheets

1. **Every checkout** — strip beds, fresh set from clean stock.
2. **Mid-stay clean for stays of 6+ nights** — change sheets around day 3-4.
3. **Stays of 12+ nights** — two mid-stay cleans, roughly every 4 days.

#### Tracking Linen Stock

Track a running stock count through the month in the Linen column:

- Each CO or mid-stay clean = -1 set from stock.
- Each ironing session = +N sets back to stock.
- **Never let stock drop below 2.** If it would, schedule ironing earlier.

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

**Task priority on light days:**

- Staff A: finish rooms → ironing → common areas / other tasks
- Staff B: finish rooms (if any) → ironing (only if urgent) → gardening

### 6. Write to Sheet

```bash
{{EMAIL_CLI}} sheets spreadsheets values update \
  --params '{"spreadsheetId": "{{SHEET_ID_TASKS}}", "range": "Schedule!B{row}:K{row}", "valueInputOption": "USER_ENTERED"}' \
  --json '{"values": [[...]]}'
```

For batch updates (recommended — avoids rate limits), use a Python script that batches the writes through your Sheets client.

### 7. Generate Staff Emails

After building the schedule, offer to draft emails to staff with their individual schedules:

- **Staff A:** In their preferred language. Table with Date | Day | Tasks (Rooms / Ironing / Other). Off days greyed out. Checkout days highlighted. Include ironing days and estimated sets.
- **Staff B:** In their preferred language. Table with Date | Day | Focus (ROOMS / IRONING / GARDENING) | Details. Colour-coded: blue (rooms), orange (ironing), green (gardening).

Both emails should include:

- The caveat that the schedule may change with new bookings/cancellations
- That extra days may be added if large bookings come in
- Linen/ironing responsibilities clearly marked

**Send as HTML** for proper table formatting. Create as **drafts** for the operator to review.

## Whole-Property Changeovers

Not part of this system. Whole-property changeovers (turnover between rentals) are handled separately if your setup needs it.

## Guardrails

- Never modify PMS data — read only (the only write is appending notes via `{{PMS_NOTES_TOOL}}`).
- Always show the operator the schedule before writing to the sheet.
- Don't overwrite staff assignments for past dates or dates already sent to staff.
- Flag unassigned rooms in the PMS as "Action" items.
