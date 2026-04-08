"""Shared Onshape API client.

Consolidates the common API client pattern used across all scripts and the MCP server.
Handles authentication, request execution, and all Onshape API endpoints.

This is the canonical API client — both CLI scripts and the MCP server import from here.
"""

import os
import json
import base64
import requests
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the script directory
load_dotenv(Path(__file__).parent / ".env")


class OnshapeClient:
    """Onshape API v10 client with common operations.

    Credentials can be passed explicitly or loaded from environment variables
    (ONSHAPE_ACCESS_KEY, ONSHAPE_SECRET_KEY, ONSHAPE_BASE_URL).
    """

    def __init__(self, access_key: str = None, secret_key: str = None,
                 base_url: str = None):
        self.base_url = base_url or os.getenv("ONSHAPE_BASE_URL", "https://cad.onshape.com")
        self.auth = (
            access_key or os.getenv("ONSHAPE_ACCESS_KEY", ""),
            secret_key or os.getenv("ONSHAPE_SECRET_KEY", ""),
        )
        self.headers = {
            "Accept": "application/json;charset=UTF-8;qs=0.09",
            "Content-Type": "application/json",
        }

    def _request(self, method: str, endpoint: str, **kwargs) -> dict | list:
        """Make an authenticated request to the Onshape API."""
        url = f"{self.base_url}/api/v10{endpoint}"
        kwargs.setdefault("timeout", 30)
        response = requests.request(
            method, url, auth=self.auth, headers=self.headers, **kwargs
        )
        response.raise_for_status()
        if response.status_code == 204:
            return {"status": "success"}
        return response.json()

    # ── Document ──────────────────────────────────────────────────────────

    def get_document(self, document_id: str) -> dict:
        """Get document information."""
        return self._request("GET", f"/documents/{document_id}")

    def get_elements(self, document_id: str, workspace_id: str) -> list:
        """Get all elements (tabs) in a document workspace."""
        return self._request("GET", f"/documents/d/{document_id}/w/{workspace_id}/elements")

    def get_document_workspaces(self, document_id: str) -> list:
        """Get all workspaces for a document."""
        return self._request("GET", f"/documents/d/{document_id}/workspaces")

    # ── Variable Studios ──────────────────────────────────────────────────

    def get_variable_studios(self, document_id: str, workspace_id: str) -> list:
        """Find all Variable Studio elements in a document."""
        elements = self.get_elements(document_id, workspace_id)
        return [e for e in elements if e.get("elementType") == "VARIABLESTUDIO"]

    def get_variables(self, document_id: str, workspace_id: str,
                      element_id: str) -> dict:
        """Get all variables from a Variable Studio."""
        return self._request(
            "GET",
            f"/variables/d/{document_id}/w/{workspace_id}/e/{element_id}/variables",
        )

    def set_variables(self, document_id: str, workspace_id: str,
                      element_id: str, variables: list) -> dict:
        """Replace ALL variables in a Variable Studio.

        WARNING: This is a full replacement — always include the complete set.
        Returns dict with status and count of updated variables.
        """
        url = (
            f"{self.base_url}/api/v10/variables/d/{document_id}"
            f"/w/{workspace_id}/e/{element_id}/variables"
        )
        resp = requests.post(
            url, auth=self.auth, headers=self.headers, json=variables, timeout=30,
        )
        resp.raise_for_status()
        return {"status": "success", "updated": len(variables)}

    # ── Parts ─────────────────────────────────────────────────────────────

    def get_parts(self, document_id: str, workspace_id: str,
                  element_id: str = None) -> list:
        """Get parts from a Part Studio, or all parts in a workspace."""
        if element_id:
            return self._request(
                "GET",
                f"/parts/d/{document_id}/w/{workspace_id}/e/{element_id}",
            )
        return self._request("GET", f"/parts/d/{document_id}/w/{workspace_id}")

    def get_part_studios(self, document_id: str, workspace_id: str) -> list:
        """Find all Part Studio elements in a document."""
        elements = self.get_elements(document_id, workspace_id)
        return [e for e in elements if e.get("elementType") == "PARTSTUDIO"]

    def get_part_metadata(self, document_id: str, workspace_id: str,
                          element_id: str, part_id: str) -> dict:
        """Get metadata for a specific part."""
        return self._request(
            "GET",
            f"/metadata/d/{document_id}/w/{workspace_id}/e/{element_id}/p/{part_id}",
        )

    def set_part_metadata(self, document_id: str, workspace_id: str,
                          element_id: str, part_id: str,
                          properties: list[dict]) -> dict:
        """Set metadata properties on a part.

        Args:
            properties: List of dicts with 'propertyId' and 'value' keys.
        """
        return self._request(
            "POST",
            f"/metadata/d/{document_id}/w/{workspace_id}/e/{element_id}/p/{part_id}",
            json={"properties": properties},
        )

    # ── Assembly / BOM ────────────────────────────────────────────────────

    def get_assembly_bom(self, document_id: str, workspace_id: str,
                         element_id: str) -> dict:
        """Get the Bill of Materials for an assembly."""
        return self._request(
            "GET",
            f"/assemblies/d/{document_id}/w/{workspace_id}/e/{element_id}/bom",
        )

    def get_assembly_definition(self, document_id: str, workspace_id: str,
                                element_id: str) -> dict:
        """Get assembly definition (instances, mates, structure)."""
        return self._request(
            "GET",
            f"/assemblies/d/{document_id}/w/{workspace_id}/e/{element_id}",
        )

    # ── Drawings ──────────────────────────────────────────────────────────

    def list_drawings(self, document_id: str, workspace_id: str) -> list:
        """List all drawing elements in a document."""
        elements = self.get_elements(document_id, workspace_id)
        return [
            e for e in elements
            if e.get("elementType") in ("DRAWING", "APPLICATION")
            and "Drawing" in e.get("name", e.get("elementType", ""))
        ]

    # ── Translation (export) ─────────────────────────────────────────────

    def start_translation(self, endpoint: str, format_name: str,
                          part_id: str = None,
                          store_in_document: bool = False) -> dict:
        """Start a translation (export) job. Returns translation response."""
        body = {
            "formatName": format_name,
            "storeInDocument": store_in_document,
        }
        if part_id:
            body["partIds"] = part_id
            body["translate"] = True
        return self._request("POST", endpoint, json=body)

    def poll_translation(self, translation_id: str, poll_interval: float = 2,
                         max_attempts: int = 60) -> dict:
        """Poll a translation until it completes."""
        import time
        for _ in range(max_attempts):
            result = self._request("GET", f"/translations/{translation_id}")
            state = result.get("requestState", "")
            if state == "DONE":
                return result
            if state == "FAILED":
                reason = result.get("failureReason", "Unknown")
                raise RuntimeError(f"Translation failed: {reason}")
            time.sleep(poll_interval)
        raise TimeoutError(f"Translation {translation_id} did not complete in time")

    def download_external_data(self, document_id: str, file_id: str,
                               output_path) -> None:
        """Download an exported file from Onshape external data."""
        from pathlib import Path
        output_path = Path(output_path)
        url = f"{self.base_url}/api/v10/documents/d/{document_id}/externaldata/{file_id}"
        resp = requests.get(
            url, auth=self.auth,
            headers={"Accept": "application/octet-stream"},
            stream=True, timeout=60,
        )
        resp.raise_for_status()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)

    # ── Features ──────────────────────────────────────────────────────────

    def get_features(self, document_id: str, workspace_id: str,
                     element_id: str) -> dict:
        """Get all features from a Part Studio feature tree."""
        return self._request(
            "GET",
            f"/partstudios/d/{document_id}/w/{workspace_id}/e/{element_id}/features",
        )

    # ── Search ────────────────────────────────────────────────────────────

    def search_documents(self, query: str, owner_type: str = "1",
                         sort_column: str = "modifiedAt",
                         sort_order: str = "desc",
                         limit: int = 20) -> dict:
        """Search for documents by name/description across the Onshape account.

        Args:
            query: Search text (matches document names and descriptions)
            owner_type: '0' = My docs, '1' = Created by me, '2' = Shared, '3' = Trash
            sort_column: 'name', 'modifiedAt', 'createdAt'
            sort_order: 'asc' or 'desc'
            limit: Max results (default 20)
        """
        params = {
            "q": query,
            "ownerType": owner_type,
            "sortColumn": sort_column,
            "sortOrder": sort_order,
            "limit": limit,
        }
        return self._request("GET", "/documents", params=params)

    def get_document_summary(self, document_id: str) -> dict:
        """Get comprehensive document summary: all workspaces and their elements."""
        doc = self.get_document(document_id)
        workspaces = self.get_document_workspaces(document_id)

        result = {
            "document": {
                "id": doc.get("id"),
                "name": doc.get("name"),
                "owner": doc.get("owner", {}).get("name", "Unknown"),
                "createdAt": doc.get("createdAt"),
                "modifiedAt": doc.get("modifiedAt"),
            },
            "workspaces": [],
        }

        for ws in workspaces:
            ws_id = ws.get("id")
            try:
                elements = self.get_elements(document_id, ws_id)
            except Exception:
                elements = []

            result["workspaces"].append({
                "id": ws_id,
                "name": ws.get("name", "Main"),
                "elements": [{
                    "id": e.get("id"),
                    "name": e.get("name"),
                    "elementType": e.get("elementType"),
                    "dataType": e.get("dataType", ""),
                } for e in elements],
            })

        return result

    def find_part_studios(self, document_id: str, workspace_id: str,
                          name_pattern: str = None) -> list:
        """Find Part Studio elements, optionally filtered by name pattern.

        Args:
            name_pattern: Case-insensitive substring match on element name (optional)
        """
        elements = self.get_elements(document_id, workspace_id)
        part_studios = [e for e in elements if e.get("elementType") == "PARTSTUDIO"]

        if name_pattern:
            name_lower = name_pattern.lower()
            part_studios = [e for e in part_studios
                            if name_lower in e.get("name", "").lower()]

        return part_studios

    # ── Assembly (extended) ───────────────────────────────────────────────

    def get_assembly_parts(self, document_id: str, workspace_id: str,
                           element_id: str) -> list:
        """Get all parts in an assembly."""
        return self._request(
            "GET",
            f"/assemblies/d/{document_id}/w/{workspace_id}/e/{element_id}",
        )

    # ── Drawings (extended) ──────────────────────────────────────────────

    def create_drawing(self, document_id: str, workspace_id: str,
                       drawing_name: str, part_element_id: str = None,
                       part_id: str = None, template_key: str = "A3") -> dict:
        """Create a new drawing in the document.

        Args:
            drawing_name: Name for the new drawing
            part_element_id: Element ID of Part Studio containing the part (optional)
            part_id: Specific part ID within the Part Studio (optional)
            template_key: Template to use - 'A3' or 'A4-Portrait'
        """
        from constants import MEMSYS_TEMPLATES

        template = MEMSYS_TEMPLATES.get(template_key)
        if not template:
            raise ValueError(
                f"Unknown template: {template_key}. "
                f"Available: {list(MEMSYS_TEMPLATES.keys())}"
            )

        body = {
            "drawingName": drawing_name,
            "templateDocumentId": template["document_id"],
            "templateWorkspaceId": template["workspace_id"],
            "templateElementId": template["element_id"],
        }

        if part_element_id:
            body["elementId"] = part_element_id
            if part_id:
                body["partId"] = part_id

        url = (
            f"{self.base_url}/api/v10/drawings"
            f"/d/{document_id}/w/{workspace_id}/create"
        )
        response = requests.post(
            url, auth=self.auth, headers=self.headers, json=body, timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def get_drawing_views(self, document_id: str, workspace_id: str,
                          element_id: str) -> list:
        """Get all views in a drawing."""
        return self._request(
            "GET",
            f"/drawings/d/{document_id}/w/{workspace_id}/e/{element_id}/views",
        )

    def modify_drawing(self, document_id: str, workspace_id: str,
                       element_id: str, json_requests: list,
                       description: str = "API modification") -> dict:
        """Modify a drawing (add views, annotations, dimensions, etc).

        Args:
            json_requests: List of modification requests following Onshape schema
            description: Short description (max 32 chars)
        """
        url = (
            f"{self.base_url}/api/v10/drawings"
            f"/d/{document_id}/w/{workspace_id}/e/{element_id}/modify"
        )
        body = {
            "description": description[:32],
            "jsonRequests": json_requests,
        }
        response = requests.post(
            url, auth=self.auth, headers=self.headers, json=body, timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def get_modification_status(self, modification_id: str) -> dict:
        """Get the status of a drawing modification."""
        return self._request("GET", f"/drawings/modify/status/{modification_id}")

    def add_note(self, document_id: str, workspace_id: str,
                 drawing_element_id: str, text: str,
                 position: dict = None, text_height: float = 0.12) -> dict:
        """Add a text note to a drawing.

        Args:
            text: The note content
            position: {'x': float, 'y': float, 'z': 0} in drawing units
            text_height: Height of the text (default 0.12)
        """
        if position is None:
            position = {"x": 350, "y": 20, "z": 0}

        note_request = {
            "messageName": "onshapeCreateAnnotations",
            "formatVersion": "2021-01-01",
            "annotations": [{
                "type": "Onshape::Note",
                "note": {
                    "position": {
                        "type": "Onshape::Reference::Point",
                        "coordinate": [
                            position.get("x", 350),
                            position.get("y", 20),
                            position.get("z", 0),
                        ],
                    },
                    "contents": text,
                    "textHeight": text_height,
                },
            }],
        }

        return self.modify_drawing(
            document_id, workspace_id, drawing_element_id,
            [note_request], "Add note",
        )

    def create_drawing_with_views(self, document_id: str, workspace_id: str,
                                  part_name: str, part_element_id: str,
                                  part_id: str, template_key: str = "A3",
                                  drawing_number: str = None,
                                  add_title_note: bool = True) -> dict:
        """Create a complete drawing with title and drawing number notes.

        Args:
            part_name: Name of the part (used for drawing name and title)
            part_element_id: Element ID of the Part Studio
            part_id: Part ID within the Part Studio
            template_key: 'A3' or 'A4-Portrait'
            drawing_number: Optional drawing number (e.g., "DRW-0001")
            add_title_note: Whether to add part name as note
        """
        import time

        drawing = self.create_drawing(
            document_id, workspace_id,
            f"{part_name} Drawing",
            part_element_id, part_id, template_key,
        )
        drawing_id = drawing.get("id")
        time.sleep(1)

        results = {"drawing": drawing, "modifications": []}

        if add_title_note:
            try:
                note_result = self.add_note(
                    document_id, workspace_id, drawing_id,
                    part_name,
                    {"x": 380, "y": 18, "z": 0},
                    text_height=0.18,
                )
                results["modifications"].append(
                    {"type": "title_note", "result": note_result}
                )
            except Exception as e:
                results["modifications"].append(
                    {"type": "title_note", "error": str(e)}
                )

        if drawing_number:
            try:
                time.sleep(0.5)
                number_result = self.add_note(
                    document_id, workspace_id, drawing_id,
                    drawing_number,
                    {"x": 380, "y": 8, "z": 0},
                    text_height=0.15,
                )
                results["modifications"].append(
                    {"type": "drawing_number", "result": number_result}
                )
            except Exception as e:
                results["modifications"].append(
                    {"type": "drawing_number", "error": str(e)}
                )

        return results

    def add_drawing_view(self, document_id: str, workspace_id: str,
                         drawing_element_id: str, source_element_id: str,
                         view_type: str = "front", position: dict = None,
                         scale: float = 1.0, part_id: str = None) -> dict:
        """Add a view to a drawing.

        Args:
            source_element_id: Element ID of the Part Studio or Assembly
            view_type: 'front', 'back', 'top', 'bottom', 'left', 'right', 'isometric'
            position: {'x': float, 'y': float} - position on drawing
            scale: View scale (e.g., 1.0 = 1:1, 0.5 = 1:2)
            part_id: Specific part ID if viewing a single part
        """
        if position is None:
            position = {"x": 200, "y": 150}

        view_request = {
            "messageName": "onshapeCreateViews",
            "formatVersion": "2021-01-01",
            "views": [{
                "viewType": "TopLevel",
                "position": position,
                "scale": {
                    "scaleSource": "Custom",
                    "numerator": int(scale * 10),
                    "denumerator": 10,
                },
                "orientation": view_type,
                "reference": {"elementId": source_element_id},
            }],
        }

        if part_id:
            view_request["views"][0]["reference"]["idTag"] = part_id

        return self.modify_drawing(
            document_id, workspace_id, drawing_element_id,
            [view_request], "Add view",
        )

    # ── Material Library ─────────────────────────────────────────────────

    def get_material_library(self, category: str = None) -> list[dict]:
        """Get all materials from the Onshape Material Library.

        Returns a list of dicts with keys: id, displayName, category, properties.
        Optionally filter by category (e.g. 'Metal', 'Plastic', 'Wood').
        """
        from constants import ONSHAPE_MATERIAL_LIBRARY

        lib = ONSHAPE_MATERIAL_LIBRARY
        url = (
            f"/appelements/d/{lib['document_id']}"
            f"/w/{lib['workspace_id']}/e/{lib['element_id']}/content"
        )
        response = self._request("GET", url)

        b64_content = response["data"][0]["baseContent"]
        library_data = json.loads(base64.b64decode(b64_content))

        materials = library_data.get("materials", [])

        if category:
            cat_lower = category.lower()
            materials = [
                m for m in materials
                if m.get("category", "").lower() == cat_lower
            ]

        return materials

    def set_part_material(self, document_id: str, workspace_id: str,
                          element_id: str, part_id: str,
                          material_name: str) -> dict:
        """Set the material of a part using the Onshape metadata API.

        Args:
            element_id: Part Studio element ID containing the part
            part_id: The part ID within the Part Studio
            material_name: Exact material name from the Onshape Material Library
                          (e.g. 'Aluminum - 6061', '300 Series Stainless Steel')

        Raises:
            ValueError: If the material name is not found in the library.
        """
        from constants import ONSHAPE_MATERIAL_LIBRARY, MATERIAL_PROPERTY_ID

        all_materials = self.get_material_library()
        material_names = {m["displayName"]: m for m in all_materials}

        if material_name not in material_names:
            lower_map = {k.lower(): k for k in material_names}
            if material_name.lower() in lower_map:
                material_name = lower_map[material_name.lower()]
            else:
                raise ValueError(
                    f"Material '{material_name}' not found in Onshape Material Library. "
                    f"Use onshape_list_materials to see available materials."
                )

        lib = ONSHAPE_MATERIAL_LIBRARY
        body = {
            "properties": [{
                "propertyId": MATERIAL_PROPERTY_ID,
                "value": {
                    "id": material_name,
                    "displayName": material_name,
                    "libraryName": lib["library_name"],
                    "libraryReference": {
                        "documentId": lib["document_id"],
                        "elementId": lib["element_id"],
                        "versionId": lib["version_id"],
                        "elementMicroversionId": lib["element_microversion_id"],
                    },
                },
            }],
        }

        return self._request(
            "POST",
            f"/metadata/d/{document_id}/w/{workspace_id}/e/{element_id}/p/{part_id}",
            json=body,
        )
