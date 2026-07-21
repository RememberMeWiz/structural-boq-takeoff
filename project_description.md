# Project Description

## Project name
DWG Structural Takeoff Tool (working title)

## Goal
A tool that ingests a structural DWG/DXF CAD drawing and produces a quantity
takeoff — starting with beam schedules (lengths, sizes, counts) — for personal
use in civil engineering work. Built during OpenAI buildweek.

## Context
Built during OpenAI buildweek. Primary motivation is personal utility: speeding
up quantity takeoff work the user (a civil engineer) does regularly. Not
intended to be given away for free — either kept as a private personal tool or
potentially monetized later, not open-sourced.

## Market context (why this is worth building, not just "does it exist")
Researched July 2026. Findings:
- DWG-to-takeoff tools already exist as a category (DesignDrafter, PriMus-TO,
  Civils.ai, PlanSwift + AI plugins), so "reads DWG and outputs quantities" is
  not a novel concept on its own.
- However, most AI takeoff tools are PDF-first, not DWG-native (e.g. PlanSwift
  doesn't process CAD/DWG/DXF natively at all).
- Trade focus in the market is fragmented and skews architectural (Togal.AI)
  or MEP/electrical (Aginera DesignOps) — structural steel/concrete beam
  schedules specifically are a thin, underserved niche.
- Pricing is enterprise-oriented ($175-299/user/month, some $8,000+/year per
  trade) — priced out of reach for a solo engineer or small firm use case.
- No tools found are localized beyond US/UK conventions, units, and cost
  databases.
- "AI takeoff" as a label is inconsistent across the market, with unverified
  vendor accuracy claims — leaves room for a narrower, more honest/reliable
  tool.

**Implication for this project**: even a personal-use MVP sits in a real gap
(DWG-native, structural-specific, low/no infrastructure cost) and could be
extended commercially later without competing head-on with enterprise
incumbents.

## Scope
**In scope (buildweek MVP)**:
- Input: DXF (DWG converted via ODA File Converter as a pre-step)
- Parse structural line/polyline entities per layer using ezdxf
- Use an LLM to semantically classify layers/entities as structural elements
  (beams, etc.) even with inconsistent/messy naming conventions — this is the
  key differentiator vs. rules-engine incumbents
- Output: beam schedule (length, count, grouping) as Excel/CSV

**Stretch goals (if time allows)**:
- Extract member sizes from block attributes/text annotations (e.g. "W12x26"),
  producing a true bill of quantities, not just lengths
- Handle DWG input directly (skip manual DXF conversion step)
- Extend beyond beams to columns, slabs, footings

**Out of scope for now**:
- MEP/electrical/architectural takeoff (leave to existing tools)
- Cost/pricing integration
- Multi-user/collaboration features
- Public release or free distribution

## Key constraints
- Buildweek time limit — MVP must be achievable in days, not weeks
- Solo project (user is the only stakeholder for now)

## Tech stack / tools in use
- Storage: Supabase (bucket: `project-files`)
- DWG→DXF conversion: ODA File Converter
- DXF parsing: ezdxf (Python)
- Layer/entity classification: LLM (model TBD)
- Output: Excel/CSV via a Python library (e.g. openpyxl)

## Stakeholders
Just the user — personal tool, not a team project (for now).

## Success criteria
A real structural DWG drawing can be fed in and produce a usable beam schedule
(lengths, grouped/counted) faster than doing it manually, with reasonable
accuracy on layer classification even without pre-configuring layer names.


---

# Phase 2: Automated Quantity Takeoff & BOQ Generation System

## Overview
This system is designed to automate the process of architectural and structural drawing ingestion (in DWG or vector PDF format), parse their annotations and geometries, perform automated quantity takeoff computations, and consolidate them into a costed **Bill of Quantities (BOQ)**.

The quantity calculations are based on the standard quantity-per-unit factors from **Max Fajardo’s Simplified Construction Estimate**.

### Phase 2 Scope:
1.  **Supported Trades**: 
    *   **Concrete Works** (mix volume derivations for Class A/B/C: cement, sand, gravel).
    *   **Steel Reinforcement** (rebar length-to-weight conversions, tie wire counts).
    *   **Masonry Works** (CHB counts for 100mm/150mm walls, plastering cement/sand factors).
2.  **Takeoff and Costing**:
    *   Geometric volume/area computations.
    *   Regional unit rate application.
    *   Element-level detailing (Back-Up Computations) rolling up to BOQ Checklist summary rows.
3.  **Input Formats**:
    *   DWG files (pre-converted via ODA File Converter CLI to DXF format).
    *   Vector-exported PDF drawings.

### Core Tech Stack:
*   **Database**: Supabase / PostgreSQL (for structured drawing DOM elements, Fajardo factors, and consolidated tables).
*   **CAD Parsers**: Python `ezdxf` + custom extraction logic.
*   **Takeoff Engine**: Python (FastAPI/CLI modules running Fajardo formulas).
*   **Output Export**: `openpyxl` (structured Excel workbooks).

### Database Design (PostgreSQL/Supabase)
The database structure is designed to hold:
1.  **Projects and Drawings**: Meta records tracing drawings back to their respective sheets and scale factors.
2.  **Drawing Object Model (DOM)**: Individual extracted geometric entities (`drawing_elements`) with their labels, concrete classes, and rebar details.
3.  **Fajardo Factors Table**: A reference table defining material/labor ratios per unit for each trade.
4.  **Consolidated BOQ Tables**: 
    *   `backup_computations`: Full element-level detail (matching drawing reference tags and raw dimensions).
    *   `boq_checklist`: High-level rolled-up items (matching the Bill of Quantities summaries).
