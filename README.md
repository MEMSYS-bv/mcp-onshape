# Onshape MCP Server

An MCP (Model Context Protocol) server that integrates Onshape with GitHub Copilot, plus standalone CLI tools for BOM extraction, STEP/PDF export, variable sync, and part metadata management.

> **New here?** Run `#setup-onshape` in Copilot Chat for an interactive setup wizard, or follow the [Setup](#setup) section below.

## Architecture

```
mcp-onshape/
├── cli.py                  # Unified CLI entry point (bom, export, vars, meta, check, docs)
├── constants.py            # Shared constants (header IDs, template refs, etc.)
├── document_registry.py    # YAML registry lookup + URL parsing
├── onshape_api.py          # Shared OnshapeClient class
├── onshape_documents.yaml  # Document registry (project code → doc IDs)
├── onshape_mcp_server.py   # MCP server (23 tools for Copilot)
├── extract_bom.py          # CLI: BOM extraction
├── export_parts.py         # CLI: STEP + PDF export
├── sync_variables.py       # CLI: Variable Studio ↔ CSV sync
├── set_part_metadata.py    # CLI: Part number / name / description
├── test_connection.py      # CLI: API connectivity test
├── pyproject.toml           # Package definition
├── .env                     # API keys (git-ignored)
├── .env.example             # Template for .env
├── .gitignore               # Git ignore rules
└── .github/prompts/
    └── setup-onshape.prompt.md  # AI-guided setup wizard
```

### Shared Modules

| Module | Purpose |
|--------|---------|
| `constants.py` | BOM header IDs, metadata property IDs, MEMSYS template refs, material library ref, variable type maps |
| `document_registry.py` | `load_documents()`, `get_document_ids()`, `get_drawing_map()`, `list_documents()`, `parse_onshape_url()` — all from `onshape_documents.yaml` |
| `onshape_api.py` | `OnshapeClient` class — auth, requests, document/parts/variables/BOM/drawing/translation/feature/search API methods |

All CLI scripts and the MCP server import from these modules. No duplicate API client or registry code.

### Credential Handling

All scripts load credentials from `.env` via `python-dotenv`:
- `ONSHAPE_ACCESS_KEY` — basic auth access key
- `ONSHAPE_SECRET_KEY` — basic auth secret key
- `ONSHAPE_BASE_URL` — defaults to `https://cad.onshape.com`

The `OnshapeClient` accepts optional `access_key`/`secret_key` constructor args, falling back to env vars.

### Document Identification

Scripts identify Onshape documents via (in order of preference):
1. **Project code** arg → looked up in `onshape_documents.yaml`
2. **`--url`** arg → parsed with regex to extract `did/wid/eid`
3. **`--did`/`--wid`** args → direct IDs

## Features

- **Read/Write Variables**: Get and set variables from any Variable Studio
- **BOM Extraction**: Extract Bill of Materials from any registered assembly
- **Drawing Creation**: Create drawings from MEMSYS templates
- **STEP/PDF Export**: Export parts as STEP files and drawings as PDFs via MCP or CLI
- **Parse URLs**: Extract document/workspace/element IDs from Onshape URLs
- **Document Registry**: YAML-based registry linking project codes to OnShape documents
- **Document Discovery**: Search across your Onshape account, get full document summaries
- **Feature Inspection**: Read Part Studio feature trees (sketches, extrudes, etc.)
- **Assembly Analysis**: Get full assembly definition with instances, mates, and sub-assemblies
- **Material Management**: List 189 materials from the Onshape library, set materials on parts

## Quick Start: Extract a BOM

```bash
# Unified CLI:
python cli.py bom EH-0080-BB1
python cli.py export EH-0080-BB1 --parts P-0016
python cli.py docs
python cli.py check

# Or use individual scripts directly:
python extract_bom.py HM-0070-EWS-V02

# By direct OnShape URL:
python extract_bom.py --url "https://cad.onshape.com/documents/{did}/w/{wid}/e/{eid}"

# List all registered documents:
python extract_bom.py --list

# Output as JSON instead of markdown:
python extract_bom.py EH-0080-BB1 --format json
```

## CLI Tools

### `extract_bom.py` — BOM Extraction

```bash
python extract_bom.py EH-0080-BB1                          # by project code
python extract_bom.py --url "https://..."                   # by URL
python extract_bom.py EH-0080-BB1 --format json             # JSON output
python extract_bom.py --list                                # list documents
```

### `export_parts.py` — STEP + Drawing PDF Export

```bash
python export_parts.py EH-0080-BB1 --parts EH-00800-P-0016 EH-00800-P-0017
python export_parts.py --url "https://..." --parts P-0016 -o ./exports
python export_parts.py --list                               # list documents
```

Naming convention: `${partNumber}_Rev${revision}-${name}.step|pdf`

### `sync_variables.py` — Variable Studio ↔ CSV Sync

```bash
python sync_variables.py EH-0080-BB2 --list                 # list Variable Studios
python sync_variables.py EH-0080-BB2 --get                  # show variables
python sync_variables.py EH-0080-BB2 --export backup.csv    # export to CSV
python sync_variables.py EH-0080-BB2 --diff vars.csv        # compare CSV vs OnShape
python sync_variables.py EH-0080-BB2 --push vars.csv        # push CSV to OnShape
python sync_variables.py EH-0080-BB2 --push vars.csv --dry-run
```

### `set_part_metadata.py` — Part Number / Name / Description

```bash
python set_part_metadata.py EH-0080-BB2 --list              # list parts
python set_part_metadata.py EH-0080-BB2 \
    --set Baseplate part_number=EH-0081-P-0001 description="Machined part"
python set_part_metadata.py EH-0080-BB2 --parts updates.json
python set_part_metadata.py EH-0080-BB2 --dry-run --set ...
```

### `test_connection.py` — API Connectivity Test

```bash
python test_connection.py                                   # test first registered doc
python test_connection.py EH-0080-BB1                       # test specific document
```

## Document Registry

All OnShape documents are registered in **`onshape_documents.yaml`**. This is the single source of truth linking project codes to OnShape document IDs.

```yaml
documents:
  EH-0080-BB1:
    name: "EH-0080 BB-1 Baseline Build"
    document_id: "c705694c548ad1e1a3837a92"
    workspace_id: "d8f69209bc4c52c8d25a4faf"
    element_id: "877dd04a8541e6360716d72d"
    url: "https://cad.onshape.com/..."
    # Optional: explicit drawing element IDs (overrides fuzzy name matching)
    drawing_map:
      EH-00800-P-0017: "81cbdd9ac479633d89c2d855"
```

### Adding a New Document

1. Open the OnShape assembly in your browser
2. Copy the URL
3. Add an entry to `onshape_documents.yaml`:
   ```yaml
   MY-PROJECT:
     name: "My Project Assembly"
     description: "Brief description"
     document_id: "{did from URL}"
     workspace_id: "{wid from URL}"
     element_id: "{eid from URL}"
     url: "https://cad.onshape.com/documents/{did}/w/{wid}/e/{eid}"
   ```
4. Verify: `python extract_bom.py MY-PROJECT`

## Setup

### 1. Get Onshape API Keys

1. Go to https://cad.onshape.com/appstore/dev-portal
2. Click **API keys** → **Create new API key**
3. Select permissions:
   - ✅ Application can read your documents
   - ✅ Application can write to your documents
4. Save both the **Access Key** and **Secret Key**

### 2. Set Environment Variables

Create a `.env` file or set these environment variables:

```bash
ONSHAPE_ACCESS_KEY=your_access_key_here
ONSHAPE_SECRET_KEY=your_secret_key_here
```

### 3. Install Dependencies

```bash
cd src/mcp-onshape
pip install -e .
```

This installs: `mcp`, `requests`, `pyyaml`, `python-dotenv`

### 4. Configure VS Code

Add to your VS Code settings (`.vscode/mcp.json`):

```json
{
  "servers": {
    "onshape": {
      "type": "stdio",
      "command": "python",
      "args": ["${workspaceFolder}/src/mcp-onshape/onshape_mcp_server.py"],
      "env": {
        "ONSHAPE_ACCESS_KEY": "your_access_key",
        "ONSHAPE_SECRET_KEY": "your_secret_key"
      }
    }
  }
}
```

## Usage

Once configured, you can ask Copilot things like:

- "Get the variables from my Onshape document [paste URL]"
- "Set the length variable to 50 mm"
- "List all Variable Studios in document abc123"
- "Parse this Onshape URL: [paste URL]"
- "Search for my BB-2 document in Onshape"
- "Show me all Part Studios in this document"
- "What features does this Part Studio have?"
- "Show the assembly structure of BB-1"

## API Reference

### Tools (23 total)

#### Document Discovery

| Tool | Description |
|------|-------------|
| `onshape_get_document` | Get document info by ID |
| `onshape_search_documents` | Search for documents by name across your Onshape account |
| `onshape_get_document_summary` | Get comprehensive document summary: all workspaces + elements |
| `onshape_parse_url` | Parse Onshape URL to IDs |

#### Variable Studio

| Tool | Description |
|------|-------------|
| `onshape_list_variable_studios` | List all Variable Studios |
| `onshape_get_variables` | Read all variables |
| `onshape_set_variable` | Set a single variable |
| `onshape_set_multiple_variables` | Set multiple variables at once |

#### Parts & Features

| Tool | Description |
|------|-------------|
| `onshape_get_parts` | Get all parts in a Part Studio or Assembly |
| `onshape_find_part_studios` | Find Part Studios by name pattern |
| `onshape_get_features` | Get Part Studio feature tree (sketches, extrudes, etc.) |

#### Assembly & BOM

| Tool | Description |
|------|-------------|
| `onshape_get_bom` | Get Bill of Materials (part numbers, names, qty, materials, masses) |
| `onshape_get_assembly_definition` | Get assembly structure (instances, mates, sub-assemblies) |

#### Material

| Tool | Description |
|------|-------------|
| `onshape_list_materials` | List available materials (189 total), filter by category or name |
| `onshape_set_part_material` | Set material on a part (validates against the Onshape Material Library) |

#### Drawing

| Tool | Description |
|------|-------------|
| `onshape_list_templates` | List available MEMSYS drawing templates |
| `onshape_list_drawings` | List all drawings in a document |
| `onshape_create_drawing` | Create drawing from MEMSYS template |
| `onshape_create_complete_drawing` | Create drawing with title + drawing number notes |
| `onshape_get_drawing_views` | Get all views in a drawing |
| `onshape_add_view` | Add a view to a drawing |
| `onshape_add_note` | Add text annotation to a drawing |

#### Export

| Tool | Description |
|------|-------------|
| `onshape_export_step` | Export a part as STEP file (async translation + download) |
| `onshape_export_drawing_pdf` | Export a drawing as PDF file (async translation + download) |

### Understanding Onshape URLs

```
https://cad.onshape.com/documents/{did}/w/{wid}/e/{eid}
                                  ↑       ↑       ↑
                              Document  Workspace  Element
```

- **Document ID (did)**: Unique ID for the document
- **Workspace ID (wid)**: The workspace/branch you're working in
- **Element ID (eid)**: The specific tab (Variable Studio, Part Studio, etc.)

## Troubleshooting

### "API keys not set"
Make sure `ONSHAPE_ACCESS_KEY` and `ONSHAPE_SECRET_KEY` are set correctly.

### "403 Forbidden"
Check that your API keys have read/write permissions enabled.

### "404 Not Found"
Verify the document/workspace/element IDs are correct. Use `onshape_parse_url` to extract them from a URL.

## File Structure

```
src/mcp-onshape/
├── onshape_mcp_server.py     # MCP server (runs in VS Code via Copilot)
├── extract_bom.py            # Generic BOM extraction script (CLI)
├── create_all_drawings.py    # Batch drawing creation script
├── restore_variables.py      # Variable restore utility
├── onshape_documents.yaml    # Document registry (project code → OnShape IDs)
├── .env                      # API credentials (not committed)
├── .env.example              # Template for .env
├── pyproject.toml            # Package config + dependencies
└── README.md                 # This file
```

## Workflow: Using OnShape Data in Documentation

1. **Register the document** in `onshape_documents.yaml` (one-time per project)
2. **Extract BOM**: `python extract_bom.py PROJECT-CODE`
3. **Copy markdown output** into your design documentation (Section 4: Hardware Design)
4. **Re-extract** whenever the CAD model changes to keep docs in sync
