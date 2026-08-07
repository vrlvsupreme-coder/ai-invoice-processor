import logging
from sqlalchemy import create_engine, and_
from sqlalchemy.orm import sessionmaker, Session
from typing import List, Optional
from datetime import datetime

from app.core.config import settings
from app.database.models import Base, Invoice, LineItem
from app.models.schemas import AgentVerificationResult, InvoiceHeaderVerified

logger = logging.getLogger(__name__)

class DatabaseService:
    def __init__(self):
        self.engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False})
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        # Create tables
        Base.metadata.create_all(bind=self.engine)
        logger.info(f"Database initialized at {settings.DATABASE_URL}")

    def get_session(self) -> Session:
        return self.SessionLocal()

    def check_duplicate(self, vendor_gstin: str, invoice_no: str) -> bool:
        """
        Checks if an invoice from the same vendor already exists.
        """
        if not vendor_gstin or not invoice_no:
            return False
            
        with self.get_session() as session:
            exists = session.query(Invoice).filter(
                and_(
                    Invoice.vendor_gstin == vendor_gstin,
                    Invoice.invoice_no == invoice_no
                )
            ).first() is not None
            return exists

    def is_file_processed(self, filename: str) -> bool:
        """
        Checks if a file with the given name has already been processed.
        """
        if not filename:
            return False
            
        with self.get_session() as session:
            # We assume a file is processed if it exists in the Invoice table
            # and its status is not 'Pending / Incomplete'. This allows retrying files.
            invoices = session.query(Invoice).filter(Invoice.file_name == filename).all()
            for invoice in invoices:
                if invoice.verification_status not in ("Pending / Incomplete", "FAILED OCR", "CALCULATION ERROR", "Incomplete"):
                    return True
            return False

    def is_hash_processed(self, file_hash: str) -> bool:
        """
        Checks if a file with the given hash has already been processed.
        """
        if not file_hash:
            return False
            
        with self.get_session() as session:
            invoices = session.query(Invoice).filter(Invoice.file_hash == file_hash).all()
            for invoice in invoices:
                if invoice.verification_status not in ("Pending / Incomplete", "FAILED OCR", "CALCULATION ERROR", "Incomplete"):
                    return True
            return False


    def save_invoice(self, result: AgentVerificationResult):
        """
        Saves a verified invoice and its line items to the database.
        """
        with self.get_session() as session:
            try:
                # Remove any existing pending entries for this file before saving the new result
                session.query(Invoice).filter(
                    and_(
                        Invoice.file_name == result.file_name,
                        Invoice.verification_status.in_(["Pending / Incomplete", "FAILED OCR"])
                    )
                ).delete()

                data = result.cleaned_data
                
                # Create Invoice record
                db_invoice = Invoice(
                    invoice_no=data.invoice_no,
                    invoice_date=data.invoice_date,
                    vendor_gstin=data.vendor_gstin,
                    buyer_gstin=data.buyer_gstin,
                    place_of_supply=data.place_of_supply,
                    dispatch_from=data.dispatch_from,
                    vendor=data.vendor,
                    address=data.address,
                    customer_order_no=data.customer_order_no,
                    bill_to_address=data.bill_to_address,
                    delivery_address=data.delivery_address,
                    invoice_amount=data.invoice_amount,
                    tcs_rate_percent=data.tcs_rate_percent,
                    tcs_amount=data.tcs_amount,
                    receivable=data.receivable,
                    total_receivable_amount=data.total_receivable_amount,
                    verification_status=result.verification_status.value,
                    confidence_score=result.confidence_score,
                    file_name=result.file_name,
                    file_hash=result.file_hash,
                    processed_at=datetime.fromisoformat(result.review_timestamp),
                    raw_ai_response=result.raw_ai_response,
                    error_message=", ".join(result.errors) if result.errors else None
                )
                
                session.add(db_invoice)

                session.flush() # Get the invoice ID
                
                # Add Line Items
                for item in data.line_items:
                    db_item = LineItem(
                        invoice_id=db_invoice.id,
                        sr_no=item.sr_no,
                        part_no_or_generic_name=item.part_no_or_generic_name,
                        description=item.description,
                        hsn_sac=item.hsn_sac,
                        qty=item.qty,
                        rate=item.rate,
                        basic_amount=item.basic_amount,
                        discount_type=item.discount_type,
                        discount_amount=item.discount_amount,
                        type_amount=item.type_amount,
                        taxable_amount=item.taxable_amount,
                        sgst_rate_percent=item.sgst_rate_percent,
                        sgst_amount=item.sgst_amount,
                        cgst_rate_percent=item.cgst_rate_percent,
                        cgst_amount=item.cgst_amount,
                        igst_rate_percent=item.igst_rate_percent,
                        igst_amount=item.igst_amount,
                        invoice_amount=item.invoice_amount
                    )
                    session.add(db_item)
                
                session.commit()
                logger.info(f"Saved invoice {data.invoice_no} to database.")
            except Exception as e:
                session.rollback()
                logger.error(f"Failed to save invoice to database: {e}")
                raise e

    def get_recent_invoices(self, limit: int = 10):
        """
        Retrieves the latest processed invoices for the dashboard.
        """
        with self.get_session() as session:
            invoices = session.query(Invoice).order_by(Invoice.processed_at.desc()).limit(limit).all()
            return invoices
