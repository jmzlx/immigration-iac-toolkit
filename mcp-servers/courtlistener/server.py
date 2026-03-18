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
from pydantic import BaseModel, Field, ConfigDict

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
            raise ValueError("Authentication failed (401). Check your COURTLISTENER_API_KEY.")
        elif e.code == 429:
            raise ValueError("Rate limited (429). Wait a few minutes and try again.")
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


# --- Tool Input Models ---

class SearchOpinionsInput(BaseModel):
    """Search case law opinions by keyword, court, and date range."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    query: str = Field(..., description="Search query (e.g., 'immigration attorney failure to advise unlawful presence')", min_length=1)
    court: Optional[str] = Field(default=None, description="Court ID filter (e.g., 'scotus', 'nys3d', 'dc', 'fla')")
    after: Optional[str] = Field(default=None, description="Filed after date (YYYY-MM-DD)")
    before: Optional[str] = Field(default=None, description="Filed before date (YYYY-MM-DD)")
    order: Optional[str] = Field(default="score", description="Sort order: 'score' (relevance), 'dateFiled+desc' (newest), 'citeCount+desc' (most cited)")
    limit: Optional[int] = Field(default=10, description="Max results (1-20)", ge=1, le=20)


class CitationLookupInput(BaseModel):
    """Look up a case by its citation string."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    citation: str = Field(..., description="Citation string (e.g., '180 A.D.3d 130', '19 I&N Dec. 637')", min_length=1)


class ClusterIdInput(BaseModel):
    """Input for operations that take a cluster ID."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    cluster_id: str = Field(..., description="Cluster ID from search results", min_length=1)
    limit: Optional[int] = Field(default=10, description="Max results for citation lookups", ge=1, le=50)


class DocketIdInput(BaseModel):
    """Input for docket lookup."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    docket_id: str = Field(..., description="Docket ID", min_length=1)


class SearchDocketsInput(BaseModel):
    """Search dockets by keyword and court."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    query: str = Field(..., description="Search query (e.g., 'Hayman Woodward')", min_length=1)
    court: Optional[str] = Field(default=None, description="Court ID filter")
    limit: Optional[int] = Field(default=10, description="Max results (1-20)", ge=1, le=20)


class CourtSearchInput(BaseModel):
    """Search for court IDs by name."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    query: str = Field(..., description="Court name to search (e.g., 'new york', 'florida')", min_length=1)


# --- Tools ---

@mcp.tool(
    name="courtlistener_search_opinions",
    annotations={
        "title": "Search Case Law Opinions",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def search_opinions(params: SearchOpinionsInput) -> str:
    """Search U.S. case law opinions by keyword, court, and date range. Returns case names, citations, courts, dates, snippets, and cluster IDs for further research."""
    api_params = {
        "q": params.query,
        "type": "o",
        "highlight": "on",
    }
    if params.court:
        api_params["court"] = params.court
    if params.after:
        api_params["filed_after"] = params.after
    if params.before:
        api_params["filed_before"] = params.before
    if params.order:
        api_params["order_by"] = params.order
    if params.limit:
        api_params["page_size"] = min(params.limit, 20)

    data = api_request("search", api_params)
    results = data.get("results", [])

    if not results:
        return "No results found. Try broadening your search terms, removing court filters, or expanding the date range."

    lines = [f"Found {data.get('count', len(results))} total results (showing {len(results)}):\n"]

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
        if len(snippet) > 300:
            snippet = snippet[:300] + "..."

        lines.append(f"[{i}] {case_name}")
        lines.append(f"    Citation: {citation}")
        lines.append(f"    Court: {court}  |  Date: {date_filed}  |  Cited {cite_count} times")
        lines.append(f"    Cluster ID: {cluster_id}")
        lines.append(f"    URL: https://www.courtlistener.com/opinion/{cluster_id}/")
        if snippet:
            lines.append(f"    Snippet: {snippet}")
        lines.append("")

    return "\n".join(lines)


@mcp.tool(
    name="courtlistener_lookup_citation",
    annotations={
        "title": "Look Up Case by Citation",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def lookup_citation(params: CitationLookupInput) -> str:
    """Look up a case by its citation string (e.g., '180 A.D.3d 130' or '19 I&N Dec. 637')."""
    api_params = {"q": f'citation:("{params.citation}")', "type": "o", "highlight": "on"}
    data = api_request("search", api_params)
    results = data.get("results", [])

    if not results:
        api_params["q"] = f'"{params.citation}"'
        data = api_request("search", api_params)
        results = data.get("results", [])

    if not results:
        return f"No results found for citation: {params.citation}"

    lines = [f"Found {len(results)} result(s) for '{params.citation}':\n"]
    for i, r in enumerate(results, 1):
        case_name = r.get("caseName", "Unknown")
        citation = r.get("citation", [])
        if isinstance(citation, list):
            citation = ", ".join(citation) if citation else "No citation"
        cluster_id = r.get("cluster_id", "")
        lines.append(f"[{i}] {case_name}")
        lines.append(f"    Citation: {citation}")
        lines.append(f"    Court: {r.get('court', '?')}  |  Date: {r.get('dateFiled', '?')}  |  Cited {r.get('citeCount', 0)} times")
        lines.append(f"    Cluster ID: {cluster_id}")
        lines.append(f"    URL: https://www.courtlistener.com/opinion/{cluster_id}/")
        lines.append("")

    return "\n".join(lines)


@mcp.tool(
    name="courtlistener_get_opinion",
    annotations={
        "title": "Get Full Opinion Text",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def get_opinion(params: ClusterIdInput) -> str:
    """Retrieve the full text of a court opinion by cluster ID. Returns the opinion text, author, and citation information."""
    cluster = api_request(f"clusters/{params.cluster_id}")

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
        opinions_data = api_request("opinions", {"cluster": params.cluster_id})
        sub_opinions = opinions_data.get("results", [])

    if not sub_opinions:
        lines.append("\nNo opinion text available for this cluster.")
        return "\n".join(lines)

    for op in sub_opinions:
        if isinstance(op, str) and op.startswith("http"):
            op_id = op.rstrip("/").split("/")[-1]
            op = api_request(f"opinions/{op_id}")

        if isinstance(op, dict):
            op_type = op.get("type", "Unknown")
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

            lines.append(f"\n{'=' * 70}")
            lines.append(f"Opinion Type: {op_type}")
            if author:
                lines.append(f"Author: {author}")
            lines.append(f"{'=' * 70}")
            if text:
                lines.append(text[:15000])
                if len(text) > 15000:
                    lines.append(f"\n... [truncated — full text is {len(text)} characters]")
            else:
                lines.append("[No text content available]")

    return "\n".join(lines)


@mcp.tool(
    name="courtlistener_cited_by",
    annotations={
        "title": "Find Cases Citing an Opinion",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def cited_by(params: ClusterIdInput) -> str:
    """Find cases that cite a given opinion. Useful for building a chain of authority and finding more recent applications of a legal principle."""
    data = api_request(f"clusters/{params.cluster_id}/citing-opinions")
    results = data.get("results", [])

    if not results:
        return f"No citing opinions found for cluster {params.cluster_id}."

    lines = [f"Cases citing cluster {params.cluster_id} ({data.get('count', len(results))} total, showing {min(len(results), params.limit)}):\n"]

    for i, r in enumerate(results[:params.limit], 1):
        if isinstance(r, str) and r.startswith("http"):
            cid = r.rstrip("/").split("/")[-1]
            r = api_request(f"clusters/{cid}")

        if isinstance(r, dict):
            case_name = r.get("case_name", "Unknown")
            date_filed = r.get("date_filed", "Unknown")
            citations = r.get("citations", [])
            cite_str = ""
            if citations and isinstance(citations[0], dict):
                c = citations[0]
                cite_str = f"{c.get('volume', '')} {c.get('reporter', '')} {c.get('page', '')}".strip()

            lines.append(f"[{i}] {case_name}")
            if cite_str:
                lines.append(f"    Citation: {cite_str}")
            lines.append(f"    Date: {date_filed}")
            lines.append("")

    return "\n".join(lines)


@mcp.tool(
    name="courtlistener_cites",
    annotations={
        "title": "Find Cases Cited by an Opinion",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def cites(params: ClusterIdInput) -> str:
    """Find cases cited by a given opinion. Useful for understanding what authority a court relied on."""
    cluster = api_request(f"clusters/{params.cluster_id}")
    opinions_cited = cluster.get("opinions_cited", [])

    if not opinions_cited:
        return f"No cited opinions found for cluster {params.cluster_id}."

    lines = [f"Opinions cited by cluster {params.cluster_id} ({len(opinions_cited)} total):\n"]

    shown = 0
    for ref in opinions_cited[:params.limit]:
        if isinstance(ref, str) and ref.startswith("http"):
            op_id = ref.rstrip("/").split("/")[-1]
            try:
                op = api_request(f"opinions/{op_id}")
                cluster_url = op.get("cluster", "")
                if cluster_url and isinstance(cluster_url, str):
                    cid = cluster_url.rstrip("/").split("/")[-1]
                    cl = api_request(f"clusters/{cid}")
                    shown += 1
                    lines.append(f"[{shown}] {cl.get('case_name', 'Unknown')}  (Date: {cl.get('date_filed', 'Unknown')})")
            except Exception:
                continue

    if shown == 0:
        lines.append("  Could not resolve cited opinions.")

    return "\n".join(lines)


@mcp.tool(
    name="courtlistener_get_docket",
    annotations={
        "title": "Get Docket Details",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def get_docket(params: DocketIdInput) -> str:
    """Retrieve docket details including case name, docket number, court, dates, and assigned judge."""
    data = api_request(f"dockets/{params.docket_id}")

    lines = [
        f"Case Name: {data.get('case_name', 'Unknown')}",
        f"Docket Number: {data.get('docket_number', 'Unknown')}",
        f"Court: {data.get('court', 'Unknown')}",
        f"Date Filed: {data.get('date_filed', 'Unknown')}",
        f"Date Terminated: {data.get('date_terminated', 'N/A')}",
        f"Assigned To: {data.get('assigned_to_str', 'N/A')}",
        f"Nature of Suit: {data.get('nature_of_suit', 'N/A')}",
        f"URL: https://www.courtlistener.com/docket/{params.docket_id}/",
    ]
    return "\n".join(lines)


@mcp.tool(
    name="courtlistener_search_dockets",
    annotations={
        "title": "Search Dockets",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def search_dockets(params: SearchDocketsInput) -> str:
    """Search court dockets by keyword and optional court filter."""
    api_params = {"q": params.query, "type": "d", "highlight": "on"}
    if params.court:
        api_params["court"] = params.court
    if params.limit:
        api_params["page_size"] = min(params.limit, 20)

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


@mcp.tool(
    name="courtlistener_search_courts",
    annotations={
        "title": "Search for Court IDs",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def search_courts(params: CourtSearchInput) -> str:
    """Search for court IDs by name. Useful when you need to filter searches by a specific court."""
    data = api_request("courts", {"q": params.query})
    results = data.get("results", [])

    if not results:
        return f"No courts found matching '{params.query}'."

    lines = [f"Courts matching '{params.query}':\n"]
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
