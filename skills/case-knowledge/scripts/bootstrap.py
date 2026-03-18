#!/usr/bin/env python3
"""
Bootstrap script for scanning legal documents and building a knowledge graph.

Scans PDFs and DOCXs in a workspace, extracts text and metadata, classifies documents,
and outputs structured JSON files + human-readable report.

Usage:
    python bootstrap.py --workspace /path/to/workspace [--incremental] [--verbose]
"""

import os
import sys
import json
import re
import argparse
import subprocess
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Set, Optional
from dataclasses import dataclass, asdict, field
from collections import defaultdict


# =============================================================================
# Configuration & Constants
# =============================================================================

ATTORNEYS = {"Camargo", "Aggarwal", "Widmer", "Wasung", "Rutahweire", "Hayman", "Woodward"}
DOCUMENT_TYPES = {
    "COMPLAINT", "RECEIPT", "EVIDENCE", "FOIA", "I-140", "I-485", "I-290",
    "EB1", "EB2", "AFFIDAVIT", "Gmail", "ANSWER", "REPLY", "MOTION", "DECLARATION"
}
JURISDICTIONS = {"DC", "NY", "NJ", "MA", "FL", "USCIS", "California", "Texas"}
USCIS_FORMS = {"I-140", "I-485", "I-290B", "G-28", "I-94", "I-131", "I-765", "I-539"}

EXCLUDE_DIRS = {".skills", ".claude", "courtlistener-dxt", "courtlistener-plugin"}

# Keywords indicating legal significance
SIGNIFICANCE_KEYWORDS = {
    "denied": "critical",
    "approved": "critical",
    "rejection": "critical",
    "unlawful presence": "critical",
    "section 245(k)": "critical",
    "portability": "important",
    "motion to reopen": "important",
    "ineffective assistance": "important",
    "appeal": "important",
    "objection": "important",
}


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class DateExtraction:
    """Represents an extracted date."""
    date: str  # YYYY-MM-DD format
    confidence: str  # high|medium|low
    extraction_method: str
    source_text: Optional[str] = None


@dataclass
class Attorney:
    """Represents an attorney."""
    name: str
    firm: Optional[str] = None
    jurisdiction: Optional[str] = None
    bar_number: Optional[str] = None
    role: Optional[str] = None
    identified_from: List[str] = field(default_factory=list)

    def to_dict(self):
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class Party:
    """Represents a party in the case."""
    name: str
    role: str
    identified_from: List[str] = field(default_factory=list)


@dataclass
class Proceeding:
    """Represents a legal proceeding."""
    docket: str
    jurisdiction: str
    type: str  # bar|uscis|court
    attorney: Optional[str] = None
    identified_from: List[str] = field(default_factory=list)

    def to_dict(self):
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class DocumentMetadata:
    """Extracted metadata from a document."""
    path: str
    rel_path: str
    file_type: str  # pdf|docx
    dates: List[DateExtraction] = field(default_factory=list)
    attorneys: Set[str] = field(default_factory=set)
    document_types: Set[str] = field(default_factory=set)
    docket_numbers: Set[str] = field(default_factory=set)
    receipt_numbers: Set[str] = field(default_factory=set)
    jurisdictions: Set[str] = field(default_factory=set)
    text_extracted: bool = False
    text_length: int = 0
    text_preview: Optional[str] = None


@dataclass
class Event:
    """Represents a significant event in the case."""
    date: str  # YYYY-MM-DD
    description: str
    source_documents: List[str]
    confidence: str  # high|medium|low
    significance: str  # critical|important|context
    extraction_method: str


@dataclass
class Unknown:
    """Represents an unanswered question."""
    question: str
    why_it_matters: str
    category: str  # findable_in_documents|discoverable_via_research|needs_external_input|missing_and_critical
    suggested_action: str


@dataclass
class Claim:
    """Represents a legal claim."""
    id: str
    description: str
    source_document: str
    attorneys: List[str] = field(default_factory=list)
    proceedings: List[str] = field(default_factory=list)
    evidence: Dict = field(default_factory=lambda: {
        "deficiency": {"supporting_docs": [], "strength": "unknown", "reasoning": "needs_deep_read"},
        "causation": {"supporting_docs": [], "strength": "unknown", "reasoning": "needs_deep_read"},
        "prejudice": {"supporting_docs": [], "strength": "unknown", "reasoning": "needs_deep_read"}
    })
    gaps: List[str] = field(default_factory=list)

    def to_dict(self):
        return asdict(self)


# =============================================================================
# Document Processing
# =============================================================================

class DocumentScanner:
    """Scans and extracts metadata from legal documents."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.pdftotext_available = self._check_pdftotext()

    def _log(self, msg: str):
        if self.verbose:
            print(f"[bootstrap] {msg}")

    def _check_pdftotext(self) -> bool:
        """Check if pdftotext is available on the system."""
        try:
            subprocess.run(["which", "pdftotext"], capture_output=True, check=True, timeout=5)
            self._log("pdftotext found on system")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            self._log("pdftotext not available, will fall back to filename analysis")
            return False

    def scan_workspace(self, workspace_path: str) -> List[DocumentMetadata]:
        """Scan workspace for PDFs and DOCXs."""
        workspace = Path(workspace_path)
        documents = []

        for file_path in workspace.rglob("*"):
            if not file_path.is_file():
                continue

            # Check if in excluded directory
            if any(excl in file_path.parts for excl in EXCLUDE_DIRS):
                continue

            if file_path.suffix.lower() == ".pdf":
                doc = self._process_pdf(file_path, workspace)
                documents.append(doc)
            elif file_path.suffix.lower() == ".docx":
                doc = self._process_docx(file_path, workspace)
                documents.append(doc)

        self._log(f"Found {len(documents)} documents")
        return documents

    def _process_pdf(self, file_path: Path, workspace: Path) -> DocumentMetadata:
        """Process a PDF file."""
        rel_path = str(file_path.relative_to(workspace))
        doc = DocumentMetadata(
            path=str(file_path),
            rel_path=rel_path,
            file_type="pdf"
        )

        # Try to extract text
        text = self._extract_pdf_text(file_path)
        if text:
            doc.text_extracted = True
            doc.text_length = len(text)
            doc.text_preview = text[:500]
            self._extract_from_text(text, doc)

        # Always extract from filename/path
        self._extract_from_filename(str(file_path), doc)
        self._extract_from_path(rel_path, doc)

        return doc

    def _process_docx(self, file_path: Path, workspace: Path) -> DocumentMetadata:
        """Process a DOCX file (ZIP + XML)."""
        rel_path = str(file_path.relative_to(workspace))
        doc = DocumentMetadata(
            path=str(file_path),
            rel_path=rel_path,
            file_type="docx"
        )

        # Try to extract text from word/document.xml
        text = self._extract_docx_text(file_path)
        if text:
            doc.text_extracted = True
            doc.text_length = len(text)
            doc.text_preview = text[:500]
            self._extract_from_text(text, doc)

        # Always extract from filename/path
        self._extract_from_filename(str(file_path), doc)
        self._extract_from_path(rel_path, doc)

        return doc

    def _extract_pdf_text(self, file_path: Path) -> Optional[str]:
        """Extract text from PDF using pdftotext or return None."""
        if not self.pdftotext_available:
            return None

        try:
            result = subprocess.run(
                ["pdftotext", str(file_path), "-"],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0 and result.stdout:
                return result.stdout
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            self._log(f"Failed to extract PDF {file_path.name}: {e}")

        return None

    def _extract_docx_text(self, file_path: Path) -> Optional[str]:
        """Extract text from DOCX (ZIP with XML)."""
        try:
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                try:
                    xml_content = zip_ref.read("word/document.xml")
                    root = ET.fromstring(xml_content)

                    # Extract all text nodes from word/document.xml
                    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
                    text_elements = root.findall(".//w:t", namespace)

                    text = "".join([elem.text or "" for elem in text_elements])
                    return text if text else None
                except (ET.ParseError, KeyError) as e:
                    self._log(f"Failed to parse DOCX {file_path.name}: {e}")
                    return None
        except zipfile.BadZipFile:
            self._log(f"Bad ZIP file: {file_path.name}")
            return None
        except Exception as e:
            self._log(f"Error extracting DOCX {file_path.name}: {e}")
            return None

    def _extract_from_text(self, text: str, doc: DocumentMetadata):
        """Extract metadata from document content."""
        text_upper = text.upper()

        # Date extraction (generous)
        dates = self._extract_dates_from_text(text)
        doc.dates.extend(dates)

        # Attorney names
        for attorney in ATTORNEYS:
            if attorney.upper() in text_upper:
                doc.attorneys.add(attorney)

        # Document types
        for doc_type in DOCUMENT_TYPES:
            if doc_type.upper() in text_upper:
                doc.document_types.add(doc_type)

        # USCIS forms
        for form in USCIS_FORMS:
            if form.upper() in text_upper:
                doc.document_types.add(form)

        # Docket numbers (patterns like 2025-D143, 2025.4024, etc.)
        dockets = re.findall(r'\d{4}[-.\s](?:D|U|[A-Z])?\d{3,5}', text)
        doc.docket_numbers.update(dockets)

        # USCIS receipt numbers (SRCxxxxxxxx, IOExxxxxxxx)
        receipts = re.findall(r'(?:SRC|IOE)\d{9,10}', text)
        doc.receipt_numbers.update(receipts)

        # Jurisdictions
        for juris in JURISDICTIONS:
            if juris.upper() in text_upper:
                doc.jurisdictions.add(juris)

    def _extract_from_filename(self, filename: str, doc: DocumentMetadata):
        """Extract metadata from filename."""
        name = os.path.basename(filename).upper()

        # Date patterns in filename (YYMMDD, YYYY-MM-DD, MM-DD-YY)
        dates = self._extract_dates_from_text(name)
        doc.dates.extend(dates)

        # Attorney names in filename
        for attorney in ATTORNEYS:
            if attorney.upper() in name:
                doc.attorneys.add(attorney)

        # Document types
        for doc_type in DOCUMENT_TYPES:
            if doc_type.upper() in name:
                doc.document_types.add(doc_type)

    def _extract_from_path(self, rel_path: str, doc: DocumentMetadata):
        """Extract metadata from directory path."""
        path_upper = rel_path.upper()

        # Attorney names in path
        for attorney in ATTORNEYS:
            if attorney.upper() in path_upper:
                doc.attorneys.add(attorney)

        # Document types from path
        for doc_type in DOCUMENT_TYPES:
            if doc_type.upper() in path_upper:
                doc.document_types.add(doc_type)

        # Jurisdictions
        for juris in JURISDICTIONS:
            if juris.upper() in path_upper:
                doc.jurisdictions.add(juris)

    def _extract_dates_from_text(self, text: str) -> List[DateExtraction]:
        """Extract dates from text using multiple patterns."""
        dates = []
        seen_dates = set()

        # YYYY-MM-DD format
        for match in re.finditer(r'(\d{4})[/-](\d{2})[/-](\d{2})', text):
            date_str = f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
            if date_str not in seen_dates and self._is_valid_date(date_str):
                dates.append(DateExtraction(
                    date=date_str,
                    confidence="high",
                    extraction_method="content_extraction",
                    source_text=match.group(0)
                ))
                seen_dates.add(date_str)

        # YYMMDD format (6 digits)
        for match in re.finditer(r'(\d{2})(\d{2})(\d{2})', text):
            yy, mm, dd = match.groups()
            try:
                year = 2000 + int(yy) if int(yy) < 50 else 1900 + int(yy)
                date_str = f"{year}-{mm}-{dd}"
                if date_str not in seen_dates and self._is_valid_date(date_str):
                    dates.append(DateExtraction(
                        date=date_str,
                        confidence="medium",
                        extraction_method="content_extraction",
                        source_text=match.group(0)
                    ))
                    seen_dates.add(date_str)
            except ValueError:
                pass

        # MM-DD-YYYY format
        for match in re.finditer(r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})', text):
            mm, dd, yyyy = match.groups()
            date_str = f"{yyyy}-{mm.zfill(2)}-{dd.zfill(2)}"
            if date_str not in seen_dates and self._is_valid_date(date_str):
                dates.append(DateExtraction(
                    date=date_str,
                    confidence="high",
                    extraction_method="content_extraction",
                    source_text=match.group(0)
                ))
                seen_dates.add(date_str)

        return dates

    @staticmethod
    def _is_valid_date(date_str: str) -> bool:
        """Check if a date string is valid."""
        try:
            parts = date_str.split('-')
            if len(parts) != 3:
                return False
            yyyy, mm, dd = int(parts[0]), int(parts[1]), int(parts[2])
            return 1900 <= yyyy <= 2100 and 1 <= mm <= 12 and 1 <= dd <= 31
        except (ValueError, AttributeError):
            return False


# =============================================================================
# Knowledge Graph Builder
# =============================================================================

class KnowledgeGraphBuilder:
    """Builds structured knowledge graph from document metadata."""

    def __init__(self, documents: List[DocumentMetadata], verbose: bool = False):
        self.documents = documents
        self.verbose = verbose

    def _log(self, msg: str):
        if self.verbose:
            print(f"[builder] {msg}")

    def build_case_facts(self) -> Dict:
        """Build case-facts.json structure."""
        self._log("Building case facts...")

        # Extract unique dates and create timeline
        events = self._build_timeline()

        # Identify parties and attorneys
        parties = self._identify_parties()
        attorneys = self._identify_attorneys()

        # Identify proceedings
        proceedings = self._identify_proceedings()

        # Identify unknowns/gaps
        unknowns = self._identify_unknowns(events, parties, proceedings)

        return {
            "generated": datetime.utcnow().isoformat() + "Z",
            "source_scan": {
                "total_files": len(self.documents),
                "pdfs": sum(1 for d in self.documents if d.file_type == "pdf"),
                "docx": sum(1 for d in self.documents if d.file_type == "docx"),
                "extracted_text": sum(1 for d in self.documents if d.text_extracted)
            },
            "events": events,
            "unknowns": unknowns,
            "parties": {
                "client": parties.get("client", {"name": "Unknown", "identified_from": []}),
                "attorneys": [asdict(a) for a in attorneys],
                "agencies": list(self._extract_agencies())
            },
            "proceedings": [asdict(p) for p in proceedings]
        }

    def build_claims_matrix(self) -> Dict:
        """Build claims-matrix.json structure."""
        self._log("Building claims matrix...")

        claims = []
        claim_id = 1

        # Find complaint documents
        complaint_docs = [d for d in self.documents
                         if "COMPLAINT" in d.document_types]

        for doc in complaint_docs:
            claim = Claim(
                id=f"auto_claim_{claim_id:03d}",
                description=f"Extracted from {doc.rel_path}",
                source_document=doc.rel_path,
                attorneys=list(doc.attorneys)
            )
            claims.append(claim.to_dict())
            claim_id += 1

        return {"claims": claims}

    def build_evidence_links(self) -> Dict:
        """Build evidence-links.json structure."""
        self._log("Building evidence links...")

        links = []
        link_id = 1

        # Find complaint documents and link to other docs
        complaint_docs = {d.rel_path: d for d in self.documents
                         if "COMPLAINT" in d.document_types}

        for claim_path, claim_doc in complaint_docs.items():
            claim_id = f"auto_claim_{link_id:03d}"

            # Find supporting documents (similar attorneys, overlapping dates)
            for doc in self.documents:
                if doc == claim_doc:
                    continue

                confidence = self._calculate_link_confidence(claim_doc, doc)
                if confidence != "low":
                    links.append({
                        "document": doc.rel_path,
                        "claim": claim_id,
                        "prong": "unknown",
                        "argument": f"auto-inferred: shared attorneys or date proximity",
                        "confidence": confidence,
                        "needs_deep_read": True
                    })

            link_id += 1

        return {"links": links}

    def build_bootstrap_report(self) -> str:
        """Build human-readable bootstrap report."""
        self._log("Building bootstrap report...")

        # Extract data
        all_dates = sorted(set(
            d.date for doc in self.documents for d in doc.dates
        ))

        all_attorneys = sorted(set(
            att for doc in self.documents for att in doc.attorneys
        ))

        all_proceedings = set()
        for doc in self.documents:
            all_proceedings.update(doc.docket_numbers)

        complaints = [d for d in self.documents if "COMPLAINT" in d.document_types]
        text_extracted = sum(1 for d in self.documents if d.text_extracted)

        # Build report
        lines = [
            "# Bootstrap Report: Case Knowledge Graph",
            "",
            f"**Generated:** {datetime.utcnow().isoformat()}Z",
            "",
            "## Scan Summary",
            "",
            f"- **Total files:** {len(self.documents)}",
            f"  - PDFs: {sum(1 for d in self.documents if d.file_type == 'pdf')}",
            f"  - DOCXs: {sum(1 for d in self.documents if d.file_type == 'docx')}",
            f"- **Text extracted:** {text_extracted}/{len(self.documents)} documents",
            "",
            "## Timeline",
            "",
            f"**{len(all_dates)} unique dates found** (sorted by confidence):",
            ""
        ]

        # Sort dates by confidence
        date_map = defaultdict(list)
        for doc in self.documents:
            for d in doc.dates:
                date_map[d.date].append((d.confidence, doc.rel_path))

        for date_str in sorted(all_dates):
            entries = date_map[date_str]
            high_conf = [e[1] for e in entries if e[0] == "high"]
            lines.append(f"- **{date_str}** (High: {len(high_conf)} docs)")
            if high_conf:
                for doc_path in high_conf[:3]:
                    lines.append(f"  - {doc_path}")

        lines.extend(["", "## Parties & Attorneys", ""])
        lines.append(f"**{len(all_attorneys)} attorneys identified:**")
        for attorney in all_attorneys:
            count = sum(1 for d in self.documents if attorney in d.attorneys)
            lines.append(f"- {attorney} ({count} documents)")

        lines.extend(["", "## Proceedings", ""])
        if all_proceedings:
            lines.append(f"**{len(all_proceedings)} proceedings found:**")
            for proceeding in sorted(all_proceedings):
                lines.append(f"- {proceeding}")
        else:
            lines.append("No proceedings explicitly identified.")

        lines.extend(["", "## Claims", ""])
        lines.append(f"**{len(complaints)} complaint documents** contain inferred claims:")
        for doc in complaints:
            lines.append(f"- {doc.rel_path}")

        lines.extend(["", "## Gaps & Unknowns", ""])
        lines.append("Key information still needed:")
        lines.append("- Full text review of complaint documents to extract specific allegations")
        lines.append("- Resolution statuses and outcomes for each proceeding")
        lines.append("- Detailed evidence linking documents to specific claims")
        lines.append("- USCIS case tracking (receipt numbers, form types)")
        lines.append("- Timeline of key decisions and objections")

        lines.extend(["", "## Recommended Next Steps", ""])
        lines.append("1. Deep-read all complaint documents in order:")
        for i, doc in enumerate(complaints, 1):
            lines.append(f"   {i}. {doc.rel_path}")
        lines.append("2. Extract specific allegations and organize by attorney")
        lines.append("3. Identify patterns of alleged misconduct")
        lines.append("4. Cross-reference with supporting evidence documents")
        lines.append("5. Build detailed evidence matrix for each claim")

        return "\n".join(lines)

    def _build_timeline(self) -> List[Dict]:
        """Build timeline of events from extracted dates."""
        date_map = defaultdict(lambda: {"docs": [], "confidence": "low"})

        for doc in self.documents:
            for date_ext in doc.dates:
                date_map[date_ext.date]["docs"].append(doc.rel_path)
                if date_ext.confidence == "high":
                    date_map[date_ext.date]["confidence"] = "high"
                elif date_ext.confidence == "medium" and date_map[date_ext.date]["confidence"] != "high":
                    date_map[date_ext.date]["confidence"] = "medium"

        events = []
        for date_str in sorted(date_map.keys()):
            entry = date_map[date_str]
            events.append({
                "date": date_str,
                "description": f"Activity involving {len(entry['docs'])} document(s)",
                "source_documents": entry["docs"],
                "confidence": entry["confidence"],
                "significance": "context",
                "extraction_method": "content_extraction"
            })

        return events

    def _identify_parties(self) -> Dict:
        """Identify parties (client, agencies, etc.)."""
        agencies = self._extract_agencies()

        # Client is typically the plaintiff in complaints
        client = {
            "name": "Unknown Client",
            "identified_from": []
        }

        return {"client": client}

    def _identify_attorneys(self) -> List[Attorney]:
        """Identify all attorneys from documents."""
        attorney_map = defaultdict(set)

        for doc in self.documents:
            for attorney in doc.attorneys:
                attorney_map[attorney].add(doc.rel_path)

        attorneys = []
        jurisdictions_map = {
            "Camargo": "California",
            "Aggarwal": "California",
            "Widmer": "California",
            "Wasung": "California",
            "Rutahweire": "California",
            "Hayman": "California",
            "Woodward": "California"
        }

        for name, docs in attorney_map.items():
            attorneys.append(Attorney(
                name=name,
                jurisdiction=jurisdictions_map.get(name),
                identified_from=list(docs)
            ))

        return attorneys

    def _identify_proceedings(self) -> List[Proceeding]:
        """Identify legal proceedings from documents."""
        proceeding_map = defaultdict(lambda: {"docs": [], "attorneys": set()})

        for doc in self.documents:
            for docket in doc.docket_numbers:
                proceeding_map[docket]["docs"].append(doc.rel_path)
                proceeding_map[docket]["attorneys"].update(doc.attorneys)

        proceedings = []
        for docket, data in proceeding_map.items():
            proc_type = "bar" if any("COMPLAINT" in d for d in data["docs"]) else "court"
            proceedings.append(Proceeding(
                docket=docket,
                jurisdiction="California",
                type=proc_type,
                attorney=list(data["attorneys"])[0] if data["attorneys"] else None,
                identified_from=data["docs"]
            ))

        return proceedings

    def _identify_unknowns(self, events: List[Dict], parties: Dict, proceedings: List) -> List[Dict]:
        """Identify key unknowns and gaps."""
        unknowns = [
            {
                "question": "What are the specific allegations in each complaint?",
                "why_it_matters": "Critical to understanding the claims and structuring the defense.",
                "category": "findable_in_documents",
                "suggested_action": "Deep-read all complaint documents and extract allegations by attorney."
            },
            {
                "question": "What is the current status of each bar complaint?",
                "why_it_matters": "Determines whether defenses are still needed or if closure is possible.",
                "category": "findable_in_documents",
                "suggested_action": "Review receipts, investigation letters, and any final decisions."
            },
            {
                "question": "What evidence proves ineffective assistance of counsel?",
                "why_it_matters": "This is the core claim and requires detailed documentary support.",
                "category": "findable_in_documents",
                "suggested_action": "Map evidence documents to specific allegations."
            },
            {
                "question": "What are the USCIS case details and outcomes?",
                "why_it_matters": "Immigration cases are date-critical and outcomes affect bar allegations.",
                "category": "findable_in_documents",
                "suggested_action": "Extract receipt numbers and track case progression."
            }
        ]

        return unknowns

    def _extract_agencies(self) -> Set[str]:
        """Extract agencies from documents."""
        agencies = set()
        for doc in self.documents:
            if "USCIS" in doc.jurisdictions:
                agencies.add("USCIS")
            if "DC" in doc.jurisdictions:
                agencies.add("US Court (DC)")

        return agencies if agencies else {"USCIS"}

    @staticmethod
    def _calculate_link_confidence(doc1: DocumentMetadata, doc2: DocumentMetadata) -> str:
        """Calculate confidence of link between two documents."""
        shared_attrs = 0
        total_possible = 3

        # Shared attorneys
        if doc1.attorneys & doc2.attorneys:
            shared_attrs += 1

        # Date proximity (within 30 days)
        doc1_dates = {d.date for d in doc1.dates}
        doc2_dates = {d.date for d in doc2.dates}
        if doc1_dates & doc2_dates:
            shared_attrs += 1

        # Shared docket numbers
        if doc1.docket_numbers & doc2.docket_numbers:
            shared_attrs += 1

        if shared_attrs >= 2:
            return "high"
        elif shared_attrs == 1:
            return "medium"
        else:
            return "low"


# =============================================================================
# Main Script
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Bootstrap: scan legal documents and build knowledge graph"
    )
    parser.add_argument(
        "--workspace",
        required=True,
        help="Path to workspace containing legal documents"
    )
    parser.add_argument(
        "--incremental",
        action="store_true",
        help="Only process files not in existing case-facts.json"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print progress to stdout"
    )

    args = parser.parse_args()

    # Verify workspace exists
    workspace = Path(args.workspace)
    if not workspace.exists():
        print(f"ERROR: Workspace not found: {args.workspace}", file=sys.stderr)
        sys.exit(1)

    # Scan documents
    print(f"Scanning workspace: {args.workspace}")
    scanner = DocumentScanner(verbose=args.verbose)
    documents = scanner.scan_workspace(str(workspace))

    if not documents:
        print("No documents found in workspace.")
        sys.exit(1)

    print(f"Found {len(documents)} documents")

    # Build knowledge graph
    builder = KnowledgeGraphBuilder(documents, verbose=args.verbose)

    case_facts = builder.build_case_facts()
    claims_matrix = builder.build_claims_matrix()
    evidence_links = builder.build_evidence_links()
    bootstrap_report = builder.build_bootstrap_report()

    # Determine output directory (parent of scripts dir)
    script_dir = Path(__file__).parent
    output_dir = script_dir.parent

    # Write output files
    case_facts_path = output_dir / "case-facts.json"
    claims_matrix_path = output_dir / "claims-matrix.json"
    evidence_links_path = output_dir / "evidence-links.json"
    report_path = output_dir / "bootstrap-report.md"

    with open(case_facts_path, 'w') as f:
        json.dump(case_facts, f, indent=2)
    print(f"Wrote: {case_facts_path}")

    with open(claims_matrix_path, 'w') as f:
        json.dump(claims_matrix, f, indent=2)
    print(f"Wrote: {claims_matrix_path}")

    with open(evidence_links_path, 'w') as f:
        json.dump(evidence_links, f, indent=2)
    print(f"Wrote: {evidence_links_path}")

    with open(report_path, 'w') as f:
        f.write(bootstrap_report)
    print(f"Wrote: {report_path}")

    print("\nBootstrap complete!")


if __name__ == "__main__":
    main()
