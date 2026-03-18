# Immigration IAC Toolkit

A Claude Code / Cowork plugin for managing immigration ineffective assistance of counsel (IAC) cases under the Matter of Lozada framework. Analyzes case documents dynamically, tracks claims across jurisdictions, manages evidence, and assists with filing preparation.

## What This Does

Drop your case files into a workspace folder and the toolkit will:

1. **Scan all documents** (PDFs, DOCXs) and build a knowledge graph with timeline, parties, proceedings, and claims
2. **Identify what you know** from the documents (with confidence levels and source citations)
3. **Flag what you don't know** — categorized as findable-in-documents, discoverable-via-research, needs-client-input, or missing-and-critical
4. **Track deadlines** across bar complaints and immigration filings with color-coded urgency
5. **Manage evidence** with duplicate detection, gap analysis, and formatted exhibit indices
6. **Draft bar complaint replies** from the complainant's perspective, sustaining all three Lozada prongs
7. **Assemble Motion to Reopen** filing packages under 8 CFR §103.5
8. **Research case law** via CourtListener API for precedent on attorney discipline and IAC claims

## Skills Included

| Skill | What It Does |
|-------|-------------|
| `case-knowledge` | Dynamic document analysis — builds knowledge graph from case files |
| `bar-complaint-reply-drafter` | Drafts complainant replies across DC, NY, NJ, MA, FL jurisdictions |
| `motion-to-reopen` | Assembles Lozada-based Motion to Reopen filing packages |
| `case-deadline-tracker` | Multi-jurisdiction deadline tracking with HTML dashboards |
| `evidence-manager` | Exhibit indexing, duplicate detection, gap analysis |
| `uscis-immigration-research` | INA/CFR/USCIS policy quick reference and research guidance |
| `courtlistener` | Case law search via CourtListener API |

## Getting Started

### 1. Install the plugin

```bash
# From a marketplace:
/plugin install immigration-iac-toolkit@your-marketplace

# Or locally during development:
claude --plugin-dir ./immigration-iac-toolkit
```

### 2. Add your case files

Place all case documents (complaints, denial notices, emails, evidence) in your workspace folder.

### 3. Bootstrap the knowledge graph

```
Analyze the case in this folder
```

This triggers the case-knowledge skill, which scans all documents and builds the initial knowledge graph.

### 4. Review gaps and unknowns

```
What's missing from the case? What do we still need?
```

### 5. Start working

```
Draft a reply to the Aggarwal bar complaint answer
What's the deadline situation?
Find case law on attorney duty to advise about §245(k)
```

## Requirements

- Claude Code or Cowork with code execution enabled
- `pdftotext` (from poppler-utils) for PDF text extraction (falls back to filename analysis if unavailable)
- CourtListener API key (set as `COURTLISTENER_API_KEY` environment variable) for case law research

## Architecture

The toolkit follows Anthropic's skill best practices with progressive disclosure:

- **Level 1 (metadata)**: Skill descriptions loaded at startup for triggering
- **Level 2 (instructions)**: SKILL.md files loaded when relevant
- **Level 3 (resources)**: Reference files and scripts loaded on demand

The case-knowledge skill is the shared state layer — all other skills read from its generated JSON files to maintain coherence across filings.

## License

MIT
