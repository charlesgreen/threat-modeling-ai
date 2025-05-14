from crewai.tools import BaseTool
from PIL import Image
import os
import base64
import io
from pydantic import BaseModel, ValidationError, Field


# ----------------------------------------
# 📦 Pydantic input schema
# ----------------------------------------

class ImageDiagramInput(BaseModel):
    image_path: str = Field(..., description="Path to a PNG, JPG, or JPEG image file")


# ----------------------------------------
# 🧠 ImageDiagramTool with validation
# ----------------------------------------

class ImageDiagramTool(BaseTool):
    name: str = "GCP Architecture Diagram Interpreter"
    description: str = (
        "Analyzes a cloud architecture diagram (PNG, JPG) using an LLM with vision capabilities to extract structured insights. "
        "Useful for identifying components, data flows, trust boundaries, and correlating with GCP metadata for STRIDE threat modeling."
    )

    def _run(self, image_path: str) -> str:
        """
        Expected Input:
        A valid image path string pointing to a PNG, JPG, or JPEG file.

        Expected Output:
        A dictionary structured as:
        {
            "type": "image_prompt",
            "image_base64": "...",  # base64 string of the image
            "instructions": "LLM prompt to extract architecture insights and STRIDE threats"
        }

        If input or image processing fails, returns an error string.
        """

        try:
            # Step 1: Validate input using Pydantic
            validated = ImageDiagramInput(image_path=image_path)

            if not os.path.exists(validated.image_path) or not validated.image_path.lower().endswith(('.png', '.jpg', '.jpeg')):
                return f"[ERROR] Invalid image file: {validated.image_path}"

            # Step 2: Load and convert image to base64 for LLM
            image = Image.open(validated.image_path)
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            encoded_image = base64.b64encode(buffer.getvalue()).decode("utf-8")

            # Step 3: Return a structured prompt for vision-capable LLM
            return {
                "type": "image_prompt",
                "image_base64": encoded_image,
                "instructions": (
                    "Analyze this cloud architecture diagram. Identify and list the main components, "
                    "data flows, and trust boundaries. If possible, match them with common Google Cloud services "
                    "(e.g., Cloud Run, Pub/Sub, GCS) and call out any missing security controls. "
                    "Apply STRIDE threat modeling categories to each major component where appropriate. "
                    "Return your output as a structured list of findings."
                )
            }

            # === Example Output Expected from the LLM ===
            # [
            #   {
            #     "component": "Cloud Run",
            #     "function": "Processes inbound user requests",
            #     "threats": [
            #       {"type": "Spoofing", "reason": "No auth between API Gateway and Cloud Run"},
            #       {"type": "Repudiation", "reason": "No audit log configuration detected"}
            #     ]
            #   },
            #   ...
            # ]

        except ValidationError as ve:
            return f"[ERROR] Input validation failed: {ve.json(indent=2)}"
        except Exception as e:
            return f"[ERROR] Failed to encode or read image: {str(e)}"
