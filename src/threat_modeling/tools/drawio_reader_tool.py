import os
import json
from pydantic import BaseModel, ValidationError, Field
from crewai.tools import BaseTool
from dotenv import load_dotenv
import xml.etree.ElementTree as ET

class DrawioReaderInput(BaseModel):
    file_path: str = Field(..., description="Absolute or relative path to the input .drawio file")

class DrawioReaderTool(BaseTool):
    name: str = "Draw.io Architecture Diagram Interpreter"
    description: str = (
        "Extracts structure and text from a .drawio diagram and sends it to an LLM for structured analysis. "
        "Useful for interpreting system designs, architecture diagrams, or threat assessments."
    )

    def _run(self, file_path: str = "", **kwargs) -> str:
        load_dotenv()
        if not file_path:
            file_path = kwargs.get("file_path") or ""
        if not file_path:
            file_path = os.environ.get("DRAWIO_PATH", "")
        print(f"[DEBUG] [DrawioReaderTool] Using file_path: {file_path}")
        try:
            validated = DrawioReaderInput(file_path=file_path)
            if not os.path.exists(validated.file_path) or not validated.file_path.endswith(".drawio"):
                return f"[ERROR] File not found or invalid format: {validated.file_path}"
            try:
                tree = ET.parse(validated.file_path)
                root = tree.getroot()
            except Exception as e:
                return f"[ERROR] Could not parse .drawio file: {str(e)}"
            # Extract shapes, connectors, and text
            cells = []
            for cell in root.iter("mxCell"):
                cell_data = {k: cell.attrib.get(k, "") for k in cell.attrib}
                value = cell.attrib.get("value", "")
                if value:
                    cell_data["text"] = value
                cells.append(cell_data)
            # Step 4: Return structured LLM prompt
            return json.dumps({
                "type": "diagram_prompt",
                "cells": cells,
                "instructions": (
                    "You are analyzing a Draw.io (.drawio) diagram related to cloud architecture or threat modeling. "
                    "Extract relevant components, security controls, service relationships, or identified threats. "
                    "If possible, align content to the STRIDE framework. "
                    "Return a structured summary of services, risks, and mitigation recommendations."
                )
            })
        except ValidationError as ve:
            return f"[ERROR] Input validation failed: {ve.json(indent=2)}"
        except Exception as e:
            return f"[ERROR] Failed to read .drawio: {str(e)}"
