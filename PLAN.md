# Onshape MCP Tooling — Scalability & Robustness Plan

> **Status:** Approved (2026-04-07)
> **Revision:** Phase 4 updated — onboarding prompt + README for repo transfer

---

## Current State Summary

The tooling works but has grown organically. Key stats:
- **1 MCP server** with 21 tools + embedded API client (~1757 lines, monolithic)
- **1 shared API client** (`onshape_api.py`) for CLI scripts — **duplicates** the MCP server's client
- **4 CLI scripts** (BOM extract, STEP/PDF export, variable sync, metadata editing)
- **3 registered documents** in YAML registry
- **Single-user** credentials via `.env`

## Problems to Solve

| # | Problem | Impact |
|---|---------|--------|
| P1 | Duplicated API client — MCP server has its own `OnshapeClient` overlapping with `onshape_api.py` | Bug fixes must be applied twice |
| P2 | MCP server monolithic — 1757-line single file | Hard to navigate, extend, review |
| P3 | No export MCP tools — STEP/PDF export is CLI-only | Copilot can't trigger exports |
| P4 | Drawing matching is fragile — name-based fuzzy matching | Wrong drawing exported |
| P5 | Limited registry — 3 docs, no workspace variants | Can't track branches/versions |
| P6 | Single-user setup — no onboarding path for colleagues | Not transferable to a team |
| P7 | No CLI entry point — each script is separate | Harder to discover |

---

## Phase 1: Unify the API Client ✅ COMPLETED

**Goal:** Single source of truth for all Onshape API calls.

- ✅ Merged MCP server's embedded `OnshapeClient` into shared `onshape_api.py` (12 methods added)
- ✅ MCP server imports from `onshape_api.py` — embedded client removed (~500 lines)
- ✅ `set_variables` return type unified (dict); `sync_variables.py` updated for compatibility
- ✅ All scripts verified: `onshape_mcp_server.py`, `export_parts.py`, `sync_variables.py` import cleanly

**Result:** `onshape_api.py` ~500 lines; MCP server reduced from ~1757 to ~1250 lines.

---

## Phase 2: Add Export Tools to MCP Server ✅ COMPLETED

**Goal:** Copilot can trigger STEP + PDF exports.

- ✅ Added `onshape_export_step` tool (Part Studio → STEP file with polling)
- ✅ Added `onshape_export_drawing_pdf` tool (Drawing → PDF file with polling)
- ✅ Both reuse `start_translation`, `poll_translation`, `download_external_data` from shared client
- ✅ Output directory auto-created; file size reported on success

**Result:** 23 total MCP tools. Full parity CLI ↔ MCP for exports.

---

## Phase 3: Improve Registry & Drawing Matching ✅ COMPLETED

### 3a. Enhanced Document Registry

- ✅ `get_document_ids()` supports both flat and multi-workspace YAML formats
- ✅ Optional `workspace` parameter to select specific workspace
- ✅ Falls back to `default_workspace`, then first workspace
- ✅ `list_documents()` shows workspace info
- ✅ Backward-compatible — existing flat entries work unchanged

### 3b. Drawing-to-Part Mapping

- ✅ `drawing_map` field added to YAML registry (EH-0080-BB1 P-0017 mapped)
- ✅ `get_drawing_map()` function added to `document_registry.py`
- ✅ `export_parts.py` checks `drawing_map` first, falls back to fuzzy matching
- ✅ All modules import cleanly

---

## Phase 4: Onboarding & Repo Transfer ✅ COMPLETED

**Goal:** Make the folder transferable to a standalone repo that colleagues can clone and set up independently.

- ✅ `README.md` updated: standalone onboarding callout, export tools in API reference, drawing map docs
- ✅ `.github/prompts/setup-onshape.prompt.md` created: 6-step interactive wizard (API keys → .env → install → test → register doc → VS Code MCP)
- ✅ `.gitignore` created: excludes `.env`, `__pycache__/`, `*.step`, `*.pdf`, IDE folders
- ✅ `.env.example` already existed with clear instructions

**Key principle:** Everyone creates their own Onshape API keys. No shared credentials.

---

## Phase 5: Unified CLI Entry Point ✅ COMPLETED

**Goal:** Single `onshape` command for all operations.

- ✅ `cli.py` created with subcommands: `bom`, `export`, `vars`, `meta`, `check`, `docs`, `server`
- ✅ `pyproject.toml` updated: `onshape = "cli:main"` console script added
- ✅ Each subcommand delegates to existing script's `main()` (no code duplication)
- ✅ Help text shown when no command provided

---

## Implementation Priority

| Phase | Effort | Impact | Order |
|-------|--------|--------|-------|
| Phase 1: Unify API client | Medium | High | **1st** |
| Phase 2: Export MCP tools | Small | Medium | **2nd** |
| Phase 3: Registry + drawing map | Small | High | **3rd** |
| Phase 4: Onboarding + repo transfer | Medium | High | **4th** |
| Phase 5: Unified CLI | Small | Low | **5th** |

## What Doesn't Change

- `.env` credential pattern (backward-compatible)
- Existing CLI script interfaces
- MCP tool names and parameters
- `constants.py`
- `pyproject.toml` dependencies
