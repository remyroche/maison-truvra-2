# backend/services/invoice_service.py
import datetime
import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph, Table, TableStyle, Spacer, Image as ReportLabImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from flask import current_app

# --- Configuration (can be adapted to pull from current_app.config if needed) ---
COMPANY_LOGO_PATH_RELATIVE_TO_SCRIPT_DIR = "../../website/image_6be700.png" 
COMPANY_NAME = "Maison Trüvra SARL"
COMPANY_ADDRESS_LINES = ["123 Rue de la Truffe", "75001 Paris, France"]
COMPANY_SIRET = "SIRET: 123 456 789 00012"
COMPANY_VAT_NUMBER = "TVA Intracom.: FR 00 123456789"
COMPANY_CONTACT_INFO = "contact@maisontruvra.com | +33 1 23 45 67 89"
INVOICE_FOOTER_TEXT = "Merci de votre confiance. Conditions de paiement : 30 jours net."
BANK_DETAILS = "Banque: XYZ | IBAN: FR76 XXXX XXXX XXXX XXXX XXXX XXX | BIC: XYZAFRPP"

styles = getSampleStyleSheet()
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
        self.setFillColorRGB(0.5, 0.5, 0.5)
        page_num_text = f"Page {self._pageNumber} sur {page_count}"
        self.drawRightString(A4[0] - 2*cm, 1.5*cm, page_num_text)

def generate_invoice_pdf_to_file(output_filepath, client_data, invoice_data, items_data):
    c = NumberedCanvas(output_filepath, pagesize=A4)
    width, height = A4
    margin_x = 2 * cm
    margin_y = 2 * cm
    content_width = width - 2 * margin_x
    current_y = height - margin_y

    # Resolve absolute path for the logo
    script_dir = os.path.dirname(os.path.abspath(__file__)) # directory of invoice_service.py
    abs_logo_path = os.path.abspath(os.path.join(script_dir, COMPANY_LOGO_PATH_RELATIVE_TO_SCRIPT_DIR))


    if os.path.exists(abs_logo_path):
        try:
            logo = ReportLabImage(abs_logo_path, width=4*cm, height=2*cm)
            logo.hAlign = 'LEFT'
            logo.drawOn(c, margin_x, current_y - 2*cm)
            current_y -= 0.5*cm
        except Exception as e:
            current_app.logger.warning(f"Could not load logo {abs_logo_path}: {e}")
    else:
        current_app.logger.warning(f"Logo not found at resolved path: {abs_logo_path}")

    c.setFont("Helvetica-Bold", 16)
    c.drawRightString(width - margin_x, current_y - 0.5*cm, "FACTURE")
    c.setFont("Helvetica", 10)
    c.drawRightString(width - margin_x, current_y - 1*cm, f"Facture N°: {invoice_data['number']}")
    try:
        invoice_date_obj = datetime.datetime.strptime(invoice_data['date'], '%Y-%m-%d').date()
        due_date_obj = datetime.datetime.strptime(invoice_data['due_date'], '%Y-%m-%d').date()
        c.drawRightString(width - margin_x, current_y - 1.5*cm, f"Date: {invoice_date_obj.strftime('%d/%m/%Y')}")
        c.drawRightString(width - margin_x, current_y - 2*cm, f"Échéance: {due_date_obj.strftime('%d/%m/%Y')}")
    except ValueError:
        c.drawRightString(width - margin_x, current_y - 1.5*cm, f"Date: {invoice_data['date']}")
        c.drawRightString(width - margin_x, current_y - 2*cm, f"Échéance: {invoice_data['due_date']}")
    current_y -= 3*cm

    c.setFont("Helvetica-Bold", 10)
    c.drawString(margin_x, current_y, COMPANY_NAME)
    current_y_company = current_y - 0.5*cm
    c.setFont("Helvetica", 9)
    for line in COMPANY_ADDRESS_LINES:
        c.drawString(margin_x, current_y_company, line)
        current_y_company -= 0.4*cm
    c.drawString(margin_x, current_y_company, COMPANY_SIRET)
    current_y_company -= 0.4*cm
    c.drawString(margin_x, current_y_company, COMPANY_VAT_NUMBER)
    current_y_company -= 0.4*cm
    c.drawString(margin_x, current_y_company, COMPANY_CONTACT_INFO)

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
    for line in client_data.get('address_lines', []): # Assuming address_lines is a list
        c.drawString(client_x_start, current_y_client, line)
        current_y_client -= 0.4*cm
    if client_data.get('vat_number'):
        c.drawString(client_x_start, current_y_client, f"N° TVA: {client_data['vat_number']}")
    current_y = min(current_y_company, current_y_client) - 1.5*cm

    table_header_data = [
        Paragraph("Description", style_table_header), Paragraph("Qté", style_table_header),
        Paragraph("Prix Unit. HT (€)", style_table_header), Paragraph("Total HT (€)", style_table_header)
    ]
    table_data = [table_header_data]
    for item in items_data:
        table_data.append([
            Paragraph(item['description'], style_table_cell),
            Paragraph(str(item['quantity']), style_table_cell_right),
            Paragraph(f"{item['unit_price_ht']:.2f}", style_table_cell_right),
            Paragraph(f"{item['total_ht']:.2f}", style_table_cell_right)
        ])
    item_table = Table(table_data, colWidths=[content_width*0.45, content_width*0.1, content_width*0.22, content_width*0.23])
    item_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#7D6A4F")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke), ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 9), ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('TOPPADDING', (0,0), (-1,0), 6), ('BACKGROUND', (0,1), (-1,-1), colors.HexColor("#F5EEDE")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey), ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5), ('FONTSIZE', (0,1), (-1,-1), 9),
    ]))
    table_width, table_height = item_table.wrapOn(c, content_width, current_y)
    if current_y - table_height < margin_y + 6*cm:
        c.showPage()
        current_y = height - margin_y - 1*cm
    item_table.drawOn(c, margin_x, current_y - table_height)
    current_y -= (table_height + 1*cm)

    totals_x_label = width - margin_x - 6*cm
    totals_x_value = width - margin_x - 0.5*cm
    c.setFont("Helvetica", 10)
    c.drawString(totals_x_label, current_y, "Total HT:")
    c.drawRightString(totals_x_value, current_y, f"{invoice_data['total_ht_before_discount']:.2f} €")
    current_y -= 0.6*cm
    if invoice_data.get('discount_amount_ht', 0) > 0:
        c.drawString(totals_x_label, current_y, f"Remise ({invoice_data.get('discount_percent', 0):.0f}%):")
        c.drawRightString(totals_x_value, current_y, f"-{invoice_data['discount_amount_ht']:.2f} €")
        current_y -= 0.6*cm
        c.setFont("Helvetica-Bold", 10)
        c.drawString(totals_x_label, current_y, "Sous-Total HT (après remise):")
        c.drawRightString(totals_x_value, current_y, f"{invoice_data['total_ht_after_discount']:.2f} €")
        c.setFont("Helvetica", 10)
        current_y -= 0.6*cm
    c.drawString(totals_x_label, current_y, f"TVA ({invoice_data['vat_rate_percent']:.0f}%):")
    c.drawRightString(totals_x_value, current_y, f"{invoice_data['vat_amount']:.2f} €")
    current_y -= 0.6*cm
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(colors.HexColor("#7D6A4F"))
    c.drawString(totals_x_label, current_y, "Total TTC:")
    c.drawRightString(totals_x_value, current_y, f"{invoice_data['total_ttc']:.2f} €")
    c.setFillColor(colors.black)
    current_y -= 2*cm

    if current_y < margin_y + 3*cm:
        c.showPage()
        current_y = height - margin_y - 1*cm
    c.setFont("Helvetica", 9)
    c.drawString(margin_x, current_y, INVOICE_FOOTER_TEXT)
    current_y -= 0.6*cm
    c.drawString(margin_x, current_y, BANK_DETAILS)
    c.save()
    current_app.logger.info(f"Facture PDF générée et sauvegardée : {output_filepath}")

def calculate_invoice_totals_service(items_data, discount_percent_str="0", vat_rate_percent_str="20"):
    # items_data should be a list of dicts: [{"description": "...", "quantity": X, "unit_price_ht": Y}, ...]
    total_ht_before_discount = sum(float(item['quantity']) * float(item['unit_price_ht']) for item in items_data)
    try: discount_percent = float(discount_percent_str)
    except (ValueError, TypeError): discount_percent = 0.0
    try: vat_rate_percent = float(vat_rate_percent_str)
    except (ValueError, TypeError): vat_rate_percent = 20.0

    discount_amount_ht = (total_ht_before_discount * discount_percent) / 100.0
    total_ht_after_discount = total_ht_before_discount - discount_amount_ht
    vat_amount = (total_ht_after_discount * vat_rate_percent) / 100.0
    total_ttc = total_ht_after_discount + vat_amount
    return {
        "total_ht_before_discount": round(total_ht_before_discount, 2),
        "discount_percent": discount_percent,
        "discount_amount_ht": round(discount_amount_ht, 2),
        "total_ht_after_discount": round(total_ht_after_discount, 2),
        "vat_rate_percent": vat_rate_percent,
        "vat_amount": round(vat_amount, 2),
        "total_ttc": round(total_ttc, 2)
    }
