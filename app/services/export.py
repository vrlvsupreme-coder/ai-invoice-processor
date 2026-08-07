import pandas as pd
import io
import logging
from sqlalchemy.orm import Session
from app.database.models import Invoice, LineItem
from app.services.database import DatabaseService

logger = logging.getLogger(__name__)

class ExportService:
    def __init__(self, db_service: DatabaseService):
        self.db_service = db_service

    def export_invoices_to_excel(self) -> bytes:
        """
        Fetches all invoices and their line items from the database 
        and generates a multi-sheet Excel file in memory.
        """
        try:
            with self.db_service.get_session() as session:
                # 1. Fetch Invoices (Summary)
                invoices = session.query(Invoice).order_by(Invoice.processed_at.desc()).all()
                if not invoices:
                    return None

                invoice_data = []
                for inv in invoices:
                    invoice_data.append({
                        "ID": inv.id,
                        "File Name": inv.file_name,
                        "Verification Status": inv.verification_status,
                        "Invoice No": inv.invoice_no,
                        "Invoice Date": inv.invoice_date,
                        "Vendor": inv.vendor,
                        "Vendor GSTIN": inv.vendor_gstin,
                        "Buyer GSTIN": inv.buyer_gstin,
                        "Place of Supply": inv.place_of_supply,
                        "Invoice Amount": inv.invoice_amount,
                        "Total Receivable": inv.total_receivable_amount,
                        "Processed At": inv.processed_at
                    })
                
                df_summary = pd.DataFrame(invoice_data)

                # 2. Fetch Line Items
                line_items = session.query(LineItem).all()
                item_data = []
                for item in line_items:
                    item_data.append({
                        "Invoice ID": item.invoice_id,
                        "Sr No": item.sr_no,
                        "Description": item.description,
                        "HSN/SAC": item.hsn_sac,
                        "Qty": item.qty,
                        "Rate": item.rate,
                        "Taxable Amount": item.taxable_amount,
                        "IGST": item.igst_amount,
                        "CGST": item.cgst_amount,
                        "SGST": item.sgst_amount,
                        "Total Item Amount": item.invoice_amount
                    })
                
                df_items = pd.DataFrame(item_data)

                # 3. Create Excel in memory
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df_summary.to_excel(writer, sheet_name='Invoice Summary', index=False)
                    df_items.to_excel(writer, sheet_name='Line Items', index=False)
                
                return output.getvalue()

        except Exception as e:
            logger.error(f"Failed to generate Excel export: {e}")
            return None
