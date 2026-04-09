---
marp: true
theme: memsys
paginate: true
size: 16:9
footer: "MEMSYS B.V. - For intended recipients only"
---

<!-- _class: title -->

# Onshape MCP Tooling

## CAD Integration for GitHub Copilot

<div class="title-date">2026</div>
<div class="title-author">MEMSYS — Energy Harvesting Team</div>

---

<!-- _class: section -->

# What can it do?

## From chat to CAD — and back

---

## Talk to your CAD model

Ask Copilot questions about your Onshape documents:

- "What variables are in BB-2?"
- "Show me the BOM for the BB-1V3"
- "What material is the baseplate?"

Copilot reads directly from Onshape — no copy-paste needed.

---

## Modify your design

Push changes from chat:

- "Set the beam length to 45 mm"
- "Change the baseplate material to Aluminum 6061"
- "Update all three stiffness variables at once"
- "Assign the following numbers, names and materials to the parts"

Changes appear in Onshape immediately.

---

## Export files

Generate deliverables without leaving the editor:

- "Export the linear guide frame as STEP"
- "Download the drawing for P-0017 as PDF"
- "Export all custom made parts as steps and drawings" 

Files are saved locally with proper naming conventions.

---

## Inspect and explore

Understand your assembly structure:

- "List all Part Studios in this document"
- "Show the feature tree for the main studio"
- "What mates hold the assembly together?"

Full read access to the Onshape document model.

---

<!-- _class: section -->

# How does it work?

## Architecture overview

---

## The MCP Protocol

```
┌─────────────┐     MCP (stdio)     ┌──────────────────┐     REST API     ┌──────────┐
│   Copilot   │ ◄═════════════════► │  MCP Server (py) │ ◄══════════════► │ Onshape  │
│  (VS Code)  │   tool calls +      │  23 tools        │   authenticated  │  Cloud   │
│             │   text responses     │                  │   HTTP requests  │          │
└─────────────┘                      └──────────────────┘                  └──────────┘
```

Copilot sends tool calls → Server translates to API requests → Returns formatted results.

---

## 23 tools in 7 categories

| Category | Tools | Examples |
|----------|-------|---------|
| **Document** | 4 | Get info, search, parse URLs |
| **Variables** | 4 | List, read, write, bulk update |
| **Parts** | 3 | List parts, find studios, features |
| **Assembly** | 2 | BOM, assembly definition |
| **Drawing** | 7 | Create, add views, annotate |
| **Material** | 2 | Browse library, set material |
| **Export** | 2 | STEP files, PDF drawings |

---

## CLI tools included

Same API client powers standalone scripts:

| Command | What it does |
|---------|-------------|
| `cli.py bom` | Extract Bill of Materials |
| `cli.py export` | STEP + PDF export |
| `cli.py vars` | Sync variables to/from CSV |
| `cli.py meta` | Set part numbers and names |
| `cli.py check` | Test API connectivity |
| `cli.py docs` | List registered documents |

---

<!-- _class: section -->

# How to set up

## 4 steps to get started

---

## Step 1 — Get API keys

1. Go to **cad.onshape.com/appstore/dev-portal**
2. Create a new API key
3. Enable read + write permissions
4. Save both keys — the secret is shown only once

---

## Step 2 — Configure credentials

Copy the template and fill in your keys:

```
cp .env.example .env
```

```env
ONSHAPE_ACCESS_KEY=on_your_key_here
ONSHAPE_SECRET_KEY=your_secret_here
```

Each team member uses their own keys.

---

## Step 3 — Install and test

```bash
pip install -e .
python cli.py check
```

Expected output:

```
Testing connection with 'EH-0080-BB1'...
  Document: EH-0080 BB-1 concept
  Connection OK!
```

---

## Step 4 — Connect to Copilot

Add to your VS Code MCP settings:

```json
{
  "servers": {
    "onshape": {
      "type": "stdio",
      "command": "python",
      "args": ["path/to/onshape_mcp_server.py"]
    }
  }
}
```

Or run `#setup-onshape` in Copilot Chat for guided setup.

---

<!-- _class: section -->

# What's next?

## Future ideas

---

## Planned improvements

- **Multi-workspace support** — switch between design branches
- **Version snapshots** — compare variables across versions
- **Automated test exports** — CI/CD triggered STEP generation
- **Notification hooks** — alert on BOM changes

---

## Integration possibilities

- **Reports** — auto-generate design review documents
- **Parameter studies** — sweep variables, export results
- **Team dashboards** — live view of part status and materials
- **Cross-document sync** — keep shared variables consistent

---

<!-- _class: lead -->

# Get started

**Clone:** `github.com/MEMSYS-bv/mcp-onshape`

**Setup:** Run `#setup-onshape` in Copilot Chat

**Questions?** Ask Sander

