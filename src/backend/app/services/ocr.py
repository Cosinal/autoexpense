"""
OCR service for extracting text from receipt images and PDFs.
"""

import io
import re
from typing import Optional, Tuple, Dict, List, Union
from pathlib import Path
import pytesseract
from PIL import Image
from pdf2image import convert_from_bytes
import PyPDF2

from app.config import settings


class OCRService:
    """Service for extracting text from receipt files."""

    def __init__(self):
        """Initialize OCR service with Tesseract configuration."""
        # Set Tesseract command path
        pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD

    def extract_text_with_bbox(self, image_data: bytes) -> Dict[str, List]:
        """
        Extract text with bounding box coordinates using Tesseract.

        Returns:
            Dictionary with keys: 'text', 'left', 'top', 'width', 'height', 'conf'
            Each key maps to a list of values for each detected word/region.
        """
        try:
            # Load image
            image = Image.open(io.BytesIO(image_data))

            # Preprocess image for better OCR
            image = self._preprocess_image(image)

            # Run OCR with bbox extraction
            custom_config = r'--oem 3 --psm 6'
            data = pytesseract.image_to_data(image, config=custom_config, output_type=pytesseract.Output.DICT)

            return data

        except Exception as e:
            print(f"Error extracting text with bbox: {str(e)}")
            return {'text': [], 'left': [], 'top': [], 'width': [], 'height': [], 'conf': []}

    def extract_text_from_image(self, image_data: bytes) -> str:
        """
        Extract text from an image using Tesseract OCR.

        Args:
            image_data: Raw image bytes (JPEG, PNG, etc.)

        Returns:
            Extracted text
        """
        try:
            # Load image
            image = Image.open(io.BytesIO(image_data))

            # Preprocess image for better OCR
            image = self._preprocess_image(image)

            # Run OCR with custom config for receipts
            custom_config = r'--oem 3 --psm 6'
            text = pytesseract.image_to_string(image, config=custom_config)

            return text.strip()

        except Exception as e:
            print(f"Error extracting text from image: {str(e)}")
            return ""

    def extract_text_from_pdf(self, pdf_data: bytes) -> str:
        """
        Extract text from a PDF file.
        First tries to extract text directly, then falls back to OCR.

        Args:
            pdf_data: Raw PDF bytes

        Returns:
            Extracted text
        """
        try:
            # First, try to extract text directly (for text-based PDFs)
            text = self._extract_pdf_text_direct(pdf_data)

            # If little or no text found, PDF might be image-based
            if len(text.strip()) < 50:
                print("PDF appears to be image-based, using OCR...")
                text = self._extract_pdf_text_ocr(pdf_data)

            return text.strip()

        except Exception as e:
            print(f"Error extracting text from PDF: {str(e)}")
            return ""

    def _extract_pdf_text_direct(self, pdf_data: bytes) -> str:
        """
        Extract text directly from PDF (for text-based PDFs).

        Args:
            pdf_data: Raw PDF bytes

        Returns:
            Extracted text
        """
        try:
            pdf_file = io.BytesIO(pdf_data)
            pdf_reader = PyPDF2.PdfReader(pdf_file)

            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"

            return text

        except Exception as e:
            print(f"Error in direct PDF text extraction: {str(e)}")
            return ""

    def extract_bbox_from_pdf(self, pdf_data: bytes, page_num: int = 0) -> Dict[str, List]:
        """
        Extract text with bounding boxes from a specific page of a PDF.

        Args:
            pdf_data: Raw PDF bytes
            page_num: Page number to extract (0-indexed)

        Returns:
            Dictionary with bbox data for the specified page
        """
        try:
            # Convert PDF pages to images
            images = convert_from_bytes(pdf_data)

            if page_num >= len(images):
                print(f"Page {page_num} does not exist in PDF (total pages: {len(images)})")
                return {'text': [], 'left': [], 'top': [], 'width': [], 'height': [], 'conf': []}

            # Get the requested page
            image = images[page_num]

            # Preprocess image
            image = self._preprocess_image(image)

            # Extract bbox data
            custom_config = r'--oem 3 --psm 6'
            data = pytesseract.image_to_data(image, config=custom_config, output_type=pytesseract.Output.DICT)

            return data

        except Exception as e:
            print(f"Error extracting bbox from PDF: {str(e)}")
            return {'text': [], 'left': [], 'top': [], 'width': [], 'height': [], 'conf': []}

    def _extract_pdf_text_ocr(self, pdf_data: bytes) -> str:
        """
        Extract text from PDF using OCR (for image-based PDFs).

        Args:
            pdf_data: Raw PDF bytes

        Returns:
            Extracted text
        """
        try:
            # Convert PDF pages to images
            images = convert_from_bytes(pdf_data)

            # OCR each page
            text = ""
            for i, image in enumerate(images):
                # Preprocess image
                image = self._preprocess_image(image)

                # Extract text
                custom_config = r'--oem 3 --psm 6'
                page_text = pytesseract.image_to_string(image, config=custom_config)
                text += page_text + "\n"

            return text

        except Exception as e:
            print(f"Error in OCR-based PDF text extraction: {str(e)}")
            return ""

    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """
        Preprocess image to improve OCR accuracy.

        Args:
            image: PIL Image object

        Returns:
            Preprocessed image
        """
        try:
            # Convert to RGB if needed
            if image.mode != 'RGB':
                image = image.convert('RGB')

            # Convert to grayscale
            image = image.convert('L')

            # Increase contrast (simple threshold)
            # This helps with faded receipts
            from PIL import ImageEnhance
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(2.0)

            return image

        except Exception as e:
            print(f"Error preprocessing image: {str(e)}")
            return image

    def extract_text_from_file(
        self,
        file_data: bytes,
        mime_type: str,
        filename: str = "",
        with_bbox: bool = False
    ) -> Union[str, Dict[str, Union[str, Dict[str, List]]]]:
        """
        Extract text from a file (auto-detects format).

        Args:
            file_data: Raw file bytes
            mime_type: MIME type of the file
            filename: Optional filename for extension detection
            with_bbox: If True, return both text and bbox data (for images/PDFs only)

        Returns:
            If with_bbox=False: Extracted text string
            If with_bbox=True: Dictionary with 'text' and 'bbox_data' keys
        """
        # Determine file type
        is_pdf = mime_type == 'application/pdf' or filename.lower().endswith('.pdf')
        is_image = mime_type.startswith('image/') or any(
            filename.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif']
        )

        if with_bbox:
            if is_pdf:
                text = self.extract_text_from_pdf(file_data)
                bbox_data = self.extract_bbox_from_pdf(file_data, page_num=0)
                return {'text': text, 'bbox_data': bbox_data}
            elif is_image:
                text = self.extract_text_from_image(file_data)
                bbox_data = self.extract_text_with_bbox(file_data)
                return {'text': text, 'bbox_data': bbox_data}
            else:
                print(f"Unsupported file type for bbox extraction: {mime_type}")
                return {'text': "", 'bbox_data': None}
        else:
            # Backward compatible - return text only
            if is_pdf:
                return self.extract_text_from_pdf(file_data)
            elif is_image:
                return self.extract_text_from_image(file_data)
            else:
                print(f"Unsupported file type: {mime_type}")
                return ""

    def normalize_text(self, text: str) -> str:
        """
        Normalize extracted text for easier parsing.

        Args:
            text: Raw OCR text

        Returns:
            Normalized text
        """
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)

        # Remove common OCR artifacts
        text = text.replace('|', 'I')  # Common misread
        text = text.replace('{}', '0')  # Common misread

        # Normalize currency symbols
        text = text.replace('$', ' $ ')  # Add spaces around $
        text = text.replace('€', ' € ')
        text = text.replace('£', ' £ ')

        # Clean up
        text = text.strip()

        return text

    def extract_and_normalize(
        self,
        file_data: bytes,
        mime_type: str,
        filename: str = ""
    ) -> str:
        """
        Extract and normalize text from a file in one step.

        Args:
            file_data: Raw file bytes
            mime_type: MIME type
            filename: Optional filename

        Returns:
            Extracted and normalized text
        """
        text = self.extract_text_from_file(file_data, mime_type, filename)
        return self.normalize_text(text)
