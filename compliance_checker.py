#!/usr/bin/env python3
"""
Design Guide Compliance Checker for Onshape Documents.

Preflight tool that checks whether an Onshape document follows the MEMSYS
design guide well enough for export and manufacturing use.

Checks:
  - Required metadata completeness (part number, revision, material)
  - Revision validity (canonical Rev format)
  - Drawing naming convention ({PartNumber} Drawing)
  - Default part names (e.g. "Part 1")
  - Registry completeness (optional, for automation workflows)

Output:
  - Terminal summary with errors/warnings
  - Optional JSON output (--json)

Usage:
    python compliance_checker.py EH-0080-BB1
    python compliance_checker.py EH-0080-BB1 --json
    python compliance_checker.py --url "https://cad.onshape.com/documents/..."
    python cli.py check-compliance EH-0080-BB1

Author: Sander (via Copilot)
Created: 2026-04-23
"""

import argparse
import json
import os
import sys

from onshape_api import OnshapeClient
from document_registry import load_documents, get_document_ids, list_documents, parse_onshape_url
from constants import METADATA_PROPERTY_IDS
from revision import is_valid_revision, normalize_revision

ONSHAPE_ACCESS_KEY = os.getenv("ONSHAPE_ACCESS_KEY", "")
ONSHAPE_SECRET_KEY = os.getenv("ONSHAPE_SECRET_KEY", "")


# ── Check definitions ─────────────────────────────────────────────────────────

def _is_default_name(name: str) -> bool:
    """Check if a part name is an Onshape default like 'Part 1', 'Part 2'."""
    if not name:
        return True
    parts = name.split()
    return len(parts) == 2 and parts[0] == "Part" and parts[1].isdigit()


def check_parts(client: OnshapeClient, did: str, wid: str) -> list[dict]:
    """Run compliance checks on all parts in a document.

    Returns a list of finding dicts with:
      - part_number, part_name, element_id, part_id
      - level: "error" or "warning"
      - check: short check identifier
      - message: human-readable description
    """
    findings = []

    # Get all part studios
    studios = client.get_part_studios(did, wid)

    for studio in studios:
        eid = studio["id"]
        sname = studio.get("name", eid)

        try:
            parts = client.get_parts(did, wid, eid)
        except Exception as e:
            findings.append({
                "part_number": "-",
                "part_name": sname,
                "element_id": eid,
                "part_id": "-",
                "level": "error",
                "check": "studio_access",
                "message": f"Cannot read Part Studio '{sname}': {e}",
            })
            continue

        for p in parts:
            pn = p.get("partNumber") or ""
            name = p.get("name", "")
            pid = p.get("partId", "")
            material = (p.get("material", {}) or {}).get("displayName", "")

            base = {
                "part_number": pn or "-",
                "part_name": name,
                "element_id": eid,
                "part_id": pid,
            }

            # Check: default name
            if _is_default_name(name):
                findings.append({**base, "level": "error", "check": "default_name",
                    "message": f"Default part name '{name}' — assign a meaningful name."})

            # Check: missing part number
            if not pn:
                findings.append({**base, "level": "error", "check": "no_part_number",
                    "message": "Missing part number."})

            # Check: missing material
            if not material:
                findings.append({**base, "level": "warning", "check": "no_material",
                    "message": "No material assigned."})

            # Check: revision
            try:
                meta = client.get_part_metadata(did, wid, eid, pid)
                revision = ""
                for prop in meta.get("properties", []):
                    if prop.get("propertyId") == METADATA_PROPERTY_IDS.get("revision"):
                        revision = str(prop.get("value", ""))
                        break

                if not revision:
                    findings.append({**base, "level": "warning", "check": "no_revision",
                        "message": "No revision set."})
                elif not is_valid_revision(revision):
                    norm = normalize_revision(revision)
                    suggestion = f" Did you mean '{norm}'?" if norm else ""
                    findings.append({**base, "level": "error", "check": "invalid_revision",
                        "message": f"Invalid revision '{revision}'.{suggestion} "
                                   f"Use format: Rev0.1, RevA, RevA.1, RevB."})
            except Exception:
                findings.append({**base, "level": "warning", "check": "metadata_read_error",
                    "message": "Could not read part metadata for revision check."})

    return findings


def check_drawings(client: OnshapeClient, did: str, wid: str,
                   parts: list[dict] | None = None) -> list[dict]:
    """Check drawing naming convention compliance.

    Verifies that drawings follow the {PartNumber} Drawing naming rule.

    Args:
        parts: Optional pre-fetched parts list. If None, fetches from all studios.
    """
    findings = []

    drawings = client.list_drawings(did, wid)
    if not drawings:
        findings.append({
            "part_number": "-", "part_name": "-",
            "element_id": "-", "part_id": "-",
            "level": "warning", "check": "no_drawings",
            "message": "No drawings found in document.",
        })
        return findings

    # Collect all part numbers
    if parts is None:
        all_parts = []
        for studio in client.get_part_studios(did, wid):
            try:
                all_parts.extend(client.get_parts(did, wid, studio["id"]))
            except Exception:
                pass
    else:
        all_parts = parts

    part_numbers = {p.get("partNumber") for p in all_parts if p.get("partNumber")}

    # Check each drawing against the naming convention
    for d in drawings:
        dname = d.get("name", "")
        # Expected format: "{PartNumber} Drawing"
        if dname.endswith(" Drawing"):
            candidate_pn = dname[:-len(" Drawing")]
            if candidate_pn in part_numbers:
                continue  # Compliant
            else:
                findings.append({
                    "part_number": candidate_pn, "part_name": "-",
                    "element_id": d.get("id", "-"), "part_id": "-",
                    "level": "warning", "check": "drawing_unmatched",
                    "message": f"Drawing '{dname}' follows naming convention but "
                               f"part number '{candidate_pn}' not found in document.",
                })
        else:
            findings.append({
                "part_number": "-", "part_name": "-",
                "element_id": d.get("id", "-"), "part_id": "-",
                "level": "warning", "check": "drawing_naming",
                "message": f"Drawing '{dname}' does not follow '{{PartNumber}} Drawing' convention.",
            })

    # Check for parts without drawings
    drawing_names = {d.get("name", "") for d in drawings}
    for pn in part_numbers:
        expected_drawing = f"{pn} Drawing"
        if expected_drawing not in drawing_names:
            findings.append({
                "part_number": pn, "part_name": "-",
                "element_id": "-", "part_id": "-",
                "level": "warning", "check": "no_drawing",
                "message": f"No drawing found for part '{pn}' "
                           f"(expected tab named '{expected_drawing}').",
            })

    return findings


def check_registry(project_code: str) -> list[dict]:
    """Check registry completeness for a project code."""
    findings = []

    docs = load_documents()
    if project_code not in docs:
        findings.append({
            "part_number": "-", "part_name": "-",
            "element_id": "-", "part_id": "-",
            "level": "warning", "check": "not_registered",
            "message": f"Project code '{project_code}' is not in onshape_documents.yaml.",
        })
        return findings

    d = docs[project_code]
    if "name" not in d:
        findings.append({
            "part_number": "-", "part_name": "-",
            "element_id": "-", "part_id": "-",
            "level": "warning", "check": "missing_name",
            "message": "Registry entry has no 'name' field.",
        })

    return findings


# ── Output formatting ─────────────────────────────────────────────────────────

def print_report(findings: list[dict], doc_name: str):
    """Print a human-readable compliance report."""
    errors = [f for f in findings if f["level"] == "error"]
    warnings = [f for f in findings if f["level"] == "warning"]

    print(f"\n{'=' * 60}")
    print(f"COMPLIANCE REPORT: {doc_name}")
    print(f"{'=' * 60}\n")

    if not findings:
        print("  ✓ All checks passed. Document is compliant.\n")
        return

    if errors:
        print(f"  ERRORS ({len(errors)}):\n")
        for f in errors:
            label = f["part_number"] if f["part_number"] != "-" else f["part_name"]
            print(f"    ✗ [{f['check']}] {label}: {f['message']}")
        print()

    if warnings:
        print(f"  WARNINGS ({len(warnings)}):\n")
        for f in warnings:
            label = f["part_number"] if f["part_number"] != "-" else f["part_name"]
            print(f"    ⚠ [{f['check']}] {label}: {f['message']}")
        print()

    print(f"  Summary: {len(errors)} error(s), {len(warnings)} warning(s)")
    if errors:
        print("  ✗ Document has blocking issues — resolve errors before export.")
    else:
        print("  ⚠ Document has warnings — review before export.")
    print()


# ── Main ──────────────────────────────────────────────────────────────────────

def run_compliance_check(client: OnshapeClient, did: str, wid: str,
                         project_code: str = None) -> list[dict]:
    """Run all compliance checks and return combined findings."""
    findings = []

    # Registry checks
    if project_code:
        findings.extend(check_registry(project_code))

    # Part checks
    findings.extend(check_parts(client, did, wid))

    # Drawing checks
    findings.extend(check_drawings(client, did, wid))

    return findings


def main():
    parser = argparse.ArgumentParser(
        description="Check Onshape document compliance with the MEMSYS design guide",
        epilog=(
            "Examples:\n"
            "  python compliance_checker.py EH-0080-BB1\n"
            "  python compliance_checker.py EH-0080-BB1 --json\n"
            "  python compliance_checker.py --url 'https://cad.onshape.com/documents/...'\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("project_code", nargs="?", help="Project code from onshape_documents.yaml")
    parser.add_argument("--url", help="Direct OnShape document URL")
    parser.add_argument("--json", action="store_true", dest="json_output",
                        help="Output results as JSON")
    parser.add_argument("--list-docs", action="store_true", help="List registered documents")
    args = parser.parse_args()

    if args.list_docs:
        list_documents()
        return

    if not args.project_code and not args.url:
        parser.print_help()
        return

    if not ONSHAPE_ACCESS_KEY or not ONSHAPE_SECRET_KEY:
        print("Error: OnShape API keys not set. Check .env file.")
        sys.exit(1)

    if args.url:
        did, wid, _ = parse_onshape_url(args.url)
        project_code = None
        label = args.url
    else:
        did, wid, _ = get_document_ids(args.project_code)
        project_code = args.project_code
        label = args.project_code

    client = OnshapeClient(ONSHAPE_ACCESS_KEY, ONSHAPE_SECRET_KEY)

    try:
        doc_info = client.get_document(did)
        doc_name = doc_info.get("name", label)
    except Exception:
        doc_name = label

    findings = run_compliance_check(client, did, wid, project_code)

    if args.json_output:
        output = {
            "document": doc_name,
            "project_code": project_code,
            "errors": [f for f in findings if f["level"] == "error"],
            "warnings": [f for f in findings if f["level"] == "warning"],
            "total_errors": sum(1 for f in findings if f["level"] == "error"),
            "total_warnings": sum(1 for f in findings if f["level"] == "warning"),
            "compliant": all(f["level"] != "error" for f in findings),
        }
        print(json.dumps(output, indent=2))
    else:
        print_report(findings, doc_name)

    # Exit non-zero if there are errors
    if any(f["level"] == "error" for f in findings):
        sys.exit(1)


if __name__ == "__main__":
    main()
