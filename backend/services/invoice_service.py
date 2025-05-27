from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_LEFT
from reportlab.lib import colors
import os
import json
from datetime import datetime
from flask import current_app, g # Added g
# Assuming database.py is in the same directory or accessible via backend.database
# and provides get_db_connection
from backend.database import get_db_connection


class InvoiceService:
    def __init__(self, app):
        self.app = app
        self.config = app.config

    def _ensure_dir(self, directory_path):
        if not os.path.exists(directory_path):
            os.makedirs(directory_path, exist_ok=True)

    def _get_db(self):
        # Helper to get DB connection, assuming flask g is used
        if 'db_conn' not in g:
            # This case should ideally not happen if db is managed per request
            db_path = current_app.config['DATABASE_PATH']
            g.db_conn = sqlite3.connect(db_path)
            g.db_conn.row_factory = sqlite3.Row
        return g.db_conn

    def create_professional_invoice_pdf(self, invoice_data):
        """
        Generates a PDF invoice for professional clients.
        invoice_data should be a dictionary containing all necessary invoice details.
        Example invoice_data:
        {
            "invoice_id_display": "INV-2023-001", // The display number for the invoice
            "professional_user_id": 1,
            "issue_date": "2023-10-26",
            "due_date": "2023-11-25",
            "client_details": {
                "company_name": "Client Corp",
                "vat_number": "FR123456789",
                "billing_address_lines": ["123 Client Street", "75001 Paris", "France"],
            },
            "items": [
                {"description": "Truffe Noire Extra 1kg", "quantity": 2, "unit_price": 800.00, "total_price": 1600.00},
                {"description": "Huile de Truffe Blanche 250ml", "quantity": 10, "unit_price": 25.00, "total_price": 250.00}
            ],
            "subtotal": 1850.00,
            "vat_rate": 0.20, // Example 20% VAT
            "vat_amount": 370.00,
            "total_amount": 2220.00,
            "notes": "Merci pour votre confiance.",
            "payment_terms": "Paiement à 30 jours."
        }
        """
        invoices_dir = self.config['INVOICES_UPLOAD_DIR']
        self._ensure_dir(invoices_dir)
        
        # Use the display invoice ID for the filename, sanitized
        display_invoice_id_sanitized = invoice_data.get('invoice_id_display', 'temp_id').replace('/', '_').replace('\\', '_')
        invoice_filename = f"facture_pro_{display_invoice_id_sanitized}.pdf"
        invoice_filepath = os.path.join(invoices_dir, invoice_filename)

        doc = SimpleDocTemplate(invoice_filepath, pagesize=A4,
                                rightMargin=30, leftMargin=30,
                                topMargin=30, bottomMargin=30)
        styles = getSampleStyleSheet()
        story = []

        # Styles
        style_h1_invoice_title = ParagraphStyle(name='InvoiceTitle', fontSize=18, alignment=TA_RIGHT, spaceAfter=10, textColor=colors.HexColor("#2c3e50"))
        style_company_name_main = ParagraphStyle(name='CompanyNameMain', fontSize=20, fontName='Helvetica-Bold', alignment=TA_LEFT, spaceAfter=5, textColor=colors.HexColor("#2c3e50"))
        style_h2 = ParagraphStyle(name='Heading2', fontSize=14, spaceBefore=10, spaceAfter=10, textColor=colors.HexColor("#e0ac69"), fontName='Helvetica-Bold')
        style_body = styles['BodyText']
        style_body.fontSize = 9 # Smaller base font for more content
        style_body_right = ParagraphStyle(name='BodyRight', parent=style_body, alignment=TA_RIGHT)
        style_body_bold = ParagraphStyle(name='BodyBold', parent=style_body, fontName='Helvetica-Bold')
        style_footer = ParagraphStyle(name='Footer', fontSize=8, alignment=TA_CENTER, textColor=colors.grey)


        # --- Header Section ---
        # Logo and Company Details on Left, Invoice Title and Dates on Right
        header_data = [[], []] # Left column, Right column

        # Left: Logo and Company Details
        left_col_content = []
        logo_path = self.config.get('LOGO_PATH')
        if logo_path and os.path.exists(logo_path):
            try:
                logo = Image(logo_path, width=120, height=60) # Adjusted size
                logo.hAlign = 'LEFT'
                left_col_content.append(logo)
                left_col_content.append(Spacer(1, 0.1 * 72))
            except Exception as e:
                self.app.logger.error(f"Error loading logo for invoice: {e}")
                left_col_content.append(Paragraph("Maison Trüvra", style_company_name_main))
        else:
            self.app.logger.warning(f"Logo not found at {logo_path} for invoice generation.")
            left_col_content.append(Paragraph("Maison Trüvra", style_company_name_main))
        
        seller_details_text = """
        MAISON TRÜVRA<br/>
        123 Rue de la Truffe<br/>
        75002 Paris, France<br/>
        SIRET: 123 456 789 00010<br/>
        TVA: FR 00 123456789<br/>
        Email: contact@maisontruvra.com<br/>
        Téléphone: +33 1 23 45 67 89
        """ # Replace with actual details
        left_col_content.append(Paragraph(seller_details_text, style_body))
        header_data[0] = left_col_content
        
        # Right: Invoice Title and Dates
        right_col_content = []
        right_col_content.append(Paragraph(f"FACTURE", style_h1_invoice_title))
        right_col_content.append(Paragraph(f"<b>N° :</b> {invoice_data.get('invoice_id_display', 'N/A')}", style_body_right))
        right_col_content.append(Paragraph(f"<b>Date d'émission :</b> {invoice_data.get('issue_date', 'N/A')}", style_body_right))
        if invoice_data.get('due_date'):
            right_col_content.append(Paragraph(f"<b>Date d'échéance :</b> {invoice_data.get('due_date', 'N/A')}", style_body_right))
        header_data[1] = right_col_content

        header_table = Table([header_data], colWidths=[doc.width/2.0 - 10, doc.width/2.0 -10]) # Adjust colWidths
        header_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('LEFTPADDING', (0,0), (0,0), 0),
            ('RIGHTPADDING', (1,0), (1,0), 0),
        ]))
        story.append(header_table)
        story.append(Spacer(1, 0.5 * 72))


        # Client Info
        story.append(Paragraph("<b>Facturé à :</b>", style_body_bold))
        client_info_data = invoice_data.get('client_details', {})
        client_address_lines = client_info_data.get('billing_address_lines', ['N/A'])
        client_address_html = "<br/>".join(client_address_lines)

        client_info_text = f"""
        {client_info_data.get('company_name', 'N/A')}<br/>
        {client_address_html}
        """
        if client_info_data.get('vat_number'):
            client_info_text += f"<br/>N° TVA: {client_info_data.get('vat_number')}"
        if client_info_data.get('siret_number'): # Assuming siret might be useful
             client_info_text += f"<br/>SIRET: {client_info_data.get('siret_number')}"

        story.append(Paragraph(client_info_text, style_body))
        story.append(Spacer(1, 0.3 * 72))


        # Items Table
        story.append(Paragraph("Détail de la commande :", style_h2))
        items_table_data = [
            [Paragraph("Description", style_body_bold), Paragraph("Quantité", style_body_bold), Paragraph("Prix Unitaire HT (€)", style_body_bold), Paragraph("Total HT (€)", style_body_bold)]
        ]
        for item in invoice_data.get('items', []):
            items_table_data.append([
                Paragraph(item.get('description', 'N/A'), style_body),
                Paragraph(str(item.get('quantity', 0)), style_body_right),
                Paragraph(f"{item.get('unit_price', 0.00):.2f}", style_body_right),
                Paragraph(f"{item.get('total_price', 0.00):.2f}", style_body_right)
            ])
        
        items_table = Table(items_table_data, colWidths=[doc.width*0.45, doc.width*0.15, doc.width*0.20, doc.width*0.20]) # Adjusted colWidths
        items_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#4a4a4a")), # Darker header
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('ALIGN', (1,1), (1,-1), 'CENTER'), # Center quantity
            ('ALIGN', (2,1), (-1,-1), 'RIGHT'), # Align numeric columns to right
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0,0), (-1,0), 10),
            ('TOPPADDING', (0,0), (-1,0), 10),
            ('BACKGROUND', (0,1), (-1,-1), colors.HexColor("#f0f0f0")), # Light grey for item rows
            ('GRID', (0,0), (-1,-1), 1, colors.HexColor("#cccccc")),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(items_table)
        story.append(Spacer(1, 0.2 * 72))

        # Totals Section
        totals_table_data = [
            [Paragraph("Sous-total HT:", style_body), Paragraph(f"{invoice_data.get('subtotal', 0.00):.2f} €", style_body_right)],
            [Paragraph(f"TVA ({invoice_data.get('vat_rate', 0)*100:.0f}%) :", style_body), Paragraph(f"{invoice_data.get('vat_amount', 0.00):.2f} €", style_body_right)],
            [Paragraph("Total TTC :", style_body_bold), Paragraph(f"{invoice_data.get('total_amount', 0.00):.2f} €", ParagraphStyle(name='TotalAmount', parent=style_body_bold, alignment=TA_RIGHT, fontSize=12))],
        ]
        
        totals_table = Table(totals_table_data, colWidths=[doc.width*0.78, doc.width*0.22]) # Adjusted
        totals_table.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'RIGHT'),
            ('LEFTPADDING', (0,0), (0,-1), doc.width*0.6), # Push first column text to right
            ('FONTNAME', (0,2), (1,2), 'Helvetica-Bold'),
            ('TEXTCOLOR', (0,2), (1,2), colors.HexColor("#e0ac69")),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('TOPPADDING', (0,0), (-1,-1), 6),
        ]))
        story.append(totals_table)
        story.append(Spacer(1, 0.3 * 72))

        # Payment Terms and Notes
        if invoice_data.get('payment_terms'):
            story.append(Paragraph(f"<b>Conditions de paiement :</b> {invoice_data.get('payment_terms')}", style_body))
            story.append(Spacer(1, 0.1 * 72))
        if invoice_data.get('notes'):
            story.append(Paragraph(f"<b>Notes :</b> {invoice_data.get('notes')}", style_body))
            story.append(Spacer(1, 0.1 * 72))
        
        # Bank Details for Payment (Example)
        bank_details = """
        <b>Coordonnées bancaires pour le paiement :</b><br/>
        Banque: Votre Banque SA<br/>
        IBAN: FR00 XXXX XXXX XXXX XXXX XXXX XXX<br/>
        BIC/SWIFT: BANKFRXX<br/>
        Titulaire du compte: MAISON TRÜVRA
        """ # Replace with actual bank details
        story.append(Paragraph(bank_details, style_body))
        story.append(Spacer(1, 0.5 * 72))


        # Footer (defined using onPage function for bottom placement)
        def footer_canvas(canvas, doc):
            canvas.saveState()
            footer_text = "Maison Trüvra - 123 Rue de la Truffe, 75002 Paris - SIRET: 123 456 789 00010 - TVA: FR00123456789"
            p = Paragraph(footer_text, style_footer)
            w, h = p.wrapOn(canvas, doc.width, doc.bottomMargin)
            p.drawOn(canvas, doc.leftMargin, h) # Adjust height for bottom
            
            page_num_text = f"Page {doc.page}"
            p_page = Paragraph(page_num_text, ParagraphStyle(name='PageNum', parent=style_footer, alignment=TA_RIGHT))
            w_page, h_page = p_page.wrapOn(canvas, doc.width, doc.bottomMargin)
            p_page.drawOn(canvas, doc.leftMargin, h_page) # Align with footer text height

            canvas.restoreState()

        try:
            doc.build(story, onFirstPage=footer_canvas, onLaterPages=footer_canvas)
            self.app.logger.info(f"Generated B2B invoice: {invoice_filepath}")
            return invoice_filepath 
        except Exception as e:
            self.app.logger.error(f"Error building PDF for invoice {invoice_data.get('invoice_id_display')}: {e}")
            return None


    def get_invoice_details_from_db(self, invoice_db_id):
        """
        Fetches invoice details from the database to populate `invoice_data` for PDF generation.
        :param invoice_db_id: The primary key of the invoice in the `professional_invoices` table.
        :return: A dictionary formatted for `create_professional_invoice_pdf` or None if not found.
        """
        db = self._get_db()
        cursor = db.cursor()

        try:
            # Fetch invoice header
            cursor.execute("""
                SELECT pi.*, u.company_name, u.vat_number as client_vat_number, u.siret_number as client_siret_number, u.billing_address
                FROM professional_invoices pi
                JOIN users u ON pi.professional_user_id = u.id
                WHERE pi.id = ?
            """, (invoice_db_id,))
            invoice_header = cursor.fetchone()

            if not invoice_header:
                self.app.logger.error(f"Invoice with DB ID {invoice_db_id} not found.")
                return None

            # Fetch invoice items
            cursor.execute("""
                SELECT * FROM professional_invoice_items WHERE invoice_id = ? ORDER BY id
            """, (invoice_db_id,))
            items_db = cursor.fetchall()
            
            items_formatted = []
            for item_row in items_db:
                items_formatted.append({
                    "description": item_row['description'],
                    "quantity": item_row['quantity'],
                    "unit_price": item_row['unit_price'],
                    "total_price": item_row['total_price']
                })

            # Parse billing address
            billing_address_lines = ["N/A"]
            if invoice_header['billing_address']:
                try:
                    address_obj = json.loads(invoice_header['billing_address'])
                    # Construct address lines based on expected keys in your JSON
                    # Example: street, city, postalCode, country
                    addr_parts = [
                        address_obj.get('street'),
                        f"{address_obj.get('postalCode', '')} {address_obj.get('city', '')}".strip(),
                        address_obj.get('country')
                    ]
                    billing_address_lines = [part for part in addr_parts if part] # Filter out empty parts
                    if not billing_address_lines: billing_address_lines = ["N/A"]
                except json.JSONDecodeError:
                    self.app.logger.warning(f"Could not parse billing_address JSON for invoice {invoice_db_id}: {invoice_header['billing_address']}")
                    billing_address_lines = [invoice_header['billing_address']] # Fallback to raw string if not JSON or parse fails


            # Calculate subtotal, assuming items_db already has total_price per item
            subtotal = sum(item['total_price'] for item in items_formatted)
            
            # VAT amount is stored, but if not, it could be calculated if rate is known
            vat_amount = invoice_header.get('vat_amount', 0.00)
            # If vat_amount is not stored, and you store vat_rate:
            # vat_rate = invoice_header.get('vat_rate', 0.20) # Assuming a default if not stored
            # vat_amount = subtotal * vat_rate

            total_amount = invoice_header.get('total_amount', subtotal + vat_amount)


            invoice_data_for_pdf = {
                "invoice_id_internal_db": invoice_header['id'], # Keep track of DB ID if needed
                "invoice_id_display": invoice_header['invoice_number'], # The number shown on the PDF
                "professional_user_id": invoice_header['professional_user_id'],
                "issue_date": invoice_header['issue_date'], # Ensure this is formatted as YYYY-MM-DD string
                "due_date": invoice_header.get('due_date'), # Ensure this is formatted as YYYY-MM-DD string
                "client_details": {
                    "company_name": invoice_header['company_name'],
                    "vat_number": invoice_header.get('client_vat_number'),
                    "siret_number": invoice_header.get('client_siret_number'),
                    "billing_address_lines": billing_address_lines,
                },
                "items": items_formatted,
                "subtotal": subtotal,
                "vat_rate": (vat_amount / subtotal) if subtotal > 0 else 0, # Calculate effective rate if not stored directly
                "vat_amount": vat_amount,
                "total_amount": total_amount,
                "notes": invoice_header.get('notes'),
                "payment_terms": invoice_header.get('payment_terms', "Paiement à 30 jours net.") # Add default if not in DB
            }
            return invoice_data_for_pdf

        except Exception as e:
            self.app.logger.error(f"Error fetching invoice details from DB for ID {invoice_db_id}: {e}")
            return None
