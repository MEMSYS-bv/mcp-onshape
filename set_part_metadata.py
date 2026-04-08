#!/usr/bin/env python3
"""
OnShape Part Metadata Script — Set Part Number, Name, Description

Sets part metadata (part number, name, description) on parts in an OnShape
Part Studio, using the metadata API. Works with any document registered in
onshape_documents.yaml or via a direct URL.

The script first lists all parts in the Part Studio so you can identify them,
then applies the metadata updates you specify.

Usage:
    # List parts in a Part Studio (by project code):
    python set_part_metadata.py EH-0080-BB2 --list

    # Set metadata on specific parts (interactive JSON input):
    python set_part_metadata.py EH-0080-BB2 --parts parts.json

    # Set metadata inline (part name match):
    python set_part_metadata.py EH-0080-BB2 \\
        --set "Baseplate" part_number=EH-0081-P-0001 description="BB-2 machined part" \\
        --set "Clamp" part_number=EH-0081-P-0002 description="BB-2 machined part"

    # By direct URL (use element ID of the Part Studio, not the assembly):
    python set_part_metadata.py --url "https://cad.onshape.com/documents/.../e/..." --list

    # List registered documents:
    python set_part_metadata.py --list-docs

Author: Sander
Created: 2026-02-17
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Optional

import requests

from onshape_api import OnshapeClient as _BaseClient
from document_registry import load_documents, get_document_ids, list_documents, parse_onshape_url
from constants import METADATA_PROPERTY_IDS as PROPERTY_IDS

# ── Configuration ─────────────────────────────────────────────────────────────

ONSHAPE_ACCESS_KEY = os.getenv("ONSHAPE_ACCESS_KEY", "")
ONSHAPE_SECRET_KEY = os.getenv("ONSHAPE_SECRET_KEY", "")


# ── Extended OnShape API Client ───────────────────────────────────────────────

class OnshapeClient(_BaseClient):
    """OnShape API client extended with part metadata convenience methods."""

    def set_part_metadata_fields(self, document_id: str, workspace_id: str,
                                 element_id: str, part_id: str,
                                 part_number: str = None,
                                 name: str = None,
                                 description: str = None) -> dict:
        """Set part metadata (part number, name, description) by field name."""
        properties = []
        if part_number is not None:
            properties.append({"propertyId": PROPERTY_IDS["part_number"], "value": part_number})
        if name is not None:
            properties.append({"propertyId": PROPERTY_IDS["name"], "value": name})
        if description is not None:
            properties.append({"propertyId": PROPERTY_IDS["description"], "value": description})
        if not properties:
            raise ValueError("At least one of part_number, name, or description must be provided.")
        return self.set_part_metadata(document_id, workspace_id, element_id, part_id, properties)


# ── Part Listing ──────────────────────────────────────────────────────────────

def list_parts(client: OnshapeClient, doc_id: str, ws_id: str,
               part_studio_eid: str = None) -> list[dict]:
    """
    List all parts. If part_studio_eid is given, list from that Part Studio.
    Otherwise discover all Part Studios in the document and list from each.

    Returns a flat list of part dicts with element context added.
    """
    if part_studio_eid:
        studios = [{"id": part_studio_eid, "name": "(specified)"}]
    else:
        studios = client.get_part_studios(doc_id, ws_id)

    all_parts = []
    for studio in studios:
        eid = studio["id"]
        sname = studio.get("name", eid)
        try:
            parts = client.get_parts(doc_id, ws_id, eid)
        except requests.HTTPError as e:
            print(f"  Warning: Could not read Part Studio '{sname}': {e}")
            continue

        for p in parts:
            all_parts.append({
                "studio_name": sname,
                "studio_eid": eid,
                "part_id": p.get("partId", ""),
                "name": p.get("name", "N/A"),
                "part_number": p.get("partNumber", "—"),
                "description": p.get("description", ""),
                "material_name": (p.get("material", {}) or {}).get("displayName", "—"),
                "body_type": p.get("bodyType", ""),
            })
    return all_parts


def print_parts_table(parts: list[dict]):
    """Pretty-print parts as a table."""
    if not parts:
        print("  No parts found.")
        return
    # Group by studio
    studios = {}
    for p in parts:
        studios.setdefault(p["studio_name"], []).append(p)

    for sname, sparts in studios.items():
        print(f"\n  Part Studio: {sname}  (element_id: {sparts[0]['studio_eid']})")
        print(f"  {'#':<4} {'Part ID':<28} {'Name':<25} {'Part Number':<22} {'Material':<25} {'Body Type'}")
        print(f"  {'-'*4} {'-'*28} {'-'*25} {'-'*22} {'-'*25} {'-'*12}")
        for i, p in enumerate(sparts, 1):
            print(f"  {i:<4} {p['part_id'][:26]:<28} {p['name'][:23]:<25} "
                  f"{str(p['part_number'])[:20]:<22} {p['material_name'][:23]:<25} {p['body_type']}")
    print()


# ── Set command parsing ───────────────────────────────────────────────────────

class SetAction(argparse.Action):
    """Parse --set "PartName" key=value key=value ... into a list of update dicts."""

    def __call__(self, parser, namespace, values, option_string=None):
        current = getattr(namespace, self.dest, None) or []
        if not values:
            parser.error("--set requires a part name followed by key=value pairs")

        part_name = values[0]
        props = {}
        for kv in values[1:]:
            if "=" not in kv:
                parser.error(f"Expected key=value, got: {kv}")
            k, v = kv.split("=", 1)
            if k not in ("part_number", "name", "description"):
                parser.error(f"Unknown property '{k}'. Use: part_number, name, description")
            props[k] = v

        current.append({"match_name": part_name, **props})
        setattr(namespace, self.dest, current)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Set part metadata (part number / name / description) in OnShape Part Studios",
        epilog=(
            "Examples:\n"
            "  # List parts in a document:\n"
            "  python set_part_metadata.py EH-0080-BB2 --list\n\n"
            "  # Set metadata by part name:\n"
            '  python set_part_metadata.py EH-0080-BB2 \\\n'
            '      --set Baseplate part_number=EH-0081-P-0001 description="BB-2 machined part" \\\n'
            '      --set Clamp part_number=EH-0081-P-0002 description="BB-2 machined part"\n\n'
            "  # From a JSON file:\n"
            "  python set_part_metadata.py EH-0080-BB2 --parts updates.json\n\n"
            "  # By direct URL:\n"
            '  python set_part_metadata.py --url "https://cad.onshape.com/documents/..." --list\n'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("project_code", nargs="?", help="Project code from onshape_documents.yaml")
    parser.add_argument("--url", help="Direct OnShape URL (document/workspace/element)")
    parser.add_argument("--list", action="store_true", dest="list_parts",
                        help="List all parts and their current metadata")
    parser.add_argument("--list-docs", action="store_true",
                        help="List registered documents")
    parser.add_argument("--studio", metavar="ELEMENT_ID",
                        help="Target a specific Part Studio element ID "
                             "(default: discover all Part Studios)")
    parser.add_argument("--set", nargs="+", action=SetAction, dest="updates",
                        help='Set metadata: --set "Part Name" part_number=X description=Y')
    parser.add_argument("--parts", metavar="JSON_FILE",
                        help="JSON file with part updates (list of objects with "
                             "part_id or match_name + part_number/name/description)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be updated without making changes")
    args = parser.parse_args()

    # ── List registered documents ─────────────────────────────────────────
    if args.list_docs:
        list_documents()
        return

    if not args.project_code and not args.url:
        parser.print_help()
        return

    # ── Validate credentials ──────────────────────────────────────────────
    if not ONSHAPE_ACCESS_KEY or not ONSHAPE_SECRET_KEY:
        print("Error: OnShape API keys not set. Check .env file.")
        sys.exit(1)

    # ── Resolve document IDs ──────────────────────────────────────────────
    if args.url:
        doc_id, ws_id, elem_id = parse_onshape_url(args.url)
        label = args.url
    else:
        doc_id, ws_id, elem_id = get_document_ids(args.project_code)
        label = args.project_code

    client = OnshapeClient(ONSHAPE_ACCESS_KEY, ONSHAPE_SECRET_KEY)

    # Get doc name for display
    try:
        doc_info = client.get_document(doc_id)
        doc_name = doc_info.get("name", label)
    except Exception:
        doc_name = label

    print(f"Document: {doc_name}")
    print(f"  did={doc_id}  wid={ws_id}  eid={elem_id}\n")

    # ── Discover parts ────────────────────────────────────────────────────
    studio_eid = args.studio  # may be None → discover all
    parts = list_parts(client, doc_id, ws_id, studio_eid)

    # ── List mode ─────────────────────────────────────────────────────────
    if args.list_parts:
        print_parts_table(parts)
        return

    # ── Collect updates ───────────────────────────────────────────────────
    updates = args.updates or []

    # Load from JSON file if specified
    if args.parts:
        json_path = Path(args.parts)
        if not json_path.exists():
            print(f"Error: File not found: {json_path}")
            sys.exit(1)
        with open(json_path) as f:
            file_updates = json.load(f)
        if not isinstance(file_updates, list):
            print("Error: JSON file must contain a list of update objects.")
            sys.exit(1)
        updates.extend(file_updates)

    if not updates:
        print("No updates specified. Use --set or --parts, or --list to see parts.")
        parser.print_help()
        return

    # ── Resolve match_name → part_id ──────────────────────────────────────
    name_map = {}
    for p in parts:
        name_lower = p["name"].lower()
        name_map.setdefault(name_lower, []).append(p)

    resolved = []
    for u in updates:
        if "part_id" in u:
            # Direct part_id — use as-is and pick studio_eid from parts list
            pid = u["part_id"]
            match = next((p for p in parts if p["part_id"] == pid), None)
            if not match:
                print(f"Warning: part_id '{pid}' not found in any Part Studio — skipping")
                continue
            resolved.append({**u, "studio_eid": match["studio_eid"],
                             "_display": f"{match['name']} ({pid[:12]}…)"})
        elif "match_name" in u:
            needle = u["match_name"].lower()
            # Exact match first, then substring
            candidates = name_map.get(needle, [])
            if not candidates:
                candidates = [p for p in parts if needle in p["name"].lower()]
            if not candidates:
                print(f"Warning: No part matching '{u['match_name']}' — skipping")
                continue
            if len(candidates) > 1:
                print(f"Warning: Multiple parts match '{u['match_name']}':")
                for c in candidates:
                    print(f"  - {c['name']}  (part_id: {c['part_id']}, studio: {c['studio_name']})")
                print("  Using first match.")
            chosen = candidates[0]
            resolved.append({
                **{k: v for k, v in u.items() if k != "match_name"},
                "part_id": chosen["part_id"],
                "studio_eid": chosen["studio_eid"],
                "_display": f"{chosen['name']} ({chosen['part_id'][:12]}…)",
            })
        else:
            print(f"Warning: Update missing part_id or match_name — skipping: {u}")

    if not resolved:
        print("No valid updates after resolution. Aborting.")
        sys.exit(1)

    # ── Preview ───────────────────────────────────────────────────────────
    print(f"{'DRY RUN — ' if args.dry_run else ''}Updates to apply ({len(resolved)}):\n")
    for r in resolved:
        print(f"  Part: {r['_display']}")
        if r.get("part_number"):
            print(f"    part_number  → {r['part_number']}")
        if r.get("name"):
            print(f"    name         → {r['name']}")
        if r.get("description"):
            print(f"    description  → {r['description']}")
        print()

    if args.dry_run:
        print("Dry run complete — no changes made.")
        return

    # ── Apply ─────────────────────────────────────────────────────────────
    print("Applying metadata updates…\n")
    success = 0
    errors = 0
    for r in resolved:
        try:
            client.set_part_metadata_fields(
                doc_id, ws_id, r["studio_eid"], r["part_id"],
                part_number=r.get("part_number"),
                name=r.get("name"),
                description=r.get("description"),
            )
            print(f"  ✓ {r['_display']}")
            success += 1
        except requests.HTTPError as e:
            print(f"  ✗ {r['_display']}: {e}")
            errors += 1

    print(f"\nDone. {success} updated, {errors} failed.")


if __name__ == "__main__":
    main()
