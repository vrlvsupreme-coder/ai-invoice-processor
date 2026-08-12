import logging
from typing import List
from app.core.config import settings
from app.models.schemas import AgentVerificationResult

logger = logging.getLogger(__name__)

class GoogleSheetsService:
    def __init__(self):
        self.auth_file = settings.GOOGLE_SHEETS_CREDENTIALS_FILE
        self.sheet_id = settings.GOOGLE_SHEET_ID
        self._is_active = False

        # Attempt to init gspread client.
        # If credentials.json doesn't exist, we fall back to a "Mock/Print" mode.
        try:
            import gspread
            import os
            
            if os.path.exists(self.auth_file):
                self.client = gspread.service_account(filename=self.auth_file)
                self.doc = self.client.open_by_key(self.sheet_id)
                
                try:
                    self.summary_sheet = self.doc.worksheet("Invoice Summary")
                except gspread.exceptions.WorksheetNotFound:
                    logger.info("Creating 'Invoice Summary' sheet.")
                    self.summary_sheet = self.doc.add_worksheet(title="Invoice Summary", rows="100", cols="23")
                    summary_headers = [
                        "Upload Date", "File Name", "Verification Status", "Error Details", 
                        "Invoice No", "Invoice Date", "Vendor GSTIN", "Buyer GSTIN", "Place of Supply",
                        "Dispatch From", "Vendor", "Address", "Customer Order No.", "Bill To Address", 
                        "Delivery Address", "Invoice Amount (Rs)", "TCS Rate (%)", "TCS Amount (Rs)", 
                        "Receivable", "Total Receivable Amount", "Confidence Score (%)", "Reviewed By", "Review Timestamp"
                    ]
                    self.summary_sheet.append_row(summary_headers)
                
                try:
                    self.items_sheet = self.doc.worksheet("Invoice Line Items")
                except gspread.exceptions.WorksheetNotFound:
                    logger.info("Creating 'Invoice Line Items' sheet.")
                    self.items_sheet = self.doc.add_worksheet(title="Invoice Line Items", rows="100", cols="19")
                    items_headers = [
                        "Invoice No (Ref)", "Sr. No", "Part No / Generic Name", "Vendor Part No", "Description", "HSN/SAC", "Qty", "Rate", "Basic Amoun", "Discount Amount", "Type Amount", "Taxable Amount", "SGST Rate", "SGST Amount", "CGST Rate", "CGST Amount", "IGST Rate", "IGST Amount", "Invoice Amount"
                    ]
                    self.items_sheet.append_row(items_headers)
                    
                self._is_active = True
                logger.info("Successfully connected to Google Sheets.")
            else:
                logger.warning(f"Google credentials file '{self.auth_file}' not found. Falling back to Mock Sheets Service.")
        except Exception as e:
            logger.error(f"Failed to connect to Google Sheets: {e}")
            self._is_active = False
            
    def append_data(self, result: AgentVerificationResult):
        """Append Agent logic results into the dual-sheet structure."""
        
        if self._is_active:
            try:
                # Prepare Summary Row
                errors_str = " | ".join(result.errors) if result.errors else "None"
                
                summary_row = [
                    result.review_timestamp[:10], # Upload Date
                    result.file_name,
                    result.verification_status.value,
                    errors_str,
                    result.cleaned_data.invoice_no,
                    result.cleaned_data.invoice_date,
                    result.cleaned_data.vendor_gstin,
                    result.cleaned_data.buyer_gstin,
                    result.cleaned_data.place_of_supply,
                    result.cleaned_data.dispatch_from,
                    result.cleaned_data.vendor,
                    result.cleaned_data.address,
                    result.cleaned_data.customer_order_no,
                    result.cleaned_data.bill_to_address,
                    result.cleaned_data.delivery_address,
                    result.cleaned_data.invoice_amount,
                    result.cleaned_data.tcs_rate_percent,
                    result.cleaned_data.tcs_amount,
                    result.cleaned_data.receivable,
                    result.cleaned_data.total_receivable_amount,
                    result.confidence_score,
                    "AI Verification Agent",
                    result.review_timestamp
                ]
                self.summary_sheet.append_row(summary_row)

                # Prepare Items Rows
                itinerary_rows = []
                for item in result.cleaned_data.line_items:
                    itinerary_rows.append([
                        result.cleaned_data.invoice_no,
                        item.sr_no,
                        item.part_no_or_generic_name,
                        item.vendor_part_no,
                        item.description,
                        item.hsn_sac,
                        item.qty,
                        item.rate,
                        item.basic_amount,
                        item.discount_type,
                        item.discount_amount,
                        item.type_amount,
                        item.taxable_amount,
                        item.sgst_rate_percent,
                        item.sgst_amount,
                        item.cgst_rate_percent,
                        item.cgst_amount,
                        item.igst_rate_percent,
                        item.igst_amount,
                        item.invoice_amount
                    ])
                
                if itinerary_rows:
                    self.items_sheet.append_rows(itinerary_rows)
                logger.info(f"Appended {result.file_name} to Google Sheets.")
            except Exception as e:
                logger.error(f"Error appending to Google Sheets: {e}")
        else:
            errors_str = " | ".join(result.errors) if result.errors else "None"
            
            summary_row = [
                result.review_timestamp[:10], # Pseudo Upload Date
                result.file_name,
                result.verification_status,  # MOVED TO COLUMN C
                errors_str,                  # MOVED TO COLUMN D
                result.cleaned_data.invoice_no,
                result.cleaned_data.invoice_date,
                result.cleaned_data.vendor_gstin,
                result.cleaned_data.buyer_gstin,
                result.cleaned_data.place_of_supply,
                result.cleaned_data.dispatch_from,
                result.cleaned_data.vendor,
                result.cleaned_data.address,
                result.cleaned_data.customer_order_no,
                result.cleaned_data.bill_to_address,
                result.cleaned_data.delivery_address,
                result.cleaned_data.invoice_amount,
                result.cleaned_data.tcs_rate_percent,
                result.cleaned_data.tcs_amount,
                result.cleaned_data.receivable,
                result.cleaned_data.total_receivable_amount,
                result.confidence_score,
                "AI Verification Agent",
                result.review_timestamp
            ]

            # 2. Prepare Items Rows
            itinerary_rows = []
            for item in result.cleaned_data.line_items:
                row = [
                    result.cleaned_data.invoice_no,
                    item.sr_no,
                    item.part_no_or_generic_name,
                    item.description,
                    item.hsn_sac,
                    item.qty,
                    item.rate,
                    item.basic_amount,
                    item.discount_type,
                    item.discount_amount,
                    item.type_amount,
                    item.taxable_amount,
                    item.sgst_rate_percent,
                    item.sgst_amount,
                    item.cgst_rate_percent,
                    item.cgst_amount,
                    item.igst_rate_percent,
                    item.igst_amount,
                    item.invoice_amount
                ]
                itinerary_rows.append(row)

            logger.info("MOCK SHEETS APPEND [Summary Row]: " + str(summary_row))
            for i, r in enumerate(itinerary_rows):
                logger.info(f"MOCK SHEETS APPEND [Item Row {i}]: " + str(r))
