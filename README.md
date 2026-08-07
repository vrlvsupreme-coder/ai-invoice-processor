
 ---
title: AI Invoice Processor
emoji: 📄
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 7860
---
# 📄 AI-Based Multi Invoice Upload & Extraction

A 24/7 AI-powered web application for uploading, extracting, verifying, and syncing Indian GST invoices to Google Sheets — powered by **Gemini AI**.

## Features
- 📤 **Multi-file Upload:** Upload multiple PDF, JPG, PNG invoices at once
- 🤖 **AI Extraction:** Gemini AI extracts all invoice fields (vendor, GSTIN, line items, GST amounts)
- ✅ **Auto-Verification:** Validates GST calculations, flags duplicates and suspicious entries
- 📊 **Google Sheets Sync:** Auto-appends verified invoices to your Google Sheet
- 📥 **Excel Export:** Download all processed data as a formatted Excel file
- 🔄 **Duplicate Detection:** Prevents re-processing of the same invoice (by filename, hash, and GSTIN+InvoiceNo)

## Environment Secrets (Required)
Set these as **Secrets** in your Hugging Face Space settings:

| Secret Name | Description |
|---|---|
| `GEMINI_API_KEY` | Your Google AI Gemini API Key |
| `GOOGLE_SHEET_ID` | The ID of your target Google Sheet |
| `GOOGLE_CREDENTIALS_JSON` | The full contents of your `credentials.json` service account file |
| `GEMINI_MODEL_NAME` | Model to use, e.g. `gemini-flash-latest` |

## Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Copy env file
cp env .env

# Run server locally
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
#   a i - i n v o i c e - p r o c e s s o r 
 
 
