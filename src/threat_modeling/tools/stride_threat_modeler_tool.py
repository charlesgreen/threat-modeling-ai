import json
from pydantic import BaseModel, ValidationError, Field
from typing import Dict, Any
from crewai.tools import BaseTool 


# ----------------------------------------
# 📦 Pydantic model for input validation
# ----------------------------------------

class STRIDEInputModel(BaseModel):
    gcp_metadata: Dict[str, Any] = Field(..., description="GCP metadata from gcloud/bq APIs")
    architecture_summary: str = Field(..., description="Summarized architecture text extracted from diagram or PDF")


# ----------------------------------------
# 🔐 CrewAI Tool Definition
# ----------------------------------------

class STRIDEThreatModelerTool(BaseTool):
    name: str = "STRIDE Threat Model Generator"
    description: str = (
        "Analyzes cloud architecture using the STRIDE framework based on GCP metadata "
        "and documentation summaries. Outputs a list of potential threats and risks."
    )

    def _run(self, summarized_input: str) -> str:
        """
        Expected Input:
        A JSON string matching this structure:
        {
            "gcp_metadata": {
                "compute_instances": [...],
                "cloud_functions": [...],
                ...
            },
            "architecture_summary": "Summarized text from diagram or PDF"
        }

        Expected LLM Output:
        A list of structured JSON objects like:
        [
            {
                "threat": "Spoofed access to Cloud Run service",
                "asset": "Cloud Run: web-app",
                "category": "Spoofing",
                "likelihood": "High",
                "impact": "Severe",
                "mitigation": "Enable authentication and restrict ingress to internal only"
            },
            ...
        ]
        """

        try:
            # Accept both dict and str input for robustness
            if isinstance(summarized_input, dict):
                parsed_json = summarized_input
            else:
                parsed_json = json.loads(summarized_input)
            # Defensive: If gcp_metadata is a string, parse it
            gcp_md = parsed_json.get("gcp_metadata")
            if isinstance(gcp_md, str):
                try:
                    parsed_json["gcp_metadata"] = json.loads(gcp_md)
                except Exception:
                    parsed_json["gcp_metadata"] = {}
            # Defensive: If gcp_metadata is still not a dict, set to empty dict
            if not isinstance(parsed_json.get("gcp_metadata"), dict):
                parsed_json["gcp_metadata"] = {}
            # Defensive: If architecture_summary is not a string, set to empty string
            if not isinstance(parsed_json.get("architecture_summary"), str):
                parsed_json["architecture_summary"] = ""
            # Use .get to avoid key errors
            validated_data = STRIDEInputModel(
                gcp_metadata=parsed_json.get("gcp_metadata", {}),
                architecture_summary=parsed_json.get("architecture_summary", "")
            )
            # Construct LLM prompt payload
            return json.dumps({
                "type": "text_prompt",
                "text": json.dumps({
                    "gcp_metadata": validated_data.gcp_metadata,
                    "architecture_summary": validated_data.architecture_summary
                }, indent=2),
                "instructions": (
                    "You are a security analyst performing a STRIDE threat model. "
                    "Analyze the provided GCP resource metadata and architecture summary. "
                    "Identify risks for each component using the STRIDE categories:\n"
                    "- S: Spoofing\n"
                    "- T: Tampering\n"
                    "- R: Repudiation\n"
                    "- I: Information Disclosure\n"
                    "- D: Denial of Service\n"
                    "- E: Elevation of Privilege\n\n"
                    "For each threat, provide:\n"
                    "- threat (short title)\n"
                    "- asset (service or component at risk)\n"
                    "- category (STRIDE type)\n"
                    "- likelihood (e.g. Low, Medium, High)\n"
                    "- impact (e.g. Minor, Moderate, Severe)\n"
                    "- mitigation (recommended security control)\n\n"
                    "Return your findings as a list of structured JSON objects."
                )
            })
        except json.JSONDecodeError:
            return "[ERROR] Invalid JSON input format. Expecting a JSON string."
        except ValidationError as ve:
            return f"[ERROR] Input validation failed: {ve.json(indent=2)}"
