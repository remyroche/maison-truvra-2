# backend/services/invoice_service.py
import os
import datetime
from flask import current_app
import sqlite3
# Assuming your generate_professional_invoice.py is in project root or accessible
# from ....admin.generate_professional_invoice import generate_invoice_pdf # Adjust path
# For now, we'll mock this functionality or assume it's refactored here.
from ..database import get_db_connection # Assuming in backend/database.py
from ..utils import format_date_french # Assuming in backend/utils.py

# Default company info if not overridden (should match generate_professional_invoice.py)
DEFAULT_COMPANY_INFO = {
    "name": "MAISON TRÜVRA",
    "address_line1": "123 Rue de la Truffe",
    "address_line2": "75001 Paris, France",
    "phone": "+33 1 23 45 67 89",
    "email": "contact@maisontruvra.com",
    "website": "www.maisontruvra.com",
    "siret": "123 456 789 00010",
    "vat_number": "FR00123456789", # TVA Intracommunautaire
    "bank_details": "IBAN: FR76 XXXX XXXX XXXX XXXX XXXX XXX BIC: XXXX",
    "logo_path": os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "assets", "logo_truvra_email.png") # Adjust path to your logo
}


class InvoiceService:
    def __init__(self):
        self.invoice_pdf_path = current_app.config['INVOICE_PDF_PATH']
        os.makedirs(self.invoice_pdf_path, exist_ok=True)

    def _get_professional_user_details(self, user_id, conn):
        cursor = conn.cursor()
        cursor.execute("""
            SELECT u.company_name, u.email, u.phone_number, u.vat_number,
                   a_bill.address_line1 as billing_address_line1, 
                   a_bill.address_line2 as billing_address_line2,
                   a_bill.city as billing_city, 
                   a_bill.postal_code as billing_postal_code, 
                   a_bill.country as billing_country
            FROM users u
            LEFT JOIN addresses a_bill ON u.id = a_bill.user_id AND a_bill.is_default_billing = 1
            WHERE u.id = ? AND u.role = 'professional'
        """, (user_id,))
        user_data = cursor.fetchone()
        if not user_data:
            raise ValueError(f"Professional user with ID {user_id} not found or no default billing address.")
        return dict(user_data)

    def create_and_save_professional_invoice(self, invoice_data: dict, company_info_override: dict = None) -> (str, str):
        """
        Creates a professional invoice PDF, saves it, and records it in the database.
        invoice_data: {
            "professional_user_id": int,
            "invoice_id_display": str, # e.g., "FACT2023-001"
            "issue_date": "YYYY-MM-DD",
            "due_date": "YYYY-MM-DD",
            "items": [{"description": str, "quantity": float, "unit_price": float, "total_price": float, "vat_rate": float (e.g. 0.20)}],
            "subtotal_ht": float,
            "total_vat_amount": float,
            "total_amount_ttc": float,
            "notes": str (optional)
        }
        company_info_override: dict to override parts of DEFAULT_COMPANY_INFO
        Returns: (path_to_pdf_file, invoice_number_from_db)
        """
        conn = get_db_connection()
        try:
            professional_user_id = invoice_data['professional_user_id']
            client_details = self._get_professional_user_details(professional_user_id, conn)

            # Prepare data for PDF generation (similar to generate_professional_invoice.py)
            pdf_generation_data = {
                "invoice_id": invoice_data['invoice_id_display'],
                "issue_date": format_date_french(invoice_data['issue_date']),
                "due_date": format_date_french(invoice_data['due_date']),
                "client_name": client_details.get('company_name', 'N/A'),
                "client_address_line1": client_details.get('billing_address_line1', ''),
                "client_address_line2": client_details.get('billing_address_line2', ''),
                "client_city_zip": f"{client_details.get('billing_postal_code','')} {client_details.get('billing_city','')}",
                "client_country": client_details.get('billing_country',''),
                "client_vat_number": client_details.get('vat_number', 'N/A'),
                "items": [], # Needs to be formatted as list of lists/tuples for reportlab table
                "subtotal_ht": f"{invoice_data['subtotal_ht']:.2f} €",
                "total_vat": f"{invoice_data['total_vat_amount']:.2f} €", # Assuming one VAT rate for simplicity of display
                "total_ttc": f"{invoice_data['total_amount_ttc']:.2f} €",
                "notes": invoice_data.get('notes', '')
            }
            
            # Format items for ReportLab table: [Description, Quantité, P.U. HT, %TVA, Montant HT]
            for item in invoice_data['items']:
                pdf_generation_data["items"].append([
                    item['description'],
                    str(item['quantity']),
                    f"{item['unit_price']:.2f} €",
                    f"{item['vat_rate']*100:.0f}%", # e.g. 20%
                    f"{item['total_price']:.2f} €" # This is usually HT for the line
                ])
            
            seller_info = DEFAULT_COMPANY_INFO.copy()
            if company_info_override:
                seller_info.update(company_info_override)

            # --- Actual PDF Generation ---
            # This is where you'd call your adapted generate_invoice_pdf function
            # from ....admin.generate_professional_invoice import generate_invoice_pdf
            # For now, creating a dummy PDF file.
            
            pdf_filename = f"{invoice_data['invoice_id_display'].replace('/', '_')}_{professional_user_id}.pdf"
            pdf_filepath = os.path.join(self.invoice_pdf_path, pdf_filename)

            # Placeholder: generate_invoice_pdf(pdf_filepath, pdf_generation_data, seller_info)
            try:
                # Simulate PDF generation by creating a dummy file
                from reportlab.pdfgen import canvas
                from reportlab.lib.pagesizes import A4
                from reportlab.lib.units import cm

                c = canvas.Canvas(pdf_filepath, pagesize=A4)
                c.drawString(3*cm, 25*cm, f"FACTURE: {pdf_generation_data['invoice_id']}")
                c.drawString(3*cm, 24*cm, f"Client: {pdf_generation_data['client_name']}")
                c.drawString(3*cm, 23*cm, f"Date: {pdf_generation_data['issue_date']}")
                c.drawString(3*cm, 22*cm, f"Total TTC: {pdf_generation_data['total_ttc']}")
                # ... add more details from pdf_generation_data and seller_info
                c.save()
                current_app.logger.info(f"Dummy Professional Invoice PDF generated: {pdf_filepath}")
            except Exception as pdf_e:
                current_app.logger.error(f"Actual PDF generation failed: {pdf_e}")
                raise # Re-raise to indicate failure in service

            # Save invoice record to database
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO professional_invoices 
                (invoice_number, professional_user_id, issue_date, due_date, subtotal_ht, 
                 total_vat_amount, total_amount_ttc, status, pdf_path, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (invoice_data['invoice_id_display'], professional_user_id, invoice_data['issue_date'], 
                  invoice_data['due_date'], invoice_data['subtotal_ht'], invoice_data['total_vat_amount'],
                  invoice_data['total_amount_ttc'], 'draft', pdf_filepath, invoice_data.get('notes')))
            conn.commit()
            db_invoice_id = cursor.lastrowid # The ID from the professional_invoices table
            
            current_app.logger.info(f"Professional invoice {invoice_data['invoice_id_display']} saved to DB (id: {db_invoice_id}) and PDF at {pdf_filepath}")
            return pdf_filepath, invoice_data['invoice_id_display']

        except sqlite3.Error as db_e:
            conn.rollback()
            current_app.logger.error(f"Database error in InvoiceService: {db_e}")
            raise Exception(f"Database operation failed: {db_e}") # Generic exception
        except ValueError as val_e: # Catch specific validation errors
            conn.rollback()
            raise val_e # Re-raise to be caught by API route
        except Exception as e:
            conn.rollback()
            current_app.logger.error(f"Unexpected error in InvoiceService: {e}")
            raise Exception(f"An unexpected error occurred in invoice generation: {e}")
        finally:
            if conn:
                conn.close()
