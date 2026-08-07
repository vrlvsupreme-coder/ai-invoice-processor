import sys
import os
import asyncio
import logging

# Ensure project structure is visible
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Enable logging printout to see skipped actions
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

from app.api.routes import process_invoice
from app.services.database import DatabaseService

async def test_api_skipping():
    db_service = DatabaseService()
    
    filename = "api_test_invoice.pdf"
    content = b"sample mock pdf file content for hashing"
    content_type = "application/pdf"
    
    # Clean DB first
    from app.database.models import Invoice
    with db_service.get_session() as session:
        session.query(Invoice).filter(Invoice.file_name == filename).delete()
        session.commit()
    print("Database cleaned for test invoice.")
    
    # 1. Run first time (Should NOT skip. It will run and try to query Gemini)
    # Note: Since the content is mock, Gemini OCR will fail, saving a 'Pending / Incomplete' or 'FAILED OCR' state.
    # A 'FAILED OCR' state still registers in the db under the file name. 
    print("\n--- TEST: Running first processing attempt ---")
    await process_invoice(filename, content, content_type)
    
    # 2. Run second time (Should skip immediately because filename / hash is already in the database)
    print("\n--- TEST: Running second duplicate processing attempt ---")
    # We will log the execution. We expect it to hit our pre-OCR duplicate code and print "Skipping extraction for..."
    # and return immediately.
    await process_invoice(filename, content, content_type)
    
    # Confirm
    print("\nTest execution finished. Clean up database invoice...")
    with db_service.get_session() as session:
        session.query(Invoice).filter(Invoice.file_name == filename).delete()
        session.commit()
    print("Clean up finished.")

if __name__ == "__main__":
    asyncio.run(test_api_skipping())
