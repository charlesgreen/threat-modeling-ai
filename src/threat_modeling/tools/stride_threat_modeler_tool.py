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

    def _run(self, combined_input: str) -> str:
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
            # Parse and validate input against schema
            parsed_json = json.loads(combined_input)
            validated_data = STRIDEInputModel(**parsed_json)

            # Construct LLM prompt payload
            return {
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
            }

        except json.JSONDecodeError:
            return "[ERROR] Invalid JSON input format. Expecting a JSON string."
        except ValidationError as ve:
            return f"[ERROR] Input validation failed: {ve.json(indent=2)}"
