from typing import List, Optional, Any
from enum import Enum
from pydantic import BaseModel, Field, field_validator
import re

# ---------------------------------------------------------
# Enums for Consistency
# ---------------------------------------------------------

class VerificationStatus(str, Enum):
    VERIFIED = "VERIFIED"
    INCOMPLETE = "INCOMPLETE"
    CALCULATION_ERROR = "CALCULATION ERROR"
    DUPLICATE = "DUPLICATE"
    SUSPICIOUS = "SUSPICIOUS"
    PENDING = "Pending / Incomplete"

# ---------------------------------------------------------
# Helper for Numeric Validation
# ---------------------------------------------------------

def clean_numeric(v: Any) -> float:
    if isinstance(v, str):
        # Remove currency symbols (₹, $, Rs.), commas, and whitespace
        clean_v = re.sub(r'[^\d.-]', '', v)
        try:
            return float(clean_v)
        except ValueError:
            return 0.0
    return v or 0.0

# ---------------------------------------------------------
# Input from OCR/AI Extraction (Raw Data)
# ---------------------------------------------------------

class InvoiceLineItemRaw(BaseModel):
    sr_no: Optional[str] = None
    part_no_or_generic_name: Optional[str] = None
    vendor_part_no: Optional[str] = None
    description: Optional[str] = None
    hsn_sac: Optional[str] = None
    qty: Optional[float] = None
    rate: Optional[float] = None
    basic_amount: Optional[float] = None
    discount_type: Optional[str] = None
    discount_amount: Optional[float] = None
    type_amount: Optional[float] = None
    taxable_amount: Optional[float] = None
    sgst_rate_percent: Optional[float] = None
    sgst_amount: Optional[float] = None
    cgst_rate_percent: Optional[float] = None
    cgst_amount: Optional[float] = None
    igst_rate_percent: Optional[float] = None
    igst_amount: Optional[float] = None
    invoice_amount: Optional[float] = None

    @field_validator("qty", "rate", "basic_amount", "discount_amount", "type_amount", 
                     "taxable_amount", "sgst_rate_percent", "sgst_amount", 
                     "cgst_rate_percent", "cgst_amount", "igst_rate_percent", 
                     "igst_amount", "invoice_amount", mode="before")
    @classmethod
    def parse_numeric(cls, v):
        return clean_numeric(v)

class InvoiceHeaderRaw(BaseModel):
    invoice_no: Optional[str] = None
    invoice_date: Optional[str] = None
    vendor_gstin: Optional[str] = None
    buyer_gstin: Optional[str] = None
    place_of_supply: Optional[str] = None
    dispatch_from: Optional[str] = None
    vendor: Optional[str] = None
    address: Optional[str] = None
    customer_order_no: Optional[str] = None
    bill_to_address: Optional[str] = None
    delivery_address: Optional[str] = None
    invoice_amount: Optional[float] = None
    tcs_rate_percent: Optional[float] = None
    tcs_amount: Optional[float] = None
    receivable: Optional[str] = None
    total_receivable_amount: Optional[float] = None
    
    line_items: List[InvoiceLineItemRaw] = Field(default_factory=list)
    ocr_failed: bool = False
    ocr_error_message: Optional[str] = None

    @field_validator("invoice_amount", "tcs_rate_percent", "tcs_amount", 
                     "total_receivable_amount", mode="before")
    @classmethod
    def parse_numeric(cls, v):
        return clean_numeric(v)

# ---------------------------------------------------------
# Verified Data (Output from AI Agent)
# ---------------------------------------------------------

class InvoiceLineItemVerified(InvoiceLineItemRaw):
    pass

class InvoiceHeaderVerified(InvoiceHeaderRaw):
    line_items: List[InvoiceLineItemVerified] = Field(default_factory=list)

class AgentVerificationResult(BaseModel):
    cleaned_data: InvoiceHeaderVerified
    verification_status: VerificationStatus
    errors: List[str] = Field(default_factory=list)
    confidence_score: float = Field(..., ge=0, le=100)
    review_timestamp: str
    file_name: str
    file_hash: str
    raw_ai_response: Optional[str] = None # For debugging
