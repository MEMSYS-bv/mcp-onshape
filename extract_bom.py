#!/usr/bin/env python3
"""
Generic OnShape BOM Extraction Script

Extracts Bill of Materials from any OnShape assembly registered in onshape_documents.yaml.
Can also accept a direct OnShape URL for one-off extractions.

Usage:
    # By project code (from YAML registry):
    python extract_bom.py EH-0080-BB1
    python extract_bom.py HM-0070-EWS-V02

    # By direct URL:
    python extract_bom.py --url "https://cad.onshape.com/documents/{did}/w/{wid}/e/{eid}"

    # List registered documents:
    python extract_bom.py --list

    # Output as markdown table (default) or JSON:
    python extract_bom.py HM-0070-EWS-V02 --format json
    python extract_bom.py HM-0070-EWS-V02 --format markdown

Author: Sander
"""

import os
import sys
import json
import argparse
from pathlib import Path

from onshape_api import OnshapeClient
from document_registry import load_documents, get_document_ids, list_documents, parse_onshape_url
from constants import BOM_HEADERS as HEADER_IDS

# ── Configuration ─────────────────────────────────────────────────────────────

ONSHAPE_ACCESS_KEY = os.getenv("ONSHAPE_ACCESS_KEY", "")
ONSHAPE_SECRET_KEY = os.getenv("ONSHAPE_SECRET_KEY", "")


# ── BOM Extraction ────────────────────────────────────────────────────────────

def extract_bom(client: OnshapeClient, doc_id: str, ws_id: str, elem_id: str) -> list:
    """Extract and parse BOM rows into a clean list of dicts."""
    bom = client.get_assembly_bom(doc_id, ws_id, elem_id)
    rows = bom.get("rows", [])
    result = []

    for row in rows:
        hv = row.get("headerIdToValue", {})

        # Parse material (can be a dict with displayName or a string)
        mat_data = hv.get(HEADER_IDS["material"])
        if isinstance(mat_data, dict):
            material = mat_data.get("displayName", "N/A")
        elif mat_data:
            material = str(mat_data)
        else:
            material = "N/A"

        # Parse quantity (float from API)
        qty_raw = hv.get(HEADER_IDS["quantity"], 1.0)
        qty = int(qty_raw) if isinstance(qty_raw, (int, float)) else qty_raw

        result.append({
            "item": hv.get(HEADER_IDS["item"], ""),
            "part_number": hv.get(HEADER_IDS["part_number"]) or "—",
            "name": hv.get(HEADER_IDS["name"], "N/A"),
            "quantity": qty,
            "material": material,
            "mass": hv.get(HEADER_IDS["mass"], "N/A"),
        })

    return result


def format_markdown(bom_rows: list, doc_name: str = "") -> str:
    """Format BOM as a markdown table."""
    lines = []
    if doc_name:
        lines.append(f"**Source:** {doc_name}")
        lines.append("")
    lines.append("| # | Part Number | Name | Qty | Material | Mass |")
    lines.append("|---|-------------|------|-----|----------|------|")
    for i, row in enumerate(bom_rows, 1):
        pn = str(row["part_number"])[:20]
        name = str(row["name"])[:40]
        qty = row["quantity"]
        mat = str(row["material"])[:28]
        mass = row["mass"]
        lines.append(f"| {i} | {pn} | {name} | {qty} | {mat} | {mass} |")
    lines.append(f"\n**Total:** {len(bom_rows)} items")
    return "\n".join(lines)


def format_json(bom_rows: list) -> str:
    """Format BOM as JSON."""
    return json.dumps(bom_rows, indent=2, default=str)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Extract BOM from OnShape assemblies",
        epilog="Examples:\n"
               "  python extract_bom.py HM-0070-EWS-V02\n"
               "  python extract_bom.py --url 'https://cad.onshape.com/documents/...'\n"
               "  python extract_bom.py --list\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("project_code", nargs="?", help="Project code from onshape_documents.yaml")
    parser.add_argument("--url", help="Direct OnShape assembly URL")
    parser.add_argument("--list", action="store_true", help="List all registered documents")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown",
                        help="Output format (default: markdown)")
    args = parser.parse_args()

    if args.list:
        list_documents()
        return

    if not args.project_code and not args.url:
        parser.print_help()
        return

    # Validate credentials
    if not ONSHAPE_ACCESS_KEY or not ONSHAPE_SECRET_KEY:
        print("Error: OnShape API keys not set. Check .env file.")
        sys.exit(1)

    # Resolve document IDs
    if args.url:
        doc_id, ws_id, elem_id = parse_onshape_url(args.url)
        label = args.url
    else:
        doc_id, ws_id, elem_id = get_document_ids(args.project_code)
        label = args.project_code

    client = OnshapeClient(ONSHAPE_ACCESS_KEY, ONSHAPE_SECRET_KEY)

    # Get document name
    try:
        doc_info = client.get_document(doc_id)
        doc_name = doc_info.get("name", label)
    except Exception:
        doc_name = label

    print(f"Extracting BOM from: {doc_name}")
    print(f"Document: {doc_id} / Workspace: {ws_id} / Element: {elem_id}\n")

    # Extract BOM
    bom_rows = extract_bom(client, doc_id, ws_id, elem_id)

    # Output
    if args.format == "json":
        print(format_json(bom_rows))
    else:
        print(format_markdown(bom_rows, doc_name))


if __name__ == "__main__":
    main()
