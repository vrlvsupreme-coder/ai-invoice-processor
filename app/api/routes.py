from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException, Form
from typing import List
import logging
import hashlib

from app.services.ocr import extract_data_from_file
from app.services.agent import AIVerificationAgent
from app.services.sheets import GoogleSheetsService
from app.models.schemas import VerificationStatus

from app.services.database import DatabaseService
from app.services.export import ExportService
from fastapi.responses import Response

logger = logging.getLogger(__name__)

router = APIRouter()
db_service = DatabaseService()
agent = AIVerificationAgent(db_service=db_service)
sheets_service = GoogleSheetsService()
export_service = ExportService(db_service=db_service)

import asyncio

# Concurrency Semaphore to process batch uploads smoothly (30-40 invoices per day)
batch_semaphore = asyncio.Semaphore(1)

async def process_invoice(filename: str, content: bytes, content_type: str, allow_duplicates: bool = False):
    """
    Background worker function that runs the full pipeline for one file,
    throttled to safely process large multi-invoice uploads (30-40 files/day).
    """
    async with batch_semaphore:
        try:
            file_hash = hashlib.sha256(content).hexdigest()
            
            # 0. Duplicate Checks (Filename & Hash) before extraction (skipped if allow_duplicates=True)
            if not allow_duplicates:
                if db_service.is_file_processed(filename):
                    logger.info(f"Skipping extraction for {filename} - filename already in database.")
                    return

                if db_service.is_hash_processed(file_hash):
                    logger.info(f"Skipping extraction for {filename} - content duplicate (hash match).")
                    return
            else:
                logger.info(f"Allowing duplicate invoice upload for {filename} (allow_duplicates=True).")

            # 1. OCR / Extraction (Gemini AI) with Multi-Model Fallback
            raw_data, raw_ai_response = await extract_data_from_file(filename, content, content_type)
            
            # 2. AI Verification Agent Pipeline
            verification_result = agent.run_pipeline(
                filename=filename,
                file_hash=file_hash,
                raw_data=raw_data,
                raw_ai_response=raw_ai_response
            )
            
            # 3. Google Sheets Integration (Only if NOT a duplicate invoice)
            if verification_result.verification_status != VerificationStatus.DUPLICATE:
                sheets_service.append_data(verification_result)
            else:
                logger.info(f"Skipping Google Sheets append for duplicate invoice metadata: {filename}")
            
            # 4. Local DB Persistence
            db_service.save_invoice(verification_result)
            
            logger.info(f"Successfully processed {filename} -> Status: {verification_result.verification_status.value}")
        except Exception as e:
            logger.error(f"Error processing {filename}: {e}")
        finally:
            # Rate pacing delay to safely stay under Gemini Free Tier limits during 30-40 batch uploads
            await asyncio.sleep(4)


@router.post("/upload/", tags=["Invoices"])
async def upload_invoices(
    background_tasks: BackgroundTasks, 
    files: List[UploadFile] = File(...),
    allow_duplicates: bool = Form(False)
):
    """
    Upload Multiple Invoices (PDF/JPG/PNG).
    Files are accepted, basic validation is done, and processing is spun into the background.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")
        
    accepted_content_types = ["application/pdf", "image/jpeg", "image/png"]
    
    accepted_files = []
    rejected_files = []
    
    for file in files:
        if file.content_type not in accepted_content_types:
            rejected_files.append({"filename": file.filename, "reason": "Unsupported file type"})
            continue
            
        accepted_files.append(file.filename)
        
        # Read content before connection closes
        content = await file.read()
        
        # Add to background worker with allow_duplicates option
        background_tasks.add_task(process_invoice, file.filename, content, file.content_type, allow_duplicates)

    return {
        "message": "Files queued for processing successfully",
        "queued": len(accepted_files),
        "rejected": len(rejected_files),
        "details": {
            "accepted_files": accepted_files,
            "rejected_files": rejected_files
        }
    }

@router.get("/recent/", tags=["Invoices"])
async def get_recent_activity():
    """
    Get the latest 10 processed invoices from the database.
    Used for the dashboard activity feed.
    """
    return db_service.get_recent_invoices(limit=10)

@router.get("/export/", tags=["Invoices"])
async def export_to_excel():
    """
    Export all processed invoices to a multi-sheet Excel file.
    """
    content = export_service.export_invoices_to_excel()
    if not content:
        raise HTTPException(status_code=404, detail="No invoice data found to export")
    
    headers = {
        'Content-Disposition': 'attachment; filename="invoices_export.xlsx"'
    }
    return Response(content, headers=headers, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@router.post("/retry-pending/", tags=["Invoices"])
async def retry_pending_invoices(background_tasks: BackgroundTasks):
    """
    Re-queues all invoices in 'Pending / Incomplete' or 'FAILED OCR' state for processing using the multi-model fallback chain.
    """
    import os
    pending_invoices = db_service.get_pending_invoices()
    if not pending_invoices:
        return {"message": "No pending or failed invoices to retry."}
    
    requeued_files = []
    missing_files = []
    
    invoices_dir = os.path.join(os.getcwd(), "invoices")
    
    for inv in pending_invoices:
        file_path = os.path.join(invoices_dir, inv.file_name)
        if os.path.exists(file_path):
            with open(file_path, "rb") as f:
                content = f.read()
            content_type = "application/pdf" if inv.file_name.lower().endswith(".pdf") else "image/jpeg"
            background_tasks.add_task(process_invoice, inv.file_name, content, content_type)
            requeued_files.append(inv.file_name)
        else:
            missing_files.append(inv.file_name)

    return {
        "message": f"Queued {len(requeued_files)} pending invoices for retry with multi-model fallback.",
        "requeued": requeued_files,
        "missing_on_disk": missing_files
    }

