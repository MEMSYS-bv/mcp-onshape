#!/usr/bin/env python3
"""
OnShape Version Management Script — Create and List Document Versions

Creates named versions (immutable snapshots) of OnShape documents, or lists
existing versions. Works with any document registered in onshape_documents.yaml
or via a direct URL.

Usage:
    # Create a version by project code:
    python create_version.py EH-0080-BB1 "V2 - Updated geometry"
    python create_version.py EH-0080-BB1 "V2" --description "Updated cantilever dimensions"

    # List existing versions:
    python create_version.py EH-0080-BB1 --list

    # By direct URL:
    python create_version.py --url "https://cad.onshape.com/documents/{did}/w/{wid}/e/{eid}" "V1"

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
        print(f"  {v['name']}{desc}")
        print(f"    ID: {v['id']}")
        print(f"    Created: {v.get('createdAt', 'unknown')}")


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
               "  python create_version.py EH-0080-BB1 'V2 - Updated'\n"
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

    # Create version
    if not args.version_name:
        print("Error: VERSION_NAME is required when creating a version.")
        print("Usage: python create_version.py PROJECT_CODE VERSION_NAME [--description TEXT]")
        sys.exit(1)

    create_version(client, doc_id, doc_name, args.version_name, args.description)


if __name__ == "__main__":
    main()
