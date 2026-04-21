# Changelog

## 2026-04-23 — Design Guide Alignment (Phases 1–6)

Aligned `mcp-onshape` tooling with the MEMSYS OnShape Design Guide. Based on
the implementation plan in `energy-harvesting-team-notes/3. Notes/Cycle 4/2026.04.16 - Analysis - OnShape Design Guide Comments.md`.

### Phase 1 — Revision Model

- Created `revision.py` with canonical revision format: `Rev0.1`, `RevA`, `RevA.1`, `RevB`
- Functions: `is_valid_revision()`, `normalize_revision()`, `parse_revision()`, `suggest_next_revision()`, `format_for_filename()`
- Loose inputs (`A`, `0.1`) auto-normalized to canonical form

### Phase 2 — Extended Metadata Support

- Extended `set_part_metadata.py` to support `revision` field (with validation)
- Added `--validate` mode for export readiness checking
- Added `--list` with readiness indicators (✓/✗) showing missing fields
- Material display in part listings

### Phase 3 — Drawing Matching

- Added `match_drawing_by_part_number()` as primary lookup strategy (exact `{PartNumber} Drawing`)
- `drawing_map` in registry as highest-priority override
- Fuzzy name matching retained as fallback for legacy documents
- Fixed double-prefix in export filenames (`_RevRevA-` → `_RevA-`)

### Phase 4 — Compliance Checker

- Created `compliance_checker.py` (standalone CLI + MCP tool `onshape_check_compliance`)
- Checks: metadata completeness, revision validity, drawing naming, default part names, registry completeness
- Human-readable terminal report + JSON output (`--json`)
- Non-zero exit on blocking errors
- Added `check-compliance` command to `cli.py`

### Phase 5 — Guided Version Creation

- Updated `create_version.py` with `--working`, `--release`, `--suggest` flags
- Auto-generates next revision name from existing versions
- Added `onshape_suggest_version` MCP tool
- Updated `onshape_create_version` MCP tool with optional `mode` parameter

### Phase 6 — Documentation & Tests

- Updated `README.md`: architecture diagram, 35 tools, revision model section, new CLI docs
- Updated `ARCHITECTURE.md`: current tool count, resolved known issues, new modules
- Created `test_revision.py` with 58 tests (validation, normalization, parsing, suggestion, filename formatting)

### Tool Count

MCP tools increased from 32 to 35:
- `onshape_suggest_version` (new)
- `onshape_check_compliance` (new)
- `onshape_create_version` (updated with guided mode)

---

## 2026-04-09 — Version Management

- Created `create_version.py` for creating/listing document versions
- Registered LAB-EMI-SHIELD-BENDER in document registry

## 2026-04-07 — Feature Building & Testing

- Added `onshape_create_document`, `onshape_delete_document` MCP tools
- Added feature creation tools (sketch, extrude, cylinder)
- Created `test_api.py` comprehensive test suite (15 tests)
- Added `cli.py create` and `cli.py cylinder` commands

## 2026-03-xx — BOM Extended Columns

- Added `--extended` flag to BOM extraction with standard columns
