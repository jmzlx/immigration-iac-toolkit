#!/usr/bin/env python3
"""
CourtListener API v4 client.

Usage:
    python courtlistener.py search "query" [--court ID] [--after DATE] [--before DATE] [--order FIELD] [--limit N]
    python courtlistener.py citation "citation string"
    python courtlistener.py opinion <cluster_id>
    python courtlistener.py cited-by <cluster_id> [--limit N]
    python courtlistener.py cites <cluster_id> [--limit N]
    python courtlistener.py docket <docket_id>
    python courtlistener.py search-dockets "query" [--court ID] [--limit N]
    python courtlistener.py courts "query"

Requires COURTLISTENER_API_KEY environment variable.
"""

import argparse
import json
import os
import re
import sys
import urllib.request
import urllib.parse
import urllib.error
from html.parser import HTMLParser


BASE_URL = "https://www.courtlistener.com/api/rest/v4"


class HTMLTextExtractor(HTMLParser):
    """Strip HTML tags, keeping text content."""
    def __init__(self):
        super().__init__()
        self._text = []

    def handle_data(self, data):
        self._text.append(data)

    def get_text(self):
        return "".join(self._text).strip()


def strip_html(html_str):
    if not html_str:
        return ""
    extractor = HTMLTextExtractor()
    extractor.feed(html_str)
    return extractor.get_text()


def get_api_key():
    key = os.environ.get("COURTLISTENER_API_KEY", "").strip()
    if not key:
        print("ERROR: COURTLISTENER_API_KEY environment variable is not set.", file=sys.stderr)
        print("Set it with: export COURTLISTENER_API_KEY='your-token-here'", file=sys.stderr)
        sys.exit(1)
    return key


def api_request(path, params=None):
    """Make an authenticated GET request to the CourtListener API."""
    key = get_api_key()
    url = f"{BASE_URL}/{path.strip('/')}/"
    if params:
        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}
        url += "?" + urllib.parse.urlencode(params)

    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Token {key}")
    req.add_header("Accept", "application/json")

    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        if e.code == 401:
            print("ERROR: Authentication failed (401). Check your COURTLISTENER_API_KEY.", file=sys.stderr)
        elif e.code == 429:
            print("ERROR: Rate limited (429). Wait a few minutes and try again.", file=sys.stderr)
        elif e.code == 404:
            print(f"ERROR: Not found (404). URL: {url}", file=sys.stderr)
        else:
            print(f"ERROR: HTTP {e.code}: {body[:500]}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"ERROR: Connection failed: {e.reason}", file=sys.stderr)
        sys.exit(1)


def cmd_search(args):
    """Search case law opinions."""
    params = {
        "q": args.query,
        "type": "o",  # opinions
    }
    if args.court:
        params["court"] = args.court
    if args.after:
        params["filed_after"] = args.after
    if args.before:
        params["filed_before"] = args.before
    if args.order:
        params["order_by"] = args.order
    if args.limit:
        params["page_size"] = min(args.limit, 20)

    # Use highlight for snippets
    params["highlight"] = "on"

    data = api_request("search", params)
    results = data.get("results", [])

    if not results:
        print("No results found.")
        return

    print(f"Found {data.get('count', len(results))} total results (showing {len(results)}):\n")

    for i, r in enumerate(results, 1):
        case_name = r.get("caseName", "Unknown")
        citation = r.get("citation", [])
        if isinstance(citation, list):
            citation = ", ".join(citation) if citation else "No citation"
        court = r.get("court", "Unknown court")
        date_filed = r.get("dateFiled", "Unknown date")
        cluster_id = r.get("cluster_id", "")
        cite_count = r.get("citeCount", 0)
        snippet = strip_html(r.get("snippet", ""))

        print(f"  [{i}] {case_name}")
        print(f"      Citation: {citation}")
        print(f"      Court: {court}  |  Date: {date_filed}  |  Cited {cite_count} times")
        print(f"      Cluster ID: {cluster_id}")
        if snippet:
            # Truncate long snippets
            if len(snippet) > 300:
                snippet = snippet[:300] + "..."
            print(f"      Snippet: {snippet}")
        print()


def cmd_citation(args):
    """Look up a case by citation string."""
    # Try the search endpoint with the citation as query
    params = {
        "q": f'citation:("{args.citation}")',
        "type": "o",
        "highlight": "on",
    }
    data = api_request("search", params)
    results = data.get("results", [])

    if not results:
        # Fallback: try as a plain search
        params["q"] = f'"{args.citation}"'
        data = api_request("search", params)
        results = data.get("results", [])

    if not results:
        print(f"No results found for citation: {args.citation}")
        return

    print(f"Found {len(results)} result(s) for citation '{args.citation}':\n")
    for i, r in enumerate(results, 1):
        case_name = r.get("caseName", "Unknown")
        citation = r.get("citation", [])
        if isinstance(citation, list):
            citation = ", ".join(citation) if citation else "No citation"
        court = r.get("court", "Unknown court")
        date_filed = r.get("dateFiled", "Unknown date")
        cluster_id = r.get("cluster_id", "")
        cite_count = r.get("citeCount", 0)

        print(f"  [{i}] {case_name}")
        print(f"      Citation: {citation}")
        print(f"      Court: {court}  |  Date: {date_filed}  |  Cited {cite_count} times")
        print(f"      Cluster ID: {cluster_id}")
        print(f"      URL: https://www.courtlistener.com/opinion/{cluster_id}/")
        print()


def cmd_opinion(args):
    """Get full opinion text by cluster ID."""
    # First get the cluster to find opinion IDs
    cluster = api_request(f"clusters/{args.cluster_id}")

    case_name = cluster.get("case_name", "Unknown")
    date_filed = cluster.get("date_filed", "Unknown")
    citations = cluster.get("citations", [])
    citation_strs = []
    for c in citations:
        if isinstance(c, dict):
            citation_strs.append(f"{c.get('volume', '')} {c.get('reporter', '')} {c.get('page', '')}".strip())
        elif isinstance(c, str):
            citation_strs.append(c)

    print(f"Case: {case_name}")
    print(f"Date Filed: {date_filed}")
    if citation_strs:
        print(f"Citations: {', '.join(citation_strs)}")

    # Get the court info
    court_url = cluster.get("docket", "")
    if court_url and isinstance(court_url, str) and court_url.startswith("http"):
        # It's a URL reference; extract docket ID
        pass

    # Get sub-opinions from the cluster
    sub_opinions = cluster.get("sub_opinions", [])
    if not sub_opinions:
        # Try getting opinions directly
        opinions_data = api_request("opinions", {"cluster": args.cluster_id})
        sub_opinions = opinions_data.get("results", [])

    if not sub_opinions:
        print("\nNo opinion text available for this cluster.")
        return

    for op in sub_opinions:
        if isinstance(op, str) and op.startswith("http"):
            # It's a URL, fetch it
            op_id = op.rstrip("/").split("/")[-1]
            op = api_request(f"opinions/{op_id}")

        if isinstance(op, dict):
            op_type = op.get("type", "Unknown")
            # Try multiple text fields in order of preference
            text = (
                op.get("html_with_citations")
                or op.get("html_columbia")
                or op.get("html_lawbox")
                or op.get("html")
                or op.get("plain_text")
                or op.get("xml_harvard")
                or ""
            )
            text = strip_html(text)

            author = op.get("author_str", "") or ""
            print(f"\n{'='*70}")
            print(f"Opinion Type: {op_type}")
            if author:
                print(f"Author: {author}")
            print(f"{'='*70}")
            if text:
                print(text[:10000])
                if len(text) > 10000:
                    print(f"\n... [truncated — full text is {len(text)} characters]")
            else:
                print("[No text content available]")


def cmd_cited_by(args):
    """Find cases that cite a given cluster."""
    data = api_request(f"clusters/{args.cluster_id}/citing-opinions")
    results = data.get("results", [])

    if not results:
        print(f"No citing opinions found for cluster {args.cluster_id}.")
        return

    print(f"Cases citing cluster {args.cluster_id} ({data.get('count', len(results))} total, showing {len(results)}):\n")
    for i, r in enumerate(results[:args.limit], 1):
        if isinstance(r, str) and r.startswith("http"):
            # URL reference — extract cluster ID
            cid = r.rstrip("/").split("/")[-1]
            r = api_request(f"clusters/{cid}")

        if isinstance(r, dict):
            case_name = r.get("case_name", "Unknown")
            date_filed = r.get("date_filed", "Unknown")
            citations = r.get("citations", [])
            cite_str = ""
            if citations:
                c = citations[0]
                if isinstance(c, dict):
                    cite_str = f"{c.get('volume', '')} {c.get('reporter', '')} {c.get('page', '')}".strip()

            print(f"  [{i}] {case_name}")
            if cite_str:
                print(f"      Citation: {cite_str}")
            print(f"      Date: {date_filed}")
            print()


def cmd_cites(args):
    """Find cases cited by a given cluster."""
    cluster = api_request(f"clusters/{args.cluster_id}")

    # The "opinions_cited" field contains the cited opinions
    opinions_cited = cluster.get("opinions_cited", [])
    if not opinions_cited:
        print(f"No cited opinions found for cluster {args.cluster_id}.")
        return

    print(f"Opinions cited by cluster {args.cluster_id} ({len(opinions_cited)} total):\n")
    shown = 0
    for ref in opinions_cited[:args.limit]:
        if isinstance(ref, str) and ref.startswith("http"):
            op_id = ref.rstrip("/").split("/")[-1]
            try:
                op = api_request(f"opinions/{op_id}")
                cluster_url = op.get("cluster", "")
                if cluster_url and isinstance(cluster_url, str):
                    cid = cluster_url.rstrip("/").split("/")[-1]
                    cl = api_request(f"clusters/{cid}")
                    shown += 1
                    case_name = cl.get("case_name", "Unknown")
                    date_filed = cl.get("date_filed", "Unknown")
                    print(f"  [{shown}] {case_name}  (Date: {date_filed})")
            except Exception:
                continue
        elif isinstance(ref, dict):
            shown += 1
            print(f"  [{shown}] {ref.get('case_name', 'Unknown')}")

    if shown == 0:
        print("  Could not resolve cited opinions.")


def cmd_docket(args):
    """Get docket details."""
    data = api_request(f"dockets/{args.docket_id}")

    print(f"Case Name: {data.get('case_name', 'Unknown')}")
    print(f"Docket Number: {data.get('docket_number', 'Unknown')}")
    print(f"Court: {data.get('court', 'Unknown')}")
    print(f"Date Filed: {data.get('date_filed', 'Unknown')}")
    print(f"Date Terminated: {data.get('date_terminated', 'N/A')}")
    print(f"Assigned To: {data.get('assigned_to_str', 'N/A')}")
    print(f"Nature of Suit: {data.get('nature_of_suit', 'N/A')}")
    print(f"URL: https://www.courtlistener.com/docket/{args.docket_id}/")


def cmd_search_dockets(args):
    """Search dockets."""
    params = {
        "q": args.query,
        "type": "d",
        "highlight": "on",
    }
    if args.court:
        params["court"] = args.court
    if args.limit:
        params["page_size"] = min(args.limit, 20)

    data = api_request("search", params)
    results = data.get("results", [])

    if not results:
        print("No dockets found.")
        return

    print(f"Found {data.get('count', len(results))} dockets (showing {len(results)}):\n")
    for i, r in enumerate(results, 1):
        case_name = r.get("caseName", "Unknown")
        docket_number = r.get("docketNumber", "Unknown")
        court = r.get("court", "Unknown")
        date_filed = r.get("dateFiled", "Unknown")
        docket_id = r.get("docket_id", "")

        print(f"  [{i}] {case_name}")
        print(f"      Docket #: {docket_number}  |  Court: {court}  |  Filed: {date_filed}")
        print(f"      Docket ID: {docket_id}")
        print()


def cmd_courts(args):
    """Search for court IDs."""
    data = api_request("courts", {"q": args.query})
    results = data.get("results", [])

    if not results:
        print(f"No courts found matching '{args.query}'.")
        return

    print(f"Courts matching '{args.query}':\n")
    for c in results:
        court_id = c.get("id", "")
        name = c.get("full_name", c.get("short_name", "Unknown"))
        jurisdiction = c.get("jurisdiction", "")
        print(f"  {court_id:20s}  {name}  ({jurisdiction})")


def main():
    parser = argparse.ArgumentParser(description="CourtListener API client")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # search
    sp = subparsers.add_parser("search", help="Search case law opinions")
    sp.add_argument("query", help="Search query")
    sp.add_argument("--court", help="Court ID filter (e.g., scotus, nys3d, dc)")
    sp.add_argument("--after", help="Filed after date (YYYY-MM-DD)")
    sp.add_argument("--before", help="Filed before date (YYYY-MM-DD)")
    sp.add_argument("--order", default="score", help="Order by: score, dateFiled+desc, citeCount+desc")
    sp.add_argument("--limit", type=int, default=10, help="Max results (default: 10)")

    # citation
    sp = subparsers.add_parser("citation", help="Look up a case by citation")
    sp.add_argument("citation", help="Citation string, e.g., '180 A.D.3d 130'")

    # opinion
    sp = subparsers.add_parser("opinion", help="Get full opinion text")
    sp.add_argument("cluster_id", help="Cluster ID from search results")

    # cited-by
    sp = subparsers.add_parser("cited-by", help="Find cases citing a given opinion")
    sp.add_argument("cluster_id", help="Cluster ID")
    sp.add_argument("--limit", type=int, default=10, help="Max results")

    # cites
    sp = subparsers.add_parser("cites", help="Find cases cited by a given opinion")
    sp.add_argument("cluster_id", help="Cluster ID")
    sp.add_argument("--limit", type=int, default=10, help="Max results")

    # docket
    sp = subparsers.add_parser("docket", help="Get docket details")
    sp.add_argument("docket_id", help="Docket ID")

    # search-dockets
    sp = subparsers.add_parser("search-dockets", help="Search dockets")
    sp.add_argument("query", help="Search query")
    sp.add_argument("--court", help="Court ID filter")
    sp.add_argument("--limit", type=int, default=10, help="Max results")

    # courts
    sp = subparsers.add_parser("courts", help="Search for court IDs")
    sp.add_argument("query", help="Court name to search for")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "search": cmd_search,
        "citation": cmd_citation,
        "opinion": cmd_opinion,
        "cited-by": cmd_cited_by,
        "cites": cmd_cites,
        "docket": cmd_docket,
        "search-dockets": cmd_search_dockets,
        "courts": cmd_courts,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
