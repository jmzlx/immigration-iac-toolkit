---
name: uscis-immigration-research
description: >
  Researches USCIS policy, INA statutes, CFR regulations, and immigration case law
  for employment-based petitions, adjustment of status, and motions to reopen.
  Provides quick-reference lookups for key statutory provisions and citation
  formatting, plus research strategies for live sources. Triggers on questions about
  immigration law, unlawful presence, §245(k), adjustment of status, EB1-A, EB2-NIW,
  motion to reopen rules, I-485 eligibility, inadmissibility bars, 3/10-year bars,
  consular processing, USCIS policy manual, INA sections, or CFR regulations.
---

# USCIS Immigration Law Research

## What This Skill Adds

Immigration law has domain-specific traps that general legal knowledge misses. This skill provides the statutory map for Julia's case — the exact provisions, how they interconnect, and where the attorneys went wrong. Read `references/key-provisions.md` for the detailed statutory reference.

## Critical Provisions for Julia's Case

These provisions interact in ways that matter. Understanding the chain is essential:

**The Chain of Failure:**
1. Julia's I-94 expired July 22, 2022 → unlawful presence began accruing
2. INA §245(k) excuses ONLY up to 180 days of status violations for EB beneficiaries
3. Julia's attorneys never warned her about this 180-day limit
4. By the time they filed EB1-A + I-485 in July 2024, she had 24+ months of unlawful presence
5. USCIS denied the I-485 citing §245(k) — she far exceeded the 180-day tolerance
6. She now faces inadmissibility bars under INA §212(a)(9)(B)

**Key Statutes** (see `references/key-provisions.md` for full details):

| Provision | What It Does | Julia's Case |
|-----------|-------------|--------------|
| INA §245(k) | Excuses ≤180 days status violations for EB immigrants | Julia had 24+ months — far exceeded |
| INA §212(a)(9)(B) | 3-year bar (>180 days) / 10-year bar (>1 year) | Julia faces 10-year bar |
| INA §245(c) | Bars adjustment for status violations | §245(k) was supposed to be the exception |
| INA §203(b)(1)(A) | EB1-A extraordinary ability | Julia's I-140 APPROVED — proves merit |
| INA §203(b)(2) | EB2-NIW | First petition; denied Aug 2023 |
| 8 CFR §103.5 | Motions to reopen | Basis for IAC motion |
| INA §240(c)(7) | Motions to reopen (removal context) | Cross-reference for Lozada standard |

## Research Workflow

### For Any Immigration Law Question

1. **Check `references/key-provisions.md` first** — it covers the provisions most relevant to Julia's case with accurate analysis
2. **Run the quick-reference script** for citation formatting and statute lookups:
   ```bash
   python scripts/uscis_research.py search-statute "245(k)"
   python scripts/uscis_research.py format-citation ina "245(k)"
   ```
3. **For current information**, use live sources:
   - **WebSearch** with `site:uscis.gov` or `site:ecfr.gov` for current policy
   - **CourtListener skill** for case law and BIA/AAO decisions
   - **WebFetch** to read USCIS Policy Manual pages at `egov.uscis.gov/policy-manual`

### Authoritative Sources (Priority Order)

| Source | URL | Use For |
|--------|-----|---------|
| INA Statutes | uscode.house.gov (Title 8) | Statutory text |
| CFR Regulations | ecfr.gov/current/title-8 | Regulatory implementation |
| USCIS Policy Manual | egov.uscis.gov/policy-manual | Agency guidance |
| AAO Decisions | myuscis.uscis.dhs.gov/case-processing/aao-decisions | Non-precedent decisions |
| BIA/EOIR Decisions | justice.gov/eoir | Precedent appeals |
| Google Scholar | scholar.google.com | Free case law research |

### USCIS Policy Manual — Key Chapters

| Volume | Chapter | Topic |
|--------|---------|-------|
| Vol. 6, Part A, Ch. 2 | EB1-A | Extraordinary ability standard |
| Vol. 6, Part A, Ch. 3 | EB2-NIW | National Interest Waiver (Dhanasar framework) |
| Vol. 7, Part A | Adjustment | I-485 eligibility and requirements |
| Vol. 7, Part B, Ch. 4 | Unlawful Presence | Accrual rules, tolling, bars |
| Vol. 7, Part C, Ch. 1 | §245(k) Exception | 180-day limit for EB immigrants |
| Vol. 12, Ch. 4 | Motions to Reopen | Procedure and Lozada standard |

## Domain-Specific Pitfalls

These are the mistakes that catch people (including Julia's attorneys):

1. **§245(k) does NOT "waive" unlawful presence** — it only excuses ≤180 days of status violations. This is the exact error Julia's attorneys made.

2. **"Portability" does NOT maintain status** — Filing I-485 does not stop unlawful presence accrual if the underlying I-94 has expired.

3. **Precedent vs. non-precedent AAO decisions** — Precedent decisions bind USCIS; non-precedent are persuasive only. Always verify which type you're citing.

4. **INA §245 ≠ 8 CFR §245.1** — The statute and its implementing regulation are different authorities. Both may apply but cite them correctly.

5. **The 30-day MTR window** — Standard motions to reopen must be filed within 30 days of the decision. Julia's I-485 denial was June 26, 2025 — 9 months ago. Research whether IAC-based motions qualify for equitable tolling or sua sponte reopening under 8 CFR §103.5(a)(5)(i).

## Integration

- **Read `references/key-provisions.md`** for complete statutory analysis with Julia's case application
- **Use `case-knowledge/` skill** (if available) for the canonical case timeline and claims matrix
- **Use `courtlistener` skill** for case law research on Lozada, §245(k), and attorney discipline
- **Use `bar-complaint-reply-drafter` skill** for jurisdiction-specific professional conduct rules
