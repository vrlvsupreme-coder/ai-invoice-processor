# ── Base image ──────────────────────────────────────────────────────────────
FROM python:3.11-slim

# ── System dependencies (for pypdfium2, Pillow) ─────────────────────────────
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libgl1-mesa-glx \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# ── Working directory ────────────────────────────────────────────────────────
WORKDIR /code

# ── Install Python dependencies ──────────────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Copy project files ───────────────────────────────────────────────────────
COPY . .

# ── Create the invoices folder (for auto-processing) ────────────────────────
RUN mkdir -p invoices

# ── Expose FastAPI port (Hugging Face Spaces uses port 7860) ─────────────────
EXPOSE 7860

# ── Start server ─────────────────────────────────────────────────────────────
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
