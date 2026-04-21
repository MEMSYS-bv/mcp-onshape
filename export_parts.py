"""
Export parts as STEP files and their drawings as PDFs from Onshape.

Naming conventions:
  STEP: ${partNumber}_Rev${revision}-${name}.step
  PDF:  ${partNumber}_Rev${revision}-${name}.pdf

Usage:
  python export_parts.py --parts EH-00800-P-0016 EH-00800-P-0017 EH-00800-P-0018 EH-00800-P-0019
  python export_parts.py --url "https://cad.onshape.com/documents/{did}/w/{wid}/e/{eid}" --parts P-0016 P-0017
  python export_parts.py --all  # Export all parts
"""

import argparse
import os
import re
import sys
import time
import json
import requests
from pathlib import Path

from onshape_api import OnshapeClient
from document_registry import get_document_ids, list_documents, parse_onshape_url, get_drawing_map
from constants import METADATA_PROPERTY_IDS
from revision import normalize_revision, format_for_filename

# ── Configuration ─────────────────────────────────────────────────────────────

ONSHAPE_ACCESS_KEY = os.getenv("ONSHAPE_ACCESS_KEY", "")
ONSHAPE_SECRET_KEY = os.getenv("ONSHAPE_SECRET_KEY", "")


def extract_revision(metadata: dict) -> str:
    """Extract and normalize revision from part metadata."""
    props = metadata.get("properties", [])
    for p in props:
        pid = p.get("propertyId", "")
        name = p.get("name", "").lower()
        if "revision" in name or pid == METADATA_PROPERTY_IDS.get("revision", ""):
            val = p.get("value", "")
            if val:
                normalized = normalize_revision(str(val))
                return normalized if normalized else str(val)
    return "-"


# --- Translation (export) workflow ---


def export_step(client: OnshapeClient, did: str, wid: str, eid: str,
                part_id: str) -> dict:
    """Start a STEP translation for a single part."""
    return client.start_translation(
        f"/partstudios/d/{did}/w/{wid}/e/{eid}/translations",
        "STEP", part_id=part_id,
    )


def export_drawing_pdf(client: OnshapeClient, did: str, wid: str,
                       eid: str) -> dict:
    """Start a PDF translation for a drawing."""
    return client.start_translation(
        f"/drawings/d/{did}/w/{wid}/e/{eid}/translations", "PDF",
    )


def make_filename(part_number: str, revision: str, name: str, extension: str) -> str:
    """Apply naming convention: ${partNumber}_Rev${revision}-${name}.ext

    Uses format_for_filename() to strip the Rev prefix from canonical
    revision labels, preventing double-prefix like _RevRevA-.
    """
    # Sanitize name for filesystem
    safe_name = re.sub(r'[<>:"/\\|?*]', '_', name)
    rev_part = format_for_filename(revision)
    return f"{part_number}_Rev{rev_part}-{safe_name}.{extension}"


# --- Main export logic ---


def match_drawing_by_part_number(drawings: list[dict], part_number: str) -> dict | None:
    """Find a drawing by exact '{PartNumber} Drawing' naming convention.

    This is the primary lookup strategy per the design guide.
    """
    expected = f"{part_number} Drawing"
    expected_lower = expected.lower()
    for d in drawings:
        if d.get("name", "").lower() == expected_lower:
            return d
    return None


def match_drawing_to_part(drawings: list[dict], part_name: str) -> dict | None:
    """Find a drawing that matches a part name (fuzzy fallback).
    
    Handles naming patterns like:
      - "Linear guide frame Drawing 1"   (space-separated + Drawing N)
      - "Drawing_Linear_Guide_Frame"      (underscore-separated + Drawing_ prefix)
      - "BB movable top clamp Drawing"    (space-separated + Drawing suffix)
    
    Prefers "Drawing 1" suffix (latest iteration) over plain "Drawing".
    """
    part_name_lower = part_name.lower()
    # Also create an underscore-normalized version for matching
    part_name_underscored = part_name.lower().replace(" ", "_")
    
    candidates = []
    for d in drawings:
        dname = d.get("name", "")
        dname_lower = dname.lower()
        dname_normalized = dname_lower.replace("_", " ")
        
        if part_name_lower in dname_lower or part_name_lower in dname_normalized:
            candidates.append(d)
        elif part_name_underscored in dname_lower:
            candidates.append(d)
    
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]
    
    # Multiple matches — rank by preference:
    # 1. "Drawing 1" suffix (latest iteration)
    # 2. "Drawing_" prefix (newer naming convention)
    # 3. Plain "Drawing" suffix (older)
    def rank(d):
        name = d.get("name", "")
        if re.search(r"Drawing\s+\d+$", name):
            return 0  # Best: "Part Drawing 1"
        if name.startswith("Drawing_"):
            return 1  # Good: "Drawing_Part_Name"
        return 2  # Fallback

    candidates.sort(key=rank)
    return candidates[0]


def export_parts_workflow(client: OnshapeClient, did: str, wid: str,
                         part_numbers: list[str], output_dir: Path,
                         drawing_map: dict = None):
    """Main workflow: find parts, export STEP + PDF, save to output directory.
    
    Args:
        drawing_map: Optional dict mapping part numbers to drawing element IDs.
                     Overrides fuzzy name matching when a part number has an entry.
    """
    
    print(f"Document: {did}")
    print(f"Workspace: {wid}")
    print(f"Output: {output_dir}")
    print(f"Target parts: {', '.join(part_numbers)}")
    print()

    # 1. Get all parts
    print("Fetching parts...")
    all_parts = client.get_parts(did, wid)
    
    # Filter by part number
    target_parts = []
    for p in all_parts:
        pn = p.get("partNumber") or ""
        if pn in part_numbers:
            target_parts.append(p)
    
    if not target_parts:
        print(f"ERROR: No parts found matching {part_numbers}")
        print("Available part numbers:")
        for p in all_parts:
            pn = p.get("partNumber")
            if pn:
                print(f"  {pn} — {p.get('name')}")
        sys.exit(1)

    print(f"Found {len(target_parts)} matching parts:")
    for p in target_parts:
        print(f"  {p.get('partNumber'):25s} | {p.get('name')}")
    print()

    # 2. Get all elements (to find drawings)
    print("Fetching elements (drawings)...")
    drawings = client.list_drawings(did, wid)
    print(f"Found {len(drawings)} drawings")
    print()

    # 3. Process each part
    results = []
    for part in target_parts:
        pn = part["partNumber"]
        name = part["name"]
        pid = part["partId"]
        eid = part["elementId"]
        
        print(f"=== {pn} — {name} ===")
        
        # Get revision metadata
        print("  Getting metadata...")
        try:
            meta = client.get_part_metadata(did, wid, eid, pid)
        except Exception:
            meta = {}
        revision = extract_revision(meta)
        print(f"  Revision: {revision}")
        
        # Export STEP
        print("  Exporting STEP...")
        try:
            trans = export_step(client, did, wid, eid, pid)
            tid = trans.get("id")
            print(f"  Translation ID: {tid}")
            
            result = client.poll_translation(tid)
            ext_ids = result.get("resultExternalDataIds", [])
            
            if ext_ids:
                step_filename = make_filename(pn, revision, name, "step")
                step_path = output_dir / step_filename
                client.download_external_data(did, ext_ids[0], step_path)
                print(f"  Downloaded: {step_path} ({step_path.stat().st_size:,} bytes)")
                results.append({"type": "STEP", "part": pn, "file": str(step_path)})
            else:
                print(f"  WARNING: No result IDs in translation response")
        except Exception as e:
            print(f"  ERROR exporting STEP: {e}")
        
        # Find and export matching drawing as PDF
        # Priority: 1. explicit drawing_map  2. exact {PartNumber} Drawing  3. fuzzy name match
        drawing = None
        if drawing_map and pn in drawing_map:
            mapped_eid = drawing_map[pn]
            drawing = next((d for d in drawings if d["id"] == mapped_eid), None)
            if drawing:
                print(f"  Drawing (from map): {drawing['name']} ({mapped_eid[:12]}...)")
            else:
                print(f"  WARNING: drawing_map entry {mapped_eid} not found in document")
        
        if not drawing:
            drawing = match_drawing_by_part_number(drawings, pn)
            if drawing:
                print(f"  Drawing (exact match): {drawing['name']} ({drawing['id'][:12]}...)")

        if not drawing:
            drawing = match_drawing_to_part(drawings, name)
            if drawing:
                print(f"  Drawing (fuzzy match): {drawing['name']} ({drawing['id'][:12]}...)")
        if drawing:
            drawing_eid = drawing["id"]
            print("  Exporting PDF...")
            
            try:
                trans = export_drawing_pdf(client, did, wid, drawing_eid)
                tid = trans.get("id")
                print(f"  Translation ID: {tid}")
                
                result = client.poll_translation(tid)
                ext_ids = result.get("resultExternalDataIds", [])
                
                if ext_ids:
                    pdf_filename = make_filename(pn, revision, name, "pdf")
                    pdf_path = output_dir / pdf_filename
                    client.download_external_data(did, ext_ids[0], pdf_path)
                    print(f"  Downloaded: {pdf_path} ({pdf_path.stat().st_size:,} bytes)")
                    results.append({"type": "PDF", "part": pn, "file": str(pdf_path)})
                else:
                    print(f"  WARNING: No result IDs in PDF translation response")
            except Exception as e:
                print(f"  ERROR exporting PDF: {e}")
        else:
            print(f"  No matching drawing found for '{name}'")
        
        print()

    # Summary
    print("\n" + "=" * 60)
    print("EXPORT SUMMARY")
    print("=" * 60)
    for r in results:
        print(f"  [{r['type']:4s}] {r['part']} → {r['file']}")
    print(f"\nTotal: {len(results)} files exported")
    
    return results


def main():
    parser = argparse.ArgumentParser(description="Export Onshape parts as STEP + drawing PDFs")
    parser.add_argument("project_code", nargs="?", help="Project code from onshape_documents.yaml")
    parser.add_argument("--url", help="Onshape document URL")
    parser.add_argument("--did", help="Document ID (alternative to URL)")
    parser.add_argument("--wid", help="Workspace ID (alternative to URL)")
    parser.add_argument("--parts", nargs="+", required=True, help="Part numbers to export")
    parser.add_argument("--output", "-o", default=".", help="Output directory")
    parser.add_argument("--list", action="store_true", help="List registered documents")
    
    args = parser.parse_args()

    if args.list:
        list_documents()
        return

    if args.url:
        did, wid, _ = parse_onshape_url(args.url)
        drawing_map = {}
    elif args.did and args.wid:
        did, wid = args.did, args.wid
        drawing_map = {}
    elif args.project_code:
        did, wid, _ = get_document_ids(args.project_code)
        drawing_map = get_drawing_map(args.project_code)
    else:
        parser.error("Provide a project_code, --url, or both --did and --wid")
    
    client = OnshapeClient(ONSHAPE_ACCESS_KEY, ONSHAPE_SECRET_KEY)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    export_parts_workflow(client, did, wid, args.parts, output_dir, drawing_map)


if __name__ == "__main__":
    main()
