#!/usr/bin/env python3
"""
OnShape Version Management Script — Create and List Document Versions

Creates named versions (immutable snapshots) of OnShape documents, or lists
existing versions. Supports guided version naming using the MEMSYS revision
model (Rev0.1, RevA, RevA.1, RevB, etc.).

Usage:
    # Create a version by project code:
    python create_version.py EH-0080-BB1 "Rev0.1 - Initial geometry"
    python create_version.py EH-0080-BB1 "RevA" --description "First release"

    # Guided mode — suggest next version name:
    python create_version.py EH-0080-BB1 --working    # Next working snapshot
    python create_version.py EH-0080-BB1 --release     # Next formal release

    # Suggest without creating:
    python create_version.py EH-0080-BB1 --suggest

    # List existing versions:
    python create_version.py EH-0080-BB1 --list

    # By direct URL:
    python create_version.py --url "https://cad.onshape.com/documents/{did}/w/{wid}/e/{eid}" "Rev0.1"

    # List registered documents:
    python create_version.py --list-docs

Author: Camilo (via Copilot)
Created: 2026-04-09
"""

import os
import sys
import argparse

from onshape_api import OnshapeClient
from document_registry import load_documents, get_document_ids, list_documents, parse_onshape_url
from revision import is_valid_revision, normalize_revision, suggest_next_revision, parse_revision

# ── Configuration ─────────────────────────────────────────────────────────────

ONSHAPE_ACCESS_KEY = os.getenv("ONSHAPE_ACCESS_KEY", "")
ONSHAPE_SECRET_KEY = os.getenv("ONSHAPE_SECRET_KEY", "")


# ── Version Operations ────────────────────────────────────────────────────────

def print_versions(client: OnshapeClient, doc_id: str, doc_name: str) -> None:
    """List all versions of a document."""
    versions = client.get_versions(doc_id)
    print(f"Versions of '{doc_name}':")
    if not versions:
        print("  (no versions)")
        return
    for v in versions:
        desc = f" — {v['description']}" if v.get("description") else ""
        valid = "✓" if is_valid_revision(v['name']) else ""
        print(f"  {v['name']}{desc}  {valid}")
        print(f"    ID: {v['id']}")
        print(f"    Created: {v.get('createdAt', 'unknown')}")


def find_latest_revision(client: OnshapeClient, doc_id: str) -> str | None:
    """Find the latest valid revision label among existing versions.

    Scans all versions and returns the most recent one that matches the
    canonical revision format. Returns None if no valid revision exists.
    """
    versions = client.get_versions(doc_id)
    latest = None
    latest_ord = (-1, -1)  # (letter_ord, sub)
    for v in versions:
        name = v.get("name", "")
        parsed = parse_revision(name)
        if not parsed:
            # Try normalizing first
            normalized = normalize_revision(name)
            if normalized:
                parsed = parse_revision(normalized)
        if not parsed:
            continue
        base = parsed["base"]
        sub = parsed["sub"] or 0
        ord_val = (0 if base == '0' else ord(base), sub)
        if ord_val > latest_ord:
            latest_ord = ord_val
            latest = normalized if 'normalized' in dir() and normalized else name
            if not is_valid_revision(latest):
                latest = normalize_revision(latest)
    return latest


def suggest_version_name(client: OnshapeClient, doc_id: str,
                         mode: str = "working") -> tuple[str, str | None]:
    """Suggest the next version name based on existing versions.

    Args:
        mode: "working" for next intermediate, "release" for next formal release.

    Returns:
        (suggested_name, current_latest) tuple.
    """
    current = find_latest_revision(client, doc_id)
    if current is None:
        # No existing revisions — start with Rev0.1 for working, RevA for release
        if mode == "release":
            return "RevA", None
        else:
            return "Rev0.1", None
    return suggest_next_revision(current, mode), current


def create_version(client: OnshapeClient, doc_id: str, doc_name: str,
                   version_name: str, description: str = "") -> None:
    """Create a named version of a document."""
    print(f"Creating version '{version_name}' for '{doc_name}'...")
    result = client.create_version(doc_id, version_name, description)
    print(f"Version created successfully!")
    print(f"  Name: {result['name']}")
    print(f"  ID: {result['id']}")
    if result.get("description"):
        print(f"  Description: {result['description']}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Create or list versions of OnShape documents",
        epilog="Examples:\n"
               "  python create_version.py EH-0080-BB1 'Rev0.1 - Initial'\n"
               "  python create_version.py EH-0080-BB1 --working\n"
               "  python create_version.py EH-0080-BB1 --release\n"
               "  python create_version.py EH-0080-BB1 --suggest\n"
               "  python create_version.py EH-0080-BB1 --list\n"
               "  python create_version.py --list-docs\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("project_code", nargs="?", help="Project code from onshape_documents.yaml")
    parser.add_argument("version_name", nargs="?", help="Name for the new version")
    parser.add_argument("--description", default="", help="Optional description for the version")
    parser.add_argument("--url", help="Direct OnShape document URL")
    parser.add_argument("--list", action="store_true", dest="list_versions",
                        help="List existing versions of the document")
    parser.add_argument("--list-docs", action="store_true",
                        help="List all registered documents")
    parser.add_argument("--working", action="store_true",
                        help="Create next working snapshot (auto-generates name)")
    parser.add_argument("--release", action="store_true",
                        help="Create next formal release (auto-generates name)")
    parser.add_argument("--suggest", action="store_true",
                        help="Show suggested next version names without creating")
    args = parser.parse_args()

    if args.list_docs:
        list_documents()
        return

    if not args.project_code and not args.url:
        parser.print_help()
        return

    # Validate credentials
    if not ONSHAPE_ACCESS_KEY or not ONSHAPE_SECRET_KEY:
        print("Error: OnShape API keys not set. Check .env file.")
        sys.exit(1)

    # Resolve document ID
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

    # Handle --list
    if args.list_versions:
        print_versions(client, doc_id, doc_name)
        return

    # Handle --suggest
    if args.suggest:
        working_name, current = suggest_version_name(client, doc_id, "working")
        release_name, _ = suggest_version_name(client, doc_id, "release")
        print(f"Document: {doc_name}")
        if current:
            print(f"  Latest revision: {current}")
        else:
            print(f"  No existing revisions found.")
        print(f"\n  Suggested next working snapshot: {working_name}")
        print(f"  Suggested next formal release:  {release_name}")
        return

    # Handle --working / --release (guided modes)
    if args.working or args.release:
        mode = "release" if args.release else "working"
        suggested, current = suggest_version_name(client, doc_id, mode)
        version_name = suggested
        desc = args.description or (
            f"{'Release' if mode == 'release' else 'Working snapshot'}"
            f"{' (from ' + current + ')' if current else ''}"
        )
        print(f"  Mode: {mode}")
        if current:
            print(f"  Latest revision: {current}")
        print(f"  Suggested name: {version_name}")
        create_version(client, doc_id, doc_name, version_name, desc)
        return

    # Create version (free-text name)
    if not args.version_name:
        print("Error: VERSION_NAME is required when creating a version.")
        print("Usage: python create_version.py PROJECT_CODE VERSION_NAME [--description TEXT]")
        print("   or: python create_version.py PROJECT_CODE --working")
        print("   or: python create_version.py PROJECT_CODE --release")
        sys.exit(1)

    create_version(client, doc_id, doc_name, args.version_name, args.description)


if __name__ == "__main__":
    main()
