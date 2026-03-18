---
name: case-deadline-tracker
description: >
  Tracks legal deadlines across multiple jurisdictions (DC, NY, NJ, MA, FL, USCIS)
  with color-coded urgency alerts, HTML dashboards, and printable status reports.
  Pre-populated with active bar complaint proceedings and immigration filings.
  Triggers on "what's due", "upcoming deadlines", "what's next", "status of my cases",
  "when do I need to file", "show me the calendar", "am I missing anything", "what's
  overdue", "dashboard", "proceeding tracker", "docket status", or "deadline check".
---

# Case Deadline Tracker

You're juggling proceedings across 5 jurisdictions plus federal immigration filings. Missing even one deadline is catastrophic—it can result in default judgments, case dismissal, or visa denials. This skill ensures nothing falls through the cracks.

## What This Does

This tracker maintains a real-time view of all your legal proceedings:
- **All deadlines at a glance**: Sorted by urgency, with days remaining
- **Multi-jurisdiction support**: DC, NY, NJ, MA, FL court systems + USCIS
- **Proceeding types**: Bar complaints, court cases, immigration filings
- **Automatic urgency flagging**: Red (< 7 days), Yellow (< 14 days), Green (safe)
- **Status dashboard**: HTML report + terminal output
- **Audit trail**: Notes and milestone tracking for every filing

Why this matters: Courts don't care about excuses. One calendar miss = default judgment. One missed deadline = dismissed with prejudice. One overlooked filing = visa denial. This tool prevents that.

## Available Commands

Run `python scripts/tracker.py [command] [options]`

### `list` - View all deadlines (sorted by urgency)
```
python scripts/tracker.py list
```
Shows all active proceedings sorted by days remaining. Red flags anything urgent.

### `add` - Add a new proceeding
```
python scripts/tracker.py add --docket "DOCKET_NUMBER" --jurisdiction "STATE" \
  --attorney "NAME" --type "bar|court|uscis" --status "investigation|pending|closed" \
  --key-dates "date1,date2" --next-deadline "YYYY-MM-DD" --notes "details"
```

Example:
```
python scripts/tracker.py add --docket "2025-D999" --jurisdiction "DC" \
  --attorney "Jane Doe" --type "bar" --status "investigation" \
  --next-deadline "2026-04-15" --notes "Motion to extend deadline filed"
```

### `update` - Update an existing proceeding
```
python scripts/tracker.py update --docket "DOCKET_NUMBER" --status "active|closed" \
  --next-deadline "YYYY-MM-DD" --notes "update message"
```

### `complete` - Mark a milestone as completed
```
python scripts/tracker.py complete --docket "DOCKET_NUMBER" --milestone "description"
```

### `dashboard` - Generate visual status report
```
python scripts/tracker.py dashboard
```
Produces both HTML file (deadlines-dashboard.html) and terminal output with color coding.

### `report` - Generate printable status document
```
python scripts/tracker.py report
```
Creates a formatted text report suitable for your attorney or personal records.

### `check` - Validate all dates and flag issues
```
python scripts/tracker.py check
```
Scans for past-due deadlines, missing information, or formatting errors.

## Your Current Proceedings

The tracker comes pre-populated with your 8 active/recent proceedings:

1. **Camargo (DC)** - Docket 2025-D143 | Bar complaint investigation
2. **Aggarwal (NY)** - Docket 2025.4024 | AGC investigation (response due soon)
3. **Widmer (NJ)** - Filed Aug 2025 | Bar complaint pending
4. **Wasung (DC)** - Docket 2025-U1347 | CLOSED (Nov 2025)
5. **Rutahweire (MA)** - Filed Aug 2025 | Bar complaint pending
6. **USCIS Motion to Reopen** - Immigration case | Pending preparation
7. **EB1-A I-140** - Immigration | Approved Nov 2024
8. **I-485 (EB1-A)** - Immigration | Denied June 2025

## Urgency Colors

- **RED** (< 7 days): Immediate action required. Contact your attorney NOW.
- **YELLOW** (7-14 days): High priority. Prepare filings this week.
- **GREEN** (> 14 days): Safe. Schedule work on this.
- **GRAY**: Closed proceedings. Archived for reference.

## How to Use This with Your Workflow

1. **Daily**: Run `python scripts/tracker.py list` first thing. Address RED items immediately.
2. **Weekly**: Run `python scripts/tracker.py dashboard` to see the full picture.
3. **After filing**: Run `python scripts/tracker.py update --docket [X] --status "filed"` to mark progress.
4. **Before attorney calls**: Run `python scripts/tracker.py report` to have current status ready.
5. **Monthly**: Run `python scripts/tracker.py check` to validate all dates are correct.

## The Data: deadlines.json

All proceedings are stored in `deadlines.json`. This is the authoritative source. Keep it backed up.

Structure per proceeding:
- `docket_number`: Court/USCIS identifier
- `jurisdiction`: DC, NY, NJ, MA, FL, or USCIS
- `attorney_name`: Primary counsel
- `proceeding_type`: "bar" | "court" | "uscis"
- `status`: "investigation" | "active" | "pending" | "closed" | "appeal"
- `key_dates`: List of important dates (filed, served, etc.)
- `next_deadline`: Most urgent upcoming deadline
- `days_remaining`: Auto-calculated from today
- `notes`: Tracking notes, filing instructions, status updates
- `milestones`: Completed actions with timestamps

## Integration with Scheduled Tasks

To get automatic daily deadline reminders, integrate with your scheduler:
- Set up a daily 7am task that runs `python scripts/tracker.py list`
- Get RED-flagged items delivered to your inbox
- Never be caught off guard

## Critical Reminders

⚠️ **Accuracy matters**: One wrong date = missed deadline. Verify all dates against official court documents.

⚠️ **Update immediately**: The moment you file something or get a ruling, update the tracker.

⚠️ **Contact your attorney**: This tool tracks dates, but your attorney makes filing decisions. Use this to stay informed and prepared.

⚠️ **Keep backups**: Export deadlines.json weekly to a backup location.

## Example Workflow

```bash
# Morning routine
python scripts/tracker.py list

# Your attorney calls with update
python scripts/tracker.py update --docket "2025.4024" --status "response-filed" \
  --notes "Response to AGC filed with extension through April 15"

# Weekly review
python scripts/tracker.py dashboard

# Before attorney meeting
python scripts/tracker.py report > status-for-attorney.txt
```

---

**Remember**: Missing a deadline in any of these jurisdictions costs you. This tool prevents that. Use it religiously.
