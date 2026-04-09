"""
Onshape MCP Server for GitHub Copilot Integration

This MCP server provides tools to read and write variables from Onshape Variable Studios,
allowing Copilot to interact directly with your CAD parameters.

Author: Sander
Created: 2026-01-20
"""

import json
import logging
from typing import Any
import requests
from mcp.server import Server
from mcp.types import Tool, TextContent
from mcp.server.stdio import stdio_server

from onshape_api import OnshapeClient
from constants import BOM_HEADERS, MEMSYS_TEMPLATES

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("onshape-mcp")

# Initialize the MCP server
server = Server("onshape-mcp")

# Initialize client (credentials loaded from .env by OnshapeClient)
client = OnshapeClient()


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available Onshape tools."""
    return [
        Tool(
            name="onshape_get_document",
            description="Get information about an Onshape document by its ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": "The Onshape document ID (from the URL after /documents/)"
                    }
                },
                "required": ["document_id"]
            }
        ),
        Tool(
            name="onshape_list_variable_studios",
            description="List all Variable Studios in an Onshape document",
            inputSchema={
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": "The Onshape document ID"
                    },
                    "workspace_id": {
                        "type": "string",
                        "description": "The workspace ID (from the URL after /w/)"
                    }
                },
                "required": ["document_id", "workspace_id"]
            }
        ),
        Tool(
            name="onshape_get_variables",
            description="Get all variables from an Onshape Variable Studio. Returns variable names, values, and expressions.",
            inputSchema={
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": "The Onshape document ID"
                    },
                    "workspace_id": {
                        "type": "string",
                        "description": "The workspace ID"
                    },
                    "element_id": {
                        "type": "string",
                        "description": "The Variable Studio element ID (from the URL after /e/)"
                    }
                },
                "required": ["document_id", "workspace_id", "element_id"]
            }
        ),
        Tool(
            name="onshape_set_variable",
            description="Set a variable value in an Onshape Variable Studio. Use Onshape expression syntax (e.g., '10 mm', '5 in', '25.4').",
            inputSchema={
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": "The Onshape document ID"
                    },
                    "workspace_id": {
                        "type": "string",
                        "description": "The workspace ID"
                    },
                    "element_id": {
                        "type": "string",
                        "description": "The Variable Studio element ID"
                    },
                    "variable_name": {
                        "type": "string",
                        "description": "Name of the variable to set"
                    },
                    "expression": {
                        "type": "string",
                        "description": "The value expression (e.g., '10 mm', '5 in', 'length * 2')"
                    }
                },
                "required": ["document_id", "workspace_id", "element_id", "variable_name", "expression"]
            }
        ),
        Tool(
            name="onshape_set_multiple_variables",
            description="Set multiple variables at once in an Onshape Variable Studio.",
            inputSchema={
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": "The Onshape document ID"
                    },
                    "workspace_id": {
                        "type": "string",
                        "description": "The workspace ID"
                    },
                    "element_id": {
                        "type": "string",
                        "description": "The Variable Studio element ID"
                    },
                    "variables": {
                        "type": "array",
                        "description": "Array of variables to set",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "expression": {"type": "string"}
                            },
                            "required": ["name", "expression"]
                        }
                    }
                },
                "required": ["document_id", "workspace_id", "element_id", "variables"]
            }
        ),
        Tool(
            name="onshape_parse_url",
            description="Parse an Onshape document URL to extract document_id, workspace_id, and element_id",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "Full Onshape document URL"
                    }
                },
                "required": ["url"]
            }
        ),
        # ========== DRAWING TOOLS ==========
        Tool(
            name="onshape_list_templates",
            description="List available MEMSYS drawing templates",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="onshape_list_drawings",
            description="List all drawings in an Onshape document",
            inputSchema={
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": "The Onshape document ID"
                    },
                    "workspace_id": {
                        "type": "string",
                        "description": "The workspace ID"
                    }
                },
                "required": ["document_id", "workspace_id"]
            }
        ),
        Tool(
            name="onshape_create_drawing",
            description="Create a new drawing from a MEMSYS template. Optionally specify a Part Studio to create views from.",
            inputSchema={
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": "Target document ID where drawing will be created"
                    },
                    "workspace_id": {
                        "type": "string",
                        "description": "The workspace ID"
                    },
                    "drawing_name": {
                        "type": "string",
                        "description": "Name for the new drawing"
                    },
                    "template": {
                        "type": "string",
                        "description": "Template to use: 'A3' or 'A4-Portrait' (default: A3)",
                        "enum": ["A3", "A4-Portrait"]
                    },
                    "part_element_id": {
                        "type": "string",
                        "description": "Optional: Element ID of Part Studio to create drawing from"
                    },
                    "part_id": {
                        "type": "string",
                        "description": "Optional: Specific part ID within the Part Studio"
                    }
                },
                "required": ["document_id", "workspace_id", "drawing_name"]
            }
        ),
        Tool(
            name="onshape_get_drawing_views",
            description="Get all views in a drawing",
            inputSchema={
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": "The Onshape document ID"
                    },
                    "workspace_id": {
                        "type": "string",
                        "description": "The workspace ID"
                    },
                    "element_id": {
                        "type": "string",
                        "description": "The drawing element ID"
                    }
                },
                "required": ["document_id", "workspace_id", "element_id"]
            }
        ),
        Tool(
            name="onshape_add_view",
            description="Add a view to an existing drawing. View types: front, back, top, bottom, left, right, isometric",
            inputSchema={
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": "The Onshape document ID"
                    },
                    "workspace_id": {
                        "type": "string",
                        "description": "The workspace ID"
                    },
                    "drawing_element_id": {
                        "type": "string",
                        "description": "The drawing element ID"
                    },
                    "source_element_id": {
                        "type": "string",
                        "description": "Element ID of Part Studio or Assembly to add view from"
                    },
                    "view_type": {
                        "type": "string",
                        "description": "View orientation: front, back, top, bottom, left, right, isometric",
                        "enum": ["front", "back", "top", "bottom", "left", "right", "isometric"]
                    },
                    "position_x": {
                        "type": "number",
                        "description": "X position on drawing (default: 200)"
                    },
                    "position_y": {
                        "type": "number",
                        "description": "Y position on drawing (default: 150)"
                    },
                    "scale": {
                        "type": "number",
                        "description": "View scale, e.g., 1.0 = 1:1, 0.5 = 1:2 (default: 1.0)"
                    },
                    "part_id": {
                        "type": "string",
                        "description": "Optional: Specific part ID for single part view"
                    }
                },
                "required": ["document_id", "workspace_id", "drawing_element_id", "source_element_id", "view_type"]
            }
        ),
        Tool(
            name="onshape_get_parts",
            description="Get all parts in a Part Studio or Assembly",
            inputSchema={
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": "The Onshape document ID"
                    },
                    "workspace_id": {
                        "type": "string",
                        "description": "The workspace ID"
                    },
                    "element_id": {
                        "type": "string",
                        "description": "The Part Studio or Assembly element ID"
                    }
                },
                "required": ["document_id", "workspace_id", "element_id"]
            }
        ),
        Tool(
            name="onshape_add_note",
            description="Add a text note to a drawing. Can be used to add part numbers, titles, or any text annotation.",
            inputSchema={
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": "The Onshape document ID"
                    },
                    "workspace_id": {
                        "type": "string",
                        "description": "The workspace ID"
                    },
                    "drawing_element_id": {
                        "type": "string",
                        "description": "The drawing element ID"
                    },
                    "text": {
                        "type": "string",
                        "description": "The text content of the note"
                    },
                    "position_x": {
                        "type": "number",
                        "description": "X position on drawing (default: 380 for title block area)"
                    },
                    "position_y": {
                        "type": "number",
                        "description": "Y position on drawing (default: 15 for title block area)"
                    },
                    "text_height": {
                        "type": "number",
                        "description": "Height of the text (default: 0.12)"
                    }
                },
                "required": ["document_id", "workspace_id", "drawing_element_id", "text"]
            }
        ),
        Tool(
            name="onshape_create_complete_drawing",
            description="Create a complete drawing with title and drawing number notes. Automatically adds both to the title block area.",
            inputSchema={
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": "Target document ID"
                    },
                    "workspace_id": {
                        "type": "string",
                        "description": "The workspace ID"
                    },
                    "part_name": {
                        "type": "string",
                        "description": "Name of the part (used for drawing name and title note)"
                    },
                    "drawing_number": {
                        "type": "string",
                        "description": "Drawing number (e.g., 'DRW-0001', 'EH-0080-01'). Added below title in title block."
                    },
                    "part_element_id": {
                        "type": "string",
                        "description": "Element ID of the Part Studio containing the part"
                    },
                    "part_id": {
                        "type": "string",
                        "description": "Part ID within the Part Studio"
                    },
                    "template": {
                        "type": "string",
                        "description": "Template: 'A3' or 'A4-Portrait' (default: A3)",
                        "enum": ["A3", "A4-Portrait"]
                    }
                },
                "required": ["document_id", "workspace_id", "part_name", "part_element_id", "part_id"]
            }
        ),
        Tool(
            name="onshape_get_bom",
            description="Get the Bill of Materials (BOM) for an OnShape assembly. Returns a formatted table with part numbers, names, quantities, materials, and masses. Use this for any BOM extraction or part inventory queries.",
            inputSchema={
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": "The Onshape document ID"
                    },
                    "workspace_id": {
                        "type": "string",
                        "description": "The workspace ID"
                    },
                    "element_id": {
                        "type": "string",
                        "description": "The Assembly element ID (must be an Assembly, not Part Studio)"
                    },
                    "format": {
                        "type": "string",
                        "description": "Output format: 'table' for formatted text table, 'markdown' for Markdown table, 'raw' for raw JSON. Default: 'markdown'",
                        "enum": ["table", "markdown", "raw"]
                    }
                },
                "required": ["document_id", "workspace_id", "element_id"]
            }
        ),
        # ========== DOCUMENT DISCOVERY TOOLS ==========
        Tool(
            name="onshape_search_documents",
            description="Search for Onshape documents by name or description. Returns matching documents with their IDs, owners, and modification dates. Use this to find a document without knowing its ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search text to match against document names and descriptions"
                    },
                    "owner_type": {
                        "type": "string",
                        "description": "Filter by ownership: '0' = My docs, '1' = Created by me, '2' = Shared with me. Default: '1'",
                        "enum": ["0", "1", "2"]
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 20)"
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="onshape_get_document_summary",
            description="Get a comprehensive summary of an Onshape document: all workspaces and their elements (Part Studios, Assemblies, Drawings, Variable Studios, etc.) in a single call. Use this to understand the full structure of a document.",
            inputSchema={
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": "The Onshape document ID"
                    }
                },
                "required": ["document_id"]
            }
        ),
        Tool(
            name="onshape_get_features",
            description="Get the feature tree of a Part Studio. Returns all features (sketches, extrudes, fillets, etc.) with their names, types, suppression state, and parameters. Use this to inspect the design history of a Part Studio.",
            inputSchema={
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": "The Onshape document ID"
                    },
                    "workspace_id": {
                        "type": "string",
                        "description": "The workspace ID"
                    },
                    "element_id": {
                        "type": "string",
                        "description": "The Part Studio element ID"
                    }
                },
                "required": ["document_id", "workspace_id", "element_id"]
            }
        ),
        Tool(
            name="onshape_find_part_studios",
            description="Find Part Studio elements in a document workspace, optionally filtered by name pattern. Returns element names and IDs.",
            inputSchema={
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": "The Onshape document ID"
                    },
                    "workspace_id": {
                        "type": "string",
                        "description": "The workspace ID"
                    },
                    "name_pattern": {
                        "type": "string",
                        "description": "Optional: case-insensitive substring to filter Part Studio names (e.g., 'cantilever', 'base')"
                    }
                },
                "required": ["document_id", "workspace_id"]
            }
        ),
        Tool(
            name="onshape_get_assembly_definition",
            description="Get the full assembly definition: instances (parts and sub-assemblies), mates, mate connectors, and transforms. Use this to understand how an assembly is structured beyond just the BOM.",
            inputSchema={
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": "The Onshape document ID"
                    },
                    "workspace_id": {
                        "type": "string",
                        "description": "The workspace ID"
                    },
                    "element_id": {
                        "type": "string",
                        "description": "The Assembly element ID"
                    }
                },
                "required": ["document_id", "workspace_id", "element_id"]
            }
        ),
        # ========== MATERIAL TOOLS ==========
        Tool(
            name="onshape_list_materials",
            description="List available materials from the Onshape Material Library (189 materials). Optionally filter by category: 'Metal', 'Plastic', 'Wood', 'Ceramic', 'Composite', 'Other'. Returns exact material names needed for onshape_set_part_material.",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Optional: filter by material category (case-insensitive). Common values: 'Metal', 'Plastic', 'Wood', 'Ceramic', 'Composite'"
                    },
                    "search": {
                        "type": "string",
                        "description": "Optional: filter material names by substring (case-insensitive), e.g. 'aluminum', 'steel', 'nylon'"
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="onshape_set_part_material",
            description="Set the material of a part in a Part Studio. Requires the exact material name from the Onshape Material Library (use onshape_list_materials to find it). The part is identified by document_id, workspace_id, element_id (Part Studio), and part_id.",
            inputSchema={
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": "The Onshape document ID"
                    },
                    "workspace_id": {
                        "type": "string",
                        "description": "The workspace ID"
                    },
                    "element_id": {
                        "type": "string",
                        "description": "The Part Studio element ID containing the part"
                    },
                    "part_id": {
                        "type": "string",
                        "description": "The part ID within the Part Studio (from BOM or parts list)"
                    },
                    "material_name": {
                        "type": "string",
                        "description": "Exact material name from the Onshape Material Library (e.g. 'Aluminum - 6061', '300 Series Stainless Steel', 'Nylon')"
                    }
                },
                "required": ["document_id", "workspace_id", "element_id", "part_id", "material_name"]
            }
        ),
        # ========== EXPORT TOOLS ==========
        Tool(
            name="onshape_export_step",
            description="Export a part from a Part Studio as a STEP file. Starts an async translation, polls until done, and downloads the result. Can take 10-60 seconds depending on part complexity.",
            inputSchema={
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": "The Onshape document ID"
                    },
                    "workspace_id": {
                        "type": "string",
                        "description": "The workspace ID"
                    },
                    "element_id": {
                        "type": "string",
                        "description": "The Part Studio element ID containing the part"
                    },
                    "part_id": {
                        "type": "string",
                        "description": "The part ID to export (from BOM or parts list)"
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Full file path to save the STEP file (e.g. 'C:/exports/part.step')"
                    }
                },
                "required": ["document_id", "workspace_id", "element_id", "part_id", "output_path"]
            }
        ),
        Tool(
            name="onshape_export_drawing_pdf",
            description="Export a drawing as a PDF file. Starts an async translation, polls until done, and downloads the result. Use onshape_list_drawings first to find the drawing element_id.",
            inputSchema={
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": "The Onshape document ID"
                    },
                    "workspace_id": {
                        "type": "string",
                        "description": "The workspace ID"
                    },
                    "element_id": {
                        "type": "string",
                        "description": "The Drawing element ID to export"
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Full file path to save the PDF file (e.g. 'C:/exports/drawing.pdf')"
                    }
                },
                "required": ["document_id", "workspace_id", "element_id", "output_path"]
            }
        ),
        Tool(
            name="onshape_create_document",
            description="Create a new Onshape document with a default Part Studio. Returns document_id, workspace_id, and element_id (Part Studio) for immediate use.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name for the new document"
                    },
                    "description": {
                        "type": "string",
                        "description": "Optional description"
                    },
                    "is_public": {
                        "type": "boolean",
                        "description": "Whether the document is publicly accessible (default: false)"
                    }
                },
                "required": ["name"]
            }
        ),
        Tool(
            name="onshape_delete_document",
            description="Delete an Onshape document permanently. WARNING: This is irreversible.",
            inputSchema={
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": "The Onshape document ID to delete"
                    }
                },
                "required": ["document_id"]
            }
        ),
        Tool(
            name="onshape_add_feature",
            description="Add a feature (sketch, extrude, etc.) to a Part Studio. Provide the raw feature JSON. Use onshape_create_cylinder for a simpler workflow.",
            inputSchema={
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": "The Onshape document ID"
                    },
                    "workspace_id": {
                        "type": "string",
                        "description": "The workspace ID"
                    },
                    "element_id": {
                        "type": "string",
                        "description": "The Part Studio element ID"
                    },
                    "feature": {
                        "type": "object",
                        "description": "Feature definition JSON (btType BTMFeature-134 or BTMSketch-151)"
                    }
                },
                "required": ["document_id", "workspace_id", "element_id", "feature"]
            }
        ),
        Tool(
            name="onshape_create_cylinder",
            description="Create a cylinder in a Part Studio by adding a circle sketch and extruding it. All dimensions in millimeters.",
            inputSchema={
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": "The Onshape document ID"
                    },
                    "workspace_id": {
                        "type": "string",
                        "description": "The workspace ID"
                    },
                    "element_id": {
                        "type": "string",
                        "description": "The Part Studio element ID"
                    },
                    "diameter_mm": {
                        "type": "number",
                        "description": "Cylinder diameter in millimeters"
                    },
                    "height_mm": {
                        "type": "number",
                        "description": "Cylinder height in millimeters"
                    },
                    "plane": {
                        "type": "string",
                        "description": "Sketch plane: 'Top', 'Front', or 'Right' (default: 'Top')",
                        "enum": ["Top", "Front", "Right"]
                    },
                    "center_x_mm": {
                        "type": "number",
                        "description": "X position of center in mm (default: 0)"
                    },
                    "center_y_mm": {
                        "type": "number",
                        "description": "Y position of center in mm (default: 0)"
                    }
                },
                "required": ["document_id", "workspace_id", "element_id", "diameter_mm", "height_mm"]
            }
        ),
        Tool(
            name="onshape_add_extrude",
            description="Add an extrude feature to a Part Studio. Extrudes all regions of a specified sketch.",
            inputSchema={
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": "The Onshape document ID"
                    },
                    "workspace_id": {
                        "type": "string",
                        "description": "The workspace ID"
                    },
                    "element_id": {
                        "type": "string",
                        "description": "The Part Studio element ID"
                    },
                    "sketch_feature_id": {
                        "type": "string",
                        "description": "Feature ID of the sketch to extrude (from onshape_get_features or onshape_add_feature response)"
                    },
                    "depth_mm": {
                        "type": "number",
                        "description": "Extrusion depth in millimeters"
                    },
                    "name": {
                        "type": "string",
                        "description": "Feature name (default: 'Extrude 1')"
                    },
                    "operation": {
                        "type": "string",
                        "description": "Body operation: 'NEW', 'ADD' (join), 'REMOVE' (cut), 'INTERSECT'",
                        "enum": ["NEW", "ADD", "REMOVE", "INTERSECT"]
                    },
                    "direction": {
                        "type": "string",
                        "description": "Extrude direction: 'BLIND', 'SYMMETRIC', 'THROUGH_ALL'",
                        "enum": ["BLIND", "SYMMETRIC", "THROUGH_ALL"]
                    }
                },
                "required": ["document_id", "workspace_id", "element_id", "sketch_feature_id", "depth_mm"]
            }
        ),
        Tool(
            name="onshape_add_sketch_circle",
            description="Add a sketch with a single circle to a Part Studio. Returns the sketch feature ID for use with onshape_add_extrude.",
            inputSchema={
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": "The Onshape document ID"
                    },
                    "workspace_id": {
                        "type": "string",
                        "description": "The workspace ID"
                    },
                    "element_id": {
                        "type": "string",
                        "description": "The Part Studio element ID"
                    },
                    "radius_mm": {
                        "type": "number",
                        "description": "Circle radius in millimeters"
                    },
                    "plane": {
                        "type": "string",
                        "description": "Sketch plane: 'Top', 'Front', or 'Right' (default: 'Top')",
                        "enum": ["Top", "Front", "Right"]
                    },
                    "center_x_mm": {
                        "type": "number",
                        "description": "X position of center in mm (default: 0)"
                    },
                    "center_y_mm": {
                        "type": "number",
                        "description": "Y position of center in mm (default: 0)"
                    },
                    "name": {
                        "type": "string",
                        "description": "Sketch name (default: 'Sketch 1')"
                    }
                },
                "required": ["document_id", "workspace_id", "element_id", "radius_mm"]
            }
        ),
        Tool(
            name="onshape_add_sketch_rectangle",
            description="Add a sketch with a rectangle to a Part Studio. Returns the sketch feature ID for use with onshape_add_extrude.",
            inputSchema={
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": "The Onshape document ID"
                    },
                    "workspace_id": {
                        "type": "string",
                        "description": "The workspace ID"
                    },
                    "element_id": {
                        "type": "string",
                        "description": "The Part Studio element ID"
                    },
                    "width_mm": {
                        "type": "number",
                        "description": "Rectangle width in millimeters"
                    },
                    "height_mm": {
                        "type": "number",
                        "description": "Rectangle height in millimeters"
                    },
                    "plane": {
                        "type": "string",
                        "description": "Sketch plane: 'Top', 'Front', or 'Right' (default: 'Top')",
                        "enum": ["Top", "Front", "Right"]
                    },
                    "center_x_mm": {
                        "type": "number",
                        "description": "X position of center in mm (default: 0)"
                    },
                    "center_y_mm": {
                        "type": "number",
                        "description": "Y position of center in mm (default: 0)"
                    },
                    "name": {
                        "type": "string",
                        "description": "Sketch name (default: 'Sketch 1')"
                    }
                },
                "required": ["document_id", "workspace_id", "element_id", "width_mm", "height_mm"]
            }
        ),
        Tool(
            name="onshape_delete_feature",
            description="Delete a feature from a Part Studio by its feature ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": "The Onshape document ID"
                    },
                    "workspace_id": {
                        "type": "string",
                        "description": "The workspace ID"
                    },
                    "element_id": {
                        "type": "string",
                        "description": "The Part Studio element ID"
                    },
                    "feature_id": {
                        "type": "string",
                        "description": "The feature ID to delete"
                    }
                },
                "required": ["document_id", "workspace_id", "element_id", "feature_id"]
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls."""
    try:
        if name == "onshape_get_document":
            result = client.get_document(arguments["document_id"])
            return [TextContent(
                type="text",
                text=f"Document: {result['name']}\n"
                     f"ID: {result['id']}\n"
                     f"Owner: {result.get('owner', {}).get('name', 'Unknown')}\n"
                     f"Created: {result.get('createdAt', 'Unknown')}"
            )]
        
        elif name == "onshape_list_variable_studios":
            studios = client.get_variable_studios(
                arguments["document_id"],
                arguments["workspace_id"]
            )
            if not studios:
                return [TextContent(type="text", text="No Variable Studios found in this document.")]
            
            result_text = "Variable Studios found:\n"
            for studio in studios:
                result_text += f"  - {studio['name']} (element_id: {studio['id']})\n"
            return [TextContent(type="text", text=result_text)]
        
        elif name == "onshape_get_variables":
            result = client.get_variables(
                arguments["document_id"],
                arguments["workspace_id"],
                arguments["element_id"]
            )
            
            # Handle response format (list with variableStudioReference wrapper)
            if isinstance(result, list) and len(result) > 0:
                variables = result[0].get("variables", [])
            else:
                variables = result.get("variables", [])
                
            if not variables:
                return [TextContent(type="text", text="No variables found in this Variable Studio.")]
            
            result_text = "Variables:\n"
            result_text += "-" * 70 + "\n"
            result_text += f"{'Name':<22} {'Expression':<15} {'Description':<30}\n"
            result_text += "-" * 70 + "\n"
            
            for var in variables:
                name = var.get("name", "")
                expression = var.get("expression", "")
                description = var.get("description", "")[:28]
                result_text += f"{name:<22} {expression:<15} {description:<30}\n"
            
            return [TextContent(type="text", text=result_text)]
        
        elif name == "onshape_set_variable":
            # First, get ALL existing variables (API replaces all, not just one!)
            existing = client.get_variables(
                arguments["document_id"],
                arguments["workspace_id"],
                arguments["element_id"]
            )
            
            # Handle response format (list with variableStudioReference wrapper)
            if isinstance(existing, list) and len(existing) > 0:
                all_vars = existing[0].get("variables", [])
            else:
                all_vars = existing.get("variables", [])
            
            # Update the specific variable
            var_name = arguments["variable_name"]
            found = False
            updated_vars = []
            for var in all_vars:
                if var["name"] == var_name:
                    updated_vars.append({
                        "name": var_name,
                        "type": var.get("type", "LENGTH"),
                        "expression": arguments["expression"],
                        "description": var.get("description", "")
                    })
                    found = True
                else:
                    updated_vars.append({
                        "name": var["name"],
                        "type": var.get("type", "LENGTH"),
                        "expression": var["expression"],
                        "description": var.get("description", "")
                    })
            
            if not found:
                return [TextContent(type="text", text=f"⚠ Variable '{var_name}' not found. Available: {[v['name'] for v in all_vars]}")]
            
            # Now update all variables
            result = client.set_variables(
                arguments["document_id"],
                arguments["workspace_id"],
                arguments["element_id"],
                updated_vars
            )
            return [TextContent(
                type="text",
                text=f"✓ Variable '{var_name}' set to '{arguments['expression']}'"
            )]
        
        elif name == "onshape_set_multiple_variables":
            # First, get ALL existing variables
            existing = client.get_variables(
                arguments["document_id"],
                arguments["workspace_id"],
                arguments["element_id"]
            )
            
            if isinstance(existing, list) and len(existing) > 0:
                all_vars = existing[0].get("variables", [])
            else:
                all_vars = existing.get("variables", [])
            
            # Build update map
            updates = {v["name"]: v["expression"] for v in arguments["variables"]}
            
            # Update variables
            updated_vars = []
            for var in all_vars:
                name = var["name"]
                if name in updates:
                    updated_vars.append({
                        "name": name,
                        "type": var.get("type", "LENGTH"),
                        "expression": updates[name],
                        "description": var.get("description", "")
                    })
                else:
                    updated_vars.append({
                        "name": name,
                        "type": var.get("type", "LENGTH"),
                        "expression": var["expression"],
                        "description": var.get("description", "")
                    })
            
            result = client.set_variables(
                arguments["document_id"],
                arguments["workspace_id"],
                arguments["element_id"],
                updated_vars
            )
            var_names = list(updates.keys())
            return [TextContent(
                type="text",
                text=f"✓ Updated {len(var_names)} variables: {', '.join(var_names)}"
            )]
        
        elif name == "onshape_parse_url":
            url = arguments["url"]
            # Parse URL like: https://cad.onshape.com/documents/{did}/w/{wid}/e/{eid}
            import re
            pattern = r"/documents/([^/]+)/w/([^/]+)/e/([^/]+)"
            match = re.search(pattern, url)
            
            if match:
                return [TextContent(
                    type="text",
                    text=f"Parsed URL:\n"
                         f"  document_id: {match.group(1)}\n"
                         f"  workspace_id: {match.group(2)}\n"
                         f"  element_id: {match.group(3)}"
                )]
            else:
                return [TextContent(type="text", text="Could not parse URL. Expected format: /documents/{did}/w/{wid}/e/{eid}")]
        
        # ========== DRAWING TOOL HANDLERS ==========
        
        elif name == "onshape_list_templates":
            result_text = "Available MEMSYS Drawing Templates:\n"
            result_text += "-" * 50 + "\n"
            for key, template in MEMSYS_TEMPLATES.items():
                result_text += f"\n📄 {key}:\n"
                result_text += f"   Name: {template['name']}\n"
                result_text += f"   Document ID: {template['document_id']}\n"
                result_text += f"   Element ID: {template['element_id']}\n"
            return [TextContent(type="text", text=result_text)]
        
        elif name == "onshape_list_drawings":
            drawings = client.list_drawings(
                arguments["document_id"],
                arguments["workspace_id"]
            )
            if not drawings:
                return [TextContent(type="text", text="No drawings found in this document.")]
            
            result_text = f"Drawings found ({len(drawings)}):\n"
            for d in drawings:
                result_text += f"  - {d.get('name')} (element_id: {d.get('id')})\n"
            return [TextContent(type="text", text=result_text)]
        
        elif name == "onshape_create_drawing":
            template_key = arguments.get("template", "A3")
            result = client.create_drawing(
                arguments["document_id"],
                arguments["workspace_id"],
                arguments["drawing_name"],
                arguments.get("part_element_id"),
                arguments.get("part_id"),
                template_key
            )
            return [TextContent(
                type="text",
                text=f"✓ Drawing created: {result.get('name', arguments['drawing_name'])}\n"
                     f"  Element ID: {result.get('id', 'N/A')}\n"
                     f"  Template: {template_key}"
            )]
        
        elif name == "onshape_get_drawing_views":
            views = client.get_drawing_views(
                arguments["document_id"],
                arguments["workspace_id"],
                arguments["element_id"]
            )
            if not views:
                return [TextContent(type="text", text="No views found in this drawing.")]
            
            result_text = f"Drawing Views ({len(views)}):\n"
            for v in views:
                result_text += f"  - {v.get('name', 'Unnamed')} (viewId: {v.get('viewId', 'N/A')})\n"
                result_text += f"    Type: {v.get('viewType', 'N/A')}, Scale: {v.get('scale', 'N/A')}\n"
            return [TextContent(type="text", text=result_text)]
        
        elif name == "onshape_add_view":
            position = {
                "x": arguments.get("position_x", 200),
                "y": arguments.get("position_y", 150)
            }
            result = client.add_drawing_view(
                arguments["document_id"],
                arguments["workspace_id"],
                arguments["drawing_element_id"],
                arguments["source_element_id"],
                arguments["view_type"],
                position,
                arguments.get("scale", 1.0),
                arguments.get("part_id")
            )
            mod_id = result.get("id", "N/A")
            return [TextContent(
                type="text",
                text=f"✓ View added ({arguments['view_type']})\n"
                     f"  Modification ID: {mod_id}\n"
                     f"  Position: ({position['x']}, {position['y']})\n"
                     f"  Note: Poll modification status with ID to confirm completion"
            )]
        
        elif name == "onshape_get_parts":
            try:
                # Try as Part Studio first
                parts = client.get_parts(
                    arguments["document_id"],
                    arguments["workspace_id"],
                    arguments["element_id"]
                )
            except:
                # If that fails, try as Assembly
                try:
                    assembly = client.get_assembly_parts(
                        arguments["document_id"],
                        arguments["workspace_id"],
                        arguments["element_id"]
                    )
                    parts = assembly.get("parts", [])
                except:
                    parts = []
            
            if not parts:
                return [TextContent(type="text", text="No parts found in this element.")]
            
            result_text = f"Parts found ({len(parts)}):\n"
            result_text += "-" * 60 + "\n"
            for p in parts:
                result_text += f"  - {p.get('name', 'Unnamed')}\n"
                result_text += f"    Part ID: {p.get('partId', 'N/A')}\n"
                result_text += f"    Element ID: {p.get('elementId', 'N/A')}\n"
            return [TextContent(type="text", text=result_text)]
        
        elif name == "onshape_add_note":
            position = {
                "x": arguments.get("position_x", 380),
                "y": arguments.get("position_y", 15),
                "z": 0
            }
            result = client.add_note(
                arguments["document_id"],
                arguments["workspace_id"],
                arguments["drawing_element_id"],
                arguments["text"],
                position,
                arguments.get("text_height", 0.12)
            )
            mod_id = result.get("id", "N/A")
            return [TextContent(
                type="text",
                text=f"✓ Note added: \"{arguments['text']}\"\n"
                     f"  Position: ({position['x']}, {position['y']})\n"
                     f"  Modification ID: {mod_id}"
            )]
        
        elif name == "onshape_create_complete_drawing":
            template_key = arguments.get("template", "A3")
            drawing_number = arguments.get("drawing_number")
            result = client.create_drawing_with_views(
                arguments["document_id"],
                arguments["workspace_id"],
                arguments["part_name"],
                arguments["part_element_id"],
                arguments["part_id"],
                template_key,
                drawing_number=drawing_number,
                add_title_note=True
            )
            drawing_id = result["drawing"].get("id", "N/A")
            drawing_name = result["drawing"].get("name", arguments["part_name"])
            
            result_text = f"✓ Complete drawing created!\n"
            result_text += f"  Name: {drawing_name}\n"
            result_text += f"  Element ID: {drawing_id}\n"
            result_text += f"  Template: {template_key}\n"
            if drawing_number:
                result_text += f"  Drawing Number: {drawing_number}\n"
            
            for mod in result.get("modifications", []):
                if "error" in mod:
                    result_text += f"  ⚠ {mod['type']}: {mod['error']}\n"
                else:
                    result_text += f"  ✓ {mod['type']}: OK\n"
            
            return [TextContent(type="text", text=result_text)]
        
        elif name == "onshape_get_bom":
            bom = client.get_assembly_bom(
                arguments["document_id"],
                arguments["workspace_id"],
                arguments["element_id"]
            )
            
            output_format = arguments.get("format", "markdown")
            
            if output_format == "raw":
                return [TextContent(type="text", text=json.dumps(bom, indent=2))]
            
            # Build header ID to name mapping
            header_map = {}
            for header in bom.get("headers", []):
                header_map[header.get("id")] = header.get("name")
            
            # Known header IDs
            item_id = BOM_HEADERS['item']
            part_number_id = BOM_HEADERS['part_number']
            name_id = BOM_HEADERS['name']
            qty_id = BOM_HEADERS['quantity']
            desc_id = BOM_HEADERS['description']
            material_id = BOM_HEADERS['material']
            mass_id = BOM_HEADERS['mass']
            
            rows = bom.get("rows", [])
            
            if not rows:
                return [TextContent(type="text", text="No BOM rows found for this assembly.")]
            
            # Parse rows
            parsed_rows = []
            total_mass = 0.0
            for i, row in enumerate(rows, 1):
                hv = row.get("headerIdToValue", {})
                
                part_num = hv.get(part_number_id, "—")
                name_val = hv.get(name_id, "Unknown")
                qty = hv.get(qty_id, 1)
                
                material_data = hv.get(material_id)
                if isinstance(material_data, dict):
                    material = material_data.get("displayName", "—")
                else:
                    material = str(material_data) if material_data else "—"
                
                mass_raw = hv.get(mass_id, "—")
                mass_str = str(mass_raw) if mass_raw else "—"
                
                # Try to accumulate total mass
                try:
                    mass_val = float(str(mass_raw).replace(" g", "").replace("g", ""))
                    total_mass += mass_val * (int(qty) if isinstance(qty, (int, str)) and str(qty).isdigit() else 1)
                except (ValueError, TypeError):
                    pass
                
                parsed_rows.append({
                    "num": i,
                    "part_number": str(part_num),
                    "name": str(name_val),
                    "qty": str(qty),
                    "material": str(material),
                    "mass": mass_str
                })
            
            if output_format == "markdown":
                result_text = f"## Bill of Materials — {bom.get('name', 'Assembly')}\n\n"
                result_text += f"**Total items:** {len(rows)} | **Total mass:** ~{total_mass:.1f} g\n\n"
                result_text += "| # | Part Number | Name | Qty | Material | Mass |\n"
                result_text += "|---|-------------|------|-----|----------|------|\n"
                for r in parsed_rows:
                    result_text += f"| {r['num']} | {r['part_number']} | {r['name']} | {r['qty']} | {r['material']} | {r['mass']} |\n"
            else:  # table
                result_text = f"BOM: {bom.get('name', 'Assembly')} ({len(rows)} items, ~{total_mass:.1f} g)\n"
                result_text += f"{'#':<4} {'Part Number':<20} {'Name':<35} {'Qty':<5} {'Material':<25} {'Mass':<12}\n"
                result_text += f"{'-'*4} {'-'*20} {'-'*35} {'-'*5} {'-'*25} {'-'*12}\n"
                for r in parsed_rows:
                    result_text += f"{r['num']:<4} {r['part_number']:<20} {r['name'][:33]:<35} {r['qty']:<5} {r['material'][:23]:<25} {r['mass']:<12}\n"
            
            return [TextContent(type="text", text=result_text)]
        
        # ========== DOCUMENT DISCOVERY TOOL HANDLERS ==========
        
        elif name == "onshape_search_documents":
            result = client.search_documents(
                arguments["query"],
                owner_type=arguments.get("owner_type", "1"),
                limit=arguments.get("limit", 20)
            )
            
            items = result.get("items", [])
            if not items:
                return [TextContent(type="text", text=f"No documents found matching '{arguments['query']}'.")]
            
            result_text = f"Documents matching '{arguments['query']}' ({len(items)} results):\n"
            result_text += "-" * 80 + "\n"
            for doc in items:
                result_text += f"\n📄 {doc.get('name', 'Unnamed')}\n"
                result_text += f"   Document ID: {doc.get('id')}\n"
                result_text += f"   Owner: {doc.get('owner', {}).get('name', 'Unknown')}\n"
                result_text += f"   Modified: {doc.get('modifiedAt', 'N/A')}\n"
                result_text += f"   Default workspace: {doc.get('defaultWorkspace', {}).get('id', 'N/A')}\n"
            return [TextContent(type="text", text=result_text)]
        
        elif name == "onshape_get_document_summary":
            summary = client.get_document_summary(arguments["document_id"])
            
            doc = summary["document"]
            result_text = f"📄 Document: {doc['name']}\n"
            result_text += f"   ID: {doc['id']}\n"
            result_text += f"   Owner: {doc['owner']}\n"
            result_text += f"   Modified: {doc.get('modifiedAt', 'N/A')}\n"
            result_text += "\n"
            
            for ws in summary["workspaces"]:
                result_text += f"📁 Workspace: {ws['name']} (id: {ws['id']})\n"
                if ws["elements"]:
                    for elem in ws["elements"]:
                        type_icon = {
                            "PARTSTUDIO": "🔧",
                            "ASSEMBLY": "📦",
                            "DRAWING": "📐",
                            "VARIABLESTUDIO": "📊",
                            "BLOB": "📎",
                        }.get(elem["elementType"], "📄")
                        result_text += f"   {type_icon} {elem['name']} ({elem['elementType']}, id: {elem['id']})\n"
                else:
                    result_text += "   (no elements)\n"
            
            return [TextContent(type="text", text=result_text)]
        
        elif name == "onshape_get_features":
            result = client.get_features(
                arguments["document_id"],
                arguments["workspace_id"],
                arguments["element_id"]
            )
            
            features = result.get("features", [])
            if not features:
                return [TextContent(type="text", text="No features found in this Part Studio.")]
            
            result_text = f"Feature Tree ({len(features)} features):\n"
            result_text += "-" * 70 + "\n"
            
            for i, feat in enumerate(features, 1):
                feat_type = feat.get("featureType", feat.get("typeName", feat.get("btType", "Unknown")))
                feat_name = feat.get("name", "Unnamed")
                suppressed = feat.get("suppressed", False)
                feat_id = feat.get("featureId", "N/A")
                
                status = " [SUPPRESSED]" if suppressed else ""
                result_text += f"  {i:>3}. {feat_name}{status}\n"
                result_text += f"       Type: {feat_type} | ID: {feat_id}\n"
            
            return [TextContent(type="text", text=result_text)]
        
        elif name == "onshape_find_part_studios":
            studios = client.find_part_studios(
                arguments["document_id"],
                arguments["workspace_id"],
                arguments.get("name_pattern")
            )
            
            if not studios:
                pattern_msg = f" matching '{arguments.get('name_pattern')}'" if arguments.get("name_pattern") else ""
                return [TextContent(type="text", text=f"No Part Studios found{pattern_msg}.")]
            
            result_text = f"Part Studios found ({len(studios)}):\n"
            for s in studios:
                result_text += f"  🔧 {s.get('name')} (element_id: {s.get('id')})\n"
            return [TextContent(type="text", text=result_text)]
        
        elif name == "onshape_get_assembly_definition":
            result = client.get_assembly_definition(
                arguments["document_id"],
                arguments["workspace_id"],
                arguments["element_id"]
            )
            
            # Parse root assembly
            root = result.get("rootAssembly", {})
            instances = root.get("instances", [])
            features = root.get("features", [])
            
            result_text = f"Assembly Definition:\n"
            result_text += "-" * 70 + "\n"
            
            # Instances
            result_text += f"\n📦 Instances ({len(instances)}):\n"
            for inst in instances:
                inst_type = inst.get("type", "Unknown")
                inst_name = inst.get("name", "Unnamed")
                suppressed = inst.get("suppressed", False)
                status = " [SUPPRESSED]" if suppressed else ""
                result_text += f"  - {inst_name} ({inst_type}){status}\n"
                result_text += f"    ID: {inst.get('id', 'N/A')}\n"
                if inst.get("partId"):
                    result_text += f"    Part ID: {inst['partId']}\n"
            
            # Mates / features
            if features:
                result_text += f"\n🔗 Mates & Connectors ({len(features)}):\n"
                for feat in features:
                    feat_type = feat.get("featureType", "Unknown")
                    feat_name = feat.get("featureData", {}).get("name", "Unnamed")
                    suppressed = feat.get("suppressed", False)
                    status = " [SUPPRESSED]" if suppressed else ""
                    result_text += f"  - {feat_name} ({feat_type}){status}\n"
            
            # Sub-assemblies
            sub_assemblies = result.get("subAssemblies", [])
            if sub_assemblies:
                result_text += f"\n📁 Sub-Assemblies ({len(sub_assemblies)}):\n"
                for sub in sub_assemblies:
                    sub_instances = sub.get("instances", [])
                    result_text += f"  - {sub.get('documentId', 'N/A')[:8]}... ({len(sub_instances)} instances)\n"
            
            return [TextContent(type="text", text=result_text)]
        
        # ========== MATERIAL TOOL HANDLERS ==========
        
        elif name == "onshape_list_materials":
            category = arguments.get("category")
            search = arguments.get("search")
            
            materials = client.get_material_library(category=category)
            
            # Apply search filter if provided
            if search:
                search_lower = search.lower()
                materials = [m for m in materials if search_lower in m.get("displayName", "").lower()]
            
            if not materials:
                filters = []
                if category:
                    filters.append(f"category='{category}'")
                if search:
                    filters.append(f"search='{search}'")
                filter_str = f" (filters: {', '.join(filters)})" if filters else ""
                return [TextContent(type="text", text=f"No materials found{filter_str}.")]
            
            # Group by category
            by_category: dict[str, list[str]] = {}
            for m in materials:
                cat = m.get("category", "Other")
                by_category.setdefault(cat, []).append(m["displayName"])
            
            result_text = f"## Onshape Material Library ({len(materials)} materials)\n\n"
            if category:
                result_text = f"## Onshape Materials — {category} ({len(materials)} materials)\n\n"
            if search:
                result_text = f"## Onshape Materials matching '{search}' ({len(materials)} results)\n\n"
            
            for cat in sorted(by_category.keys()):
                names = by_category[cat]
                result_text += f"### {cat} ({len(names)})\n"
                for n in sorted(names):
                    result_text += f"- {n}\n"
                result_text += "\n"
            
            return [TextContent(type="text", text=result_text)]
        
        elif name == "onshape_set_part_material":
            material_name = arguments["material_name"]
            
            try:
                result = client.set_part_material(
                    arguments["document_id"],
                    arguments["workspace_id"],
                    arguments["element_id"],
                    arguments["part_id"],
                    material_name
                )
            except ValueError as ve:
                return [TextContent(type="text", text=f"❌ {str(ve)}")]
            
            status = result.get("status", "UNKNOWN")
            
            if status == "SUCCEEDED":
                # Verify by reading back the part
                try:
                    parts = client.get_parts(
                        arguments["document_id"],
                        arguments["workspace_id"],
                        arguments["element_id"]
                    )
                    part_name = "Unknown"
                    verified_material = "Unknown"
                    for p in parts:
                        if p.get("partId") == arguments["part_id"]:
                            part_name = p.get("name", "Unknown")
                            verified_material = p.get("material", {}).get("displayName", "Not set")
                            break
                    
                    result_text = f"✓ Material updated successfully!\n"
                    result_text += f"  Part: {part_name}\n"
                    result_text += f"  Material: {verified_material}\n"
                except Exception:
                    result_text = f"✓ Material set to '{material_name}' (verification skipped).\n"
            else:
                error_msg = result.get("properties", [{}])[0].get("errorMessage", "Unknown error")
                result_text = f"❌ Failed to set material: {error_msg}\n"
                result_text += f"  Status: {status}\n"
            
            return [TextContent(type="text", text=result_text)]
        
        # ========== EXPORT TOOL HANDLERS ==========
        
        elif name == "onshape_export_step":
            from pathlib import Path
            did = arguments["document_id"]
            wid = arguments["workspace_id"]
            eid = arguments["element_id"]
            pid = arguments["part_id"]
            output_path = Path(arguments["output_path"])
            
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            result_text = f"Exporting STEP for part {pid}...\n"
            
            endpoint = f"/partstudios/d/{did}/w/{wid}/e/{eid}/translations"
            trans = client.start_translation(endpoint, "STEP", part_id=pid)
            tid = trans.get("id")
            result_text += f"Translation started (ID: {tid})\n"
            
            result = client.poll_translation(tid)
            ext_ids = result.get("resultExternalDataIds", [])
            
            if ext_ids:
                client.download_external_data(did, ext_ids[0], output_path)
                file_size = output_path.stat().st_size
                result_text += f"✓ Downloaded: {output_path} ({file_size:,} bytes)\n"
            else:
                result_text += "❌ Translation completed but no result file was produced.\n"
            
            return [TextContent(type="text", text=result_text)]
        
        elif name == "onshape_export_drawing_pdf":
            from pathlib import Path
            did = arguments["document_id"]
            wid = arguments["workspace_id"]
            eid = arguments["element_id"]
            output_path = Path(arguments["output_path"])
            
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            result_text = f"Exporting PDF for drawing {eid}...\n"
            
            endpoint = f"/drawings/d/{did}/w/{wid}/e/{eid}/translations"
            trans = client.start_translation(endpoint, "PDF")
            tid = trans.get("id")
            result_text += f"Translation started (ID: {tid})\n"
            
            result = client.poll_translation(tid)
            ext_ids = result.get("resultExternalDataIds", [])
            
            if ext_ids:
                client.download_external_data(did, ext_ids[0], output_path)
                file_size = output_path.stat().st_size
                result_text += f"✓ Downloaded: {output_path} ({file_size:,} bytes)\n"
            else:
                result_text += "❌ Translation completed but no result file was produced.\n"
            
            return [TextContent(type="text", text=result_text)]

        elif name == "onshape_create_document":
            result = client.create_document(
                name=arguments["name"],
                description=arguments.get("description", ""),
                is_public=arguments.get("is_public", False),
            )
            return [TextContent(
                type="text",
                text=f"Document created: {result['name']}\n"
                     f"document_id: {result['document_id']}\n"
                     f"workspace_id: {result['workspace_id']}\n"
                     f"element_id (Part Studio): {result['element_id']}\n"
                     f"URL: {result['url']}"
            )]

        elif name == "onshape_delete_document":
            result = client.delete_document(arguments["document_id"])
            return [TextContent(
                type="text",
                text=f"Document {result['document_id']} deleted permanently."
            )]

        elif name == "onshape_add_feature":
            result = client.add_feature(
                arguments["document_id"],
                arguments["workspace_id"],
                arguments["element_id"],
                arguments["feature"],
            )
            feature = result.get("feature", {})
            state = result.get("featureState", {})
            return [TextContent(
                type="text",
                text=f"Feature added: {feature.get('name', '?')}\n"
                     f"featureId: {feature.get('featureId', '?')}\n"
                     f"featureType: {feature.get('featureType', '?')}\n"
                     f"status: {state.get('featureStatus', '?')}"
            )]

        elif name == "onshape_create_cylinder":
            result = client.create_cylinder(
                arguments["document_id"],
                arguments["workspace_id"],
                arguments["element_id"],
                diameter_mm=arguments["diameter_mm"],
                height_mm=arguments["height_mm"],
                plane=arguments.get("plane", "Top"),
                center_x_mm=arguments.get("center_x_mm", 0.0),
                center_y_mm=arguments.get("center_y_mm", 0.0),
            )
            return [TextContent(
                type="text",
                text=f"Cylinder created:\n"
                     f"  Sketch featureId: {result['sketch']['featureId']}\n"
                     f"  Sketch status: {result['sketch']['state'].get('featureStatus', '?')}\n"
                     f"  Extrude featureId: {result['extrude']['featureId']}\n"
                     f"  Extrude status: {result['extrude']['state'].get('featureStatus', '?')}"
            )]

        elif name == "onshape_add_extrude":
            extrude = client.build_extrude(
                sketch_feature_id=arguments["sketch_feature_id"],
                depth_mm=arguments["depth_mm"],
                name=arguments.get("name", "Extrude 1"),
                operation=arguments.get("operation", "NEW"),
                direction=arguments.get("direction", "BLIND"),
            )
            result = client.add_feature(
                arguments["document_id"],
                arguments["workspace_id"],
                arguments["element_id"],
                extrude,
            )
            feature = result.get("feature", {})
            state = result.get("featureState", {})
            return [TextContent(
                type="text",
                text=f"Extrude added: {feature.get('name', '?')}\n"
                     f"featureId: {feature.get('featureId', '?')}\n"
                     f"status: {state.get('featureStatus', '?')}"
            )]

        elif name == "onshape_add_sketch_circle":
            sketch = client.build_sketch_circle(
                name=arguments.get("name", "Sketch 1"),
                plane=arguments.get("plane", "Top"),
                radius_mm=arguments["radius_mm"],
                center_x_mm=arguments.get("center_x_mm", 0.0),
                center_y_mm=arguments.get("center_y_mm", 0.0),
            )
            result = client.add_feature(
                arguments["document_id"],
                arguments["workspace_id"],
                arguments["element_id"],
                sketch,
            )
            feature = result.get("feature", {})
            state = result.get("featureState", {})
            return [TextContent(
                type="text",
                text=f"Sketch added: {feature.get('name', '?')}\n"
                     f"featureId: {feature.get('featureId', '?')}\n"
                     f"status: {state.get('featureStatus', '?')}"
            )]

        elif name == "onshape_add_sketch_rectangle":
            sketch = client.build_sketch_rectangle(
                name=arguments.get("name", "Sketch 1"),
                plane=arguments.get("plane", "Top"),
                width_mm=arguments["width_mm"],
                height_mm=arguments["height_mm"],
                center_x_mm=arguments.get("center_x_mm", 0.0),
                center_y_mm=arguments.get("center_y_mm", 0.0),
            )
            result = client.add_feature(
                arguments["document_id"],
                arguments["workspace_id"],
                arguments["element_id"],
                sketch,
            )
            feature = result.get("feature", {})
            state = result.get("featureState", {})
            return [TextContent(
                type="text",
                text=f"Sketch added: {feature.get('name', '?')}\n"
                     f"featureId: {feature.get('featureId', '?')}\n"
                     f"status: {state.get('featureStatus', '?')}"
            )]

        elif name == "onshape_delete_feature":
            result = client.delete_feature(
                arguments["document_id"],
                arguments["workspace_id"],
                arguments["element_id"],
                arguments["feature_id"],
            )
            return [TextContent(
                type="text",
                text=f"Feature {arguments['feature_id']} deleted."
            )]

        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
            
    except requests.exceptions.HTTPError as e:
        return [TextContent(type="text", text=f"Onshape API error: {e.response.status_code} - {e.response.text}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def main():
    """Run the MCP server."""
    if not client.auth[0] or not client.auth[1]:
        logger.error("ONSHAPE_ACCESS_KEY and ONSHAPE_SECRET_KEY environment variables must be set!")
        logger.error("Get your API keys from: https://cad.onshape.com/appstore/dev-portal")
        return
    
    logger.info("Starting Onshape MCP Server...")
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
