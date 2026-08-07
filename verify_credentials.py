import os
import google.generativeai as genai
import gspread
from dotenv import load_dotenv

def verify():
    load_dotenv()
    
    api_key = os.getenv("GEMINI_API_KEY")
    print(f"Testing Gemini API Key: {api_key[:10]}...{api_key[-4:]}")
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-flash-latest')
        response = model.generate_content("Hello")
        print("Gemini API: Connection Successful!")
    except Exception as e:
        print(f"Gemini API: Connection Failed! {e}")

    auth_file = os.getenv("GOOGLE_SHEETS_CREDENTIALS_FILE", "credentials.json")
    sheet_id = os.getenv("GOOGLE_SHEET_ID")
    print(f"Testing Google Sheets: {auth_file}, ID: {sheet_id[:10]}...")
    
    try:
        client = gspread.service_account(filename=auth_file)
        doc = client.open_by_key(sheet_id)
        print(f"Google Sheets: Connection Successful! (Sheet: {doc.title})")
    except Exception as e:
        print(f"Google Sheets: Connection Failed! {e}")

if __name__ == "__main__":
    verify()
