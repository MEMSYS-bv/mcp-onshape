"""
Unified CLI entry point for Onshape MCP tooling.

Usage:
  python cli.py bom EH-0080-BB1                     # Extract BOM
  python cli.py bom --url "https://..." --format json
  python cli.py export EH-0080-BB1 --parts P-0016   # Export STEP+PDF
  python cli.py vars EH-0080-BB1 --get               # Show variables
  python cli.py vars EH-0080-BB1 --export backup.csv
  python cli.py vars EH-0080-BB1 --push vars.csv
  python cli.py meta EH-0080-BB1 --list              # Part metadata
  python cli.py check                                 # Connection test
  python cli.py check-compliance EH-0080-BB1          # Design guide compliance
  python cli.py docs                                  # List registered docs
  python cli.py create "My Document"                  # Create new document
  python cli.py cylinder --did X --wid Y --eid Z --diameter 30 --height 100
"""

import sys


def main():
    if len(sys.argv) < 2:
        print(__doc__.strip())
        sys.exit(1)

    command = sys.argv[1]
    # Remove the command from argv so sub-scripts see their own args
    sys.argv = [sys.argv[0]] + sys.argv[2:]

    if command == "bom":
        from extract_bom import main as bom_main
        bom_main()

    elif command == "export":
        from export_parts import main as export_main
        export_main()

    elif command == "vars":
        from sync_variables import main as vars_main
        vars_main()

    elif command == "meta":
        from set_part_metadata import main as meta_main
        meta_main()

    elif command == "check":
        from test_connection import main as check_main
        check_main()

    elif command == "docs":
        from document_registry import list_documents
        list_documents()

    elif command == "server":
        import asyncio
        from onshape_mcp_server import main as server_main
        asyncio.run(server_main())

    elif command == "create":
        _cmd_create()

    elif command == "cylinder":
        _cmd_cylinder()

    elif command == "check-compliance":
        from compliance_checker import main as compliance_main
        compliance_main()

    else:
        print(f"Unknown command: {command}")
        print("Available commands: bom, export, vars, meta, check, check-compliance, docs, server, create, cylinder")
        sys.exit(1)


def _cmd_create():
    """Create a new Onshape document."""
    import argparse
    parser = argparse.ArgumentParser(description="Create a new Onshape document")
    parser.add_argument("name", help="Document name")
    parser.add_argument("--description", "-d", default="", help="Document description")
    parser.add_argument("--public", action="store_true", help="Make document public")
    args = parser.parse_args()

    from onshape_api import OnshapeClient
    client = OnshapeClient()
    result = client.create_document(args.name, args.description, args.public)

    print(f"Document created: {result['name']}")
    print(f"  document_id:  {result['document_id']}")
    print(f"  workspace_id: {result['workspace_id']}")
    print(f"  element_id:   {result['element_id']}")
    print(f"  URL: {result['url']}")


def _cmd_cylinder():
    """Create a cylinder in a Part Studio."""
    import argparse
    parser = argparse.ArgumentParser(description="Create a cylinder in a Part Studio")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--url", help="Onshape URL of the Part Studio")
    group.add_argument("--did", help="Document ID (use with --wid and --eid)")
    parser.add_argument("--wid", help="Workspace ID")
    parser.add_argument("--eid", help="Part Studio element ID")
    parser.add_argument("--diameter", type=float, required=True, help="Diameter in mm")
    parser.add_argument("--height", type=float, required=True, help="Height in mm")
    parser.add_argument("--plane", default="Top", choices=["Top", "Front", "Right"],
                        help="Sketch plane (default: Top)")
    args = parser.parse_args()

    from onshape_api import OnshapeClient
    client = OnshapeClient()

    if args.url:
        from document_registry import parse_onshape_url
        ids = parse_onshape_url(args.url)
        did, wid, eid = ids["document_id"], ids["workspace_id"], ids["element_id"]
    else:
        if not args.wid or not args.eid:
            parser.error("--wid and --eid are required when using --did")
        did, wid, eid = args.did, args.wid, args.eid

    result = client.create_cylinder(did, wid, eid, args.diameter, args.height,
                                    plane=args.plane)
    print(f"Cylinder created (diameter={args.diameter}mm, height={args.height}mm):")
    print(f"  Sketch:  {result['sketch']['featureId']} — {result['sketch']['state'].get('featureStatus', '?')}")
    print(f"  Extrude: {result['extrude']['featureId']} — {result['extrude']['state'].get('featureStatus', '?')}")


if __name__ == "__main__":
    main()
