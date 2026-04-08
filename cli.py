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
  python cli.py docs                                  # List registered docs
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

    else:
        print(f"Unknown command: {command}")
        print("Available commands: bom, export, vars, meta, check, docs, server")
        sys.exit(1)


if __name__ == "__main__":
    main()
