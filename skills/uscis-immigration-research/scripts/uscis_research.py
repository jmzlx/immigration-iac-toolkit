#!/usr/bin/env python3
"""
USCIS Immigration Law Quick Reference Tool

This is a LOCAL REFERENCE TOOL, not a live search engine. It provides:
- Quick lookups for common INA sections, CFR regulations, and USCIS policy chapters
- Citation formatting (INA and CFR)
- Guidance on where to find authoritative sources online

For actual live research, use:
- WebSearch tool to search uscis.gov, ecfr.gov, congress.gov
- CourtListener skill for case law
- Direct URL access to egov.uscis.gov/policy-manual

Usage:
  python3 uscis_research.py --help
  python3 uscis_research.py search-statute "245(k)"
  python3 uscis_research.py search-policy "EB2-NIW"
  python3 uscis_research.py format-citation ina "203(b)(1)(A)"
  python3 uscis_research.py case-status "receipt number"

Purpose: Quick reference for Julia Salas's immigration case research
"""

import sys
import urllib.request
import urllib.parse
import json
from urllib.error import URLError
from html.parser import HTMLParser


class HTMLStripper(HTMLParser):
    """Remove HTML tags from content."""

    def __init__(self):
        super().__init__()
        self.reset()
        self.fed = []

    def handle_data(self, d):
        self.fed.append(d)

    def get_data(self):
        return ''.join(self.fed)


def strip_html_tags(html):
    """Strip HTML tags from string."""
    s = HTMLStripper()
    try:
        s.feed(html)
        return s.get_data()
    except Exception:
        return html


def fetch_url(url, timeout=10):
    """
    Fetch content from URL safely.

    Args:
        url: URL to fetch
        timeout: Request timeout in seconds

    Returns:
        Tuple of (success, content) where content is HTML string or error message
    """
    try:
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'USCIS-Immigration-Research-Tool/1.0'}
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            content = response.read().decode('utf-8', errors='replace')
            return True, content
    except URLError as e:
        return False, f"Error fetching URL: {str(e)}"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"


def format_ina_citation(section):
    """
    Format INA statute citation consistently.

    Args:
        section: Section number (e.g., "245(k)", "203(b)(1)(A)")

    Returns:
        Formatted citation string
    """
    section = section.strip().lstrip('§').strip()
    return f"INA §{section} (8 U.S.C. §{section})"


def format_cfr_citation(section):
    """
    Format CFR regulation citation consistently.

    Args:
        section: Section number (e.g., "245.1", "103.5")

    Returns:
        Formatted citation string
    """
    section = section.strip().lstrip('§').strip()
    return f"8 CFR §{section}"


def search_statute(query):
    """
    Search for INA statute information.

    Args:
        query: Search term (e.g., "245(k)", "unlawful presence")

    Returns:
        Information string with search tips
    """
    print("\n=== INA Statute Search ===")
    print(f"Searching for: {query}\n")

    # Map common queries to statute sections
    statute_map = {
        '245(k)': {
            'section': '245(k)',
            'title': 'Exception to §245(c) for Employment-Based Immigrants',
            'relevance': 'CRITICAL: Waives §245(c) bars for EB-based beneficiaries with approved petitions',
            'access': 'https://uscode.house.gov (search "8 U.S.C. 1255")'
        },
        '212(a)(9)(b)': {
            'section': '212(a)(9)(B)',
            'title': 'Inadmissibility for Unlawful Presence',
            'relevance': 'Unlawful presence bar (3/10-year bars); §245(k) may provide exception',
            'access': 'https://uscode.house.gov (search "8 U.S.C. 1182")'
        },
        '203(b)': {
            'section': '203(b)',
            'title': 'Employment-Based Preferences',
            'relevance': 'EB1-A (extraordinary ability) and EB2 (advanced degree/NIW)',
            'access': 'https://uscode.house.gov (search "8 U.S.C. 1153")'
        },
        '245(c)': {
            'section': '245(c)',
            'title': 'Grounds That Bar Adjustment of Status',
            'relevance': 'Bars adjustment unless exception applies (see §245(k) exception)',
            'access': 'https://uscode.house.gov (search "8 U.S.C. 1255")'
        },
        'unlawful presence': {
            'section': '212(a)(9)(B)',
            'title': 'Inadmissibility for Unlawful Presence',
            'relevance': '3-year bar if >180 days unlawful; 10-year bar if >1 year unlawful',
            'access': 'https://uscode.house.gov (search "8 U.S.C. 1182")'
        },
        'eb1-a': {
            'section': '203(b)(1)(A)',
            'title': 'EB1 Extraordinary Ability',
            'relevance': 'Employment-based first preference (highest priority)',
            'access': 'https://uscode.house.gov (search "8 U.S.C. 1153")'
        },
        'eb2-niw': {
            'section': '203(b)(2)',
            'title': 'EB2 National Interest Waiver',
            'relevance': 'Employment-based second preference; allows waiver of labor certification',
            'access': 'https://uscode.house.gov (search "8 U.S.C. 1153")'
        },
    }

    query_lower = query.lower().replace(' ', '').replace('-', '')

    found = False
    for key, info in statute_map.items():
        if query_lower.replace(' ', '').replace('-', '') in key or key in query_lower.replace(' ', '').replace('-', ''):
            found = True
            print(f"Section: {info['section']}")
            print(f"Title: {info['title']}")
            print(f"Relevance: {info['relevance']}")
            print(f"Access: {info['access']}")
            print()

    if not found:
        print("No direct match found in statute map.")
        print("\nTo search for statute sections:")
        print("1. Go to https://uscode.house.gov")
        print("2. Search for 'Title 8' (Immigration and Nationality Act)")
        print("3. Search for specific section (e.g., '245(k)', '212(a)(9)(B)')")
        print("\nOr use: https://congress.gov and search '8 U.S.C. [section]'")
        print("\nKey sections for Julia's case:")
        print("  - INA §245(k) — EB immigrant exception to §245(c)")
        print("  - INA §212(a)(9)(B) — Unlawful presence inadmissibility")
        print("  - INA §203(b) — Employment-based preferences")
        print("  - INA §203(b)(1)(A) — EB1-A extraordinary ability")
        print("  - INA §203(b)(2) — EB2 and NIW")


def search_uscis_policy(query):
    """
    Provide guidance for searching USCIS Policy Manual.

    Args:
        query: Search term (e.g., "EB2-NIW", "adjustment")

    Returns:
        Search guidance information
    """
    print("\n=== USCIS Policy Manual Search ===")
    print(f"Searching for: {query}\n")

    # Map common queries to policy chapters
    policy_map = {
        'eb1-a': {
            'volume': '6 (Immigrants)',
            'chapter': 'Part A, Chapter 2',
            'title': 'EB1 Extraordinary Ability',
            'url': 'https://egov.uscis.gov/policy-manual/index.html?action=article&article_id=1'
        },
        'eb2-niw': {
            'volume': '6 (Immigrants)',
            'chapter': 'Part A, Chapter 3',
            'title': 'EB2 National Interest Waiver',
            'url': 'https://egov.uscis.gov/policy-manual/index.html?action=article&article_id=1'
        },
        'adjustment': {
            'volume': '7 (Adjustment of Status)',
            'chapter': 'Part A (Basic Requirements)',
            'title': 'Adjustment of Status Eligibility',
            'url': 'https://egov.uscis.gov/policy-manual/index.html?action=article&article_id=1'
        },
        'unlawful presence': {
            'volume': '7 (Adjustment of Status)',
            'chapter': 'Part B, Chapter 4',
            'title': 'Unlawful Presence Grounds',
            'url': 'https://egov.uscis.gov/policy-manual/index.html?action=article&article_id=1'
        },
        '245(k)': {
            'volume': '7 (Adjustment of Status)',
            'chapter': 'Part C, Chapter 1',
            'title': '§245(k) Exception for EB Immigrants',
            'url': 'https://egov.uscis.gov/policy-manual/index.html?action=article&article_id=1'
        },
        'motion to reopen': {
            'volume': '12 (Motions)',
            'chapter': 'Chapter 4',
            'title': 'Motions to Reopen',
            'url': 'https://egov.uscis.gov/policy-manual/index.html?action=article&article_id=1'
        },
    }

    query_lower = query.lower().replace(' ', '').replace('-', '')

    found = False
    for key, info in policy_map.items():
        if query_lower.replace(' ', '').replace('-', '') in key or key in query_lower.replace(' ', '').replace('-', ''):
            found = True
            print(f"Volume: {info['volume']}")
            print(f"Chapter: {info['chapter']}")
            print(f"Title: {info['title']}")
            print(f"Access: https://egov.uscis.gov/policy-manual")
            print()

    if not found:
        print("No direct match found in policy map.")
        print("\nTo search USCIS Policy Manual:")
        print("1. Go to https://egov.uscis.gov/policy-manual")
        print("2. Select Volume (6 for Immigrants, 7 for Adjustment, 12 for Motions)")
        print("3. Browse chapters or use search function")
        print("\nKey volumes for Julia's case:")
        print("  - Volume 6 (Immigrants) — EB1-A and EB2-NIW policy")
        print("  - Volume 7 (Adjustment) — Adjustment eligibility and unlawful presence")
        print("  - Volume 12 (Motions) — Motion to Reopen procedure")


def search_cfr(query):
    """
    Provide guidance for searching CFR regulations.

    Args:
        query: Search term (e.g., "245.1", "adjustment")

    Returns:
        Search guidance information
    """
    print("\n=== CFR (8 CFR) Search ===")
    print(f"Searching for: {query}\n")

    cfr_map = {
        '245.1': {
            'section': '8 CFR §245.1',
            'title': 'Adjustment of Status — General Eligibility',
            'relevance': 'Eligibility for adjustment including §245(c) bars',
            'url': 'https://ecfr.gov/current/title-8/section-245.1'
        },
        '103.5': {
            'section': '8 CFR §103.5',
            'title': 'Motions to Reopen or Reconsider',
            'relevance': 'Procedure and requirements for motions; ineffective assistance standard',
            'url': 'https://ecfr.gov/current/title-8/section-103.5'
        },
        '204.5': {
            'section': '8 CFR §204.5',
            'title': 'Employment-Based Petitions',
            'relevance': 'EB1 and EB2 petition procedures, priority dates',
            'url': 'https://ecfr.gov/current/title-8/section-204.5'
        },
        '292': {
            'section': '8 CFR §292',
            'title': 'Authority of Representatives',
            'relevance': 'Attorney representation and scope of authority',
            'url': 'https://ecfr.gov/current/title-8/section-292'
        },
    }

    query_lower = query.lower().replace(' ', '').replace('-', '')

    found = False
    for key, info in cfr_map.items():
        if key in query_lower:
            found = True
            print(f"Section: {info['section']}")
            print(f"Title: {info['title']}")
            print(f"Relevance: {info['relevance']}")
            print(f"Access: {info['url']}")
            print()

    if not found:
        print("No direct match found in CFR map.")
        print("\nTo search CFR regulations:")
        print("1. Go to https://ecfr.gov/current/title-8")
        print("2. Browse parts (Part 103, 204, 245, etc.)")
        print("3. Search for specific section")
        print("\nKey sections for Julia's case:")
        print("  - 8 CFR §245.1 — Adjustment eligibility")
        print("  - 8 CFR §103.5 — Motions to reopen")
        print("  - 8 CFR §204.5 — EB petitions")
        print("  - 8 CFR §292 — Attorney authority")


def format_citation(citation_type, section):
    """
    Format legal citations consistently.

    Args:
        citation_type: 'ina' or 'cfr'
        section: Section number

    Returns:
        Formatted citation string
    """
    print("\n=== Citation Formatter ===\n")

    if citation_type.lower() == 'ina':
        formatted = format_ina_citation(section)
        print(f"INA Citation: {formatted}")
    elif citation_type.lower() == 'cfr':
        formatted = format_cfr_citation(section)
        print(f"CFR Citation: {formatted}")
    else:
        print(f"Unknown citation type: {citation_type}")
        print("Use 'ina' for INA statutes or 'cfr' for CFR regulations")
        return

    print("\nCitation Notes:")
    print("- INA sections are published in Title 8 U.S.C. (U.S. Code)")
    print("- Both formats are equivalent: INA §245(k) = 8 U.S.C. §1255(k)")
    print("- CFR sections implement INA provisions")
    print("- Always cite the specific section and subsection (e.g., §245(c)(2), not just §245)")


def search_case_status(receipt_number):
    """
    Provide guidance for checking USCIS case status.

    Args:
        receipt_number: USCIS receipt number (format: YYCxxxxxxxxx)

    Returns:
        Guidance for checking status
    """
    print("\n=== USCIS Case Status Search ===\n")

    if not receipt_number or len(receipt_number) < 10:
        print("No valid receipt number provided.")
        print("\nReceipt number format: YYCxxxxxxxxx (e.g., 22C0123456789)")
        print("  YY = Last 2 digits of year filed")
        print("  C = Center code")
        print("  x = Sequential number")
    else:
        print(f"Searching for receipt number: {receipt_number}")

    print("\nTo check case status:")
    print("1. Go to https://myuscis.uscis.dhs.gov/case-processing/case-status")
    print("2. Enter your receipt number (found on your Notice of Action, form I-797)")
    print("3. Click 'Check Status'")
    print("\nWhat the status tells you:")
    print("  - 'Application Received' — Within normal processing time")
    print("  - 'Fingerprints Received' — Processing assignment pending")
    print("  - 'Case Decision Mailed' — Decision sent; check for official letter")
    print("  - 'Approval Notice Sent' — Approved! Check for official I-797 approval notice")
    print("  - 'Denial Notice Sent' — Denied; check for official notice")
    print("  - 'Request for Additional Evidence' — RFE issued; respond within 87 days")
    print("\nFor further questions:")
    print("  - Contact USCIS customer service: 1-800-375-5283 (US) or 1-800-767-1833 (international)")
    print("  - Or visit: https://www.uscis.gov/contact-us")


def print_help():
    """Print help message."""
    print("""
USCIS Immigration Law Research Tool

Usage:
  python3 uscis_research.py <command> [options]

Commands:

  search-statute <query>
    Search for INA statute information
    Examples: "245(k)", "unlawful presence", "EB1-A", "203(b)"

  search-policy <query>
    Search for USCIS Policy Manual chapters
    Examples: "EB2-NIW", "adjustment", "unlawful presence"

  search-cfr <query>
    Search for CFR regulation information
    Examples: "245.1", "103.5", "204.5"

  format-citation <type> <section>
    Format legal citations consistently
    Examples: "format-citation ina 245(k)"
              "format-citation cfr 103.5"

  case-status [receipt-number]
    Get guidance on checking USCIS case status
    Example: "case-status 22C0123456789"

  --help, -h, help
    Show this help message

Examples:

  python3 uscis_research.py search-statute "245(k)"
  python3 uscis_research.py search-policy "EB2-NIW"
  python3 uscis_research.py format-citation ina "203(b)(1)(A)"
  python3 uscis_research.py case-status "22C0123456789"

Notes:

- This tool provides guidance for researching immigration law
- Always verify information against primary sources (statute, policy, decisions)
- For Julia's case: Focus on EB1-A/EB2-NIW, unlawful presence, and motion to reopen
- Key resources:
    * Statutes: https://uscode.house.gov (Title 8)
    * Policy: https://egov.uscis.gov/policy-manual
    * Regulations: https://ecfr.gov/current/title-8
    * Decisions: https://justice.gov/eoir (EOIR/AAO)

For detailed guidance, see SKILL.md in this skill directory.
""")


def main():
    """Main entry point."""
    if len(sys.argv) < 2 or sys.argv[1] in ['--help', '-h', 'help']:
        print_help()
        sys.exit(0)

    command = sys.argv[1].lower()

    if command == 'search-statute':
        query = ' '.join(sys.argv[2:]) if len(sys.argv) > 2 else ''
        search_statute(query)

    elif command == 'search-policy':
        query = ' '.join(sys.argv[2:]) if len(sys.argv) > 2 else ''
        search_uscis_policy(query)

    elif command == 'search-cfr':
        query = ' '.join(sys.argv[2:]) if len(sys.argv) > 2 else ''
        search_cfr(query)

    elif command == 'format-citation':
        if len(sys.argv) < 4:
            print("Error: format-citation requires citation type and section")
            print("Usage: format-citation <ina|cfr> <section>")
            print("Example: format-citation ina 245(k)")
            sys.exit(1)
        citation_type = sys.argv[2]
        section = ' '.join(sys.argv[3:])
        format_citation(citation_type, section)

    elif command == 'case-status':
        receipt_number = sys.argv[2] if len(sys.argv) > 2 else ''
        search_case_status(receipt_number)

    else:
        print(f"Unknown command: {command}")
        print("Use '--help' for usage information")
        sys.exit(1)


if __name__ == '__main__':
    main()
