# generate_professional_invoice.py (Standalone script)
# from reportlab.pdfgen import canvas
# from reportlab.lib.pagesizes import A4
# from reportlab.lib.units import cm

def generate_invoice_pdf(output_filename, client_data, invoice_data, items_data, company_info):
    # client_data = {"company_name": "Pro Client Inc.", "contact_person": "John Doe", "address": "..."}
    # invoice_data = {"number": "FACT2025-001", "date": "2025-05-27", "due_date": "2025-06-26", "total_ht": 500.00, "total_ttc": 600.00, "d# admin/generate_professional_invoice.py
import datetime
import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph, Table, TableStyle, Spacer, Image as ReportLabImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

# --- Configuration ---
# These could be moved to a config file or passed as arguments for more flexibility
COMPANY_LOGO_PATH = "../website/image_6be700.png" # Relative to this script's location
COMPANY_NAME = "Maison Trüvra SARL"
COMPANY_ADDRESS_LINES = [
    "123 Rue de la Truffe",
    "75001 Paris, France"
]
COMPANY_SIRET = "SIRET: 123 456 789 00012"
COMPANY_VAT_NUMBER = "TVA Intracom.: FR 00 123456789"
COMPANY_CONTACT_INFO = "contact@maisontruvra.com | +33 1 23 45 67 89"
INVOICE_FOOTER_TEXT = "Merci de votre confiance. Conditions de paiement : 30 jours net."
BANK_DETAILS = "Banque: XYZ | IBAN: FR76 XXXX XXXX XXXX XXXX XXXX XXX | BIC: XYZAFRPP"

# --- Styles ---
styles = getSampleStyleSheet()
style_normal = styles['Normal']
style_normal.fontName = 'Helvetica'
style_normal.fontSize = 10
style_normal.leading = 12

style_bold = ParagraphStyle('Bold', parent=style_normal, fontName='Helvetica-Bold')
style_h1_title = ParagraphStyle('H1Title', parent=style_bold, fontSize=18, alignment=TA_RIGHT, spaceAfter=0.5*cm) # Renamed
style_h2_section = ParagraphStyle('H2Section', parent=style_bold, fontSize=14, spaceBefore=0.5*cm, spaceAfter=0.3*cm) # Renamed
style_right_align = ParagraphStyle('RightAlign', parent=style_normal, alignment=TA_RIGHT) # Renamed
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


def generate_invoice_pdf(output_filename, client_data, invoice_data, items_data):
    c = NumberedCanvas(output_filename, pagesize=A4)
    width, height = A4

    margin_x = 2 * cm
    margin_y = 2 * cm
    content_width = width - 2 * margin_x
    current_y = height - margin_y

    # --- Header ---
    if os.path.exists(COMPANY_LOGO_PATH):
        try:
            logo = ReportLabImage(COMPANY_LOGO_PATH, width=4*cm, height=2*cm)
            logo.hAlign = 'LEFT'
            logo.drawOn(c, margin_x, current_y - 2*cm)
            current_y -= 0.5*cm # Adjust if logo pushes content down
        except Exception as e:
            print(f"Warning: Could not load logo {COMPANY_LOGO_PATH}: {e}")
    
    c.setFont("Helvetica-Bold", 16)
    c.drawRightString(width - margin_x, current_y - 0.5*cm, "FACTURE")
    c.setFont("Helvetica", 10)
    c.drawRightString(width - margin_x, current_y - 1*cm, f"Facture N°: {invoice_data['number']}")
    try:
        invoice_date_obj = datetime.datetime.strptime(invoice_data['date'], '%Y-%m-%d')
        due_date_obj = datetime.datetime.strptime(invoice_data['due_date'], '%Y-%m-%d')
        c.drawRightString(width - margin_x, current_y - 1.5*cm, f"Date: {invoice_date_obj.strftime('%d/%m/%Y')}")
        c.drawRightString(width - margin_x, current_y - 2*cm, f"Échéance: {due_date_obj.strftime('%d/%m/%Y')}")
    except ValueError:
        c.drawRightString(width - margin_x, current_y - 1.5*cm, f"Date: {invoice_data['date']}")
        c.drawRightString(width - margin_x, current_y - 2*cm, f"Échéance: {invoice_data['due_date']}")


    current_y -= 3*cm

    # --- Company Info (Left) & Client Info (Right) ---
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
    for line in client_data.get('address_lines', []):
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
            Paragraph(item['description'], style_table_cell),
            Paragraph(str(item['quantity']), style_table_cell_right),
            Paragraph(f"{item['unit_price_ht']:.2f}", style_table_cell_right),
            Paragraph(f"{item['total_ht']:.2f}", style_table_cell_right)
        ])

    item_table = Table(table_data, colWidths=[content_width*0.45, content_width*0.1, content_width*0.22, content_width*0.23])
    item_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#7D6A4F")), # brand-earth-brown
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 9),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('TOPPADDING', (0,0), (-1,0), 6),
        ('BACKGROUND', (0,1), (-1,-1), colors.HexColor("#F5EEDE")), # brand-cream
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
        ('FONTSIZE', (0,1), (-1,-1), 9),
    ]))
    
    table_width, table_height = item_table.wrapOn(c, content_width, current_y)
    if current_y - table_height < margin_y + 6*cm: # Check space for table + totals + footer
        c.showPage()
        current_y = height - margin_y - 1*cm 
    
    item_table.drawOn(c, margin_x, current_y - table_height)
    current_y -= (table_height + 1*cm)

    # --- Totals Section ---
    totals_x_label = width - margin_x - 6*cm # Adjusted for longer labels
    totals_x_value = width - margin_x - 0.5*cm # Align values to the right edge of content_width
    
    c.setFont("Helvetica", 10)
    c.drawString(totals_x_label, current_y, "Total HT:")
    c.drawRightString(totals_x_value, current_y, f"{invoice_data['total_ht']:.2f} €")
    current_y -= 0.6*cm

    if invoice_data.get('discount_amount_ht', 0) > 0:
        c.drawString(totals_x_label, current_y, f"Remise ({invoice_data.get('discount_percent', 0):.0f}%):")
        c.drawRightString(totals_x_value, current_y, f"-{invoice_data['discount_amount_ht']:.2f} €")
        current_y -= 0.6*cm
        
        subtotal_after_discount = invoice_data['total_ht_after_discount'] # Use calculated value
        c.setFont("Helvetica-Bold", 10)
        c.drawString(totals_x_label, current_y, "Sous-Total HT (après remise):")
        c.drawRightString(totals_x_value, current_y, f"{subtotal_after_discount:.2f} €")
        c.setFont("Helvetica", 10)
        current_y -= 0.6*cm

    c.drawString(totals_x_label, current_y, f"TVA ({invoice_data['vat_rate_percent']:.0f}%):")
    c.drawRightString(totals_x_value, current_y, f"{invoice_data['vat_amount']:.2f} €")
    current_y -= 0.6*cm

    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(colors.HexColor("#7D6A4F"))
    c.drawString(totals_x_label, current_y, "Total TTC:")
    c.drawRightString(totals_x_value, current_y, f"{invoice_data['total_ttc']:.2f} €")
    c.setFillColor(colors.black) # Reset color

    current_y -= 2*cm

    # --- Footer Notes & Bank Details ---
    if current_y < margin_y + 3*cm: # Check if enough space for footer
        c.showPage()
        current_y = height - margin_y - 1*cm

    c.setFont("Helvetica", 9)
    c.drawString(margin_x, current_y, INVOICE_FOOTER_TEXT)
    current_y -= 0.6*cm
    c.drawString(margin_x, current_y, BANK_DETAILS)

    c.save() # This calls the NumberedCanvas save method
    print(f"Facture PDF générée : {output_filename}")


def calculate_invoice_totals(items_data, discount_percent_str="0", vat_rate_percent_str="20"):
    total_ht_before_discount = sum(item['quantity'] * item['unit_price_ht'] for item in items_data)
    
    try: discount_percent = float(discount_percent_str)
    except ValueError: discount_percent = 0.0
        
    try: vat_rate_percent = float(vat_rate_percent_str)
    except ValueError: vat_rate_percent = 20.0

    discount_amount_ht = (total_ht_before_discount * discount_percent) / 100.0
    total_ht_after_discount = total_ht_before_discount - discount_amount_ht
    vat_amount = (total_ht_after_discount * vat_rate_percent) / 100.0
    total_ttc = total_ht_after_discount + vat_amount

    return {
        "total_ht_before_discount": total_ht_before_discount, # This is the sum of item totals before discount
        "discount_percent": discount_percent,
        "discount_amount_ht": discount_amount_ht,
        "total_ht_after_discount": total_ht_after_discount, # This is the subtotal after discount
        "vat_rate_percent": vat_rate_percent,
        "vat_amount": vat_amount,
        "total_ttc": total_ttc
    }

if __name__ == '__main__':
    print("--- Générateur de Facture Professionnelle Maison Trüvra ---")
    
    output_dir = "generated_invoices_b2b" # Store B2B invoices in a specific folder relative to script
    os.makedirs(output_dir, exist_ok=True)
    
    # --- Admin Inputs ---
    client_company = input("Nom de l'entreprise cliente: ")
    client_contact = input("Nom du contact client (optionnel): ")
    client_address1 = input("Adresse client (ligne 1 - ex: 10 Rue des Peupliers): ")
    client_address2 = input("Adresse client (ligne 2 - ex: 75010 Paris): ")
    client_address3 = input("Adresse client (ligne 3 - ex: France - optionnel): ")
    client_vat = input("N° TVA client (optionnel): ")

    invoice_number_input = input(f"Numéro de facture (ex: FACT{datetime.date.today().year}-001): ") or f"FACT{datetime.date.today().year}-{str(datetime.datetime.now().timestamp()).split('.')[0][-4:]}"
    invoice_date_input = input(f"Date de facture (AAAA-MM-JJ, défaut: aujourd'hui): ") or datetime.date.today().strftime('%Y-%m-%d')
    
    try:
        parsed_invoice_date = datetime.datetime.strptime(invoice_date_input, '%Y-%m-%d')
    except ValueError:
        print("Format de date de facture invalide. Utilisation de la date d'aujourd'hui.")
        parsed_invoice_date = datetime.date.today()
        invoice_date_input = parsed_invoice_date.strftime('%Y-%m-%d')

    due_date_input = input(f"Date d'échéance (AAAA-MM-JJ, défaut +30j): ") or \
                     (parsed_invoice_date + datetime.timedelta(days=30)).strftime('%Y-%m-%d')

    items = []
    print("\n--- Articles de la Facture ---")
    while True:
        item_desc = input("Description de l'article (ou 'fin' pour terminer): ")
        if item_desc.lower() == 'fin':
            if not items:
                print("Aucun article ajouté. Veuillez ajouter au moins un article.")
                continue
            break
        item_qty_str = input(f"Quantité pour '{item_desc}': ")
        item_unit_price_ht_str = input(f"Prix unitaire HT (€) pour '{item_desc}': ")
        try:
            item_qty = int(item_qty_str)
            item_unit_price_ht = float(item_unit_price_ht_str)
            if item_qty <= 0 or item_unit_price_ht < 0:
                print("La quantité doit être positive et le prix unitaire non-négatif.")
                continue
            items.append({
                "description": item_desc,
                "quantity": item_qty,
                "unit_price_ht": item_unit_price_ht,
                "total_ht": item_qty * item_unit_price_ht # Line item total HT
            })
        except ValueError:
            print("Quantité ou prix invalide. Veuillez entrer des nombres.")
            continue
            
    discount_str = input("Remise globale en % (ex: 5 pour 5%, 0 si aucune): ") or "0"
    vat_rate_str = input("Taux de TVA en % (ex: 20 pour 20%, ou 5.5, 10): ") or "20"

    # --- Prepare Data for PDF ---
    client_data_input = {
        "company_name": client_company,
        "contact_person": client_contact,
        "address_lines": [line for line in [client_address1, client_address2, client_address3] if line.strip()],
        "vat_number": client_vat
    }

    calculated_totals = calculate_invoice_totals(items, discount_str, vat_rate_str)

    invoice_data_input = {
        "number": invoice_number_input,
        "date": invoice_date_input,
        "due_date": due_date_input,
        "total_ht": calculated_totals['total_ht_before_discount'], # This is sum of line items before discount
        "discount_percent": calculated_totals['discount_percent'],
        "discount_amount_ht": calculated_totals['discount_amount_ht'],
        "total_ht_after_discount": calculated_totals['total_ht_after_discount'], #This is the subtotal displayed
        "vat_rate_percent": calculated_totals['vat_rate_percent'],
        "vat_amount": calculated_totals['vat_amount'],
        "total_ttc": calculated_totals['total_ttc']
    }
    
    pdf_filename = os.path.join(output_dir, f"Facture_{invoice_number_input.replace('/', '-')}.pdf")
    
    generate_invoice_pdf(pdf_filename, client_data_input, invoice_data_input, items)
    
    print(f"\nFacture PDF générée avec succès : {os.path.abspath(pdf_filename)}")
    print("Vous pouvez maintenant téléverser ce PDF via le panneau d'administration Maison Trüvra.")
