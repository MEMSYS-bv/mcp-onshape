"""Quick test to verify Onshape API connectivity.

Usage:
    python test_connection.py [PROJECT_CODE]
    python test_connection.py              # defaults to first registered document
"""
import sys
from onshape_api import OnshapeClient
from document_registry import load_documents

def main():
    client = OnshapeClient()
    docs = load_documents()

    if len(sys.argv) > 1:
        code = sys.argv[1]
        if code not in docs:
            print(f"Unknown project code '{code}'. Available: {', '.join(docs.keys())}")
            sys.exit(1)
        doc_id = docs[code]["document_id"]
        ws_id = docs[code]["workspace_id"]
    else:
        code = next(iter(docs))
        doc_id = docs[code]["document_id"]
        ws_id = docs[code]["workspace_id"]

    # Test 1: Get document info
    print(f"Testing connection with '{code}' ({doc_id[:12]}...)...")
    try:
        d = client.get_document(doc_id)
        print(f"  Document: {d.get('name')}")
        print(f"  Owner: {d.get('owner', {}).get('name')}")
    except Exception as e:
        print(f"  FAILED: {e}")
        sys.exit(1)

    # Test 2: Get elements
    print(f"\n  Elements in workspace {ws_id[:12]}...:")
    try:
        elements = client.get_elements(doc_id, ws_id)
        for e in elements:
            print(f"    {e.get('elementType'):15s} | {e.get('id')[:12]}... | {e.get('name')}")
    except Exception as e:
        print(f"  FAILED: {e}")
        sys.exit(1)

    print("\n  Connection OK!")


if __name__ == "__main__":
    main()
