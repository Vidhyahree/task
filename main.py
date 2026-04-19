from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
import mysql.connector
from models import Customer

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="1358",
        database="manage_invoices"
    )
class Item(BaseModel):
    product_name: str
    quantity: int
    price: float

class Invoice(BaseModel):
    customer_id: int
    items: List[Item]
    gst: float

customers = [ ]

@app.post("/customer")
def add_customer(customer: Customer):
    conn = get_db()
    cursor = conn.cursor()

    query = "INSERT INTO customers (id, name, email, phone) VALUES (%s, %s, %s, %s)"
    values = (customer.id, customer.name, customer.email, customer.phone)

    cursor.execute(query, values)
    conn.commit()

    cursor.close()
    conn.close()

    return {"message": "Customer added successfully"}

@app.post("/create-invoice/")
def create_invoice(data: dict):
    conn = get_db()
    cursor = conn.cursor()

    try:
        total = 0
        for item in data["items"]:
            total += item["quantity"] * item["price"]

        gst_amount = total * data["gst"] / 100
        final_total = total + gst_amount

        status = data.get("status", "draft")

        cursor.execute(
            "INSERT INTO invoices (customer_id, total, gst, status) VALUES (%s, %s, %s, %s)",
            (data["customer_id"], final_total, gst_amount, status)
        )

        invoice_id = cursor.lastrowid

        for item in data["items"]:
            item_total = item["quantity"] * item["price"]

            cursor.execute(
                "INSERT INTO invoice_items (invoice_id, product_name, quantity, price, total) VALUES (%s, %s, %s, %s, %s)",
                (invoice_id, item["product_name"], item["quantity"], item["price"], item_total)
            )

        conn.commit()
        return {"message": "Invoice created successfully"}

    except Exception as e:
        conn.rollback()
        return {"error": str(e)}

    finally:
        cursor.close()
        conn.close()

@app.get("/invoices/")
def get_invoices():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM invoices")
    data = cursor.fetchall()

    cursor.close()
    conn.close()

    return data

@app.get("/invoice/{invoice_id}")
def get_invoice(invoice_id: int):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM invoices WHERE id=%s", (invoice_id,))
    invoice = cursor.fetchone()

    cursor.execute("SELECT * FROM invoice_items WHERE invoice_id=%s", (invoice_id,))
    items = cursor.fetchall()

    cursor.close()
    conn.close()

    return {"invoice": invoice, "items": items}

@app.put("/invoice/{invoice_id}/status")
def update_status(invoice_id: int, status: str):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE invoices SET status=%s WHERE id=%s",
        (status, invoice_id)
    )

    conn.commit()
    cursor.close()
    conn.close()

    return {"message": "Status updated"}

@app.get("/invoice/{invoice_id}/pdf")
def generate_pdf(invoice_id: int):

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM invoices WHERE id=%s", (invoice_id,))
    invoice = cursor.fetchone()

    cursor.execute("SELECT * FROM invoice_items WHERE invoice_id=%s", (invoice_id,))
    items = cursor.fetchall()

    file_name = f"invoice_{invoice_id}.pdf"

    doc = SimpleDocTemplate(file_name)
    styles = getSampleStyleSheet()

    content = []
    content.append(Paragraph(f"Invoice ID: {invoice_id}", styles["Normal"]))
    content.append(Paragraph(f"Total: {invoice['total']}", styles["Normal"]))
    content.append(Paragraph(f"Status: {invoice['status']}", styles["Normal"]))
    content.append(Paragraph("Items:", styles["Normal"]))

    for item in items:
        content.append(
            Paragraph(
                f"{item['product_name']} - Qty: {item['quantity']} - Price: {item['price']}",
                styles["Normal"]
            )
        )

    doc.build(content)

    cursor.close()
    conn.close()

    return FileResponse(
        path=file_name,
        media_type='application/pdf',
        filename=file_name
    )
