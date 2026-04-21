# Onshape MCP Tooling — Architecture Overview

> **Purpose:** Technical reference for the Onshape integration tooling.
> Intended audience: developers (human + AI) working on or extending this tooling.
> **Last updated:** 2026-04-23

---

## What This Tooling Does

Connects Onshape CAD (cloud-based) to local development workflows:
- **MCP Server** — Exposes 35 Onshape tools to GitHub Copilot via Model Context Protocol
- **CLI Scripts** — Standalone tools for BOM extraction, variable sync, STEP/PDF export, metadata management, compliance checking, version creation
- **Document Registry** — YAML-based mapping of project codes → Onshape document IDs
- **Revision Model** — Canonical revision format (Rev0.1, RevA, RevA.1, RevB) shared across all tools

---

## Directory Structure

```
mcp-onshape/
├── onshape_mcp_server.py   # MCP server (35 tools) — runs as stdio process for VS Code
├── onshape_api.py          # Shared API client class (OnshapeClient)
├── constants.py            # Onshape metadata IDs, templates, material library refs
├── document_registry.py    # YAML loader + URL parser for document lookup
├── onshape_documents.yaml  # Project code → Onshape document ID registry
├── revision.py             # Canonical revision model (validation, normalization, suggestions)
│
├── cli.py                  # Unified CLI entry point
├── extract_bom.py          # CLI: Extract Bill of Materials from assemblies
├── export_parts.py         # CLI: Export parts as STEP + drawings as PDF
├── sync_variables.py       # CLI: Bidirectional CSV ↔ Onshape variable sync
├── set_part_metadata.py    # CLI: Part metadata (number, name, description, revision)
├── create_version.py       # CLI: Version creation with guided naming
├── compliance_checker.py   # CLI: Design guide compliance checker
├── test_connection.py      # CLI: Quick API health check
│
├── test_api.py             # Comprehensive API test suite (15 tests)
├── test_revision.py        # Revision model tests (58 tests)
│
├── .env                    # Onshape API credentials (ONSHAPE_ACCESS_KEY, ONSHAPE_SECRET_KEY)
├── .env.example            # Template for credentials
├── pyproject.toml          # Package config
└── README.md               # User-facing documentation
```

---

## How It Works

### Authentication

All scripts and the MCP server use **HTTP Basic Auth** with Onshape API keys:

```
ONSHAPE_ACCESS_KEY=<from Onshape Dev Portal>
ONSHAPE_SECRET_KEY=<from Onshape Dev Portal>
```

Keys are loaded from `.env` via `python-dotenv`. Never hardcoded.

### Document Identification (3 methods, priority order)

1. **Project code** → lookup in `onshape_documents.yaml` (e.g. `EH-0080-BB1`)
2. **Direct URL** → regex-parsed to extract `document_id/workspace_id/element_id`
3. **Explicit IDs** → `--did`, `--wid` CLI arguments

### API Client

- **`onshape_api.py`** — `OnshapeClient` class used by all CLI scripts
- **`onshape_mcp_server.py`** — has its own embedded `OnshapeClient` (duplicated, see [Known Issues](#known-issues))
- All calls go to Onshape REST API v10 at `https://cad.onshape.com/api/v10/`

### Onshape URL Anatomy

```
https://cad.onshape.com/documents/{did}/w/{wid}/e/{eid}
                                  │       │       │
                              Document  Workspace  Element (tab)
```

- **Document**: Container for all design data
- **Workspace**: A branch (like git branches)
- **Element**: A tab — Part Studio, Assembly, Drawing, Variable Studio, etc.

---

## Component Details

### MCP Server (`onshape_mcp_server.py`, ~1757 lines)

Runs as a stdio MCP server for VS Code/GitHub Copilot. Provides 35 tools:

| Category | Tools | Description |
|----------|-------|-------------|
| **Document** | `onshape_get_document`, `onshape_search_documents`, `onshape_get_document_summary`, `onshape_parse_url`, `onshape_create_document`, `onshape_delete_document` | Find, inspect, create, and navigate documents |
| **Variables** | `onshape_list_variable_studios`, `onshape_get_variables`, `onshape_set_variable`, `onshape_set_multiple_variables` | Read/write Variable Studio values |
| **Parts & Features** | `onshape_get_parts`, `onshape_find_part_studios`, `onshape_get_features`, `onshape_add_feature`, `onshape_add_sketch_circle`, `onshape_add_sketch_rectangle`, `onshape_add_extrude`, `onshape_create_cylinder`, `onshape_delete_feature` | Inspect and modify Part Studios |
| **Assembly & BOM** | `onshape_get_bom`, `onshape_get_assembly_definition` | BOM extraction and assembly structure |
| **Materials** | `onshape_list_materials`, `onshape_set_part_material` | Browse 189 materials, set on parts |
| **Drawings** | `onshape_list_templates`, `onshape_list_drawings`, `onshape_create_drawing`, `onshape_create_complete_drawing`, `onshape_get_drawing_views`, `onshape_add_view`, `onshape_add_note` | Create and modify engineering drawings |
| **Export** | `onshape_export_step`, `onshape_export_drawing_pdf` | Export parts as STEP, drawings as PDF |
| **Version** | `onshape_create_version`, `onshape_suggest_version`, `onshape_list_versions` | Guided version creation with revision suggestions |
| **Import** | `onshape_import_file`, `onshape_import_file_and_wait`, `onshape_list_translation_formats` | Import CAD files (STEP, IGES, etc.) |
| **Compliance** | `onshape_check_compliance` | Design guide preflight check |

### CLI Scripts

| Script | Purpose | Key Commands |
|--------|---------|--------------|
| `extract_bom.py` | Export BOM to markdown/JSON | `python extract_bom.py EH-0080-BB1` |
| `export_parts.py` | Export STEP + drawing PDFs | `python export_parts.py EH-0080-BB1 --parts P-0016 P-0017 -o ./out` |
| `sync_variables.py` | CSV ↔ Onshape variable sync | `python sync_variables.py EH-0080-BB1 --export vars.csv` |
| `set_part_metadata.py` | Part metadata (incl. revision) | `python set_part_metadata.py EH-0080-BB2 --list` |
| `create_version.py` | Guided version creation | `python create_version.py EH-0080-BB1 --working` |
| `compliance_checker.py` | Design guide compliance | `python compliance_checker.py EH-0080-BB1` |
| `test_connection.py` | API connectivity check | `python test_connection.py` |

### Shared Modules

| Module | Purpose |
|--------|---------|
| `onshape_api.py` | `OnshapeClient` class with methods for documents, parts, variables, BOM, assembly, drawings, translation, features, search |
| `constants.py` | Onshape standard IDs (BOM headers, metadata properties), MEMSYS drawing templates, material library reference, variable type mappings |
| `document_registry.py` | Load `onshape_documents.yaml`, resolve project codes, parse URLs |
| `revision.py` | Canonical revision model — `is_valid_revision()`, `normalize_revision()`, `suggest_next_revision()`, `format_for_filename()`, `parse_revision()` |

### Document Registry (`onshape_documents.yaml`)

Currently registered (3 documents):

| Code | Document | Purpose |
|------|----------|---------|
| `EH-0080-BB1` | EH-0080 BB-1 Baseline Build | Energy harvester baseline prototype |
| `EH-0080-BB2` | EH-0080 BB-2 Compact Tunable | Compact tunable harvester concept |
| `HM-0070-EWS-V02` | HM-0070 V0.2 (detail design) | EWS V0.2 vibration sensor |

---

## Known Issues

1. **Duplicated API Client** — The MCP server embeds its own `OnshapeClient` that overlaps with `onshape_api.py`. They have diverged: the MCP version has drawing creation, material management, and template logic that the shared version lacks.

2. ~~**Drawing-to-Part Matching**~~ — **Resolved.** Primary match is now exact `{PartNumber} Drawing`, with `drawing_map` override and fuzzy fallback for legacy documents.

3. ~~**No Export MCP Tools**~~ — **Resolved.** `onshape_export_step` and `onshape_export_drawing_pdf` now available as MCP tools.

4. **Single-User Credentials** — One `.env` file with one set of API keys. No multi-user support.

5. ~~**Registry Limited**~~ — **Partially resolved.** Multi-workspace format supported. Still limited document count.

6. **MCP Server Monolithic** — Large single file (tool definitions + handlers + client + boilerplate).

7. **OnShape-side export UX** — No OnShape app/button to store exported files back into the CAD document. Long-term goal.

---

## Dependencies

- Python ≥ 3.10
- `mcp >= 1.0.0` — Model Context Protocol SDK
- `requests >= 2.31.0` — HTTP client
- `pyyaml >= 6.0` — YAML parsing
- `python-dotenv >= 1.0.0` — .env file loading

Install: `pip install -e .` from this directory.

---

## VS Code Integration

MCP server is configured in `.vscode/mcp.json`:

```json
{
  "servers": {
    "onshape": {
      "type": "stdio",
      "command": "python",
      "args": ["${workspaceFolder}/src/mcp-onshape/onshape_mcp_server.py"],
      "env": {
        "ONSHAPE_ACCESS_KEY": "...",
        "ONSHAPE_SECRET_KEY": "..."
      }
    }
  }
}
```

---

## Onshape API Reference

- **Base URL:** `https://cad.onshape.com/api/v10/`
- **Auth:** HTTP Basic (Access Key + Secret Key)
- **API Explorer:** https://cad.onshape.com/glassworks/explorer/
- **Key endpoints used:**
  - `/documents/` — Document CRUD and search
  - `/parts/` — Part metadata
  - `/variables/` — Variable Studio read/write
  - `/assemblies/` — BOM and assembly definition
  - `/drawings/` — Drawing creation and manipulation
  - `/partstudios/` — Features and translation (export)
  - `/translations/` — Async export status polling
  - `/metadata/` — Part metadata (name, description, revision)
