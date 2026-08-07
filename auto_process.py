import os
import asyncio
import logging
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from process_invoices import process_single_invoice
from app.services.database import DatabaseService
from app.services.agent import AIVerificationAgent
from app.services.sheets import GoogleSheetsService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

class InvoiceHandler(FileSystemEventHandler):
    def __init__(self, loop):
        self.loop = loop
        self.db_service = DatabaseService()
        self.agent = AIVerificationAgent(db_service=self.db_service)
        self.sheets_service = GoogleSheetsService()
        self.semaphore = asyncio.Semaphore(1)
        self.directory_path = os.path.join(os.path.dirname(__file__), "invoices")

    def on_created(self, event):
        if event.is_directory:
            return
        
        filename = os.path.basename(event.src_path)
        # Filter for invoice types
        if filename.lower().endswith(('.pdf', '.jpg', '.jpeg', '.png')):
            logging.info(f"New file detected: {filename}. Triggering automation...")
            asyncio.run_coroutine_threadsafe(
                self.process_file_with_delay(filename), 
                self.loop
            )

    async def process_file_with_delay(self, filename):
        """Small delay to ensure the file is fully written/closed by the OS before processing."""
        await asyncio.sleep(2)
        await process_single_invoice(
            filename, 
            self.directory_path, 
            self.db_service, 
            self.agent, 
            self.sheets_service, 
            self.semaphore
        )

def run_watcher():
    path = os.path.join(os.path.dirname(__file__), "invoices")
    if not os.path.exists(path):
        os.makedirs(path)
        
    loop = asyncio.new_event_loop()
    
    # Start the event loop in a separate thread if needed, 
    # but since this is a standalone script, we'll run it here.
    from threading import Thread
    def start_loop(loop):
        asyncio.set_event_loop(loop)
        loop.run_forever()

    t = Thread(target=start_loop, args=(loop,))
    t.start()

    event_handler = InvoiceHandler(loop)
    observer = Observer()
    observer.schedule(event_handler, path, recursive=False)
    
    logging.info(f"🚀 Invoice Watcher started! Monitoring folder: {path}")
    logging.info("Press Ctrl+C to stop.")
    
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        loop.call_soon_threadsafe(loop.stop)
    observer.join()
    t.join()

if __name__ == "__main__":
    run_watcher()
