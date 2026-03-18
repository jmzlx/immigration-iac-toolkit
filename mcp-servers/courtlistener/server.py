#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "mcp>=1.0.0",
#     "pydantic>=2.0.0",
# ]
# ///
"""
CourtListener MCP Server

Provides U.S. case law search, opinion retrieval, citation networks, and docket
lookup via the CourtListener REST API v4. Runs as a stdio MCP server so it
executes on the host machine with full network access.

Requires COURTLISTENER_API_KEY environment variable.
"""

import json
import os
import urllib.parse
import urllib.request
import urllib.error
from html.parser import HTMLParser
from typing import Optional

from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# CourtListener API client
# ---------------------------------------------------------------------------

BASE_URL = "https://www.courtlistener.com/api/rest/v4"


class HTMLTextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self._text = []

    def handle_data(self, data):
        self._text.append(data)

    def get_text(self):
        return "".join(self._text).strip()


def strip_html(html_str: str) -> str:
    if not html_str:
        return ""
    extractor = HTMLTextExtractor()
    extractor.feed(html_str)
    return extractor.get_text()


def get_api_key() -> str:
    key = os.environ.get("COURTLISTENER_API_KEY", "").strip()
    if not key:
        raise ValueError(
            "COURTLISTENER_API_KEY environment variable is not set. "
            "Get a free key at https://www.courtlistener.com/sign-in/"
        )
    return key


def api_request(path: str, params: dict = None) -> dict:
    key = get_api_key()
    url = f"{BASE_URL}/{path.strip('/')}/"
    if params:
        params = {k: v for k, v in params.items() if v is not None}
        url += "?" + urllib.parse.urlencode(params)

    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Token {key}")
    req.add_header("Accept", "application/json")

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        if e.code == 401:
            raise ValueError("Authentication failed (401). Check COURTLISTENER_API_KEY.")
        elif e.code == 429:
            raise ValueError("Rate limited (429). Wait a few minutes.")
        elif e.code == 404:
            raise ValueError(f"Not found (404). URL: {url}")
        else:
            raise ValueError(f"HTTP {e.code}: {body[:500]}")
    except urllib.error.URLError as e:
        raise ValueError(f"Connection failed: {e.reason}")


# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------

mcp = FastMCP("courtlistener_mcp")


@mcp.tool()
async def courtlistener_search_opinions(
    query: str,
    court: Optional[str] = None,
    after: Optional[str] = None,
    before: Optional[str] = None,
    order: str = "score",
    limit: int = 10,
) -> str:
    """Search U.S. case law opinions by keyword, court, and date range.

    Args:
        query: Search query (e.g., 'immigration attorney failure to advise unlawful presence')
        court: Court ID filter (e.g., 'scotus', 'nys3d', 'dc', 'fla')
        after: Filed after date (YYYY-MM-DD)
        before: Filed before date (YYYY-MM-DD)
        order: Sort: 'score' (relevance), 'dateFiled+desc' (newest), 'citeCount+desc' (most cited)
        limit: Max results (1-20)
    """
    api_params = {"q": query, "type": "o", "highlight": "on"}
    if court:
        api_params["court"] = court
    if after:
        api_params["filed_after"] = after
    if before:
        api_params["filed_before"] = before
    if order:
        api_params["order_by"] = order
    api_params["page_size"] = min(limit, 20)

    data = api_request("search", api_params)
    results = data.get("results", [])

    if not results:
        return "No results found. Try broadening search terms, removing court filters, or expanding dates."

    lines = [f"Found {data.get('count', len(results))} total (showing {len(results)}):\n"]
    for i, r in enumerate(results, 1):
        case_name = r.get("caseName", "Unknown")
        citation = r.get("citation", [])
        if isinstance(citation, list):
            citation = ", ".join(citation) if citation else "No citation"
        snippet = strip_html(r.get("snippet", ""))
        if len(snippet) > 300:
            snippet = snippet[:300] + "..."

        lines.append(f"[{i}] {case_name}")
        lines.append(f"    Citation: {citation}")
        lines.append(f"    Court: {r.get('court', '?')}  |  Date: {r.get('dateFiled', '?')}  |  Cited {r.get('citeCount', 0)} times")
        lines.append(f"    Cluster ID: {r.get('cluster_id', '')}")
        lines.append(f"    URL: https://www.courtlistener.com/opinion/{r.get('cluster_id', '')}/")
        if snippet:
            lines.append(f"    Snippet: {snippet}")
        lines.append("")

    return "\n".join(lines)


@mcp.tool()
async def courtlistener_lookup_citation(citation: str) -> str:
    """Look up a case by citation string (e.g., '180 A.D.3d 130' or '19 I&N Dec. 637').

    Args:
        citation: The citation string to look up
    """
    api_params = {"q": f'citation:("{citation}")', "type": "o", "highlight": "on"}
    data = api_request("search", api_params)
    results = data.get("results", [])

    if not results:
        api_params["q"] = f'"{citation}"'
        data = api_request("search", api_params)
        results = data.get("results", [])

    if not results:
        return f"No results found for citation: {citation}"

    lines = [f"Found {len(results)} result(s) for '{citation}':\n"]
    for i, r in enumerate(results, 1):
        cit = r.get("citation", [])
        if isinstance(cit, list):
            cit = ", ".join(cit) if cit else "No citation"
        cluster_id = r.get("cluster_id", "")
        lines.append(f"[{i}] {r.get('caseName', 'Unknown')}")
        lines.append(f"    Citation: {cit}")
        lines.append(f"    Court: {r.get('court', '?')}  |  Date: {r.get('dateFiled', '?')}  |  Cited {r.get('citeCount', 0)} times")
        lines.append(f"    Cluster ID: {cluster_id}")
        lines.append(f"    URL: https://www.courtlistener.com/opinion/{cluster_id}/")
        lines.append("")

    return "\n".join(lines)


@mcp.tool()
async def courtlistener_get_opinion(cluster_id: str) -> str:
    """Get the full text of a court opinion by cluster ID.

    Args:
        cluster_id: Cluster ID from search results
    """
    cluster = api_request(f"clusters/{cluster_id}")

    case_name = cluster.get("case_name", "Unknown")
    date_filed = cluster.get("date_filed", "Unknown")
    citations = cluster.get("citations", [])
    citation_strs = []
    for c in citations:
        if isinstance(c, dict):
            citation_strs.append(f"{c.get('volume', '')} {c.get('reporter', '')} {c.get('page', '')}".strip())
        elif isinstance(c, str):
            citation_strs.append(c)

    lines = [f"Case: {case_name}", f"Date Filed: {date_filed}"]
    if citation_strs:
        lines.append(f"Citations: {', '.join(citation_strs)}")

    sub_opinions = cluster.get("sub_opinions", [])
    if not sub_opinions:
        opinions_data = api_request("opinions", {"cluster": cluster_id})
        sub_opinions = opinions_data.get("results", [])

    if not sub_opinions:
        lines.append("\nNo opinion text available.")
        return "\n".join(lines)

    for op in sub_opinions:
        if isinstance(op, str) and op.startswith("http"):
            op_id = op.rstrip("/").split("/")[-1]
            op = api_request(f"opinions/{op_id}")

        if isinstance(op, dict):
            text = (
                op.get("html_with_citations") or op.get("html_columbia")
                or op.get("html_lawbox") or op.get("html")
                or op.get("plain_text") or op.get("xml_harvard") or ""
            )
            text = strip_html(text)
            author = op.get("author_str", "") or ""

            lines.append(f"\n{'=' * 70}")
            lines.append(f"Opinion Type: {op.get('type', '?')}")
            if author:
                lines.append(f"Author: {author}")
            lines.append("=" * 70)
            if text:
                lines.append(text[:15000])
                if len(text) > 15000:
                    lines.append(f"\n... [truncated — full text is {len(text)} chars]")
            else:
                lines.append("[No text content]")

    return "\n".join(lines)


@mcp.tool()
async def courtlistener_cited_by(cluster_id: str, limit: int = 10) -> str:
    """Find cases that cite a given opinion. Builds chains of authority.

    Args:
        cluster_id: Cluster ID of the opinion to find citations for
        limit: Max results (1-50)
    """
    data = api_request(f"clusters/{cluster_id}/citing-opinions")
    results = data.get("results", [])

    if not results:
        return f"No citing opinions found for cluster {cluster_id}."

    lines = [f"Cases citing cluster {cluster_id} ({data.get('count', len(results))} total, showing {min(len(results), limit)}):\n"]
    for i, r in enumerate(results[:limit], 1):
        if isinstance(r, str) and r.startswith("http"):
            cid = r.rstrip("/").split("/")[-1]
            r = api_request(f"clusters/{cid}")
        if isinstance(r, dict):
            citations = r.get("citations", [])
            cite_str = ""
            if citations and isinstance(citations[0], dict):
                c = citations[0]
                cite_str = f"{c.get('volume', '')} {c.get('reporter', '')} {c.get('page', '')}".strip()
            lines.append(f"[{i}] {r.get('case_name', 'Unknown')}")
            if cite_str:
                lines.append(f"    Citation: {cite_str}")
            lines.append(f"    Date: {r.get('date_filed', '?')}")
            lines.append("")

    return "\n".join(lines)


@mcp.tool()
async def courtlistener_cites(cluster_id: str, limit: int = 10) -> str:
    """Find cases cited by a given opinion. Shows what authority was relied on.

    Args:
        cluster_id: Cluster ID of the opinion
        limit: Max results (1-50)
    """
    cluster = api_request(f"clusters/{cluster_id}")
    opinions_cited = cluster.get("opinions_cited", [])

    if not opinions_cited:
        return f"No cited opinions found for cluster {cluster_id}."

    lines = [f"Opinions cited by cluster {cluster_id} ({len(opinions_cited)} total):\n"]
    shown = 0
    for ref in opinions_cited[:limit]:
        if isinstance(ref, str) and ref.startswith("http"):
            op_id = ref.rstrip("/").split("/")[-1]
            try:
                op = api_request(f"opinions/{op_id}")
                cluster_url = op.get("cluster", "")
                if cluster_url and isinstance(cluster_url, str):
                    cid = cluster_url.rstrip("/").split("/")[-1]
                    cl = api_request(f"clusters/{cid}")
                    shown += 1
                    lines.append(f"[{shown}] {cl.get('case_name', 'Unknown')}  (Date: {cl.get('date_filed', '?')})")
            except Exception:
                continue

    if shown == 0:
        lines.append("  Could not resolve cited opinions.")

    return "\n".join(lines)


@mcp.tool()
async def courtlistener_get_docket(docket_id: str) -> str:
    """Get docket details including case name, number, court, dates, and judge.

    Args:
        docket_id: Docket ID to look up
    """
    data = api_request(f"dockets/{docket_id}")
    return "\n".join([
        f"Case Name: {data.get('case_name', 'Unknown')}",
        f"Docket Number: {data.get('docket_number', 'Unknown')}",
        f"Court: {data.get('court', 'Unknown')}",
        f"Date Filed: {data.get('date_filed', 'Unknown')}",
        f"Date Terminated: {data.get('date_terminated', 'N/A')}",
        f"Assigned To: {data.get('assigned_to_str', 'N/A')}",
        f"Nature of Suit: {data.get('nature_of_suit', 'N/A')}",
        f"URL: https://www.courtlistener.com/docket/{docket_id}/",
    ])


@mcp.tool()
async def courtlistener_search_dockets(
    query: str, court: Optional[str] = None, limit: int = 10
) -> str:
    """Search court dockets by keyword and optional court filter.

    Args:
        query: Search query (e.g., 'Hayman Woodward')
        court: Court ID filter
        limit: Max results (1-20)
    """
    api_params = {"q": query, "type": "d", "highlight": "on"}
    if court:
        api_params["court"] = court
    api_params["page_size"] = min(limit, 20)

    data = api_request("search", api_params)
    results = data.get("results", [])

    if not results:
        return "No dockets found."

    lines = [f"Found {data.get('count', len(results))} dockets (showing {len(results)}):\n"]
    for i, r in enumerate(results, 1):
        lines.append(f"[{i}] {r.get('caseName', 'Unknown')}")
        lines.append(f"    Docket #: {r.get('docketNumber', '?')}  |  Court: {r.get('court', '?')}  |  Filed: {r.get('dateFiled', '?')}")
        lines.append(f"    Docket ID: {r.get('docket_id', '')}")
        lines.append("")

    return "\n".join(lines)


@mcp.tool()
async def courtlistener_search_courts(query: str) -> str:
    """Search for court IDs by name. Use when you need a court ID to filter searches.

    Args:
        query: Court name to search (e.g., 'new york', 'florida')
    """
    data = api_request("courts", {"q": query})
    results = data.get("results", [])

    if not results:
        return f"No courts found matching '{query}'."

    lines = [f"Courts matching '{query}':\n"]
    for c in results:
        court_id = c.get("id", "")
        name = c.get("full_name", c.get("short_name", "Unknown"))
        jurisdiction = c.get("jurisdiction", "")
        lines.append(f"  {court_id:20s}  {name}  ({jurisdiction})")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport="stdio")
