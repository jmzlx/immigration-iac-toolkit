---
name: evidence-manager
description: >
  Manages exhibits and evidence across bar complaints, immigration cases, and appeals.
  Scans workspace files, builds a master evidence index, detects duplicates by content
  hash, searches by keyword, cross-references exhibits to proceedings, and generates
  formatted evidence indices for filing. Triggers on "which exhibits support this
  claim", "what evidence do I have for", "find documents about", "are there duplicates",
  "what's missing from my evidence", "build an evidence index", "organize my exhibits",
  "scan my files", "evidence for the Aggarwal response", "exhibits for the motion",
  or any request to assemble, search, or cross-reference legal documents.
---

# Evidence Manager for Legal Proceedings

Manage 34+ exhibits across 5+ bar complaints and immigration filings. This skill maintains a master evidence index that tracks every exhibit—where it lives, what it proves, which proceedings need it, and which claims it supports. Never again lose track of critical evidence or wonder if you've covered all your claims.

## Why This Matters

Legal evidence management is a coordination problem. You have exhibits scattered across nested folders for different attorneys, different cases, different appeals. When you respond to a bar complaint, you need exactly the right subset of exhibits in order, numbered correctly for that jurisdiction. When you discover new evidence, you need to know instantly which other proceedings it supports. When you revise a claim, you need to know if you have gaps.

This skill automates that complexity. It scans your workspace, builds an evidence index, finds duplicates, and generates formatted evidence indices tailored to each proceeding.

## What It Does

**Evidence Index (evidence_index.json)**
- Master record of every exhibit you've identified
- Each entry: ID, description, file path, date created, file type, which proceedings reference it, which claims it supports
- Updated automatically when you scan or add exhibits
- Queryable by proceeding, claim, date range, file type, or keyword

**Core Commands**

`scan` - Crawl the workspace recursively, auto-discover evidence files (PDF, DOCX, images, audio/video), build or update the evidence index. Use this when you add new folders or files to the workspace.

`list` - Display all indexed exhibits, optionally filtered by proceeding, claim, type, or date. Useful for spot-checks and understanding coverage.

`search <query>` - Find exhibits by keyword in description or filename. Helps you locate evidence you vaguely remember.

`add <filepath> <description> [--proceeding=<name>] [--claims=<claim1,claim2>]` - Manually index an exhibit if auto-scan missed it, or add metadata to an existing entry.

`tag <exhibit_id> --proceeding=<name> --claims=<claim1,claim2>` - Update which proceedings and claims an exhibit supports. Use when you realize evidence is relevant to a case you hadn't considered.

`cross-reference` - Show all exhibits linked to a specific proceeding or claim. Helps you understand the evidence map for a given case.

`duplicates` - Identify duplicate files across the workspace (by hash). Duplicates waste space and create inconsistency—flag them for consolidation.

`gaps <proceeding>` - Analyze which claims in a proceeding lack supporting evidence. Red flag: claims without exhibits need additional work or need to be reconsidered.

`generate-index <proceeding> [--output-path=<path>]` - Export a formatted, exhibit-numbered evidence index as a .docx file suitable for submission. Each proceeding's output follows that jurisdiction's numbering convention (e.g., Exhibit A, Exhibit 1, etc.).

## Folder Structure Awareness

The skill understands your workspace layout:

- **BAR COMPLAINTS/10.SUPPORTING EVIDENCE/** - Shared evidence referenced across multiple bar complaint responses
- **BAR COMPLAINTS/[ATTORNEY_NAME]/** - Per-attorney complaint response folders (each attorney's separate proceeding)
- **CASES EB1 AND EB2/** - Immigration case documents and supporting evidence
- **Binders/** - Appeal binder evidence and compilations
- **camargo-reply/** - Evidence for the Camargo proceeding response
- **julia_response_malika/** - Evidence for the Aggarwal proceeding response
- Other nested folders with exhibits

The skill tracks file paths relative to your workspace root, so if you move a folder, you can update the index to reflect the new structure.

## File Types Supported

- **Documents**: PDF, DOCX, XLSX, TXT, RTF
- **Images**: JPG, PNG, TIFF, GIF
- **Audio/Video**: MP3, MP4, WAV, MOV, AVI
- **Archives**: ZIP (optionally indexed by contents)

## How the Evidence Index Works

Each entry in evidence_index.json contains:

```json
{
  "id": "EX-001",
  "filename": "email-complaint-unauthorized-practice.pdf",
  "description": "Email from client detailing unauthorized practice of law by Attorney Smith",
  "file_path": "BAR_COMPLAINTS/Attorney_Smith/supporting_evidence/email_2024_03.pdf",
  "date_created": "2024-03-15",
  "file_type": "pdf",
  "file_hash": "abc123def456",
  "proceedings": ["Smith_Bar_Complaint_2024", "Immigration_EB2_2024"],
  "claims": ["unauthorized_practice", "fee_misrepresentation"],
  "tags": ["email", "client_communication"],
  "date_indexed": "2025-02-10",
  "notes": "Also supports immigration case claim of pattern of misconduct"
}
```

**Key fields:**
- `id` - Unique identifier for quick reference
- `description` - Plain English summary of what the exhibit shows
- `proceedings` - Which legal matters this evidence is relevant to
- `claims` - Which specific claims or allegations this exhibit supports
- `file_hash` - Used to detect duplicates across folders

## Duplicate Detection

When you run `duplicates`, the skill identifies files with identical content across different folders. Example output:

```
DUPLICATES FOUND:
[hash: a1b2c3...]
  - BAR_COMPLAINTS/10.SUPPORTING_EVIDENCE/email_march_2024.pdf
  - BAR_COMPLAINTS/Smith/email_march_2024.pdf
  - CASES_EB1_AND_EB2/smith_evidence.pdf

Action: Keep primary copy, delete or symlink duplicates to avoid inconsistency.
```

## Gap Analysis

Run `gaps smith_bar_complaint` to flag claims lacking evidence:

```
CLAIMS WITHOUT SUPPORTING EVIDENCE:
- claim: fee_overcharging
  status: 1 exhibit (thin)
  exhibits: EX-012
  recommendation: Locate additional invoices or client communications

- claim: failure_to_represent
  status: 0 exhibits (CRITICAL GAP)
  exhibits: (none)
  action: Search for client letters, missed deadlines, or court filings
```

## Generate Evidence Index for Submission

When you're ready to file a bar complaint response, generate a formatted index:

```bash
evidence-manager generate-index "Smith_Bar_Complaint_2024" --output-path="./Smith_Bar_Complaint_Response.docx"
```

Output: A professionally formatted .docx with:
- Exhibit numbering (Exhibit A, Exhibit B, etc., or per-jurisdiction convention)
- Exhibit descriptions
- Page counts
- File paths (optional, for internal use)
- Cross-reference to claims each exhibit supports

Perfect for attaching to your filed response.

## Usage Examples

**Build your initial index:**
```
evidence-manager scan
```
Creates or updates `evidence_index.json` at workspace root. Crawls all subdirectories.

**Find all evidence supporting a specific claim:**
```
evidence-manager cross-reference --claim="unauthorized_practice"
```
Lists all exhibits tagged with that claim across all proceedings.

**Check what evidence you have for the Aggarwal complaint:**
```
evidence-manager cross-reference --proceeding="Aggarwal_Bar_Complaint"
```

**Find duplicates and consolidate:**
```
evidence-manager duplicates
```
Identifies files with identical content, recommend consolidation.

**Check if your Camargo response is fully supported:**
```
evidence-manager gaps "Camargo_Proceeding"
```
Flags any claims you asserted without exhibits.

**Generate a formatted evidence index for filing:**
```
evidence-manager generate-index "Smith_Bar_Complaint_2024"
```
Outputs `Smith_Bar_Complaint_2024_Evidence_Index.docx` ready to attach.

## Installation & First Run

1. Place this skill in your `.skills/` directory
2. Run `evidence-manager scan` to build the initial index
3. Review `evidence_index.json` and add manual notes via `add` or `tag` commands
4. Use `gaps <proceeding>` to identify missing evidence
5. Run `generate-index <proceeding>` when filing

## Technical Notes

- The evidence_index.json is stored at the workspace root, making it portable across backup/sync scenarios
- File paths are stored relative to workspace root for portability
- File hashing (MD5 or SHA256) detects duplicates even if filenames differ
- The .docx generator preserves formatting and can include optional metadata (dates, hashes for internal reference)
- All dates stored in ISO 8601 format (YYYY-MM-DD) for consistency

## Integration with Case Knowledge

When tagging exhibits or running gap analysis, cross-reference with `../case-knowledge/claims-matrix.json` to see which claims need evidence support. After updating exhibit tags, run:
```bash
python ../case-knowledge/scripts/case_analyzer.py exhibit-coverage
```
This shows which exhibits are heavily used vs. unused, helping prioritize evidence gathering.

## Limitations & Future Enhancements

- Currently does not extract text from PDFs (future: OCR for searchable index)
- Does not validate claims exist in a master claims registry (future: link to claim definitions)
- Exhibit numbering is basic; future versions can support custom numbering schemes per jurisdiction
- No built-in encryption; evidence_index.json should be stored securely
