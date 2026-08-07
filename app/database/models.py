from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime

Base = declarative_base()

class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    invoice_no = Column(String, index=True)
    invoice_date = Column(String)
    vendor_gstin = Column(String, index=True)
    buyer_gstin = Column(String)
    place_of_supply = Column(String)
    dispatch_from = Column(String)
    vendor = Column(String)
    address = Column(String)
    customer_order_no = Column(String)
    bill_to_address = Column(String)
    delivery_address = Column(String)
    invoice_amount = Column(Float)
    tcs_rate_percent = Column(Float)
    tcs_amount = Column(Float)
    receivable = Column(String)
    total_receivable_amount = Column(Float)
    
    # Verification details
    verification_status = Column(String)
    confidence_score = Column(Float)
    file_name = Column(String)
    file_hash = Column(String, index=True)
    processed_at = Column(DateTime, default=datetime.utcnow)
    raw_ai_response = Column(Text)
    error_message = Column(Text)
    
    # Relationships
    line_items = relationship("LineItem", back_populates="invoice", cascade="all, delete-orphan")

class LineItem(Base):
    __tablename__ = "line_items"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"))
    sr_no = Column(String)
    part_no_or_generic_name = Column(String)
    description = Column(String)
    hsn_sac = Column(String)
    qty = Column(Float)
    rate = Column(Float)
    basic_amount = Column(Float)
    discount_type = Column(String)
    discount_amount = Column(Float)
    type_amount = Column(Float)
    taxable_amount = Column(Float)
    sgst_rate_percent = Column(Float)
    sgst_amount = Column(Float)
    cgst_rate_percent = Column(Float)
    cgst_amount = Column(Float)
    igst_rate_percent = Column(Float)
    igst_amount = Column(Float)
    invoice_amount = Column(Float)

    invoice = relationship("Invoice", back_populates="line_items")
