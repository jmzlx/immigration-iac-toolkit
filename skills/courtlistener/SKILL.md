---
name: courtlistener
description: >
  Search and retrieve U.S. case law, court opinions, dockets, and citation networks
  using the CourtListener API. Use this skill whenever the user wants to look up a
  court case, search for case law by topic or keyword, find opinions from a specific
  court or jurisdiction, retrieve the full text of an opinion, check what cases cite
  a given case (or what it cites), look up attorney disciplinary decisions, or verify
  a legal citation. Also use for researching Matter of Lozada precedent, ineffective
  assistance of counsel case law, immigration attorney discipline cases, §245(k)
  court decisions, or any BIA/AAO opinion research. Trigger on phrases like "find
  cases about", "look up this case", "search CourtListener", "what does [case name]
  say", "cases citing", "cited by", "disciplinary cases in [state]", "precedent for",
  "case law on", "has any court ruled on", "find similar cases", or any request
  involving U.S. case law research, court opinions, or legal citations — even if
  the user doesn't mention CourtListener by name.
---

# CourtListener API Skill

This skill provides access to the CourtListener REST API (v4) for searching and retrieving U.S. case law, court opinions, dockets, and citation networks.

## Setup

The API key must be available as the environment variable `COURTLISTENER_API_KEY`. All requests require authentication — unauthenticated requests return 401.

Rate limit: 5,000 requests per hour.

## How to Use This Skill

Run the helper script at `scripts/courtlistener.py` (located in this skill's directory) using Python. The script handles authentication, pagination, and output formatting.

### Quick Reference

| Task | Command |
|------|---------|
| Search opinions by keyword | `python scripts/courtlistener.py search "immigration attorney discipline"` |
| Search within a court | `python scripts/courtlistener.py search "attorney discipline" --court nys3d` |
| Look up by citation | `python scripts/courtlistener.py citation "180 A.D.3d 130"` |
| Get full opinion text | `python scripts/courtlistener.py opinion <cluster_id>` |
| Get cases citing a given opinion | `python scripts/courtlistener.py cited-by <cluster_id>` |
| Get cases cited by a given opinion | `python scripts/courtlistener.py cites <cluster_id>` |
| Look up a docket | `python scripts/courtlistener.py docket <docket_id>` |
| Search dockets | `python scripts/courtlistener.py search-dockets "Hayman Woodward"` |

All commands accept `--limit N` to control how many results to return (default: 10).

### Common Court IDs

These are the most commonly needed court identifiers for filtering:

| Court | ID |
|-------|----|
| U.S. Supreme Court | `scotus` |
| D.C. Court of Appeals | `dc` |
| NY App. Div. 1st Dept | `nyappd1` or `nys1d` |
| NY App. Div. 2nd Dept | `nyappd2` or `nys2d` |
| NY App. Div. 3rd Dept | `nyappd3` or `nys3d` |
| NY App. Div. 4th Dept | `nyappd4` or `nys4d` |
| NY Court of Appeals | `ny` |
| FL Supreme Court | `fla` |
| FL Dist. Ct. App. | `fladistctapp` |

If you're unsure of a court ID, run: `python scripts/courtlistener.py courts "new york"` to search for it.

### Search Tips

- **Date filtering**: Use `--after YYYY-MM-DD` and `--before YYYY-MM-DD` to filter by decision date.
- **Sorting**: Use `--order score` (relevance, default), `--order dateFiled+desc` (newest first), or `--order citeCount+desc` (most cited first).
- **Combining filters**: All flags can be combined, e.g.:
  ```
  python scripts/courtlistener.py search "attorney suspension immigration" --court nys3d --after 2015-01-01 --order dateFiled+desc --limit 20
  ```
- **Getting full text**: The search endpoint returns snippets. To get the full opinion text, first search, then use `opinion <cluster_id>` with the cluster ID from the search results.
- **Citation networks**: After finding a case, use `cited-by` to see subsequent cases that relied on it, or `cites` to see what it relied on. This is powerful for building a chain of authority.

### Workflow Example

A typical research workflow looks like this:

1. **Search** for relevant cases: `search "immigration attorney failure to advise" --court nys3d --after 2015-01-01`
2. **Read** a promising result: `opinion <cluster_id>` to get the full text
3. **Expand** your research: `cited-by <cluster_id>` to find more recent cases that cite it
4. **Verify** a known citation: `citation "180 A.D.3d 130"` to confirm details

### Understanding the Output

- **Search results** return: case name, citation, court, date filed, snippet, cluster ID, and citation count.
- **Opinion text** returns: the full HTML-cleaned text of the opinion. The `html_with_citations` field is the most reliable for full text.
- **Citation results** return: citing/cited case name, citation, court, and date.

### Integration with Case Knowledge

Before researching, check `../case-knowledge/claims-matrix.json` to see which claims need case law support. After finding relevant cases, update `../case-knowledge/evidence-links.json` to link the case to the relevant claim and Lozada prong.

### Error Handling

- **401 Unauthorized**: Your API key is missing or invalid. Check that `COURTLISTENER_API_KEY` is set.
- **429 Too Many Requests**: You've hit the rate limit (5,000/hour). Wait a few minutes.
- **Empty results**: Try broadening your search terms, removing court filters, or expanding the date range.
