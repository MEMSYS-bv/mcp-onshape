"""Shared document registry and URL parsing for Onshape scripts.

Loads project-to-document mappings from onshape_documents.yaml,
and provides URL parsing utilities.
"""

import re
import sys
from pathlib import Path

import yaml

DEFAULT_YAML = Path(__file__).parent / "onshape_documents.yaml"


def load_documents(yaml_path: Path = None) -> dict:
    """Load the document registry from YAML."""
    path = yaml_path or DEFAULT_YAML
    if not path.exists():
        print(f"Error: Registry not found at {path}")
        sys.exit(1)
    with open(path) as f:
        data = yaml.safe_load(f)
    return data.get("documents", {})


def get_document_ids(project_code: str, workspace: str = None,
                     yaml_path: Path = None) -> tuple[str, str, str]:
    """Look up (document_id, workspace_id, element_id) by project code.
    
    Supports both flat and multi-workspace registry formats:
      Flat:  { document_id, workspace_id, element_id }
      Multi: { document_id, workspaces: { name: { workspace_id, element_id } }, default_workspace }
    
    Args:
        project_code: The project key in the registry (e.g. 'EH-0080-BB1').
        workspace: Optional workspace name for multi-workspace entries.
                   Falls back to default_workspace, then first workspace.
        yaml_path: Optional path to the YAML file.
    """
    docs = load_documents(yaml_path)
    if project_code not in docs:
        print(f"Error: '{project_code}' not found in registry.")
        print(f"Available: {', '.join(docs.keys())}")
        sys.exit(1)
    d = docs[project_code]
    did = d["document_id"]
    
    # Flat format (backward compatible)
    if "workspace_id" in d:
        return did, d["workspace_id"], d["element_id"]
    
    # Multi-workspace format
    workspaces = d.get("workspaces", {})
    if not workspaces:
        print(f"Error: '{project_code}' has no workspace_id or workspaces defined.")
        sys.exit(1)
    
    ws_name = workspace or d.get("default_workspace") or next(iter(workspaces))
    if ws_name not in workspaces:
        print(f"Error: workspace '{ws_name}' not found for '{project_code}'.")
        print(f"Available: {', '.join(workspaces.keys())}")
        sys.exit(1)
    
    ws = workspaces[ws_name]
    return did, ws["workspace_id"], ws["element_id"]


def get_drawing_map(project_code: str, yaml_path: Path = None) -> dict:
    """Get the explicit drawing-to-element mapping for a project.
    
    Returns a dict mapping part numbers to drawing element IDs,
    or an empty dict if no drawing_map is defined.
    """
    docs = load_documents(yaml_path)
    d = docs.get(project_code, {})
    return d.get("drawing_map", {})


def list_documents(yaml_path: Path = None):
    """Print all registered OnShape documents."""
    docs = load_documents(yaml_path)
    if not docs:
        print("No documents registered in onshape_documents.yaml")
        return
    print(f"\nRegistered OnShape documents ({len(docs)}):\n")
    print(f"  {'Code':<22} {'Name':<45} {'Workspaces'}")
    print(f"  {'-' * 22} {'-' * 45} {'-' * 20}")
    for code, info in docs.items():
        if "workspaces" in info:
            ws_names = ", ".join(info["workspaces"].keys())
            default = info.get("default_workspace", "")
            ws_display = f"{ws_names} (default: {default})" if default else ws_names
        else:
            ws_display = "flat"
        print(f"  {code:<22} {info['name'][:43]:<45} {ws_display}")
    print()


def parse_onshape_url(url: str) -> tuple[str, str, str]:
    """Extract (document_id, workspace_id, element_id) from an OnShape URL.

    Handles URLs like:
        https://cad.onshape.com/documents/{did}/w/{wid}/e/{eid}
    """
    pattern = r"documents/([a-f0-9]+)/w/([a-f0-9]+)(?:/e/([a-f0-9]+))?"
    match = re.search(pattern, url)
    if not match:
        print(f"Error: Could not parse OnShape URL: {url}")
        sys.exit(1)
    return match.group(1), match.group(2), match.group(3)
