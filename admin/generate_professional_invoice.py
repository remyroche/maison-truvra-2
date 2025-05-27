# generate_professional_invoice.py (Standalone script)
# from reportlab.pdfgen import canvas
# from reportlab.lib.pagesizes import A4
# from reportlab.lib.units import cm

def generate_invoice_pdf(output_filename, client_data, invoice_data, items_data, company_info):
    # client_data = {"company_name": "Pro Client Inc.", "contact_person": "John Doe", "address": "..."}
    # invoice_data = {"number": "FACT2025-001", "date": "2025-05-27", "due_date": "2025-06-26", "total_ht": 500.00, "total_ttc": 600.00, "discount_percent": 5}
    # items_data = [{"name": "Truffe Noire Extra 50g", "quantity": 2, "unit_price_ht": 100.00, "total_ht": 200.00}, ...]
    # company_info = {"name": "Maison Trüvra", "address": "...", "siret": "...", "vat_number": "..."}

    # c = canvas.Canvas(output_filename, pagesize=A4)
    # width, height = A4

    # --- Header (Your company logo, address) ---
    # c.setFont("Helvetica-Bold", 16)
    # c.drawString(3*cm, height - 3*cm, company_info["name"])
    # ...

    # --- Client Info ---
    # c.setFont("Helvetica", 12)
    # c.drawString(3*cm, height - 5*cm, client_data["company_name"])
    # ...

    # --- Invoice Meta (Number, Date, Due Date) ---
    # ...

    # --- Line Items Table ---
    # y_position = height - 10*cm
    # for item in items_data:
    #     c.drawString(3*cm, y_position, item["name"])
    #     c.drawString(10*cm, y_position, str(item["quantity"]))
    #     # ... and so on for unit price, total price
    #     y_position -= 0.7*cm

    # --- Totals (HT, Discount, VAT, TTC) ---
    # ...

    # --- Footer (Payment terms, bank details) ---
    # ...

    # c.save()
    print(f"Invoice {output_filename} would be generated here.")

if __name__ == '__main__':
    # This is where an admin would typically input data or load from a CSV/DB
    mock_client = {"company_name": "Restaurant Le Gourmet", "contact_person": "Chef Cuisine", "address": "1 Rue de la Paix, Paris"}
    mock_invoice = {"number": "FACT2025-B2B-001", "date": "2025-05-27", "total_ht": 250.00, "total_ttc": 300.00, "discount_percent": 0}
    mock_items = [
        {"name": "Truffe Noire Melanosporum - Qualité Extra (100g)", "quantity": 1, "unit_price_ht": 200.00, "total_ht": 200.00},
        {"name": "Huile d'olive à la truffe noire 250ml", "quantity": 2, "unit_price_ht": 25.00, "total_ht": 50.00}
    ]
    mock_company = {"name": "Maison Trüvra SARL", "address": "Quelque Part, France", "siret": "12345678900012", "vat_number": "FR00123456789"}

    # Admin would run:
    # generate_invoice_pdf(f"{mock_invoice['number']}.pdf", mock_client, mock_invoice, mock_items, mock_company)
    print(f"Conceptual generation for invoice {mock_invoice['number']}.pdf")
    print("Install a PDF library like 'reportlab' or 'fpdf2' and implement the drawing logic.")
