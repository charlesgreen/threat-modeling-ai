from crewai_tools import BaseTool
import fitz  # PyMuPDF
import os
import json

class PDFReaderTool(BaseTool):
    name: str = "PDF Reader Tool"
    description: str = (
        "Reads and extracts text from PDF files. "
        "Useful for analyzing architecture diagrams, cloud documentation, or any planning documents provided as PDFs."
    )

    def _run(self, file_path: str) -> str:
        if not os.path.exists(file_path) or not file_path.endswith(".pdf"):
            return f"[ERROR] File not found or invalid format: {file_path}"

        try:
            doc = fitz.open(file_path)
            text_data = []

            for page_num, page in enumerate(doc, start=1):
                text = page.get_text()
                text_data.append({"page": page_num, "text": text.strip()})

            return json.dumps(text_data, indent=2)

        except Exception as e:
            return f"[ERROR] Failed to read PDF: {str(e)}"
