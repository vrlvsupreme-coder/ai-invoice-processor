import os
import asyncio
import logging
import hashlib
from app.services.ocr import extract_data_from_file
from app.services.agent import AIVerificationAgent
from app.services.sheets import GoogleSheetsService
from app.services.database import DatabaseService

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def calculate_file_hash(file_path: str) -> str:
    """Calculates SHA256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

async def process_single_invoice(filename: str, directory_path: str, db_service: DatabaseService, agent: AIVerificationAgent, sheets_service: GoogleSheetsService, semaphore: asyncio.Semaphore):
    """Processes a single invoice file with a concurrency limit."""
    async with semaphore:
        file_path = os.path.join(directory_path, filename)
        file_hash = calculate_file_hash(file_path)
        
        logging.info(f"\n--- Checking {filename} ---")
        
        # 1. Duplicate Checks (Filename & Hash)
        if db_service.is_file_processed(filename):
            logging.info(f"Skipping {filename} - filename already in database.")
            return

        if db_service.is_hash_processed(file_hash):
            logging.info(f"Skipping {filename} - content duplicate (hash match).")
            return

        logging.info(f"Processing {filename}...")
        
        try:
            with open(file_path, "rb") as f:
                content = f.read()
                
                # 2. Extract Data (Gemini AI)
                raw_data, raw_ai_response = await extract_data_from_file(filename, content)
                
                # 3. Clean & Verify (AI Agent)
                verified_result = agent.run_pipeline(filename, file_hash, raw_data, raw_ai_response)
                
                logging.info(f"Result for {filename}: {verified_result.verification_status.value}")
                if verified_result.errors:
                    logging.info(f"Errors in {filename}: {verified_result.errors}")
                
                # 4. Append to Google Sheets
                sheets_service.append_data(verified_result)
                
                # 5. Save to Local DB
                db_service.save_invoice(verified_result)
                
            # Rate limit mitigation for Free Tier (max 15 RPM = wait >4s)
            await asyncio.sleep(6)
            
        except Exception as e:
            logging.error(f"Failed to process {filename}: {e}")

async def process_directory(directory_path: str):
    """
    Processes all items in the directory in parallel with controlled concurrency.
    """
    if not os.path.exists(directory_path):
        logging.error(f"Directory '{directory_path}' does not exist.")
        return

    files = [f for f in os.listdir(directory_path) if os.path.isfile(os.path.join(directory_path, f))]
    
    if not files:
        logging.warning(f"No files found in '{directory_path}'.")
        return

    logging.info(f"Found {len(files)} files. Starting concurrent processing...")
    
    db_service = DatabaseService()
    agent = AIVerificationAgent(db_service=db_service)
    sheets_service = GoogleSheetsService()
    
    # Limit concurrency strictly to avoid Gemini 429 errors (Free tier is 15 RPM)
    semaphore = asyncio.Semaphore(1) 
    
    tasks = [
        process_single_invoice(f, directory_path, db_service, agent, sheets_service, semaphore) 
        for f in files
    ]
    
    await asyncio.gather(*tasks)
    logging.info("\nBatch processing complete.")

if __name__ == "__main__":
    INVOICES_DIR = os.path.join(os.path.dirname(__file__), "invoices")
    asyncio.run(process_directory(INVOICES_DIR))

