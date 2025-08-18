#!/usr/bin/env python3
"""
Simple script to run Medtronic PDF extraction
Usage: python run_extraction.py [pdf_file_path]
"""

import sys
import os
from pathlib import Path

# Add current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from src.utils.logger import setup_logging
from src.extractors.medtronic_parser import MedtronicParser
from src.database.operations import MedtronicDataInserter

def main():
    # Setup logging
    logger = setup_logging()
    
    # Get PDF file path
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
    else:
        # Look for PDFs in the current directory
        curr_dir = Path(".")
        pdf_files = list(curr_dir.glob("*.pdf"))

        if not pdf_files:
            logger.error("No PDF files found in current directory")
            logger.info("Usage: python run_extraction.py [pdf_file_path]")
            logger.info("Or place PDF files in the current directory")
            return

        pdf_path = pdf_files[0]  # Use first PDF found
        logger.info(f"Using PDF: {pdf_path}")

    # Check if file exists
    if not Path(pdf_path).exists():
        logger.error(f"PDF file not found: {pdf_path}")
        return

    try:
        # Extract data from PDF
        logger.info(f"🔍 Extracting data from {pdf_path}")
        parser = MedtronicParser(str(pdf_path))
        result = parser.extract_medtronic_data()

        if result["status"] == "error":
            logger.error(f"❌ Extraction failed: {result['error']}")
            return

        extracted_data = result["data"]
        logger.info("✅ PDF extraction successful")

        # Print summary
        print("\n" + "="*60)
        print("EXTRACTION SUMMARY")
        print("="*60)
        print(f"Patient: {extracted_data['patient'].get('patient_name', 'Unknown')}")
        print(f"Device: {extracted_data['device'].get('device_model', 'Unknown')}")
        print(f"Serial: {extracted_data['device'].get('serial_number', 'Unknown')}")
        print(f"Parameters: {len(extracted_data['parameters'])}")
        print(f"Measurements: {len(extracted_data['measurements'])}")
        print(f"Episodes: {len(extracted_data['episodes'])}")

        # Insert into database
        logger.info("💾 Inserting data into database...")
        with MedtronicDataInserter() as inserter:
            session_id = inserter.insert_complete_session(extracted_data)

            if session_id:
                logger.info(f"✅ Data successfully saved to database")
                logger.info(f"📋 Session ID: {session_id}")
                print(f"\n🎉 SUCCESS: Data saved with session ID: {session_id}")
            else:
                logger.error("❌ Failed to save data to database")

    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()