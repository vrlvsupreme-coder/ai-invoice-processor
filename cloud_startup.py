"""
cloud_startup.py
----------------
Run this ONCE when deploying to HuggingFace Spaces or any cloud environment
where secrets are stored as environment variables instead of files.

It reads the GOOGLE_CREDENTIALS_JSON environment variable and writes it
to credentials.json on disk, so gspread can authenticate normally.
"""
import os
import json

def write_credentials():
    creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
    if creds_json:
        try:
            parsed = json.loads(creds_json)
            with open("credentials.json", "w") as f:
                json.dump(parsed, f, indent=2)
            print("credentials.json written from GOOGLE_CREDENTIALS_JSON env var.")
        except Exception as e:
            print(f"Warning: Failed to write credentials.json from env: {e}")
    else:
        print("GOOGLE_CREDENTIALS_JSON not found in env. Checking for local credentials.json...")
        if os.path.exists("credentials.json"):
            print("Local credentials.json found.")
        else:
            print("ERROR: No credentials found! Set GOOGLE_CREDENTIALS_JSON environment variable.")
            raise FileNotFoundError("No google credentials found.")

if __name__ == "__main__":
    write_credentials()
