#!/usr/bin/env python3
"""
Case Analyzer — works with bootstrap-generated knowledge graph.

Reads the dynamically-generated JSON files from bootstrap.py and runs diagnostic
checks. Adapts to whatever structure bootstrap produces.

Usage:
    python scripts/case_analyzer.py [command]

Commands:
    gap-analysis      Claims lacking evidence, unknowns categorized by resolution path
    coherence-check   Cross-proceeding consistency and fact verification
    strength-report   Claim viability assessment with confidence levels
    timeline-verify   Chronological consistency of extracted events
    exhibit-coverage  Document utilization patterns across claims
    unknowns          Categorized list of what we don't know and how to find it
"""

import json
import sys
from pathlib import Path
from collections import defaultdict


def load_data():
    """Load the three JSON files, adapting to bootstrap format."""
    base_dir = Path(__file__).parent.parent

    facts_path = base_dir / 'case-facts.json'
    claims_path = base_dir / 'claims-matrix.json'
    links_path = base_dir / 'evidence-links.json'

    facts = {}
    claims_data = []
    links_data = []

    if facts_path.exists():
        with open(facts_path) as f:
            raw = json.load(f)
            facts = raw  # Keep full structure including unknowns, parties, proceedings

    if claims_path.exists():
        with open(claims_path) as f:
            raw = json.load(f)
            claims_data = raw.get('claims', [])

    if links_path.exists():
        with open(links_path) as f:
            raw = json.load(f)
            links_data = raw.get('links', [])

    return facts, claims_data, links_data


def gap_analysis(facts, claims_data, links_data):
    """Identify missing evidence and categorize unknowns."""
    print("\n" + "=" * 80)
    print("GAP ANALYSIS: Missing Evidence and Categorized Unknowns")
    print("=" * 80)

    events = facts.get('events', [])
    unknowns = facts.get('unknowns', [])
    proceedings = facts.get('proceedings', [])

    # Claims with weak or unknown evidence
    print(f"\n--- Claims Needing Attention ({len(claims_data)} total claims) ---\n")

    needs_deep_read = 0
    has_gaps = 0
    for claim in claims_data:
        evidence = claim.get('evidence', {})
        gaps = claim.get('gaps', [])
        claim_issues = []

        for prong in ['deficiency', 'causation', 'prejudice']:
            prong_data = evidence.get(prong, {})
            strength = prong_data.get('strength', 'unknown')
            reasoning = prong_data.get('reasoning', '')
            if strength == 'unknown' or 'needs_deep_read' in reasoning:
                claim_issues.append(f"  {prong}: needs deep-read analysis")
                needs_deep_read += 1
            elif strength in ('weak', 'gap'):
                claim_issues.append(f"  {prong}: {strength}")
                has_gaps += 1

        if gaps:
            for gap in gaps:
                claim_issues.append(f"  GAP: {gap.get('what', gap) if isinstance(gap, dict) else gap}")

        if claim_issues:
            print(f"  [{claim.get('id', '?')}] {claim.get('description', '?')[:60]}")
            for issue in claim_issues[:3]:  # Limit output per claim
                print(f"    {issue}")
            print()

    print(f"Summary: {needs_deep_read} prongs need deep-read, {has_gaps} have identified gaps")

    # Evidence links needing deep read
    deep_read_links = [l for l in links_data if l.get('needs_deep_read', False)]
    print(f"\n--- Evidence Links Needing Deep Read: {len(deep_read_links)} of {len(links_data)} ---\n")
    high_confidence = [l for l in links_data if l.get('confidence') == 'high']
    medium = [l for l in links_data if l.get('confidence') == 'medium']
    low = [l for l in links_data if l.get('confidence') == 'low']
    print(f"  High confidence: {len(high_confidence)}")
    print(f"  Medium confidence: {len(medium)}")
    print(f"  Low confidence: {len(low)}")

    # Unknowns from case-facts
    if unknowns:
        print(f"\n--- Unknowns from Document Analysis ({len(unknowns)}) ---\n")
        by_category = defaultdict(list)
        for u in unknowns:
            cat = u.get('category', 'uncategorized')
            by_category[cat].append(u)

        for cat in ['findable_in_documents', 'discoverable_via_research',
                     'needs_external_input', 'missing_and_critical', 'uncategorized']:
            items = by_category.get(cat, [])
            if items:
                print(f"  [{cat}] ({len(items)} items)")
                for item in items[:5]:
                    q = item.get('question', str(item))
                    action = item.get('suggested_action', '')
                    print(f"    • {q}")
                    if action:
                        print(f"      → {action}")
                print()

    # Proceedings without claims
    proceeding_ids = set()
    for claim in claims_data:
        for p in claim.get('proceedings', []):
            proceeding_ids.add(p)

    print(f"\n--- Proceedings Coverage ---")
    print(f"  {len(proceedings)} proceedings identified in documents")
    print(f"  {len(proceeding_ids)} proceedings have claims mapped to them")


def coherence_check(facts, claims_data, links_data):
    """Check cross-proceeding consistency."""
    print("\n" + "=" * 80)
    print("COHERENCE CHECK: Cross-Proceeding Consistency")
    print("=" * 80)

    events = facts.get('events', [])
    parties = facts.get('parties', {})
    proceedings = facts.get('proceedings', [])

    # Attorney accountability
    print("\n--- Attorney Coverage ---\n")
    attorney_claims = defaultdict(set)
    for claim in claims_data:
        for attorney in claim.get('attorneys', []):
            attorney_claims[attorney].add(claim.get('id', '?'))

    for attorney in sorted(attorney_claims.keys()):
        claims = attorney_claims[attorney]
        print(f"  {attorney}: {len(claims)} claims")
        for c in sorted(claims)[:5]:
            print(f"    • {c}")
        if len(claims) > 5:
            print(f"    ... and {len(claims) - 5} more")

    # Check key events exist
    print("\n--- Key Event Verification ---\n")
    event_descriptions = ' '.join(e.get('description', '') for e in events).lower()

    checks = [
        ('I-94 or visa expiration', ['i-94', 'visa expir', 'expired']),
        ('I-485 filing', ['i-485', '485']),
        ('I-140 filing or denial', ['i-140', '140']),
        ('Bar complaint filing', ['bar complaint', 'complaint filed', 'grievance']),
        ('Attorney communication failure', ['failed to', 'never', 'did not advise']),
        ('USCIS denial', ['denied', 'denial']),
    ]

    for check_name, keywords in checks:
        found = any(kw in event_descriptions for kw in keywords)
        marker = "✓" if found else "✗"
        print(f"  {marker} {check_name}")

    # Cross-check: Do all claims reference valid proceedings?
    print("\n--- Proceeding Validation ---\n")
    known_proceedings = {p.get('docket', p.get('id', '?')) for p in proceedings}
    claim_proceedings = set()
    for claim in claims_data:
        for p in claim.get('proceedings', []):
            claim_proceedings.add(p)

    orphaned = claim_proceedings - known_proceedings if known_proceedings else set()
    if orphaned:
        print(f"  ⚠ {len(orphaned)} claim proceedings not in known proceedings list:")
        for p in sorted(orphaned)[:10]:
            print(f"    • {p}")
    else:
        print("  ✓ All claim proceedings are tracked")


def strength_report(facts, claims_data, links_data):
    """Claim viability assessment."""
    print("\n" + "=" * 80)
    print("STRENGTH REPORT: Claim Viability")
    print("=" * 80)

    # Build link counts per claim
    link_counts = defaultdict(lambda: defaultdict(int))
    for link in links_data:
        claim = link.get('claim', '')
        confidence = link.get('confidence', 'unknown')
        link_counts[claim][confidence] += 1

    print(f"\n{'Claim ID':<40} {'High':<6} {'Med':<6} {'Low':<6} {'Proceedings':<30}")
    print("-" * 90)

    for claim in claims_data[:30]:  # Limit display
        cid = claim.get('id', '?')
        procs = ', '.join(claim.get('proceedings', [])[:3])
        counts = link_counts.get(cid, {})
        high = counts.get('high', 0)
        med = counts.get('medium', 0)
        low = counts.get('low', 0)
        print(f"{cid[:39]:<40} {high:<6} {med:<6} {low:<6} {procs:<30}")

    if len(claims_data) > 30:
        print(f"\n... and {len(claims_data) - 30} more claims")

    print(f"\nTotal claims: {len(claims_data)}")
    print(f"Total evidence links: {len(links_data)}")


def timeline_verify(facts, claims_data, links_data):
    """Check chronological consistency."""
    print("\n" + "=" * 80)
    print("TIMELINE VERIFICATION: Chronological Consistency")
    print("=" * 80)

    events = facts.get('events', [])
    print(f"\nTotal events: {len(events)}\n")

    if not events:
        print("No events found. Run bootstrap.py first.")
        return

    # Check chronological order
    dates = [e.get('date', '') for e in events]
    if dates == sorted(dates):
        print("✓ Timeline is in chronological order.\n")
    else:
        print("✗ Timeline has ordering issues.\n")

    # Show events grouped by significance
    critical = [e for e in events if e.get('significance') == 'critical']
    important = [e for e in events if e.get('significance') == 'important']

    if critical:
        print(f"Critical Events ({len(critical)}):\n")
        for e in critical[:20]:
            conf = e.get('confidence', '?')
            print(f"  [{conf}] {e['date']}: {e.get('description', '?')[:70]}")

    if important:
        print(f"\nImportant Events ({len(important)}):\n")
        for e in important[:20]:
            conf = e.get('confidence', '?')
            print(f"  [{conf}] {e['date']}: {e.get('description', '?')[:70]}")

    # Show confidence distribution
    print("\nConfidence Distribution:")
    conf_counts = defaultdict(int)
    for e in events:
        conf_counts[e.get('confidence', 'unknown')] += 1
    for conf in ['high', 'medium', 'low', 'unknown']:
        if conf_counts[conf]:
            print(f"  {conf}: {conf_counts[conf]}")


def exhibit_coverage(facts, claims_data, links_data):
    """Document utilization patterns."""
    print("\n" + "=" * 80)
    print("EXHIBIT COVERAGE: Document Utilization")
    print("=" * 80)

    # Count how many claims each document supports
    doc_claims = defaultdict(set)
    doc_prongs = defaultdict(set)
    for link in links_data:
        doc = link.get('document', '')
        claim = link.get('claim', '')
        prong = link.get('prong', '')
        doc_claims[doc].add(claim)
        doc_prongs[doc].add(prong)

    print(f"\nTotal documents linked: {len(doc_claims)}")
    print(f"Total evidence links: {len(links_data)}")

    # Most connected documents
    sorted_docs = sorted(doc_claims.items(), key=lambda x: len(x[1]), reverse=True)

    print(f"\nMost Connected Documents (support multiple claims):\n")
    for doc, claims in sorted_docs[:15]:
        prongs = doc_prongs[doc]
        doc_short = doc.split('/')[-1][:50] if '/' in doc else doc[:50]
        print(f"  {len(claims)} claims, {len(prongs)} prongs: {doc_short}")

    # Documents supporting all 3 prongs
    all_prong_docs = [doc for doc, prongs in doc_prongs.items()
                      if {'deficiency', 'causation', 'prejudice'}.issubset(prongs)]
    if all_prong_docs:
        print(f"\nDocuments supporting ALL 3 Lozada prongs ({len(all_prong_docs)}):\n")
        for doc in all_prong_docs[:10]:
            doc_short = doc.split('/')[-1][:60] if '/' in doc else doc[:60]
            print(f"  • {doc_short}")

    # Orphaned documents (in workspace but not linked)
    events = facts.get('events', [])
    docs_in_timeline = set()
    for e in events:
        for d in e.get('source_documents', []):
            docs_in_timeline.add(d)

    linked_docs = set(doc_claims.keys())
    timeline_only = docs_in_timeline - linked_docs
    if timeline_only:
        print(f"\nDocuments in timeline but not linked to claims ({len(timeline_only)}):")
        for doc in sorted(timeline_only)[:10]:
            doc_short = doc.split('/')[-1][:60] if '/' in doc else doc[:60]
            print(f"  • {doc_short}")


def unknowns_report(facts, claims_data, links_data):
    """Detailed categorized report of what we don't know."""
    print("\n" + "=" * 80)
    print("UNKNOWNS REPORT: What We Don't Know & How to Find It")
    print("=" * 80)

    unknowns = facts.get('unknowns', [])

    if not unknowns:
        print("\nNo unknowns recorded. Run bootstrap.py to identify gaps.")
        return

    categories = {
        'findable_in_documents': {
            'label': 'FINDABLE IN EXISTING DOCUMENTS',
            'action': 'Deep-read the relevant document more carefully',
            'icon': '📄'
        },
        'discoverable_via_research': {
            'label': 'DISCOVERABLE VIA RESEARCH',
            'action': 'Use courtlistener or uscis-immigration-research skills',
            'icon': '🔍'
        },
        'needs_external_input': {
            'label': 'NEEDS CLIENT/ATTORNEY INPUT',
            'action': 'Ask Julia or her current attorney',
            'icon': '👤'
        },
        'missing_and_critical': {
            'label': 'MISSING & CRITICAL',
            'action': 'Request via FOIA, former counsel, or other channels',
            'icon': '🚨'
        }
    }

    by_category = defaultdict(list)
    for u in unknowns:
        cat = u.get('category', 'uncategorized')
        by_category[cat].append(u)

    for cat_key, cat_info in categories.items():
        items = by_category.get(cat_key, [])
        if items:
            print(f"\n{cat_info['icon']} {cat_info['label']} ({len(items)} items)")
            print(f"   Default action: {cat_info['action']}")
            print()
            for item in items:
                q = item.get('question', str(item))
                why = item.get('why_it_matters', '')
                action = item.get('suggested_action', '')
                print(f"   • {q}")
                if why:
                    print(f"     Why it matters: {why}")
                if action:
                    print(f"     Suggested action: {action}")
                print()

    uncategorized = by_category.get('uncategorized', [])
    if uncategorized:
        print(f"\n❓ UNCATEGORIZED ({len(uncategorized)} items)")
        for item in uncategorized:
            print(f"   • {item.get('question', str(item))}")

    # Also check claims for gaps
    claim_gaps = []
    for claim in claims_data:
        for gap in claim.get('gaps', []):
            if isinstance(gap, dict):
                claim_gaps.append({
                    'claim': claim.get('id', '?'),
                    'what': gap.get('what', '?'),
                    'category': gap.get('category', 'uncategorized'),
                    'importance': gap.get('importance', 'unknown')
                })

    if claim_gaps:
        print(f"\n--- Gaps in Claims ({len(claim_gaps)}) ---\n")
        for gap in claim_gaps[:20]:
            print(f"  [{gap['importance']}] {gap['claim']}: {gap['what']}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]
    facts, claims_data, links_data = load_data()

    commands = {
        'gap-analysis': gap_analysis,
        'coherence-check': coherence_check,
        'strength-report': strength_report,
        'timeline-verify': timeline_verify,
        'exhibit-coverage': exhibit_coverage,
        'unknowns': unknowns_report,
    }

    if command in commands:
        commands[command](facts, claims_data, links_data)
    else:
        print(f"Unknown command: {command}")
        print("\nAvailable commands:")
        for cmd, fn in commands.items():
            print(f"  {cmd:20s} {fn.__doc__.strip()}")
        sys.exit(1)


if __name__ == '__main__':
    main()
