#!/usr/bin/env python3
"""
OnShape Variable Studio Sync Script

Read, write, export, and import variables from OnShape Variable Studios.
Works with any document registered in onshape_documents.yaml or via direct URL.

Usage:
    # List Variable Studios in a document:
    python sync_variables.py EH-0080-BB2 --list

    # Show current variables in a specific Variable Studio:
    python sync_variables.py EH-0080-BB2 --get [--studio ELEMENT_ID]

    # Push variables from a CSV file (replaces ALL variables):
    python sync_variables.py EH-0080-BB2 --push path/to/variables.csv

    # Export current variables to CSV (backup):
    python sync_variables.py EH-0080-BB2 --export path/to/backup.csv

    # Diff: compare CSV against OnShape (no changes):
    python sync_variables.py EH-0080-BB2 --diff path/to/variables.csv

    # By direct URL:
    python sync_variables.py --url "https://cad.onshape.com/documents/..." --list

    # List registered documents:
    python sync_variables.py --list-docs

Author: Sander
Created: 2026-02-17
"""

import os
import sys
import csv
import json
import argparse
from pathlib import Path
from typing import Optional

from onshape_api import OnshapeClient
from document_registry import load_documents, get_document_ids, list_documents, parse_onshape_url
from constants import VARIABLE_TYPE_MAP as TYPE_MAP, VARIABLE_UNIT_MAP as UNIT_MAP, REVERSE_TYPE_MAP

# ── Configuration ─────────────────────────────────────────────────────────────

ONSHAPE_ACCESS_KEY = os.getenv("ONSHAPE_ACCESS_KEY", "")
ONSHAPE_SECRET_KEY = os.getenv("ONSHAPE_SECRET_KEY", "")


# ── Variable API helpers ──────────────────────────────────────────────────────

def _unpack_variables(data) -> list[dict]:
    """Unpack the raw API response into a flat list of variable dicts.

    The API returns a list of variable-table objects, each with a "variables" key.
    """
    all_vars = []
    if isinstance(data, list):
        for table in data:
            all_vars.extend(table.get("variables", []))
    elif isinstance(data, dict):
        all_vars.extend(data.get("variables", []))
    return all_vars


# ── CSV ↔ Variable conversion ─────────────────────────────────────────────────

def csv_to_variables(csv_path: Path) -> list[dict]:
    """
    Read a CSV file and convert rows to OnShape variable dicts.

    Expected CSV columns: Name, Variable type, Value, Description
    """
    variables = []
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            vtype_raw = row["Variable type"].strip().lower()
            vtype = TYPE_MAP.get(vtype_raw, vtype_raw.upper())
            value = row["Value"].strip()
            unit = UNIT_MAP.get(vtype, "")
            # Add unit suffix if not already present
            if unit and not value.lower().endswith(unit):
                expression = f"{value} {unit}"
            else:
                expression = value
            variables.append({
                "type": vtype,
                "name": row["Name"].strip(),
                "expression": expression,
                "description": row["Description"].strip(),
            })
    return variables


def variables_to_csv(variables: list[dict], csv_path: Path):
    """Export OnShape variables to CSV."""
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Name", "Variable type", "Value", "Description"])
        for v in variables:
            vtype = REVERSE_TYPE_MAP.get(v.get("type", ""), v.get("type", ""))
            # Strip unit suffix from expression for clean CSV value
            expr = v.get("expression", v.get("value", ""))
            for unit in UNIT_MAP.values():
                if isinstance(expr, str) and expr.lower().endswith(unit):
                    expr = expr[: -len(unit)].strip()
                    break
            desc = v.get("description", "")
            writer.writerow([v["name"], vtype, expr, desc])


def strip_unit(expression: str) -> str:
    """Remove unit suffix for comparison."""
    for unit in UNIT_MAP.values():
        if expression.lower().rstrip().endswith(unit):
            return expression[: -len(unit)].strip()
    return expression.strip()


# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_list_studios(client: OnshapeClient, doc_id: str, ws_id: str):
    studios = client.get_variable_studios(doc_id, ws_id)
    if not studios:
        print("  No Variable Studios found in this document.")
        return
    print(f"\n  Variable Studios ({len(studios)}):\n")
    print(f"  {'#':<4} {'Element ID':<30} {'Name'}")
    print(f"  {'-' * 4} {'-' * 30} {'-' * 30}")
    for i, s in enumerate(studios, 1):
        print(f"  {i:<4} {s['id']:<30} {s['name']}")
    print()


def resolve_studio(client: OnshapeClient, doc_id: str, ws_id: str,
                    studio_arg: Optional[str]) -> tuple[str, str]:
    """Resolve a --studio argument (name, element_id, or index) to (eid, name)."""
    studios = client.get_variable_studios(doc_id, ws_id)
    if not studios:
        print("Error: No Variable Studios found in this document.")
        sys.exit(1)

    if studio_arg is None:
        if len(studios) == 1:
            s = studios[0]
            return s["id"], s["name"]
        else:
            print(f"Multiple Variable Studios found — specify one with --studio:")
            for i, s in enumerate(studios, 1):
                print(f"  {i}. {s['name']}  ({s['id']})")
            sys.exit(1)

    # Try matching by index, element ID, or name (case-insensitive)
    if studio_arg.isdigit():
        idx = int(studio_arg) - 1
        if 0 <= idx < len(studios):
            s = studios[idx]
            return s["id"], s["name"]
    for s in studios:
        if s["id"] == studio_arg or s["name"].lower() == studio_arg.lower():
            return s["id"], s["name"]

    print(f"Error: Studio '{studio_arg}' not found. Available:")
    for s in studios:
        print(f"  {s['name']}  ({s['id']})")
    sys.exit(1)


def cmd_get(client: OnshapeClient, doc_id: str, ws_id: str,
            studio_arg: Optional[str], as_json: bool = False):
    eid, sname = resolve_studio(client, doc_id, ws_id, studio_arg)
    variables = _unpack_variables(client.get_variables(doc_id, ws_id, eid))

    if as_json:
        print(json.dumps(variables, indent=2))
        return

    print(f"\n  Variables in '{sname}' ({len(variables)}):\n")
    print(f"  {'#':<4} {'Name':<28} {'Type':<10} {'Expression':<20} {'Description'}")
    print(f"  {'-' * 4} {'-' * 28} {'-' * 10} {'-' * 20} {'-' * 35}")
    for i, v in enumerate(variables, 1):
        print(
            f"  {i:<4} {v['name'][:26]:<28} {v.get('type', '?'):<10} "
            f"{str(v.get('expression', v.get('value', '')))[:18]:<20} "
            f"{v.get('description', '')[:35]}"
        )
    print()


def cmd_push(client: OnshapeClient, doc_id: str, ws_id: str,
             studio_arg: Optional[str], csv_path: Path, dry_run: bool = False):
    eid, sname = resolve_studio(client, doc_id, ws_id, studio_arg)

    # 1. Read current OnShape variables and CSV variables
    remote_vars = _unpack_variables(client.get_variables(doc_id, ws_id, eid))
    csv_vars = csv_to_variables(csv_path)

    remote_map = {v["name"]: v for v in remote_vars}
    csv_map = {v["name"]: v for v in csv_vars}

    # 2. Classify each variable
    unchanged, changed, new_vars, preserved = [], [], [], []

    for name in remote_map:
        if name in csv_map:
            r_expr = strip_unit(str(remote_map[name].get("expression", "")))
            c_expr = strip_unit(str(csv_map[name].get("expression", "")))
            if r_expr == c_expr:
                unchanged.append(name)
            else:
                changed.append(name)
        else:
            preserved.append(name)

    for name in csv_map:
        if name not in remote_map:
            new_vars.append(name)

    # 3. Build merged list: OnShape order first, then new CSV-only variables
    #    Only include the 4 fields the API expects: type, name, expression, description
    def clean_var(v: dict) -> dict:
        return {
            "type": v.get("type", "LENGTH"),
            "name": v["name"],
            "expression": v.get("expression", v.get("value", "")),
            "description": v.get("description", ""),
        }

    merged = []
    for v in remote_vars:
        name = v["name"]
        if name in csv_map:
            merged.append(clean_var(csv_map[name]))   # CSV wins
        else:
            merged.append(clean_var(v))                # preserve OnShape-only
    for name in new_vars:
        merged.append(clean_var(csv_map[name]))        # append new CSV variables

    # 4. Print summary
    print(f"\n  Target: '{sname}' ({eid})")
    print(f"  Source: {csv_path}")
    print(f"  OnShape variables: {len(remote_vars)}")
    print(f"  CSV variables:     {len(csv_vars)}")
    print(f"  Merged total:      {len(merged)}\n")

    print(f"  Summary:")
    print(f"    Unchanged:          {len(unchanged)}")
    print(f"    Changed (CSV wins): {len(changed)}")
    print(f"    New (CSV only):     {len(new_vars)}")
    print(f"    Preserved (OnShape only): {len(preserved)}\n")

    if changed:
        print(f"  ~ Changed variables:")
        for name in changed:
            r_expr = remote_map[name].get("expression", "?")
            c_expr = csv_map[name].get("expression", "?")
            print(f"      {name:<28}  {r_expr:<18} → {c_expr}")
        print()

    if new_vars:
        print(f"  + New variables (from CSV):")
        for name in new_vars:
            v = csv_map[name]
            print(f"      {name:<28} = {v['expression']:<18}  ({v['type']})")
        print()

    if preserved:
        print(f"  ● Preserved variables (OnShape only):")
        for name in preserved:
            v = remote_map[name]
            expr = v.get("expression", v.get("value", "?"))
            print(f"      {name:<28} = {expr}")
        print()

    if dry_run:
        print(f"  Dry run — no changes made.")
        return

    print(f"  Pushing {len(merged)} merged variables...\n")

    status = client.set_variables(doc_id, ws_id, eid, merged)
    if isinstance(status, dict) and status.get("status") == "success":
        print(f"  ✓ All {len(merged)} variables pushed successfully!")
    elif status in (200, 204):
        print(f"  ✓ All {len(merged)} variables pushed successfully!")
    else:
        print(f"  Unexpected status: {status}")


def cmd_export(client: OnshapeClient, doc_id: str, ws_id: str,
               studio_arg: Optional[str], csv_path: Path):
    eid, sname = resolve_studio(client, doc_id, ws_id, studio_arg)
    variables = _unpack_variables(client.get_variables(doc_id, ws_id, eid))

    variables_to_csv(variables, csv_path)
    print(f"  ✓ Exported {len(variables)} variables from '{sname}' to {csv_path}")


def cmd_diff(client: OnshapeClient, doc_id: str, ws_id: str,
             studio_arg: Optional[str], csv_path: Path):
    eid, sname = resolve_studio(client, doc_id, ws_id, studio_arg)
    remote_vars = _unpack_variables(client.get_variables(doc_id, ws_id, eid))
    local_vars = csv_to_variables(csv_path)

    remote_map = {v["name"]: v for v in remote_vars}
    local_map = {v["name"]: v for v in local_vars}

    all_names = sorted(set(list(remote_map.keys()) + list(local_map.keys())))
    added, removed, changed, same = [], [], [], []

    for name in all_names:
        in_remote = name in remote_map
        in_local = name in local_map

        if in_local and not in_remote:
            added.append(name)
        elif in_remote and not in_local:
            removed.append(name)
        else:
            r_expr = strip_unit(str(remote_map[name].get("expression", "")))
            l_expr = strip_unit(str(local_map[name].get("expression", "")))
            if r_expr != l_expr:
                changed.append((name, remote_map[name], local_map[name]))
            else:
                same.append(name)

    print(f"\n  Diff: CSV ({csv_path.name}) vs OnShape ('{sname}')\n")

    if not added and not removed and not changed:
        print(f"  ✓ No differences — {len(same)} variables match.")
        return

    if added:
        print(f"  + Added in CSV ({len(added)}):")
        for n in added:
            v = local_map[n]
            print(f"      + {n:<25} = {v['expression']}")
    if removed:
        print(f"  - Only in OnShape ({len(removed)}):")
        for n in removed:
            v = remote_map[n]
            expr = v.get("expression", v.get("value", "?"))
            print(f"      - {n:<25} = {expr}")
    if changed:
        print(f"  ~ Changed ({len(changed)}):")
        for n, rv, lv in changed:
            r_expr = rv.get("expression", rv.get("value", "?"))
            l_expr = lv.get("expression", "?")
            print(f"      ~ {n:<25}  OnShape: {r_expr:<15}  CSV: {l_expr}")

    print(f"\n  Summary: {len(added)} added, {len(removed)} only-in-OnShape, "
          f"{len(changed)} changed, {len(same)} unchanged")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Sync variables between OnShape Variable Studios and CSV files",
        epilog=(
            "Examples:\n"
            "  # List Variable Studios:\n"
            "  python sync_variables.py EH-0080-BB2 --list\n\n"
            "  # Show current variables:\n"
            "  python sync_variables.py EH-0080-BB2 --get\n\n"
            "  # Push CSV to OnShape (full replace):\n"
            "  python sync_variables.py EH-0080-BB2 --push vars.csv\n\n"
            "  # Export from OnShape to CSV:\n"
            "  python sync_variables.py EH-0080-BB2 --export backup.csv\n\n"
            "  # See differences without changing anything:\n"
            "  python sync_variables.py EH-0080-BB2 --diff vars.csv\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("project_code", nargs="?",
                        help="Project code from onshape_documents.yaml")
    parser.add_argument("--url", help="Direct OnShape URL")
    parser.add_argument("--studio", metavar="ID_OR_NAME",
                        help="Variable Studio element ID, name, or index "
                             "(default: auto-select if only one exists)")
    parser.add_argument("--list", action="store_true", dest="list_studios",
                        help="List Variable Studios in the document")
    parser.add_argument("--list-docs", action="store_true",
                        help="List registered documents")
    parser.add_argument("--get", action="store_true",
                        help="Show current variables")
    parser.add_argument("--get-json", action="store_true",
                        help="Show current variables as raw JSON")
    parser.add_argument("--push", metavar="CSV_FILE",
                        help="Push variables from CSV to OnShape (full replace)")
    parser.add_argument("--export", metavar="CSV_FILE",
                        help="Export current OnShape variables to CSV")
    parser.add_argument("--diff", metavar="CSV_FILE",
                        help="Compare CSV against OnShape (no changes)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what --push would do without applying")
    args = parser.parse_args()

    # ── List docs ─────────────────────────────────────────────────────────
    if args.list_docs:
        list_documents()
        return

    if not args.project_code and not args.url:
        parser.print_help()
        return

    # ── Credentials ───────────────────────────────────────────────────────
    if not ONSHAPE_ACCESS_KEY or not ONSHAPE_SECRET_KEY:
        print("Error: OnShape API keys not set. Check .env file.")
        sys.exit(1)

    # ── Resolve document ──────────────────────────────────────────────────
    if args.url:
        doc_id, ws_id, _ = parse_onshape_url(args.url)
        label = args.url
    else:
        doc_id, ws_id, _ = get_document_ids(args.project_code)
        label = args.project_code

    client = OnshapeClient(ONSHAPE_ACCESS_KEY, ONSHAPE_SECRET_KEY)

    try:
        doc_info = client.get_document(doc_id)
        doc_name = doc_info.get("name", label)
    except Exception:
        doc_name = label

    print(f"Document: {doc_name}  ({label})")

    # ── Dispatch ──────────────────────────────────────────────────────────
    if args.list_studios:
        cmd_list_studios(client, doc_id, ws_id)

    elif args.get or args.get_json:
        cmd_get(client, doc_id, ws_id, args.studio, as_json=args.get_json)

    elif args.push:
        csv_path = Path(args.push)
        if not csv_path.exists():
            print(f"Error: File not found: {csv_path}")
            sys.exit(1)
        cmd_push(client, doc_id, ws_id, args.studio, csv_path,
                 dry_run=args.dry_run)

    elif args.export:
        cmd_export(client, doc_id, ws_id, args.studio, Path(args.export))

    elif args.diff:
        csv_path = Path(args.diff)
        if not csv_path.exists():
            print(f"Error: File not found: {csv_path}")
            sys.exit(1)
        cmd_diff(client, doc_id, ws_id, args.studio, csv_path)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
