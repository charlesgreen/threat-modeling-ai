import fitz  # PyMuPDF
import os
from pydantic import BaseModel, ValidationError, Field
from crewai.tools import BaseTool
from dotenv import load_dotenv
import json

# ----------------------------------------
# 📦 Pydantic model for input validation
# ----------------------------------------

class PDFReaderInput(BaseModel):
    file_path: str = Field(..., description="Absolute or relative path to the input PDF file")


# ----------------------------------------
# 🧠 PDFReaderTool definition
# ----------------------------------------

class PDFReaderTool(BaseTool):
    name: str = "Cloud Architecture PDF Interpreter"
    description: str = (
        "Extracts text from a PDF document and sends it to an LLM for structured analysis. "
        "Useful for interpreting system designs, architecture write-ups, or threat assessments."
    )

    def _run(self, file_path: str = "", **kwargs) -> str:
        load_dotenv()
        # Allow file_path from kwargs or env
        if not file_path:
            file_path = kwargs.get("file_path") or ""
        if not file_path:
            file_path = os.environ.get("PDF_PATH", "")
        print(f"[DEBUG] [PDFReaderTool] Using file_path: {file_path}")
        """
        Expected Input:
        A string containing a valid file path to a `.pdf` file.

        Expected Output:
        A dictionary with:
        - type: "text_prompt"
        - text: (full extracted text from PDF)
        - instructions: prompt to guide LLM to extract security-relevant insights

        If validation or reading fails, returns a string error.
        """

        try:
            # Step 1: Validate input using Pydantic
            validated = PDFReaderInput(file_path=file_path)

            # Step 2: Check file existence and extension
            if not os.path.exists(validated.file_path) or not validated.file_path.endswith(".pdf"):
                return f"[ERROR] File not found or invalid format: {validated.file_path}"

            # Step 3: Extract all text from the PDF using PyMuPDF
            try:
                doc = fitz.open(validated.file_path)
            except Exception as e:
                return f"[ERROR] Could not open PDF file: {str(e)}"
            full_text = ""
            for page in doc:
                full_text += page.get_text() + "\n\n"

            # Step 4: Return structured LLM prompt
            return json.dumps({
                "type": "text_prompt",
                "text": full_text.strip(),
                "instructions": (
                    "You are analyzing a PDF document related to cloud architecture or threat modeling. "
                    "Extract any relevant components, security controls, service relationships, or identified threats. "
                    "If possible, align content to the STRIDE framework. "
                    "Return a structured summary of services, risks, and mitigation recommendations."
                )
            })

        except ValidationError as ve:
            return f"[ERROR] Input validation failed: {ve.json(indent=2)}"
        except Exception as e:
            return f"[ERROR] Failed to read PDF: {str(e)}"
