from crewai_tools import BaseTool
import pytesseract
from PIL import Image
import os

class ImageDiagramTool(BaseTool):
    name: str = "Image Diagram Reader"
    description: str = (
        "Extracts text from architectural diagrams or screenshots using OCR. "
        "Useful when provided with image-based diagrams (PNG, JPG) to understand systems and data flows."
    )

    def _run(self, image_path: str) -> str:
        if not os.path.exists(image_path) or not image_path.lower().endswith(('.png', '.jpg', '.jpeg')):
            return f"[ERROR] Invalid image file: {image_path}"

        try:
            image = Image.open(image_path)
            text = pytesseract.image_to_string(image)
            return text.strip() or "[INFO] No readable text found in the image."

        except Exception as e:
            return f"[ERROR] Failed to extract text: {str(e)}"
