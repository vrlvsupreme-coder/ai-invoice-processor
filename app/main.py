import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router as api_router
from app.core.config import settings

from fastapi.staticfiles import StaticFiles
import os

# Bootstrap Google credentials from env variable (needed for cloud/HF Spaces deployment)
from cloud_startup import write_credentials
write_credentials()

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="AI-Based Multi Invoice Upload, Extraction, Verification & Google Sheets Automation",
    version="1.0.0"
)

# CORS middleware to allow frontend connections
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)

# Serve static files for the frontend
static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)

app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

@app.get("/health", tags=["Health"])
async def root():
    return {
        "message": "AI-Based Multi Invoice Processing API is running.",
        "docs_url": "/docs"
    }

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
