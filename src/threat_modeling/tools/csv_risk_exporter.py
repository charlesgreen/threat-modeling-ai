
import csv
import io
import json
from crewai_tools import BaseTool

class CSVRiskExporterTool(BaseTool):
    name: str = "Threat Model CSV Exporter"
    description: str = "Takes structured threat data and outputs a CSV string for use by penetration testing teams."

    def _run(self, risks_json: str) -> str:
        risks = json.loads(risks_json)
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=["threat", "asset", "category", "likelihood", "impact", "mitigation"])
        writer.writeheader()
        writer.writerows(risks)
        return output.getvalue()
