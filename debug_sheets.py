import os
import gspread
from dotenv import load_dotenv
import traceback

def debug_sheets():
    load_dotenv()
    auth_file = os.getenv("GOOGLE_SHEETS_CREDENTIALS_FILE", "credentials.json")
    sheet_id = os.getenv("GOOGLE_SHEET_ID")
    
    print(f"Using auth file: {auth_file}")
    print(f"Using sheet ID: {sheet_id}")
    
    try:
        client = gspread.service_account(filename=auth_file)
        doc = client.open_by_key(sheet_id)
        print(f"Google Sheets: Connection Successful! (Sheet: {doc.title})")
    except Exception as e:
        print(f"Google Sheets: Connection Failed!")
        traceback.print_exc()

if __name__ == "__main__":
    debug_sheets()
