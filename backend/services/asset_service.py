from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_LEFT
from reportlab.lib import colors
import os
from datetime import datetime
from flask import current_app # For accessing app.config

class InvoiceService:
    def __init__(self, app):
        self.app = app
        self.config = app.config

    def _ensure_dir(self, directory_path):
        if not os.path.exists(directory_path):
            os.makedirs(directory_path, exist_ok=True)

    def create_professional_invoice_pdf(self, invoice_data):
        """
        Generates a PDF invoice for professional clients.
        invoice_data should be a dictionary containing all necessary invoice details.
        Example invoice_data:
        {
            "invoice_id": "INV-2023-001",
            "professional_user_id": 1,
            "issue_date": "2023-10-26",
            "due_date": "2023-11-25",
            "client_details": {
                "company_name": "Client Corp",
                "vat_number": "FR123456789",
                "billing_address": "123 Client Street, 75001 Paris, France",
                "shipping_address": "123 Client Street, 75001 Paris, France" (if different)
            },
            "items": [
                {"description": "Truffe Noire Extra 1kg", "quantity": 2, "unit_price": 800.00, "total_price": 1600.00},
                {"description": "Huile de Truffe Blanche 250ml", "quantity": 10, "unit_price": 25.00, "total_price": 250.00}
            ],
            "subtotal": 1850.00,
            "vat_rate": 0.20, # Example 20% VAT
            "vat_amount": 370.00,
            "total_amount": 2220.00,
            "notes": "Merci pour votre confiance.",
            "payment_terms": "Paiement à 30 jours."
        }
        """
        invoices_dir = self.config['INVOICES_UPLOAD_DIR']
        self._ensure_dir(invoices_dir)
        
        invoice_filename = f"facture_pro_{invoice_data.get('invoice_id', 'temp_id').replace('/', '_')}.pdf"
        invoice_filepath = os.path.join(invoices_dir, invoice_filename)

        doc = SimpleDocTemplate(invoice_filepath, pagesize=A4,
                                rightMargin=30, leftMargin=30,
                                topMargin=30, bottomMargin=30)
        styles = getSampleStyleSheet()
        story = []

        # Styles
        style_h1 = ParagraphStyle(name='Heading1', fontSize=18, alignment=TA_CENTER, spaceAfter=20, textColor=colors.HexColor("#2c3e50"))
        style_h2 = ParagraphStyle(name='Heading2', fontSize=14, spaceBefore=10, spaceAfter=10, textColor=colors.HexColor("#e0ac69"))
        style_body = styles['BodyText']
        style_body_right = ParagraphStyle(name='BodyRight', parent=style_body, alignment=TA_RIGHT)
        style_body_bold = ParagraphStyle(name='BodyBold', parent=style_body, fontName='Helvetica-Bold')

        # Logo (ensure LOGO_PATH is correct in config)
        logo_path = self.config.get('LOGO_PATH')
        if logo_path and os.path.exists(logo_path):
            try:
                logo = Image(logo_path, width=150, height=75) # Adjust size as needed
                logo.hAlign = 'LEFT'
                story.append(logo)
                story.append(Spacer(1, 0.25 * 72)) # 0.25 inch spacer
            except Exception as e:
                self.app.logger.error(f"Error loading logo for invoice: {e}")
        else:
            self.app.logger.warning(f"Logo not found at {logo_path} for invoice generation.")
            story.append(Paragraph("Maison Trüvra", style_h1)) # Fallback text logo

        # Invoice Title
        story.append(Paragraph(f"FACTURE N° : {invoice_data.get('invoice_id', 'N/A')}", style_h1))
        story.append(Spacer(1, 0.5 * 72))

        # Seller and Client Info Table
        seller_info = f"""
        <b>MAISON TRÜVRA</b><br/>
        Votre Adresse Complète<br/>
        Ville, Code Postal<br/>
        SIRET: Votre SIRET<br/>
        TVA: Votre Numéro de TVA<br/>
        Email: contact@maisontruvra.com
        """
        client_info_data = invoice_data.get('client_details', {})
        client_info = f"""
        <b>Facturé à :</b><br/>
        {client_info_data.get('company_name', 'N/A')}<br/>
        {client_info_data.get('billing_address', 'N/A').replace(os.linesep, '<br/>')}<br/>
        """
        if client_info_data.get('vat_number'):
            client_info += f"N° TVA: {client_info_data.get('vat_number')}<br/>"


        info_table_data = [
            [Paragraph(seller_info, style_body), Paragraph(client_info, style_body)],
        ]
        info_table = Table(info_table_data, colWidths=[doc.width/2.0]*2)
        info_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 0.3 * 72))

        # Dates
        story.append(Paragraph(f"Date d'émission : {invoice_data.get('issue_date', 'N/A')}", style_body))
        story.append(Paragraph(f"Date d'échéance : {invoice_data.get('due_date', 'N/A')}", style_body))
        story.append(Spacer(1, 0.3 * 72))

        # Items Table
        story.append(Paragraph("Détail de la commande :", style_h2))
        items_data = [
            [Paragraph("Description", style_body_bold), Paragraph("Quantité", style_body_bold), Paragraph("Prix Unitaire HT", style_body_bold), Paragraph("Total HT", style_body_bold)]
        ]
        for item in invoice_data.get('items', []):
            items_data.append([
                Paragraph(item.get('description', 'N/A'), style_body),
                Paragraph(str(item.get('quantity', 0)), style_body_right),
                Paragraph(f"{item.get('unit_price', 0.00):.2f} €", style_body_right),
                Paragraph(f"{item.get('total_price', 0.00):.2f} €", style_body_right)
            ])
        
        items_table = Table(items_data, colWidths=[doc.width*0.4, doc.width*0.15, doc.width*0.25, doc.width*0.20])
        items_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#e0ac69")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('ALIGN', (1,1), (-1,-1), 'RIGHT'), # Align numeric columns to right
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0,0), (-1,0), 12),
            ('BACKGROUND', (0,1), (-1,-1), colors.beige),
            ('GRID', (0,0), (-1,-1), 1, colors.black)
        ]))
        story.append(items_table)
        story.append(Spacer(1, 0.2 * 72))

        # Totals Section
        totals_data = [
            ["Sous-total HT:", f"{invoice_data.get('subtotal', 0.00):.2f} €"],
            [f"TVA ({invoice_data.get('vat_rate', 0)*100:.0f}%) :", f"{invoice_data.get('vat_amount', 0.00):.2f} €"],
            [Paragraph("Total TTC :", style_body_bold), Paragraph(f"{invoice_data.get('total_amount', 0.00):.2f} €", style_body_bold)],
        ]
        
        totals_table = Table(totals_data, colWidths=[doc.width*0.75, doc.width*0.25])
        totals_table.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'RIGHT'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey), # Optional grid for totals
            ('FONTNAME', (0,2), (1,2), 'Helvetica-Bold'), # Bold for Total TTC line
        ]))
        story.append(totals_table)
        story.append(Spacer(1, 0.3 * 72))

        # Payment Terms and Notes
        if invoice_data.get('payment_terms'):
            story.append(Paragraph(f"Conditions de paiement : {invoice_data.get('payment_terms')}", style_body))
        if invoice_data.get('notes'):
            story.append(Paragraph(f"Notes : {invoice_data.get('notes')}", style_body))
        story.append(Spacer(1, 0.5 * 72))

        # Footer
        # (ReportLab adds page numbers automatically if needed, or you can customize)
        # For a fixed footer, you might need to use onFirstPage/onLaterPages in SimpleDocTemplate
        story.append(Paragraph("Merci de votre confiance.", style_body_bold))
        story.append(Paragraph("Maison Trüvra - contact@maisontruvra.com", ParagraphStyle(name='Footer', fontSize=9, alignment=TA_CENTER)))


        try:
            doc.build(story)
            self.app.logger.info(f"Generated B2B invoice: {invoice_filepath}")
            
            # Return the web-accessible path if INVOICES_UPLOAD_DIR is under static,
            # otherwise, this path is server-side only.
            # Assuming INVOICES_UPLOAD_DIR is NOT directly web-accessible for security.
            # You'd typically have a separate route to serve these securely.
            # For now, returning the filesystem path.
            # If you want a web path, adjust config and this return value.
            # e.g., if INVOICES_UPLOAD_DIR was 'website/static/invoices/professional'
            # static_base_invoice_path = os.path.join('static', 'invoices', 'professional')
            # invoice_web_path = os.path.join(static_base_invoice_path, invoice_filename).replace("\\","/")
            # return invoice_web_path
            
            return invoice_filepath # Returning server filesystem path
        except Exception as e:
            self.app.logger.error(f"Error building PDF for invoice {invoice_data.get('invoice_id')}: {e}")
            return None


    def get_invoice_details_from_db(self, invoice_id_db): # Assuming invoice_id_db is the DB primary key
        """
        Placeholder: Fetches invoice details from the database to populate `invoice_data`.
        You need to implement this based on your database schema.
        """
        # Example:
        # conn = get_db_connection() # Assuming you have a get_db_connection function
        # cur = conn.cursor()
        # cur.execute("SELECT * FROM professional_invoices WHERE id = ?", (invoice_id_db,))
        # invoice_header = cur.fetchone()
        # if not invoice_header:
        #     return None
        #
        # cur.execute("SELECT * FROM users WHERE id = ?", (invoice_header['professional_user_id'],))
        # client = cur.fetchone()
        #
        # cur.execute("SELECT * FROM professional_invoice_items WHERE invoice_id = ?", (invoice_id_db,))
        # items_db = cur.fetchall()
        # conn.close()
        #
        # items_formatted = [{"description": i['description'], "quantity": i['quantity'], ...} for i in items_db]
        # client_details_formatted = {"company_name": client['company_name'], ...}
        #
        # return {
        #     "invoice_id": invoice_header['invoice_number'],
        #     "professional_user_id": invoice_header['professional_user_id'],
        #     "issue_date": invoice_header['issue_date'],
        #     ...
        #     "client_details": client_details_formatted,
        #     "items": items_formatted,
        #     ...
        # }
        self.app.logger.warning("get_invoice_details_from_db is a placeholder and needs implementation.")
        return None
