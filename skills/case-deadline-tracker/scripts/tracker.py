#!/usr/bin/env python3
"""
Case Deadline Tracker for Multi-Jurisdiction Legal Proceedings
Julia Salas - Tracking 5 jurisdictions + USCIS immigration filings

This script manages deadlines.json with color-coded urgency alerts.
Missing a deadline is catastrophic. This tool prevents that.
"""

import json
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path
import argparse

# ANSI color codes for terminal output
class Colors:
    RED = '\033[91m'
    YELLOW = '\033[93m'
    GREEN = '\033[92m'
    GRAY = '\033[90m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

# Get the workspace directory (parent of scripts directory)
SCRIPT_DIR = Path(__file__).parent
WORKSPACE = SCRIPT_DIR.parent
TRACKER_FILE = WORKSPACE / 'deadlines.json'


def get_color_by_urgency(days_remaining):
    """Return color code based on days remaining."""
    if days_remaining < 0:
        return Colors.RED  # Past due
    elif days_remaining < 7:
        return Colors.RED  # Urgent
    elif days_remaining < 14:
        return Colors.YELLOW  # High priority
    else:
        return Colors.GREEN  # Safe


def get_urgency_label(days_remaining):
    """Return text label for urgency."""
    if days_remaining < 0:
        return "OVERDUE"
    elif days_remaining < 7:
        return "URGENT"
    elif days_remaining < 14:
        return "HIGH"
    else:
        return "SAFE"


def calculate_days_remaining(deadline_str):
    """Calculate days from today to deadline. Returns int (negative = overdue)."""
    try:
        deadline = datetime.strptime(deadline_str, '%Y-%m-%d').date()
        today = datetime.now().date()
        delta = (deadline - today).days
        return delta
    except (ValueError, TypeError):
        return None


def load_tracker():
    """Load deadlines.json. Create empty structure if it doesn't exist."""
    if TRACKER_FILE.exists():
        with open(TRACKER_FILE, 'r') as f:
            return json.load(f)
    else:
        return {'proceedings': []}


def save_tracker(data):
    """Save tracker data to deadlines.json."""
    with open(TRACKER_FILE, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"✓ Saved to {TRACKER_FILE}")


def initialize_default_data():
    """Initialize tracker with Julia's known proceedings. Only used if deadlines.json doesn't exist."""
    return {
        'proceedings': [
            {
                'docket_number': '2025-D143',
                'jurisdiction': 'DC',
                'attorney_name': 'Bertha Lucia Camargo',
                'proceeding_type': 'bar',
                'status': 'investigation',
                'key_dates': ['2025-08-05', '2026-01-16'],
                'next_deadline': '2026-01-30',
                'notes': 'Camargo (DC Bar #1670766) bar complaint. Answer received Jan 16, 2026. Reply due Jan 30 — OVERDUE.',
                'milestones': []
            },
            {
                'docket_number': '2025.4024',
                'jurisdiction': 'NY',
                'attorney_name': 'Malika Aggarwal',
                'proceeding_type': 'bar',
                'status': 'investigation',
                'key_dates': ['2025-08-05', '2026-02-16', '2026-03-09'],
                'next_deadline': '2026-03-23',
                'notes': 'Aggarwal (NY Bar #5892435) AGC investigation. Reply due March 23, 2026.',
                'milestones': []
            },
            {
                'docket_number': 'Filed-2025-08-05',
                'jurisdiction': 'NJ',
                'attorney_name': 'Jasmine Widmer',
                'proceeding_type': 'bar',
                'status': 'pending',
                'key_dates': ['2025-08-05'],
                'next_deadline': 'TBD',
                'notes': 'Widmer (NJ Bar #045672004) complaint. Pending investigation.',
                'milestones': []
            },
            {
                'docket_number': '2025-U1347',
                'jurisdiction': 'DC',
                'attorney_name': 'Pieter Wasung',
                'proceeding_type': 'bar',
                'status': 'closed',
                'key_dates': ['2025-08-05', '2025-11-03'],
                'next_deadline': 'N/A',
                'notes': 'Wasung (DC Bar #1722983). CLOSED Nov 3, 2025.',
                'milestones': []
            },
            {
                'docket_number': 'Filed-2025-08-05',
                'jurisdiction': 'MA',
                'attorney_name': 'Phillip Rutahweire',
                'proceeding_type': 'bar',
                'status': 'pending',
                'key_dates': ['2025-08-05'],
                'next_deadline': 'TBD',
                'notes': 'Rutahweire (MA Bar — currently SUSPENDED). Pending investigation.',
                'milestones': []
            },
            {
                'docket_number': 'USCIS-MTR',
                'jurisdiction': 'USCIS',
                'attorney_name': 'New immigration counsel (TBD)',
                'proceeding_type': 'uscis',
                'status': 'pending',
                'key_dates': ['2025-06-26'],
                'next_deadline': 'TBD',
                'notes': 'Motion to Reopen under Matter of Lozada. Pending preparation.',
                'milestones': []
            },
            {
                'docket_number': 'EB1-A-I140',
                'jurisdiction': 'USCIS',
                'attorney_name': 'Olga Ayo (independent counsel)',
                'proceeding_type': 'uscis',
                'status': 'closed',
                'key_dates': ['2024-07-29', '2024-11-15'],
                'next_deadline': 'N/A',
                'notes': 'EB1-A I-140. APPROVED Nov 15, 2024.',
                'milestones': []
            },
            {
                'docket_number': 'EB1-A-I485',
                'jurisdiction': 'USCIS',
                'attorney_name': 'Hayman Woodward (former)',
                'proceeding_type': 'uscis',
                'status': 'closed',
                'key_dates': ['2024-07-29', '2025-06-26'],
                'next_deadline': 'N/A',
                'notes': 'I-485. DENIED June 26, 2025 — §245(k) violation.',
                'milestones': []
            }
        ]
    }


def cmd_list(args):
    """List all proceedings sorted by urgency."""
    tracker = load_tracker()

    if not tracker['proceedings']:
        print("No proceedings tracked yet.")
        return

    # Calculate days remaining for each proceeding and sort
    proceedings_with_days = []
    for proc in tracker['proceedings']:
        if proc['next_deadline'] and proc['next_deadline'] != 'TBD' and proc['next_deadline'] != 'N/A':
            days = calculate_days_remaining(proc['next_deadline'])
            if days is not None:
                proceedings_with_days.append((proc, days))
        else:
            # Put TBD/N/A at the end
            proceedings_with_days.append((proc, float('inf')))

    # Sort by days remaining (urgent first)
    proceedings_with_days.sort(key=lambda x: x[1] if x[1] != float('inf') else float('inf'))

    print(f"\n{Colors.BOLD}CASE DEADLINE TRACKER - All Proceedings{Colors.END}")
    print("=" * 120)
    print(f"{'URGENCY':<10} {'DOCKET':<20} {'JURISDICTION':<12} {'TYPE':<8} {'STATUS':<15} {'DEADLINE':<12} {'DAYS':<8} {'ATTORNEY':<20}")
    print("=" * 120)

    for proc, days in proceedings_with_days:
        if days == float('inf'):
            days_str = "—"
            color = Colors.GRAY if proc['status'] == 'closed' else Colors.BLUE
            urgency = "—"
        else:
            days_str = str(days)
            color = get_color_by_urgency(days)
            urgency = get_urgency_label(days)

        deadline_str = proc['next_deadline'] if proc['next_deadline'] != 'TBD' else '—'

        print(f"{color}{urgency:<10}{Colors.END} {proc['docket_number']:<20} {proc['jurisdiction']:<12} "
              f"{proc['proceeding_type']:<8} {proc['status']:<15} {deadline_str:<12} {days_str:<8} "
              f"{proc['attorney_name']:<20}")

    print("\n" + Colors.RED + "RED (< 7 days)" + Colors.END +
          " | " + Colors.YELLOW + "YELLOW (7-14 days)" + Colors.END +
          " | " + Colors.GREEN + "GREEN (> 14 days)" + Colors.END)


def cmd_add(args):
    """Add a new proceeding."""
    tracker = load_tracker()

    new_proc = {
        'docket_number': args.docket,
        'jurisdiction': args.jurisdiction.upper(),
        'attorney_name': args.attorney or 'Unknown',
        'proceeding_type': args.type,
        'status': args.status,
        'key_dates': args.key_dates.split(',') if args.key_dates else [],
        'next_deadline': args.next_deadline or 'TBD',
        'notes': args.notes or '',
        'milestones': []
    }

    tracker['proceedings'].append(new_proc)
    save_tracker(tracker)
    print(f"✓ Added proceeding: {args.docket} ({args.jurisdiction})")


def cmd_update(args):
    """Update an existing proceeding."""
    tracker = load_tracker()

    found = False
    for proc in tracker['proceedings']:
        if proc['docket_number'] == args.docket:
            if args.status:
                proc['status'] = args.status
            if args.next_deadline:
                proc['next_deadline'] = args.next_deadline
            if args.notes:
                proc['notes'] += f" | [UPDATE {datetime.now().strftime('%Y-%m-%d')}] {args.notes}"
            found = True
            break

    if found:
        save_tracker(tracker)
        print(f"✓ Updated proceeding: {args.docket}")
    else:
        print(f"✗ Proceeding not found: {args.docket}")
        sys.exit(1)


def cmd_complete(args):
    """Mark a milestone as completed."""
    tracker = load_tracker()

    found = False
    for proc in tracker['proceedings']:
        if proc['docket_number'] == args.docket:
            milestone = {
                'completed_date': datetime.now().strftime('%Y-%m-%d'),
                'description': args.milestone
            }
            proc['milestones'].append(milestone)
            found = True
            break

    if found:
        save_tracker(tracker)
        print(f"✓ Milestone marked complete for {args.docket}: {args.milestone}")
    else:
        print(f"✗ Proceeding not found: {args.docket}")
        sys.exit(1)


def cmd_dashboard(args):
    """Generate visual dashboard and HTML report."""
    tracker = load_tracker()

    # Terminal dashboard
    print(f"\n{Colors.BOLD}{Colors.BLUE}╔═══════════════════════════════════════════════════════════════╗{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}║        LEGAL DEADLINE TRACKER - STATUS DASHBOARD               ║{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}║        Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S'):<43} ║{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}╚═══════════════════════════════════════════════════════════════╝{Colors.END}\n")

    # Summary statistics
    total = len(tracker['proceedings'])
    active = len([p for p in tracker['proceedings'] if p['status'] != 'closed'])
    closed = len([p for p in tracker['proceedings'] if p['status'] == 'closed'])

    print(f"Total Proceedings: {total} | Active: {active} | Closed: {closed}")
    print(f"Jurisdictions: DC, NY, NJ, MA, FL, USCIS\n")

    # Count urgency levels
    urgent = 0
    high = 0
    safe = 0

    for proc in tracker['proceedings']:
        if proc['next_deadline'] and proc['next_deadline'] not in ['TBD', 'N/A']:
            days = calculate_days_remaining(proc['next_deadline'])
            if days is not None:
                if days < 7:
                    urgent += 1
                elif days < 14:
                    high += 1
                else:
                    safe += 1

    print(f"{Colors.RED}🚨 URGENT (< 7 days): {urgent}{Colors.END} | "
          f"{Colors.YELLOW}⚠️  HIGH PRIORITY (7-14 days): {high}{Colors.END} | "
          f"{Colors.GREEN}✓ SAFE (> 14 days): {safe}{Colors.END}\n")

    # Grouped by jurisdiction
    jurisdictions = {}
    for proc in tracker['proceedings']:
        juris = proc['jurisdiction']
        if juris not in jurisdictions:
            jurisdictions[juris] = []
        jurisdictions[juris].append(proc)

    for juris in sorted(jurisdictions.keys()):
        procs = jurisdictions[juris]
        print(f"{Colors.BOLD}{juris}{Colors.END}:")
        for proc in procs:
            if proc['next_deadline'] and proc['next_deadline'] not in ['TBD', 'N/A']:
                days = calculate_days_remaining(proc['next_deadline'])
                if days is not None:
                    color = get_color_by_urgency(days)
                    print(f"  {color}→{Colors.END} {proc['docket_number']:<18} | {proc['status']:<12} | {proc['next_deadline']} ({days} days)")
            else:
                print(f"  → {proc['docket_number']:<18} | {proc['status']:<12} | TBD")
        print()

    # Generate HTML dashboard
    html_content = generate_html_dashboard(tracker)
    html_file = WORKSPACE / 'deadlines-dashboard.html'
    with open(html_file, 'w') as f:
        f.write(html_content)
    print(f"✓ HTML dashboard saved: {html_file}")


def generate_html_dashboard(tracker):
    """Generate HTML dashboard file."""
    html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Legal Deadline Tracker</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
               background: #f5f5f5; padding: 20px; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
        h1 { color: #1a1a1a; margin-bottom: 10px; }
        .timestamp { color: #666; font-size: 14px; margin-bottom: 20px; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 30px; }
        .stat-card { padding: 15px; border-radius: 6px; text-align: center; }
        .stat-card h3 { font-size: 28px; margin: 10px 0 5px; }
        .stat-card p { color: #666; font-size: 12px; }
        .urgent { background: #ffe5e5; border-left: 4px solid #d32f2f; }
        .high { background: #fff3e0; border-left: 4px solid #f57c00; }
        .safe { background: #e8f5e9; border-left: 4px solid #388e3c; }
        table { width: 100%; border-collapse: collapse; margin-bottom: 30px; }
        th { background: #f0f0f0; padding: 12px; text-align: left; font-weight: 600; border-bottom: 2px solid #ddd; }
        td { padding: 12px; border-bottom: 1px solid #eee; }
        tr:hover { background: #fafafa; }
        .red { color: #d32f2f; font-weight: 600; }
        .yellow { color: #f57c00; font-weight: 600; }
        .green { color: #388e3c; font-weight: 600; }
        .gray { color: #999; }
        .jurisdiction-header { background: #e3f2fd; font-weight: 600; padding: 12px; margin-top: 20px; }
        .closed { opacity: 0.6; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Legal Deadline Tracker Dashboard</h1>
        <div class="timestamp">Generated: """ + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + """</div>

        <div class="stats">
"""

    # Add statistics
    total = len(tracker['proceedings'])
    active = len([p for p in tracker['proceedings'] if p['status'] != 'closed'])
    closed = len([p for p in tracker['proceedings'] if p['status'] == 'closed'])

    urgent = 0
    high = 0
    safe = 0

    for proc in tracker['proceedings']:
        if proc['next_deadline'] and proc['next_deadline'] not in ['TBD', 'N/A']:
            days = calculate_days_remaining(proc['next_deadline'])
            if days is not None:
                if days < 7:
                    urgent += 1
                elif days < 14:
                    high += 1
                else:
                    safe += 1

    html += f"""            <div class="stat-card urgent">
                <p>URGENT</p>
                <h3>{urgent}</h3>
                <p>&lt; 7 days</p>
            </div>
            <div class="stat-card high">
                <p>HIGH PRIORITY</p>
                <h3>{high}</h3>
                <p>7-14 days</p>
            </div>
            <div class="stat-card safe">
                <p>SAFE</p>
                <h3>{safe}</h3>
                <p>&gt; 14 days</p>
            </div>
        </div>

        <h2>All Proceedings</h2>
        <table>
            <thead>
                <tr>
                    <th>Docket</th>
                    <th>Jurisdiction</th>
                    <th>Type</th>
                    <th>Status</th>
                    <th>Next Deadline</th>
                    <th>Days Remaining</th>
                    <th>Attorney</th>
                </tr>
            </thead>
            <tbody>
"""

    # Sort proceedings by urgency
    proceedings_with_days = []
    for proc in tracker['proceedings']:
        if proc['next_deadline'] and proc['next_deadline'] not in ['TBD', 'N/A']:
            days = calculate_days_remaining(proc['next_deadline'])
            if days is not None:
                proceedings_with_days.append((proc, days))
        else:
            proceedings_with_days.append((proc, float('inf')))

    proceedings_with_days.sort(key=lambda x: x[1] if x[1] != float('inf') else float('inf'))

    for proc, days in proceedings_with_days:
        closed_class = 'closed' if proc['status'] == 'closed' else ''

        if days == float('inf'):
            days_html = '<span class="gray">—</span>'
            urgency_class = 'gray'
        else:
            if days < 7:
                urgency_class = 'red'
                days_html = f'<span class="red">{days}</span>'
            elif days < 14:
                urgency_class = 'yellow'
                days_html = f'<span class="yellow">{days}</span>'
            else:
                urgency_class = 'green'
                days_html = f'<span class="green">{days}</span>'

        deadline_str = proc['next_deadline'] if proc['next_deadline'] != 'TBD' else '—'

        html += f"""                <tr class="{closed_class}">
                    <td>{proc['docket_number']}</td>
                    <td>{proc['jurisdiction']}</td>
                    <td>{proc['proceeding_type']}</td>
                    <td>{proc['status']}</td>
                    <td>{deadline_str}</td>
                    <td>{days_html}</td>
                    <td>{proc['attorney_name']}</td>
                </tr>
"""

    html += """            </tbody>
        </table>
    </div>
</body>
</html>
"""

    return html


def cmd_report(args):
    """Generate printable status report."""
    tracker = load_tracker()

    report = []
    report.append("=" * 80)
    report.append("LEGAL CASE DEADLINE TRACKER - STATUS REPORT")
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("=" * 80)
    report.append("")

    # Summary
    report.append("SUMMARY")
    report.append("-" * 80)
    total = len(tracker['proceedings'])
    active = len([p for p in tracker['proceedings'] if p['status'] != 'closed'])
    closed = len([p for p in tracker['proceedings'] if p['status'] == 'closed'])
    report.append(f"Total Proceedings: {total}")
    report.append(f"Active Cases: {active}")
    report.append(f"Closed Cases: {closed}")
    report.append("")

    # Proceedings by jurisdiction
    jurisdictions = {}
    for proc in tracker['proceedings']:
        juris = proc['jurisdiction']
        if juris not in jurisdictions:
            jurisdictions[juris] = []
        jurisdictions[juris].append(proc)

    for juris in sorted(jurisdictions.keys()):
        report.append("")
        report.append(f"{juris} JURISDICTION")
        report.append("-" * 80)

        for proc in jurisdictions[juris]:
            report.append(f"Docket: {proc['docket_number']}")
            report.append(f"Type: {proc['proceeding_type']}")
            report.append(f"Status: {proc['status']}")
            report.append(f"Attorney: {proc['attorney_name']}")

            if proc['next_deadline'] and proc['next_deadline'] not in ['TBD', 'N/A']:
                days = calculate_days_remaining(proc['next_deadline'])
                if days is not None:
                    report.append(f"Next Deadline: {proc['next_deadline']} ({days} days remaining)")
            else:
                report.append(f"Next Deadline: {proc['next_deadline']}")

            if proc['notes']:
                report.append(f"Notes: {proc['notes']}")

            if proc['milestones']:
                report.append("Milestones:")
                for milestone in proc['milestones']:
                    report.append(f"  - {milestone['completed_date']}: {milestone['description']}")

            report.append("")

    report_text = "\n".join(report)
    print(report_text)

    # Save to file
    report_file = WORKSPACE / f"status-report-{datetime.now().strftime('%Y%m%d')}.txt"
    with open(report_file, 'w') as f:
        f.write(report_text)
    print(f"\n✓ Report saved: {report_file}")


def cmd_check(args):
    """Validate all dates and flag issues."""
    tracker = load_tracker()

    print(f"\n{Colors.BOLD}VALIDATION REPORT{Colors.END}")
    print("=" * 80)

    issues_found = 0

    for proc in tracker['proceedings']:
        proc_issues = []

        # Check for missing critical fields
        if not proc.get('docket_number'):
            proc_issues.append("Missing docket number")
        if not proc.get('jurisdiction'):
            proc_issues.append("Missing jurisdiction")
        if proc.get('status') not in ['active', 'pending', 'closed', 'investigation', 'appeal', 'response-filed']:
            proc_issues.append(f"Unclear status: {proc.get('status')}")

        # Check for past-due deadlines
        if proc['next_deadline'] and proc['next_deadline'] not in ['TBD', 'N/A']:
            days = calculate_days_remaining(proc['next_deadline'])
            if days is not None and days < 0:
                proc_issues.append(f"PAST DUE by {abs(days)} days!")
                issues_found += 1

        if proc_issues:
            print(f"\n{proc['docket_number']} ({proc['jurisdiction']}):")
            for issue in proc_issues:
                print(f"  ⚠️  {issue}")

    if issues_found == 0:
        print(f"{Colors.GREEN}✓ No critical issues found.{Colors.END}")
    else:
        print(f"\n{Colors.RED}⚠️  {issues_found} critical issue(s) found. Review immediately.{Colors.END}")


def cmd_init(args):
    """Initialize tracker with default data."""
    if TRACKER_FILE.exists():
        print(f"✓ Tracker already exists at {TRACKER_FILE}")
        return

    default_data = initialize_default_data()
    save_tracker(default_data)
    print(f"✓ Initialized tracker with {len(default_data['proceedings'])} proceedings")
    cmd_list(None)


def main():
    parser = argparse.ArgumentParser(
        description='Case Deadline Tracker for Multi-Jurisdiction Legal Proceedings',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tracker.py init                          # Initialize with default proceedings
  python tracker.py list                          # Show all deadlines by urgency
  python tracker.py add --docket 2025-D999 --jurisdiction DC --type bar --status investigation --next-deadline 2026-04-15
  python tracker.py update --docket 2025-D999 --status filed
  python tracker.py complete --docket 2025-D999 --milestone "Response filed"
  python tracker.py dashboard                    # Generate HTML dashboard
  python tracker.py report                       # Generate printable report
  python tracker.py check                        # Validate all dates
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # init
    subparsers.add_parser('init', help='Initialize tracker with default data')

    # list
    subparsers.add_parser('list', help='List all proceedings sorted by urgency')

    # add
    add_parser = subparsers.add_parser('add', help='Add a new proceeding')
    add_parser.add_argument('--docket', required=True, help='Docket number')
    add_parser.add_argument('--jurisdiction', required=True, help='Jurisdiction (DC, NY, NJ, MA, FL, USCIS)')
    add_parser.add_argument('--attorney', help='Attorney name')
    add_parser.add_argument('--type', required=True, choices=['bar', 'court', 'uscis'], help='Proceeding type')
    add_parser.add_argument('--status', required=True, help='Status')
    add_parser.add_argument('--key-dates', help='Comma-separated key dates')
    add_parser.add_argument('--next-deadline', help='Next deadline (YYYY-MM-DD)')
    add_parser.add_argument('--notes', help='Notes')

    # update
    update_parser = subparsers.add_parser('update', help='Update an existing proceeding')
    update_parser.add_argument('--docket', required=True, help='Docket number')
    update_parser.add_argument('--status', help='New status')
    update_parser.add_argument('--next-deadline', help='New deadline (YYYY-MM-DD)')
    update_parser.add_argument('--notes', help='Update notes')

    # complete
    complete_parser = subparsers.add_parser('complete', help='Mark a milestone as completed')
    complete_parser.add_argument('--docket', required=True, help='Docket number')
    complete_parser.add_argument('--milestone', required=True, help='Milestone description')

    # dashboard
    subparsers.add_parser('dashboard', help='Generate visual status dashboard')

    # report
    subparsers.add_parser('report', help='Generate printable status report')

    # check
    subparsers.add_parser('check', help='Validate all dates and flag issues')

    args = parser.parse_args()

    # Initialize tracker if it doesn't exist
    if not TRACKER_FILE.exists() and args.command != 'init':
        print("Initializing tracker...")
        cmd_init(None)

    # Execute command
    if args.command == 'init':
        cmd_init(args)
    elif args.command == 'list':
        cmd_list(args)
    elif args.command == 'add':
        cmd_add(args)
    elif args.command == 'update':
        cmd_update(args)
    elif args.command == 'complete':
        cmd_complete(args)
    elif args.command == 'dashboard':
        cmd_dashboard(args)
    elif args.command == 'report':
        cmd_report(args)
    elif args.command == 'check':
        cmd_check(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
