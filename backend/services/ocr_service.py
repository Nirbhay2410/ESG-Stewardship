import os
from typing import Optional
import mimetypes


class OCRService:
    """
    Service for extracting text from various file formats
    """
    
    def __init__(self):
        self.supported_formats = ['.txt', '.csv', '.pdf', '.png', '.jpg', '.jpeg']
    
    async def extract_text(self, file_path: str) -> str:
        """
        Extract text from a file based on its format
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        file_extension = os.path.splitext(file_path)[1].lower()
        
        # Text files
        if file_extension in ['.txt', '.csv']:
            return await self._extract_from_text(file_path)
        
        # PDF files
        elif file_extension == '.pdf':
            return await self._extract_from_pdf(file_path)
        
        # Image files
        elif file_extension in ['.png', '.jpg', '.jpeg']:
            return await self._extract_from_image(file_path)
        
        else:
            raise ValueError(f"Unsupported file format: {file_extension}")
    
    async def _extract_from_text(self, file_path: str) -> str:
        """Extract text from plain text or CSV files"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            # Try with different encoding
            with open(file_path, 'r', encoding='latin-1') as f:
                return f.read()
    
    async def _extract_from_pdf(self, file_path: str) -> str:
        """Extract text from PDF files"""
        try:
            import PyPDF2
            
            text = ""
            with open(file_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
            
            return text.strip()
        except ImportError:
            return "[PDF extraction requires PyPDF2 - install with: pip install PyPDF2]"
        except Exception as e:
            return f"[Error extracting PDF: {str(e)}]"
    
    async def _extract_from_image(self, file_path: str) -> str:
        """Extract text from image files using OCR"""
        try:
            from PIL import Image
            import pytesseract
            
            image = Image.open(file_path)
            text = pytesseract.image_to_string(image)
            
            return text.strip()
        except ImportError:
            return "[Image OCR requires pytesseract and Pillow - install with: pip install pytesseract pillow]"
        except Exception as e:
            return f"[Error extracting text from image: {str(e)}]"


# Singleton instance
ocr_service = OCRService()
