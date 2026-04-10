"""Shared constants for Onshape API integration.

Contains standard Onshape metadata property IDs, BOM header IDs,
MEMSYS drawing templates, and material library references.
"""

# ── Standard OnShape BOM header IDs ──────────────────────────────────────────

BOM_HEADERS = {
    "item": "5ace8269c046ad612c65a0ba",
    "quantity": "5ace84d3c046ad611c65a0dd",
    "name": "57f3fb8efa3416c06701d60d",
    "part_number": "57f3fb8efa3416c06701d60f",
    "description": "57f3fb8efa3416c06701d60e",
    "material": "57f3fb8efa3416c06701d615",
    "revision": "57f3fb8efa3416c06701d616",
    "mass": "57f3fb8efa3416c06701d626",
    "state": "57f3fb8efa3416c06701d611",
}

# ── Metadata property IDs ─────────────────────────────────────────────────────

METADATA_PROPERTY_IDS = {
    "name": "57f3fb8efa3416c06701d60d",
    "description": "57f3fb8efa3416c06701d60e",
    "part_number": "57f3fb8efa3416c06701d60f",
    "revision": "57f3fb8efa3416c06701d616",
    "material": "57f3fb8efa3416c06701d615",
}

MATERIAL_PROPERTY_ID = "57f3fb8efa3416c06701d615"

# ── MEMSYS Drawing Templates (.dwt BLOB files) ───────────────────────────────

MEMSYS_TEMPLATES = {
    "A3": {
        "name": "MEMSYS A3 Template ML-0040",
        "document_id": "55bf94cb1518f5060f9802c3",
        "workspace_id": "73852bbdecfd9cc8027f2385",
        "element_id": "02c13bc68de0b7b353c5b8a7",
    },
    "A4-Portrait": {
        "name": "MEMSYS A4-Portrait Template ML-0040",
        "document_id": "55bf94cb1518f5060f9802c3",
        "workspace_id": "73852bbdecfd9cc8027f2385",
        "element_id": "25af5c0bbec13025fff919b2",
    },
}

# ── Onshape Material Library reference ────────────────────────────────────────

ONSHAPE_MATERIAL_LIBRARY = {
    "document_id": "2718281828459eacfeeda11f",
    "element_id": "6bbab304a1f64e7d640a2d7d",
    "workspace_id": "97628b48cc974c2681faacfc",
    "version_id": "7e0317fdf97739c9457998f0",
    "element_microversion_id": "b722224aa714b6346c7e8278",
    "library_name": "Onshape Material Library",
}

# ── Variable type mappings (for CSV sync) ─────────────────────────────────────

VARIABLE_TYPE_MAP = {
    "length": "LENGTH",
    "angle": "ANGLE",
    "real": "REAL",
    "integer": "INTEGER",
    "boolean": "BOOLEAN",
    "string": "STRING",
    "anything": "ANYTHING",
}

VARIABLE_UNIT_MAP = {
    "LENGTH": "mm",
    "ANGLE": "deg",
}

REVERSE_TYPE_MAP = {v: k.capitalize() for k, v in VARIABLE_TYPE_MAP.items()}
