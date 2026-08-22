import logging
import json
import io
import asyncio
import re
from typing import Optional
import google.generativeai as genai
from PIL import Image
import pypdfium2 as pdfium

from app.core.config import settings
from app.models.schemas import InvoiceHeaderRaw, InvoiceLineItemRaw

MAX_RETRIES = 5

logger = logging.getLogger(__name__)

# Configure Gemini
if settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY)

PROMPT = """
You are an expert Indian Invoice processing AI. 
Extract the data from the attached invoice image/PDF and return it in a strictly valid JSON format.

Specific Guidance for Indian GST Invoices:
- "vendor_gstin": Usually labelled as "GSTIN" near the vendor name or header.
- "buyer_gstin": Usually labelled as "GSTIN" under the "Bill To" or "Customer" section.
- "place_of_supply": State name or code where the supply is made.
- "igst": Integrated Tax. If IGST is present, SGST/CGST will usually be 0 or empty.
- "hsn_sac": Extract the HSN or SAC code for each item.
- "vendor_part_no": The vendor's internal part number, often labeled "VEND PART", "Vendor Part No", or "Part No" on the invoice — distinct from the generic/description part number.


The JSON must follow this exact structure:

{
  "invoice_no": "...",
  "invoice_date": "...",
  "vendor_gstin": "...",
  "buyer_gstin": "...",
  "place_of_supply": "...",
  "dispatch_from": "...",
  "vendor": "...",
  "address": "...",
  "customer_order_no": "...",
  "bill_to_address": "...",
  "delivery_address": "...",
  "invoice_amount": 0.0,
  "tcs_rate_percent": 0.0,
  "tcs_amount": 0.0,
  "receivable": "...",
  "total_receivable_amount": 0.0,
  "line_items": [
    {
      "sr_no": "...",
      "part_no_or_generic_name": "...",
      "vendor_part_no": "...",
      "description": "...",
      "hsn_sac": "...",
      "qty": 0.0,
      "rate": 0.0,
      "basic_amount": 0.0,
      "discount_type": "...",
      "discount_amount": 0.0,
      "type_amount": 0.0,
      "taxable_amount": 0.0,
      "sgst_rate_percent": 0.0,
      "sgst_amount": 0.0,
      "cgst_rate_percent": 0.0,
      "cgst_amount": 0.0,
      "igst_rate_percent": 0.0,
      "igst_amount": 0.0,
      "invoice_amount": 0.0
    }
  ]
}

Important Rules:
1. Return ONLY the raw JSON block. No markdown markers (like ```json), no intro text.
2. If a value is missing, use null or an empty string.
3. For all numeric fields, ensure they are numeric (floats).
4. Extract line items carefully, checking for multiple pages if present.

Special Layout Recognition (Vendor-Aware Hints):
- AMAZON: Look for "Tax Invoice/Bill of Supply" at the top. Line items are usually in a horizontal table with "Description", "Unit Price", "Quantity", and "Tax Amount".
- SAP/ENTERPRISE: Often has "Material Number" or "Part Number" columns.
- SMALL RETAIL: Look for hand-written looking fonts or thermal printer layouts. Focus on "Total Amount" and "GST %".
"""


async def extract_data_from_file(filename: str, content: bytes, content_type: Optional[str] = None) -> tuple[InvoiceHeaderRaw, str]:
    """
    Real OCR & AI Data Extraction logic using Gemini with multi-page support,
    multi-model fallback chain, and multi-key rotation to handle 429 quota limits.
    Returns: (ParsedModel, RawAIResponseText)
    """
    logger.info(f"Extracting data from file: {filename} (Size: {len(content)} bytes)")
    
    keys = settings.api_keys
    if not keys:
        logger.warning("No GEMINI_API_KEY found in settings. Returning failed state.")
        return InvoiceHeaderRaw(ocr_failed=True, ocr_error_message="GEMINI_API_KEY is missing."), "NO_API_KEY"

    text_response = "NO_RESPONSE"
    try:
        content_parts = [PROMPT]
        
        # Handle PDF vs Image
        if filename.lower().endswith(".pdf"):
            logger.info("Processing PDF via pypdfium2...")
            pdf = pdfium.PdfDocument(content)
            logger.info(f"PDF has {len(pdf)} pages.")
            MAX_PAGES = 3
            for i in range(len(pdf)):
                if i >= MAX_PAGES:
                    logger.info(f"Reached MAX_PAGES limit of {MAX_PAGES}. Skipping remaining pages.")
                    break
                page = pdf[i]
                bitmap = page.render(scale=3)
                pil_image = bitmap.to_pil()
                
                img_byte_arr = io.BytesIO()
                pil_image.save(img_byte_arr, format='JPEG', quality=95)
                content_parts.append({
                    "mime_type": "image/jpeg",
                    "data": img_byte_arr.getvalue()
                })
            pdf.close()

        else:
            logger.info("Processing Image file...")
            content_parts.append({
                "mime_type": content_type or "image/jpeg",
                "data": content
            })

        # Run AI Inference with Multi-Model Fallback and Key Rotation
        models_to_try = settings.fallback_models
        logger.info(f"Starting AI Inference. Candidate models: {models_to_try}")
        
        loop = asyncio.get_event_loop()
        response = None
        last_error = None

        for key_idx, api_key in enumerate(keys):
            genai.configure(api_key=api_key)
            for model_name in models_to_try:
                logger.info(f"Attempting extraction with model '{model_name}' (Key #{key_idx + 1})...")
                try:
                    model = genai.GenerativeModel(model_name)
                    response = await loop.run_in_executor(None, lambda: model.generate_content(content_parts))
                    logger.info(f"Successfully received response from model '{model_name}'.")
                    break # Model succeeded!
                except Exception as api_error:
                    last_error = api_error
                    error_str = str(api_error)
                    if "429" in error_str or "Quota exceeded" in error_str or "ResourceExhausted" in error_str:
                        logger.warning(
                            f"Quota/Rate limit (429) hit for model '{model_name}' (Key #{key_idx + 1}). "
                            f"Falling back to next candidate..."
                        )
                        # Optional short sleep before trying fallback model to prevent burst back-to-back hits
                        await asyncio.sleep(2)
                        continue
                    else:
                        logger.error(f"Non-quota error encountered with model '{model_name}': {api_error}")
                        # For non-429 errors (e.g. invalid argument), also attempt next model before giving up
                        continue
            if response is not None:
                break # Key & model combination succeeded!

        if response is None:
            raise last_error or RuntimeError("All Gemini models and API keys failed extraction.")

        text_response = response.text.strip()
        logger.info("Received AI response.")
        
        # Clean up possible markdown artifacts
        clean_json = text_response
        if "```json" in clean_json:
            clean_json = clean_json.split("```json")[1].split("```")[0].strip()
        elif "```" in clean_json:
            clean_json = clean_json.split("```")[1].split("```")[0].strip()

        data_dict = json.loads(clean_json)
        
        return InvoiceHeaderRaw(**data_dict), text_response

    except Exception as e:
        logger.error(f"Gemini Extraction failed at stage: {type(e).__name__} for {filename}. Details: {e}")
        return InvoiceHeaderRaw(ocr_failed=True, ocr_error_message=f"Extraction Error: {str(e)}"), text_response

