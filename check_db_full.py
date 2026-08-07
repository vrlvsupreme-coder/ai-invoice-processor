import sqlite3

conn = sqlite3.connect("invoices.db")
cursor = conn.cursor()

print("--- INVOICES ---")
cursor.execute("SELECT id, invoice_no, vendor, verification_status, file_name, invoice_amount FROM invoices")
rows = cursor.fetchall()
for row in rows:
    print(row)

print("\n--- LINE ITEMS ---")
cursor.execute("SELECT invoice_id, sr_no, description, qty, rate, invoice_amount FROM line_items")
rows = cursor.fetchall()
for row in rows:
    print(row)

conn.close()
