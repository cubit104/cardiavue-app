import pdfplumber
import PyPDF2
import fitz  # pymupdf
from pathlib import Path
from typing import Dict, List, Optional, Any
from loguru import logger
import re

class PDFParser:
    """Base PDF parser with multiple extraction methods"""
    
    def __init__(self, pdf_path: str):
        self.pdf_path = Path(pdf_path)
        self.text_content = ""
        self.tables = []
        self.metadata = {}
        
    def extract_all(self) -> Dict[str, Any]:
        """Extract all data from PDF"""
        try:
            # Extract text content
            self.text_content = self._extract_text_pdfplumber()
            
            # Extract tables
            self.tables = self._extract_tables_pdfplumber()
            
            # Extract metadata
            self.metadata = self._extract_metadata()
            
            logger.info(f"✅ Extracted data from {self.pdf_path.name}")
            return {
                "text": self.text_content,
                "tables": self.tables,
                "metadata": self.metadata,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to extract from {self.pdf_path.name}: {e}")
            return {"status": "error", "error": str(e)}
    
    def _extract_text_pdfplumber(self) -> str:
        """Extract text using pdfplumber (best for structured text)"""
        text_content = ""
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    page_text = page.extract_text()
                    if page_text:
                        text_content += f"\n--- Page {page_num + 1} ---\n"
                        text_content += page_text
        except Exception as e:
            logger.warning(f"pdfplumber extraction failed: {e}")
            # Fallback to PyPDF2
            text_content = self._extract_text_pypdf2()
        
        return text_content
    
    def _extract_text_pypdf2(self) -> str:
        """Fallback text extraction using PyPDF2"""
        text_content = ""
        try:
            with open(self.pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page_num, page in enumerate(pdf_reader.pages):
                    page_text = page.extract_text()
                    if page_text:
                        text_content += f"\n--- Page {page_num + 1} ---\n"
                        text_content += page_text
        except Exception as e:
            logger.error(f"PyPDF2 extraction also failed: {e}")
        
        return text_content
    
    def _extract_tables_pdfplumber(self) -> List[List[List[str]]]:
        """Extract tables using pdfplumber"""
        all_tables = []
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    tables = page.extract_tables()
                    if tables:
                        for table in tables:
                            # Clean up table data
                            cleaned_table = []
                            for row in table:
                                cleaned_row = [cell.strip() if cell else "" for cell in row]
                                cleaned_table.append(cleaned_row)
                            all_tables.append(cleaned_table)
                        logger.info(f"Found {len(tables)} tables on page {page_num + 1}")
        except Exception as e:
            logger.warning(f"Table extraction failed: {e}")
        
        return all_tables
    
    def _extract_metadata(self) -> Dict[str, Any]:
        """Extract PDF metadata"""
        metadata = {}
        try:
            with open(self.pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                if pdf_reader.metadata:
                    metadata = {
                        "title": pdf_reader.metadata.get("/Title", ""),
                        "author": pdf_reader.metadata.get("/Author", ""),
                        "creator": pdf_reader.metadata.get("/Creator", ""),
                        "creation_date": pdf_reader.metadata.get("/CreationDate", ""),
                        "pages": len(pdf_reader.pages)
                    }
        except Exception as e:
            logger.warning(f"Metadata extraction failed: {e}")
        
        return metadata

# Test the basic parser
if __name__ == "__main__":
    # Test with a sample PDF
    parser = PDFParser("test_pdfs/sample_medtronic.pdf")
    result = parser.extract_all()
    
    print("=== EXTRACTED TEXT ===")
    print(result["text"][:500])  # First 500 characters
    
    print("\n=== TABLES FOUND ===")
    print(f"Number of tables: {len(result['tables'])}")
    
    if result["tables"]:
        print("First table preview:")
        for row in result["tables"][0][:3]:  # First 3 rows
            print(row)