import csv
import io
import json
from typing import List
from pydantic import BaseModel, ValidationError, Field
from crewai.tools import BaseTool


# ----------------------------------------
# 📦 Pydantic schema for each risk item
# ----------------------------------------

class RiskItem(BaseModel):
    threat: str = Field(..., description="Brief description of the threat")
    asset: str = Field(..., description="Asset or component at risk")
    category: str = Field(..., description="STRIDE category (e.g., Tampering)")
    likelihood: str = Field(..., description="Likelihood (Low, Medium, High)")
    impact: str = Field(..., description="Impact level (Minor, Moderate, Severe)")
    mitigation: str = Field(..., description="Recommended mitigation strategy")


# ----------------------------------------
# 🧠 CSV Exporter Tool with validation
# ----------------------------------------

class CSVRiskExporterTool(BaseTool):
    name: str = "Threat Model CSV Exporter"
    description: str = (
        "Takes structured threat data and outputs a CSV string for use by penetration testing teams. "
        "Input must be a JSON array of threats with keys: threat, asset, category, likelihood, impact, mitigation."
    )

    def _run(self, risks_json: str = "", **kwargs) -> str:
        import os
        from dotenv import load_dotenv
        load_dotenv()
        # Allow risks_json from kwargs or env
        if not risks_json:
            risks_json = kwargs.get("risks_json") or ""
        if not risks_json:
            risks_json = os.environ.get("RISKS_JSON", "")
        csv_path = os.environ.get("CSV_PATH", "threat_model.csv")
        print(f"[DEBUG] [CSVRiskExporterTool] Using csv_path: {csv_path}")
        """
        Expected Input:
        JSON string of the form:
        [
          {
            "threat": "Unauthorized access to storage bucket",
            "asset": "GCS: logs-prod",
            "category": "Information Disclosure",
            "likelihood": "High",
            "impact": "Severe",
            "mitigation": "Enable uniform bucket-level access and restrict IAM roles"
          },
          ...
        ]

        Output:
        CSV string with header row and one row per risk.
        """
        try:
            parsed = json.loads(risks_json)
            risks: List[RiskItem] = [RiskItem(**item) for item in parsed]

            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=["threat", "asset", "category", "likelihood", "impact", "mitigation"])
            writer.writeheader()

            for item in risks:
                writer.writerow(item.dict())

            csv_content = output.getvalue()
            # Write to file at csv_path
            with open(csv_path, "w") as f:
                f.write(csv_content)

            return csv_content

        except (json.JSONDecodeError, ValidationError) as e:
            return f"[ERROR] Invalid input: {str(e)}"
