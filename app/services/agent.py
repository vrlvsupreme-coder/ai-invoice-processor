from datetime import datetime
from typing import Optional
from app.models.schemas import (
    InvoiceHeaderRaw,
    InvoiceHeaderVerified,
    AgentVerificationResult,
    VerificationStatus
)
from app.services.database import DatabaseService

class AIVerificationAgent:
    """
    Core Intelligence Layer.
    Processes Raw OCR Output -> Cleans -> Validates -> Checks Finances -> Detects Fraud
    """

    def __init__(self, db_service: Optional[DatabaseService] = None):
        self.db_service = db_service

    def run_pipeline(self, filename: str, file_hash: str, raw_data: InvoiceHeaderRaw, raw_ai_response: Optional[str] = None) -> AgentVerificationResult:
        # 0. Check for OCR failure
        if raw_data.ocr_failed:
            return AgentVerificationResult(
                cleaned_data=InvoiceHeaderVerified(**raw_data.model_dump(exclude={"ocr_failed", "ocr_error_message"})),
                verification_status=VerificationStatus.PENDING,
                errors=[f"OCR Error: {raw_data.ocr_error_message}"],
                confidence_score=0.0,
                review_timestamp=datetime.now().isoformat(),
                file_name=filename,
                file_hash=file_hash,
                raw_ai_response=raw_ai_response
            )


        # 1. Clean Data
        cleaned = self._clean_data(raw_data)

        status = VerificationStatus.VERIFIED
        errors = []

        # 2. Mandatory Checks
        is_complete, missing_fields = self._check_mandatory_fields(cleaned)
        if not is_complete:
            status = VerificationStatus.INCOMPLETE
            errors.extend([f"Missing mandatory field: {f}" for f in missing_fields])

        # 3 & 4. Financial Calculations
        calc_valid, calc_errors = self._verify_calculations(cleaned)
        if not calc_valid:
            status = VerificationStatus.CALCULATION_ERROR
            errors.extend(calc_errors)

        # 5. Duplicate Detection (Real DB Check)
        is_dup = self._check_duplicates(cleaned)
        if is_dup:
            status = VerificationStatus.DUPLICATE
            errors.append(f"Duplicate invoice detected in local database (Vendor GSTIN: {cleaned.vendor_gstin}, No: {cleaned.invoice_no}).")

        # 6. Fraud / Suspicious Rules
        is_sus, sus_errors = self._check_fraud_suspicious(cleaned)
        if is_sus:
            if status != VerificationStatus.DUPLICATE:
                status = VerificationStatus.SUSPICIOUS
            errors.extend(sus_errors)

        # Output Construction
        confidence = 95.0 # Example mock value

        return AgentVerificationResult(
            cleaned_data=cleaned,
            verification_status=status,
            errors=errors,
            confidence_score=confidence,
            review_timestamp=datetime.now().isoformat(),
            file_name=filename,
            file_hash=file_hash,
            raw_ai_response=raw_ai_response
        )



    def _clean_data(self, raw: InvoiceHeaderRaw) -> InvoiceHeaderVerified:
        """
        Data Cleaning Rules.
        """
        # Note: In a real agent, this is often done via prompt instruction to an LLM,
        # but hardcoding heuristics works great for deterministic business rules.

        data_dict = raw.model_dump()

        # Clean Date (Attempting basic string conversion for demo)
        date_str = data_dict.get("invoice_date")
        if date_str:
            try:
                # E.g. 15-Oct-23 -> 15-10-2023
                parsed = datetime.strptime(date_str.replace(" ", ""), "%d-%b-%y")
                data_dict["invoice_date"] = parsed.strftime("%d-%m-%Y")
            except Exception:
                pass # LLM fallback or leave as is if unparseable
                
        # Trim Spaces & Clean GSTINs
        for key in ["vendor_gstin", "buyer_gstin"]:
            val = data_dict.get(key)
            if val:
                # Normalize: Uppercase, strip, replace 'O' with '0', limit to 15 chars
                data_dict[key] = str(val).strip().upper().replace("O", "0")[:15]
            
        # Standardize Strings
        for key in ["vendor", "dispatch_from", "invoice_no"]:
            val = data_dict.get(key)
            if val:
                data_dict[key] = str(val).strip()

        # Build Verified Model
        # (This implicitly dumps all keys and attempts to instantiate the verified model)
        return InvoiceHeaderVerified(**data_dict)

    def _check_mandatory_fields(self, data: InvoiceHeaderVerified):
        missing = []
        if not data.invoice_no: missing.append("Invoice No")
        if not data.invoice_date: missing.append("Invoice Date")
        if not data.vendor: missing.append("Vendor")
        if not data.vendor_gstin: missing.append("Vendor GSTIN")
        if not data.buyer_gstin: missing.append("Buyer GSTIN")
        if not data.place_of_supply: missing.append("Place of Supply")
        if data.invoice_amount is None: missing.append("Invoice Amount")
        if data.total_receivable_amount is None: missing.append("Total Receivable Amount")
        
        return len(missing) == 0, missing

    def _verify_calculations(self, data: InvoiceHeaderVerified):
        errors = []
        is_valid = True
        
        # Line Items verification
        total_calculated_invoice = 0.0
        
        for item in data.line_items:
            # Taxable Amount = Basic Amount - Discount
            calc_taxable = (item.basic_amount or 0) - (item.discount_amount or 0)
            if abs(calc_taxable - (item.taxable_amount or 0)) > 1.0:
                # Fallback: if Taxable + Taxes = Invoice Amount, then Taxable is valid despite basic_amount mismatch
                calc_item_total_check = (item.taxable_amount or 0) + (item.sgst_amount or 0) + (item.cgst_amount or 0) + (item.igst_amount or 0)
                if abs(calc_item_total_check - (item.invoice_amount or 0)) > 1.0:
                    is_valid = False
                    errors.append(f"Item {item.sr_no}: Taxable discrepancy (Expected {calc_taxable}, Got {item.taxable_amount})")
            
            # SGST Amount = Taxable × SGST %
            calc_sgst = (item.taxable_amount or 0) * (item.sgst_rate_percent or 0) / 100
            if abs(calc_sgst - (item.sgst_amount or 0)) > 1.0:
                 is_valid = False
                 errors.append(f"Item {item.sr_no}: SGST discrepancy")

            # CGST Amount = Taxable × CGST %
            calc_cgst = (item.taxable_amount or 0) * (item.cgst_rate_percent or 0) / 100
            if abs(calc_cgst - (item.cgst_amount or 0)) > 1.0:
                 is_valid = False
                 errors.append(f"Item {item.sr_no}: CGST discrepancy")
                 
            # IGST Amount = Taxable × IGST %
            calc_igst = (item.taxable_amount or 0) * (item.igst_rate_percent or 0) / 100
            if abs(calc_igst - (item.igst_amount or 0)) > 1.0:
                 is_valid = False
                 errors.append(f"Item {item.sr_no}: IGST discrepancy")

            # Invoice Amount = Taxable + SGST + CGST + IGST
            calc_item_total = (item.taxable_amount or 0) + (item.sgst_amount or 0) + (item.cgst_amount or 0) + (item.igst_amount or 0)
            if abs(calc_item_total - (item.invoice_amount or 0)) > 1.0:
                 is_valid = False
                 errors.append(f"Item {item.sr_no}: Total Item Amount discrepancy")
            
            total_calculated_invoice += (item.invoice_amount or 0)
            
        # Total Receivable Verification
        # Header Invoice Amount vs Item sum check (optional but good practice)
        if abs(total_calculated_invoice - (data.invoice_amount or 0)) > 1.0 and len(data.line_items) > 0:
            is_valid = False
            errors.append(f"Header Invoice Amount ({data.invoice_amount}) does not match sum of items ({total_calculated_invoice})")

        # Total Receivable = Invoice Amount + TCS Amount
        calc_total = (data.invoice_amount or 0) + (data.tcs_amount or 0)
        if abs(calc_total - (data.total_receivable_amount or 0)) > 1.0:
            is_valid = False
            errors.append(f"Total Receivable discrepancy (Expected {calc_total}, Got {data.total_receivable_amount})")

        return is_valid, errors

    def _check_duplicates(self, data: InvoiceHeaderVerified) -> bool:
        if self.db_service:
            return self.db_service.check_duplicate(data.vendor_gstin, data.invoice_no)
        return False

    def _check_fraud_suspicious(self, data: InvoiceHeaderVerified):
        errors = []
        is_sus = False
        
        # 1. Missing Line Items
        if not data.line_items or len(data.line_items) == 0:
            is_sus = True
            errors.append("Suspicious: No line items provided")

        # 2. Negative Amounts
        if (data.invoice_amount or 0) < 0 or (data.total_receivable_amount or 0) < 0:
             is_sus = True
             errors.append("Suspicious: Negative header amounts")

        # 3. Future invoice date
        try:
            if data.invoice_date:
                # Normalized format DD-MM-YYYY
                inv_date = datetime.strptime(data.invoice_date, "%d-%m-%Y")
                if inv_date > datetime.now():
                    is_sus = True
                    errors.append("Suspicious: Future invoice date")
        except:
             pass

        # Check line items logic
        for item in data.line_items:
             if (item.sgst_rate_percent or 0) + (item.cgst_rate_percent or 0) > 28.0:
                  is_sus = True
                  errors.append(f"Suspicious Item {item.sr_no}: GST > 28% ({item.sgst_rate_percent} + {item.cgst_rate_percent})")
             if (item.basic_amount or 0) > 0:
                 discount_percent = ((item.discount_amount or 0) / item.basic_amount) * 100
                 if discount_percent > 50.0:
                     is_sus = True
                     errors.append(f"Suspicious Item {item.sr_no}: Discount > 50% ({discount_percent}%)")

        return is_sus, errors
