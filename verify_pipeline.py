# Mock Verification Script

import asyncio
from fastapi import UploadFile
from typing import IO
from app.services.ocr import extract_data_from_file
from app.services.agent import AIVerificationAgent
from app.services.sheets import GoogleSheetsService
from app.models.schemas import InvoiceHeaderRaw

class MockFile:
    def __init__(self, filename: str, content_type: str):
        self.filename = filename
        self.content_type = content_type

async def run_verification():
    print("Starting AI Validation Pipeline Test...\n")
    
    # Init Services
    agent = AIVerificationAgent()
    sheets_service = GoogleSheetsService()
    
    # Mock some basic file upload objects
    files = [
        MockFile("invoice_001.pdf", "application/pdf"),
        MockFile("purchase_receipt_55.jpg", "image/jpeg")
    ]
    
    for f in files:
        print(f"--- Processing {f.filename} ---")
        
        # 1. Mock Extraction
        raw_data = await extract_data_from_file(f)
        
        # Inject some errors into the second file to test fraud detection
        if "purchase_receipt_55" in f.filename:
            raw_data.invoice_amount = -500.0  # Should trigger suspicious
            raw_data.gstin_number = ""        # Should trigger incomplete
            
        print("Raw Extraction Done.")
        
        # 2. Validation
        result = agent.run_pipeline(f.filename, raw_data)
        print(f"Agent Status: {result.verification_status}")
        if result.errors:
            print(f"Agent Errors: {result.errors}")
            
        # 3. Sheets
        sheets_service.append_data(result)
        print("Sheets Append Done (Check logs for mock print).")
        print("-" * 40 + "\n")

if __name__ == "__main__":
    asyncio.run(run_verification())
