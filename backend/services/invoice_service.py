# backend/services/invoice_service.py
import os
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepInFrame
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_LEFT
from reportlab.lib.colors import HexColor, black, gray, lightgrey
from reportlab.lib.units import cm
from flask import current_app # For accessing config

# --- Default Company Details (Can be overridden by config) ---
DEFAULT_COMPANY_NAME = "Maison Trüvra SàRL"
DEFAULT_COMPANY_ADDRESS_LINES = [
    "123 Rue de la Truffe",
    "75001 Paris, France"
]
DEFAULT_COMPANY_VAT = "FR123456789"
DEFAULT_COMPANY_EMAIL = "contact@maisontruvra.com"
DEFAULT_COMPANY_PHONE = "+33 1 23 45 67 89"
DEFAULT_CURRENCY_SYMBOL = "€"


def get_company_details_from_config():
    """Fetches company details from Flask app config or uses defaults."""
    return {
        'name': current_app.config.get('INVOICE_COMPANY_NAME', DEFAULT_COMPANY_NAME),
        'address_lines': current_app.config.get('INVOICE_COMPANY_ADDRESS_LINES', DEFAULT_COMPANY_ADDRESS_LINES),
        'vat': current_app.config.get('INVOICE_COMPANY_VAT', DEFAULT_COMPANY_VAT),
        'email': current_app.config.get('INVOICE_COMPANY_EMAIL', DEFAULT_COMPANY_EMAIL),
        'phone': current_app.config.get('INVOICE_COMPANY_PHONE', DEFAULT_COMPANY_PHONE),
        'logo_path': current_app.config.get('INVOICE_COMPANY_LOGO_PATH'), # This should be an absolute path or resolvable
        'font_regular': current_app.config.get('INVOICE_FONT_REGULAR_PATH'),
        'font_bold': current_app.config.get('INVOICE_FONT_BOLD_PATH'),
        'currency_symbol': current_app.config.get('CURRENCY_SYMBOL', DEFAULT_CURRENCY_SYMBOL)
    }

def calculate_invoice_totals_service(items, tax_rate_percentage=20.0):
    """
    Calculates subtotal, tax amount, and grand total for invoice items.
    Assumes items is a list of dicts, each with 'quantity' and 'unit_price'.
    'unit_price' is assumed to be tax-exclusive.
    """
    subtotal = 0
    for item in items:
        try:
            quantity = float(item.get('quantity', 0))
            unit_price = float(item.get('unit_price', 0))
            subtotal += quantity * unit_price
        except (ValueError, TypeError) as e:
            current_app.logger.warning(f"Could not parse quantity/price for item {item}: {e}")
            continue # Skip item if data is invalid

    tax_amount = (subtotal * tax_rate_percentage) / 100
    grand_total = subtotal + tax_amount
    
    return {
        'subtotal': round(subtotal, 2),
        'tax_rate_percentage': tax_rate_percentage,
        'tax_amount': round(tax_amount, 2),
        'grand_total': round(grand_total, 2)
    }


def generate_invoice_pdf_to_file(pdf_file_path, invoice_data):
    """
    Generates a PDF invoice and saves it to the given file path.
    invoice_data should be a dictionary containing all necessary invoice details.
    """
    company_details = get_company_details_from_config()
    currency_symbol = company_details['currency_symbol']

    doc = SimpleDocTemplate(pdf_file_path, pagesize=A4,
                            rightMargin=2*cm, leftMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    
    styles = getSampleStyleSheet()
    # Register custom fonts if paths are provided
    if company_details.get('font_regular') and os.path.exists(company_details['font_regular']) and \
       company_details.get('font_bold') and os.path.exists(company_details['font_bold']):
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        try:
            pdfmetrics.registerFont(TTFont('DejaVuSans', company_details['font_regular']))
            pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', company_details['font_bold']))
            styles.add(ParagraphStyle(name='Normal_Custom', fontName='DejaVuSans', fontSize=10, leading=12))
            styles.add(ParagraphStyle(name='Heading1_Custom', fontName='DejaVuSans-Bold', fontSize=18, alignment=TA_RIGHT, spaceAfter=6))
            styles.add(ParagraphStyle(name='Heading2_Custom', fontName='DejaVuSans-Bold', fontSize=12, spaceBefore=10, spaceAfter=4))
            styles.add(ParagraphStyle(name='SmallText_Custom', fontName='DejaVuSans', fontSize=8, leading=10))
            styles.add(ParagraphStyle(name='RightAlign_Custom', fontName='DejaVuSans', fontSize=10, alignment=TA_RIGHT))
            normal_style = styles['Normal_Custom']
            h1_style = styles['Heading1_Custom']
            h2_style = styles['Heading2_Custom']
            small_style = styles['SmallText_Custom']
            right_align_style = styles['RightAlign_Custom']
        except Exception as e:
            current_app.logger.error(f"Error registering custom fonts for PDF: {e}. Falling back to default fonts.")
            normal_style = styles['Normal']
            h1_style = styles['h1']
            h2_style = styles['h2']
            small_style = ParagraphStyle(name='SmallText', parent=styles['Normal'], fontSize=8, leading=10) # Ensure small_style exists
            right_align_style = ParagraphStyle(name='RightAlign', parent=styles['Normal'], alignment=TA_RIGHT)
    else:
        current_app.logger.warning("Custom invoice fonts not found or not configured. Using default fonts.")
        normal_style = styles['Normal']
        h1_style = styles['h1'] # ReportLab's h1 is often too large, might need custom
        h1_style.alignment = TA_RIGHT
        h1_style.fontSize = 18
        h2_style = styles['h2']
        small_style = ParagraphStyle(name='SmallText', parent=styles['Normal'], fontSize=8, leading=10)
        right_align_style = ParagraphStyle(name='RightAlign', parent=styles['Normal'], alignment=TA_RIGHT)


    story = []

    # Header: Logo and Company Details on one side, Invoice Title on the other
    header_data = []
    logo_and_company_col = []
    if company_details.get('logo_path') and os.path.exists(company_details['logo_path']):
        try:
            logo = Image(company_details['logo_path'], width=4*cm, height=2*cm) # Adjust size as needed
            logo.hAlign = 'LEFT'
            logo_and_company_col.append(logo)
            logo_and_company_col.append(Spacer(1, 0.2*cm))
        except Exception as e:
            current_app.logger.error(f"Error loading invoice logo: {e}")
            logo_and_company_col.append(Paragraph(company_details['name'], h2_style))


    logo_and_company_col.append(Paragraph(company_details['name'], normal_style))
    for line in company_details['address_lines']:
        logo_and_company_col.append(Paragraph(line, normal_style))
    if company_details['vat']: logo_and_company_col.append(Paragraph(f"VAT: {company_details['vat']}", normal_style))
    if company_details['email']: logo_and_company_col.append(Paragraph(f"Email: {company_details['email']}", normal_style))
    if company_details['phone']: logo_and_company_col.append(Paragraph(f"Phone: {company_details['phone']}", normal_style))

    invoice_title_col = [Paragraph("INVOICE", h1_style)]
    if invoice_data.get('invoice_number'):
        invoice_title_col.append(Paragraph(f"Invoice #: {invoice_data['invoice_number']}", right_align_style))
    if invoice_data.get('issue_date'):
        invoice_title_col.append(Paragraph(f"Date: {invoice_data['issue_date']}", right_align_style))
    if invoice_data.get('due_date'):
        invoice_title_col.append(Paragraph(f"Due Date: {invoice_data['due_date']}", right_align_style))


    header_table = Table([[KeepInFrame(10*cm, 20*cm, logo_and_company_col), KeepInFrame(8*cm, 20*cm, invoice_title_col)]], colWidths=[10*cm, 6*cm]) # Adjust colWidths
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 1*cm))

    # Client Details
    story.append(Paragraph("Bill To:", h2_style))
    if invoice_data.get('client_name'): story.append(Paragraph(invoice_data['client_name'], normal_style))
    if invoice_data.get('client_address'):
        # Assuming client_address can be a multiline string or list of strings
        if isinstance(invoice_data['client_address'], list):
            for line in invoice_data['client_address']: story.append(Paragraph(line, normal_style))
        else:
            for line in invoice_data['client_address'].split('\n'): story.append(Paragraph(line, normal_style))
    if invoice_data.get('client_vat'): story.append(Paragraph(f"VAT: {invoice_data['client_vat']}", normal_style))
    story.append(Spacer(1, 1*cm))

    # Items Table
    table_data = [
        [Paragraph("<b>Description</b>", normal_style), Paragraph("<b>Quantity</b>", normal_style), Paragraph("<b>Unit Price</b>", normal_style), Paragraph("<b>Total</b>", normal_style)]
    ]
    for item in invoice_data.get('items', []):
        try:
            qty = float(item.get('quantity', 0))
            unit_price = float(item.get('unit_price', 0))
            total_item_price = qty * unit_price
            table_data.append([
                Paragraph(item.get('description', 'N/A'), normal_style),
                Paragraph(str(qty), normal_style),
                Paragraph(f"{currency_symbol}{unit_price:.2f}", normal_style),
                Paragraph(f"{currency_symbol}{total_item_price:.2f}", normal_style)
            ])
        except (ValueError, TypeError):
             table_data.append([Paragraph(item.get('description', 'Error in item data'), normal_style), '', '', ''])


    item_table = Table(table_data, colWidths=[8*cm, 2*cm, 3*cm, 3*cm]) # Adjust colWidths
    item_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), HexColor("#EEEEEE")), # Header background
        ('TEXTCOLOR', (0,0), (-1,0), black),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('ALIGN', (1,1), (-1,-1), 'RIGHT'), # Align numbers to right
        ('FONTNAME', (0,0), (-1,0), 'DejaVuSans-Bold' if 'DejaVuSans-Bold' in styles else 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,0), 12),
        ('BACKGROUND', (0,1), (-1,-1), HexColor("#FFFFFF")),
        ('GRID', (0,0), (-1,-1), 1, gray)
    ]))
    story.append(item_table)
    story.append(Spacer(1, 0.5*cm))

    # Totals Section
    totals_data = []
    if 'subtotal' in invoice_data:
        totals_data.append([Paragraph("Subtotal:", normal_style), Paragraph(f"{currency_symbol}{invoice_data['subtotal']:.2f}", right_align_style)])
    if 'tax_amount' in invoice_data:
        tax_rate = invoice_data.get('tax_rate_percentage', 20.0) # Get actual rate used
        totals_data.append([Paragraph(f"Tax ({tax_rate:.1f}%):", normal_style), Paragraph(f"{currency_symbol}{invoice_data['tax_amount']:.2f}", right_align_style)])
    if 'grand_total' in invoice_data:
        totals_data.append([Paragraph("<b>Grand Total:</b>", normal_style), Paragraph(f"<b>{currency_symbol}{invoice_data['grand_total']:.2f}</b>", right_align_style)])

    if totals_data:
        totals_table = Table(totals_data, colWidths=[13*cm, 3*cm]) # Adjust colWidths
        totals_table.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'RIGHT'),
            ('LEFTPADDING', (0,0), (-1,-1), 0), # Remove padding for better alignment control with Paragraph
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
            ('FONTNAME', (0, -1), (1, -1), 'DejaVuSans-Bold' if 'DejaVuSans-Bold' in styles else 'Helvetica-Bold'), # Last row (grand total) bold
        ]))
        story.append(totals_table)
    story.append(Spacer(1, 1*cm))

    # Payment Information / Notes
    if invoice_data.get('payment_terms'):
        story.append(Paragraph("Payment Terms:", h2_style))
        story.append(Paragraph(invoice_data['payment_terms'], normal_style))
        story.append(Spacer(1, 0.5*cm))
    
    if invoice_data.get('notes'):
        story.append(Paragraph("Notes:", h2_style))
        story.append(Paragraph(invoice_data['notes'], normal_style))
        story.append(Spacer(1, 0.5*cm))

    # Footer (e.g., Thank you message)
    story.append(Paragraph("Thank you for your business!", ParagraphStyle(name='Center', parent=normal_style, alignment=TA_CENTER)))

    try:
        doc.build(story)
        current_app.logger.info(f"Invoice PDF generated successfully: {pdf_file_path}")
    except Exception as e:
        current_app.logger.error(f"Error building PDF document for {pdf_file_path}: {e}", exc_info=True)
        raise # Re-raise the exception to be caught by the caller

if __name__ == '__main__':
    # This is for standalone testing if needed.
    # You'd need to mock current_app or provide a dummy config.
    
    # Dummy current_app and config for testing
    class MockConfig:
        INVOICE_COMPANY_NAME = "Test Corp"
        INVOICE_COMPANY_ADDRESS_LINES = ["1 Test St", "Testville, TS 12345"]
        INVOICE_COMPANY_VAT = "GB123456789"
        INVOICE_COMPANY_EMAIL = "test@testcorp.com"
        INVOICE_COMPANY_PHONE = "0123456789"
        INVOICE_COMPANY_LOGO_PATH = None # Provide a path to a test logo if you have one
        CURRENCY_SYMBOL = "$"
        INVOICE_FONT_REGULAR_PATH = None # Provide paths to test fonts
        INVOICE_FONT_BOLD_PATH = None

    class MockApp:
        def __init__(self):
            self.config = MockConfig()
            self.logger = logging.getLogger(__name__) # Basic logger for testing

    current_app = MockApp() # Mock current_app for standalone execution

    test_invoice_data = {
        'invoice_number': 'TEST-2024-001',
        'issue_date': '2024-05-27',
        'due_date': '2024-06-26',
        'client_name': 'John Doe',
        'client_address': '123 Client Ave\nClient City, CL 67890',
        'client_vat': 'CL987654321',
        'items': [
            {'description': 'Premium Truffle Oil', 'quantity': 2, 'unit_price': 25.00},
            {'description': 'Fresh Black Truffles (100g)', 'quantity': 1, 'unit_price': 150.00},
        ],
        # Totals will be calculated by calculate_invoice_totals_service
        'payment_terms': 'Payment due within 30 days.',
        'notes': 'Handle truffles with care.'
    }
    totals = calculate_invoice_totals_service(test_invoice_data['items'])
    test_invoice_data.update(totals)

    if not os.path.exists("test_invoices"):
        os.makedirs("test_invoices")
    test_pdf_path = "test_invoices/sample_invoice.pdf"
    
    try:
        generate_invoice_pdf_to_file(test_pdf_path, test_invoice_data)
        print(f"Test invoice generated: {test_pdf_path}")
    except Exception as e:
        print(f"Error generating test invoice: {e}")
