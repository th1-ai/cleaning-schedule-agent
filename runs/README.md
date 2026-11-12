# runs/

The run log and the handoff files of the cleaning-schedule skill. The skill creates them; git ignores everything in this folder except this file and `.gitkeep`, because the entries name rooms, dates and reservation IDs.

## `LOG.md`

One entry per run, newest at the bottom. The skill reads the last 10 entries before it acts, so that it does not repeat a write, a draft or a "Needs you" item, and so that it can count shadow runs and daily caps.

Entry format (the values are invented):

```
## 2027-05-03 06:30 | scheduled | Level 2 (shadow 3/5)
- Checked: PMS 2027-05-03 to 2027-06-30 (41 reservations, 41 notes read); Schedule rows 59; adjustments: 1 pending
- Done: none (shadow run)
- Proposed: 2027-05-09 new checkout <RoomType> (res 12345) -> Proposed!A9:L9; 2027-05-14 note changed (res 12377, late checkout)
- Errors: none
- Needs you: 2027-05-09 has staff already and gains 1 checkout: now Heavy
```

Rules for an entry:

- `Done` lists each write with its target (sheet range or draft ID), so the next run can skip it.
- Use reservation IDs and room names. No guest names, no dietary or health details.
- A skipped run (`Level: 0` or PAUSED) and a stopped run (tool error) also get an entry, with the reason.
- The last entry is the latest run summary. Sibling agents read it there.

## `handoff/cleaning-schedule-agent.md`

Written by every scheduled run, replaced each time. It is the input for [`morning-routine-agent`](https://github.com/th1-ai/morning-routine-agent).

```
# Housekeeping handoff
Generated: 2027-05-03 06:30 | Level 2 | source: cleaning-schedule-agent

## Needs you
- 2027-05-09 has staff already and gains 1 checkout: now Heavy

## Today (2027-05-03)
Checkouts 2, stayovers 3, check-ins 1 | Staff: <Staff A> | Flag: none | Linen stock 4

## Tomorrow (2027-05-04)
Checkouts 0, stayovers 4, check-ins 2 | Staff: <Staff A> (ironing 3 sets) | Flag: none

## Next 7 days: flagged days
- 2027-05-07 Heavy (3 checkouts)
```
