---
description: "Interactive setup wizard for the Onshape MCP tooling. Walks through API key creation, .env configuration, dependency installation, and connection testing."
mode: agent
---

# Onshape MCP Setup Wizard

You are helping the user set up the Onshape MCP tooling for the first time. Follow these steps in order, confirming each one before proceeding.

## Step 1: API Keys

Ask: "Do you already have Onshape API keys?"

- **If yes** → Ask them to provide the Access Key (it starts with `on_`). Do NOT ask for the Secret Key in chat — you'll write it to `.env` in the next step.
- **If no** → Guide them:
  1. Go to https://cad.onshape.com/appstore/dev-portal
  2. Click **API keys** → **Create new API key**
  3. Select permissions:
     - ✅ Application can read your documents
     - ✅ Application can write to your documents
  4. **Save both keys immediately** — the Secret Key is only shown once
  5. Come back with the Access Key

## Step 2: Create `.env`

Once they have keys:
1. Copy `.env.example` to `.env`
2. Ask the user to paste their Access Key and Secret Key
3. Write the keys to `.env`
4. Verify `.env` is in `.gitignore`

## Step 3: Install Dependencies

Run:
```
pip install -e .
```

This installs: `mcp`, `requests`, `pyyaml`, `python-dotenv`

## Step 4: Test Connection

Run:
```
python test_connection.py
```

If successful, it will show the document name and element count for the first registered document.

If it fails:
- **401 Unauthorized** → Keys are wrong. Re-check copy/paste.
- **403 Forbidden** → Keys lack read/write permissions. Create new keys with correct permissions.
- **Connection error** → Check network access to `cad.onshape.com`

## Step 5: Register a Document

Ask: "Do you have an Onshape document you'd like to register?"

If yes:
1. Ask for the Onshape URL (format: `https://cad.onshape.com/documents/{did}/w/{wid}/e/{eid}`)
2. Ask for a project code (short identifier, e.g. `MY-PROJECT`)
3. Add entry to `onshape_documents.yaml`
4. Verify with: `python extract_bom.py {project_code}`

## Step 6: Configure VS Code MCP Server (optional)

Ask: "Would you like to connect this to GitHub Copilot via MCP?"

If yes, create or update `.vscode/mcp.json`:
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

Note: The server reads credentials from `.env` automatically — no need to duplicate keys in MCP config.

## Done

Summarize what was set up and suggest next steps:
- Try `python extract_bom.py --list` to see registered documents
- Try asking Copilot: "Get the variables from my Onshape document"
- Read `README.md` for full CLI usage
