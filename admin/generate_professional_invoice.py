# generate_professional_invoice.py
import datetime
import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph, Table, TableStyle, Spacer, Image as ReportLabImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

# --- Default Company Info (can be overridden by passing `company_info` dictionary) ---
DEFAULT_COMPANY_INFO = {
    "logo_path": "../website/image_6be700.png", # Path relative to this script's location
    "name": "Maison Trüvra SARL",
    "address_lines": [
        "123 Rue de la Truffe",
        "75001 Paris, France"
    ],
    "siret": "SIRET: 123 456 789 00012",
    "vat_number": "TVA Intracom.: FR 00 123456789",
    "contact_info": "contact@maisontruvra.com | +33 1 23 45 67 89",
    "footer_text": "Merci de votre confiance. Conditions de paiement : 30 jours net.",
    "bank_details": "Banque: XYZ | IBAN: FR76 XXXX XXXX XXXX XXXX XXXX XXX | BIC: XYZAFRPP"
}

# --- Styles ---
styles = getSampleStyleSheet() # This should be fine as is.
style_normal = styles['Normal']
style_normal.fontName = 'Helvetica'
style_normal.fontSize = 10
style_normal.leading = 12

style_bold = ParagraphStyle('Bold', parent=style_normal, fontName='Helvetica-Bold')
style_h1_title = ParagraphStyle('H1Title', parent=style_bold, fontSize=18, alignment=TA_RIGHT, spaceAfter=0.5*cm)
style_h2_section = ParagraphStyle('H2Section', parent=style_bold, fontSize=14, spaceBefore=0.5*cm, spaceAfter=0.3*cm)
style_right_align = ParagraphStyle('RightAlign', parent=style_normal, alignment=TA_RIGHT)
style_table_header = ParagraphStyle('TableHeader', parent=style_bold, alignment=TA_CENTER, textColor=colors.whitesmoke)
style_table_cell = ParagraphStyle('TableCell', parent=style_normal)
style_table_cell_right = ParagraphStyle('TableCellRight', parent=style_normal, alignment=TA_RIGHT)


class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            super().showPage()
        super().save()

    def draw_page_number(self, page_count):
        self.setFont("Helvetica", 8)
        self.setFillColorRGB(0.5, 0.5, 0.5) # Grey
        page_num_text = f"Page {self._pageNumber} sur {page_count}"
        self.drawRightString(A4[0] - 2*cm, 1.5*cm, page_num_text)


def generate_invoice_pdf(output_filename, client_data, invoice_data, items_data, company_info_override=None):
    """
    Generates a PDF invoice.
    :param output_filename: Path to save the PDF.
    :param client_data: Dictionary with client details.
    :param invoice_data: Dictionary with invoice metadata (number, dates, totals).
    :param items_data: List of dictionaries, each representing a line item.
    :param company_info_override: Optional dictionary to override default company info.
    """
    c = NumberedCanvas(output_filename, pagesize=A4)
    width, height = A4

    # Merge provided company_info with defaults
    company_info = DEFAULT_COMPANY_INFO.copy()
    if company_info_override:
        company_info.update(company_info_override)

    margin_x = 2 * cm
    margin_y = 2 * cm
    content_width = width - 2 * margin_x
    current_y = height - margin_y

    # --- Header ---
    logo_path_to_use = company_info.get("logo_path", DEFAULT_COMPANY_INFO["logo_path"])
    # Ensure the logo path is correct. If it's relative to this script, it's fine.
    # If it's an absolute path from config, that also works.
    # If it's relative to the Flask app's static folder, ensure it's accessible.
    if os.path.exists(logo_path_to_use):
        try:
            # Adjust logo size as needed
            logo_width, logo_height = 4*cm, 2*cm 
            # Check if image is too large for these dimensions, scale if necessary
            img_reader = ReportLabImage(logo_path_to_use) # Read image to get its dimensions
            img_w, img_h = img_reader.drawWidth, img_reader.drawHeight
            aspect = img_h / float(img_w)
            
            final_logo_width = logo_width
            final_logo_height = logo_width * aspect
            if final_logo_height > logo_height: # too tall
                final_logo_height = logo_height
                final_logo_width = final_logo_height / aspect

            logo = ReportLabImage(logo_path_to_use, width=final_logo_width, height=final_logo_height)
            logo.hAlign = 'LEFT'
            logo.drawOn(c, margin_x, current_y - final_logo_height) # Adjust y based on actual height
            # current_y -= 0.5*cm # Adjust if logo pushes content down significantly
        except Exception as e:
            print(f"Warning: Could not load or draw logo {logo_path_to_use}: {e}")
    
    c.setFont("Helvetica-Bold", 16)
    c.drawRightString(width - margin_x, current_y - 0.5*cm, "FACTURE")
    c.setFont("Helvetica", 10)
    c.drawRightString(width - margin_x, current_y - 1*cm, f"Facture N°: {invoice_data['number']}")
    try:
        # Ensure dates are in string format if they come from datetime objects from DB
        invoice_date_str = invoice_data['date'] if isinstance(invoice_data['date'], str) else invoice_data['date'].strftime('%Y-%m-%d')
        due_date_str = invoice_data['due_date'] if isinstance(invoice_data['due_date'], str) else invoice_data['due_date'].strftime('%Y-%m-%d')

        invoice_date_obj = datetime.datetime.strptime(invoice_date_str, '%Y-%m-%d')
        due_date_obj = datetime.datetime.strptime(due_date_str, '%Y-%m-%d')
        c.drawRightString(width - margin_x, current_y - 1.5*cm, f"Date: {invoice_date_obj.strftime('%d/%m/%Y')}")
        c.drawRightString(width - margin_x, current_y - 2*cm, f"Échéance: {due_date_obj.strftime('%d/%m/%Y')}")
    except ValueError: # Fallback if dates are not in expected string format
        c.drawRightString(width - margin_x, current_y - 1.5*cm, f"Date: {invoice_data['date']}")
        c.drawRightString(width - margin_x, current_y - 2*cm, f"Échéance: {invoice_data['due_date']}")

    current_y -= 3*cm

    # --- Company Info (Left) & Client Info (Right) ---
    c.setFont("Helvetica-Bold", 10)
    c.drawString(margin_x, current_y, company_info.get("name", DEFAULT_COMPANY_INFO["name"]))
    current_y_company = current_y - 0.5*cm
    c.setFont("Helvetica", 9)
    for line in company_info.get("address_lines", DEFAULT_COMPANY_INFO["address_lines"]):
        c.drawString(margin_x, current_y_company, line)
        current_y_company -= 0.4*cm
    c.drawString(margin_x, current_y_company, company_info.get("siret", DEFAULT_COMPANY_INFO["siret"]))
    current_y_company -= 0.4*cm
    c.drawString(margin_x, current_y_company, company_info.get("vat_number", DEFAULT_COMPANY_INFO["vat_number"]))
    current_y_company -= 0.4*cm
    c.drawString(margin_x, current_y_company, company_info.get("contact_info", DEFAULT_COMPANY_INFO["contact_info"]))

    client_x_start = width / 2 + 0.5 * cm
    c.setFont("Helvetica-Bold", 10)
    c.drawString(client_x_start, current_y, "Facturé à :")
    current_y_client = current_y - 0.5*cm
    c.setFont("Helvetica", 9)
    c.drawString(client_x_start, current_y_client, client_data.get('company_name', 'N/A'))
    current_y_client -= 0.4*cm
    if client_data.get('contact_person'):
        c.drawString(client_x_start, current_y_client, client_data['contact_person'])
        current_y_client -= 0.4*cm
    for line in client_data.get('address_lines', []): # Expecting a list of strings
        c.drawString(client_x_start, current_y_client, line)
        current_y_client -= 0.4*cm
    if client_data.get('vat_number'):
        c.drawString(client_x_start, current_y_client, f"N° TVA: {client_data['vat_number']}")

    current_y = min(current_y_company, current_y_client) - 1.5*cm

    # --- Line Items Table ---
    table_header_data = [
        Paragraph("Description", style_table_header),
        Paragraph("Qté", style_table_header),
        Paragraph("Prix Unit. HT (€)", style_table_header),
        Paragraph("Total HT (€)", style_table_header)
    ]
    table_data = [table_header_data]

    for item in items_data:
        table_data.append([
            Paragraph(str(item.get('description', 'N/A')), style_table_cell), # Ensure description is a string
            Paragraph(str(item.get('quantity', 0)), style_table_cell_right),
            Paragraph(f"{item.get('unit_price_ht', 0.0):.2f}", style_table_cell_right),
            Paragraph(f"{item.get('total_ht', 0.0):.2f}", style_table_cell_right)
        ])

    item_table = Table(table_data, colWidths=[content_width*0.45, content_width*0.1, content_width*0.22, content_width*0.23])
    item_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#7D6A4F")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 9),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('TOPPADDING', (0,0), (-1,0), 6),
        ('BACKGROUND', (0,1), (-1,-1), colors.HexColor("#F5EEDE")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
        ('FONTSIZE', (0,1), (-1,-1), 9),
    ]))
    
    table_width_actual, table_height_actual = item_table.wrapOn(c, content_width, current_y)
    if current_y - table_height_actual < margin_y + 7*cm: # Increased space for totals + footer
        c.showPage()
        current_y = height - margin_y - 1*cm 
    
    item_table.drawOn(c, margin_x, current_y - table_height_actual)
    current_y -= (table_height_actual + 1*cm)

    # --- Totals Section ---
    totals_x_label = width - margin_x - 7*cm # Adjusted for potentially longer labels like "Sous-Total HT (après remise):"
    totals_x_value = width - margin_x - 0.5*cm 
    
    c.setFont("Helvetica", 10)
    # invoice_data['total_ht'] is total_ht_before_discount
    c.drawString(totals_x_label, current_y, "Total HT (avant remise):")
    c.drawRightString(totals_x_value, current_y, f"{invoice_data.get('total_ht', 0.0):.2f} €")
    current_y -= 0.6*cm

    if invoice_data.get('discount_amount_ht', 0) > 0:
        c.drawString(totals_x_label, current_y, f"Remise ({invoice_data.get('discount_percent', 0):.0f}%):")
        c.drawRightString(totals_x_value, current_y, f"-{invoice_data['discount_amount_ht']:.2f} €")
        current_y -= 0.6*cm
        
        subtotal_after_discount = invoice_data.get('total_ht_after_discount', invoice_data.get('total_ht', 0.0))
        c.setFont("Helvetica-Bold", 10)
        c.drawString(totals_x_label, current_y, "Sous-Total HT (après remise):")
        c.drawRightString(totals_x_value, current_y, f"{subtotal_after_discount:.2f} €")
        c.setFont("Helvetica", 10) # Reset to normal for next lines
        current_y -= 0.6*cm
    
    c.drawString(totals_x_label, current_y, f"TVA ({invoice_data.get('vat_rate_percent', 0):.0f}%):")
    c.drawRightString(totals_x_value, current_y, f"{invoice_data.get('vat_amount', 0.0):.2f} €")
    current_y -= 0.6*cm

    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(colors.HexColor("#7D6A4F"))
    c.drawString(totals_x_label, current_y, "Total TTC:")
    c.drawRightString(totals_x_value, current_y, f"{invoice_data.get('total_ttc', 0.0):.2f} €")
    c.setFillColor(colors.black)

    current_y -= 2*cm

    # --- Footer Notes & Bank Details ---
    if current_y < margin_y + 3*cm:
        c.showPage()
        current_y = height - margin_y - 1*cm

    c.setFont("Helvetica", 9)
    c.drawString(margin_x, current_y, company_info.get("footer_text", DEFAULT_COMPANY_INFO["footer_text"]))
    current_y -= 0.6*cm
    c.drawString(margin_x, current_y, company_info.get("bank_details", DEFAULT_COMPANY_INFO["bank_details"]))

    c.save()
    print(f"Facture PDF générée : {output_filename}")


def calculate_invoice_totals(items_data, discount_percent_str="0", vat_rate_percent_str="20"):
    """
    Calculates various totals for an invoice.
    :param items_data: List of item dicts, each with 'quantity' and 'unit_price_ht'.
    :param discount_percent_str: Overall discount percentage as a string.
    :param vat_rate_percent_str: VAT rate percentage as a string.
    :return: Dictionary with calculated totals.
    """
    total_ht_before_discount = sum(
        float(item.get('quantity', 0)) * float(item.get('unit_price_ht', 0)) for item in items_data
    )
    
    try: discount_percent = float(discount_percent_str)
    except (ValueError, TypeError): discount_percent = 0.0
        
    try: vat_rate_percent = float(vat_rate_percent_str)
    except (ValueError, TypeError): vat_rate_percent = 20.0 # Default VAT if invalid

    discount_amount_ht = (total_ht_before_discount * discount_percent) / 100.0
    total_ht_after_discount = total_ht_before_discount - discount_amount_ht
    vat_amount = (total_ht_after_discount * vat_rate_percent) / 100.0
    total_ttc = total_ht_after_discount + vat_amount

    return {
        "total_ht_before_discount": total_ht_before_discount,
        "discount_percent": discount_percent,
        "discount_amount_ht": discount_amount_ht,
        "total_ht_after_discount": total_ht_after_discount,
        "vat_rate_percent": vat_rate_percent,
        "vat_amount": vat_amount,
        "total_ttc": total_ttc
    }

if __name__ == '__main__':
    print("--- Générateur de Facture Professionnelle Maison Trüvra (Test Local) ---")
    
    # Create a directory for test outputs if it doesn't exist
    output_dir_test = "generated_invoices_b2b_test" 
    os.makedirs(output_dir_test, exist_ok=True)
    
    # --- Example Data for Testing ---
    client_data_test = {
        "company_name": "Restaurant Le Gourmet Test",
        "contact_person": "Chef Antoine Test",
        "address_lines": ["10 Rue de la Gastronomie", "75002 Paris", "France"],
        "vat_number": "FRXX123456789"
    }

    invoice_number_test = f"TESTFACT{datetime.date.today().year}-{str(datetime.datetime.now().microsecond)[:4]}"
    invoice_date_test = datetime.date.today().strftime('%Y-%m-%d')
    due_date_test = (datetime.date.today() + datetime.timedelta(days=30)).strftime('%Y-%m-%d')

    items_test = [
        {"description": "Truffe Noire Extra (Tuber Melanosporum) - 50g", "quantity": 2, "unit_price_ht": 75.00, "total_ht": 150.00},
        {"description": "Huile d'olive à la truffe noire - 250ml", "quantity": 5, "unit_price_ht": 18.50, "total_ht": 92.50},
        {"description": "Sel à la truffe d'été - 100g", "quantity": 3, "unit_price_ht": 12.00, "total_ht": 36.00}
    ]
    
    # Test with default company info
    calculated_totals_test = calculate_invoice_totals(items_test, "10", "20") # 10% discount, 20% VAT
    invoice_data_test = {
        "number": invoice_number_test,
        "date": invoice_date_test,
        "due_date": due_date_test,
        **calculated_totals_test # Merge calculated totals
    }
    
    pdf_filename_test = os.path.join(output_dir_test, f"Facture_{invoice_number_test}.pdf")
    generate_invoice_pdf(pdf_filename_test, client_data_test, invoice_data_test, items_test)
    print(f"\nFacture de test générée : {os.path.abspath(pdf_filename_test)}")

    # Test with overridden company info
    custom_company_info = {
        "name": "Maison Trüvra (Édition Spéciale)",
        "footer_text": "Paiement à réception. Merci !",
        "logo_path": "" # Test without logo or with a different one
    }
    invoice_number_test_custom = f"TESTFACT-CUSTOM-{datetime.date.today().year}-{str(datetime.datetime.now().microsecond)[:4]}"
    calculated_totals_test_custom = calculate_invoice_totals(items_test, "0", "5.5") # No discount, 5.5% VAT
    invoice_data_test_custom = {
        "number": invoice_number_test_custom,
        "date": invoice_date_test,
        "due_date": due_date_test,
        **calculated_totals_test_custom
    }
    pdf_filename_test_custom = os.path.join(output_dir_test, f"Facture_{invoice_number_test_custom}.pdf")
    generate_invoice_pdf(pdf_filename_test_custom, client_data_test, invoice_data_test_custom, items_test, company_info_override=custom_company_info)
    print(f"Facture de test (custom info) générée : {os.path.abspath(pdf_filename_test_custom)}")

