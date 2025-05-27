# backend/services/asset_service.py
import os
import qrcode
from flask import current_app
from PIL import Image # For label generation if using Pillow directly here
# Assuming generate_label.py and generate_passport_html.py are in the project root
# and can be imported or their logic moved here.
# For now, let's assume their core logic might be refactored into this service.
# from ...generate_label import generate_label_image  # Adjust import path
# from ...generate_passport_html import generate_passport_html_content # Adjust import path

class AssetService:
    def __init__(self):
        self.qr_code_path = current_app.config['PRODUCT_QR_CODE_PATH']
        self.label_path = current_app.config['PRODUCT_LABEL_PATH']
        self.passport_path = current_app.config['PRODUCT_PASSPORT_PATH']
        os.makedirs(self.qr_code_path, exist_ok=True)
        os.makedirs(self.label_path, exist_ok=True)
        os.makedirs(self.passport_path, exist_ok=True)

    def generate_qr_code(self, product_id: int, data_to_encode: str) -> str:
        """Generates a QR code for the product and saves it."""
        filename = f"qr_product_{product_id}.png"
        filepath = os.path.join(self.qr_code_path, filename)
        
        img = qrcode.make(data_to_encode)
        img.save(filepath)
        current_app.logger.info(f"QR code generated for product {product_id} at {filepath}")
        # Return relative path for URL generation
        return f"/{os.path.basename(self.qr_code_path)}/{filename}"


    def generate_product_label(self, product_details: dict) -> str:
        """
        Generates a product label image.
        product_details: dict containing name, weight, price_per_kg, origin, etc.
        This should call the logic from your existing generate_label.py.
        For now, a placeholder.
        """
        product_id = product_details.get('product_id', 'unknown')
        filename = f"label_product_{product_id}.png"
        filepath = os.path.join(self.label_path, filename)

        # --- Placeholder for actual label generation logic ---
        # Example: from generate_label import create_label_for_pot_gratte_tuber_melanosporum_30g
        # if product_details.get('weight_grams') == 30 and "melanosporum" in product_details.get('product_name','').lower():
        #     try:
        #         # This function needs to be adapted to take product_details and save path
        #         # image = create_label_for_pot_gratte_tuber_melanosporum_30g(
        #         #     product_name=product_details['product_name'],
        #         #     price_per_kg=str(int(product_details.get('price_per_kg', 0))), # Ensure string
        #         #     date_of_packaging=product_details.get('harvest_date', 'N/A'), # Or packaging date
        #         #     product_id_display=product_details.get('product_id_display', '')
        #         # )
        #         # image.save(filepath)
        #         # current_app.logger.info(f"Product label generated for product {product_id} at {filepath}")
        #
        #         # SIMPLIFIED PLACEHOLDER: Create a dummy image
        img = Image.new('RGB', (400, 200), color = 'white')
        # Add text or drawing if needed for placeholder
        img.save(filepath) # Save a dummy file
        current_app.logger.info(f"Placeholder product label generated for product {product_id} at {filepath}")

        #     except Exception as e:
        #         current_app.logger.error(f"Error generating label for product {product_id} using external script: {e}")
        #         raise # Re-raise to indicate failure
        # else:
        #     # Fallback or error if no specific label template matches
        #     current_app.logger.warning(f"No specific label template for product {product_id}, details: {product_details}")
        #     # Create a dummy file for now
        #     with open(filepath, 'w') as f:
        #         f.write(f"Label for {product_details.get('product_name', 'N/A')}")
        #     current_app.logger.info(f"Dummy product label created for product {product_id} at {filepath}")
        # --- End Placeholder ---
        
        return f"/{os.path.basename(self.label_path)}/{filename}"


    def generate_product_passport(self, product_details: dict) -> str:
        """
        Generates a product passport HTML file.
        product_details: dict containing name, origin, harvest_date, qr_code_path, etc.
        This should call the logic from your existing generate_passport_html.py.
        For now, a placeholder.
        """
        product_id = product_details.get('product_id', 'unknown')
        filename = f"passport_product_{product_id}.html"
        filepath = os.path.join(self.passport_path, filename)

        # --- Placeholder for actual passport generation logic ---
        # Example: from generate_passport_html import generate_html # Needs adaptation
        # try:
        #     # This function needs to be adapted to take product_details and save path
        #     # html_content = generate_html(
        #     #     product_name=product_details['product_name'],
        #     #     category=product_details.get('category_name', ''),
        #     #     composition=product_details.get('composition', ''),
        #     #     origin=product_details.get('origin', ''),
        #     #     harvest_date_str=product_details.get('harvest_date', ''),
        #     #     qr_code_filename=os.path.basename(product_details.get('qr_code_path_on_server','')), # Relative to passport
        #     #     product_id_display=product_details.get('product_id_display', '')
        #     # )
        #     # with open(filepath, 'w', encoding='utf-8') as f:
        #     #     f.write(html_content)
        #     # current_app.logger.info(f"Product passport generated for product {product_id} at {filepath}")
        #
        # SIMPLIFIED PLACEHOLDER: Create a dummy HTML file
        html_content = f"<html><body><h1>Passport for {product_details.get('product_name', 'N/A')}</h1>"
        html_content += f"<p>ID: {product_details.get('product_id_display', product_id)}</p>"
        # Include QR code image if path is available
        # qr_image_url = product_details.get('qr_code_url_for_passport') # This needs to be relative or absolute
        # if qr_image_url: html_content += f"<img src='{qr_image_url}' alt='QR Code'>"
        html_content += "</body></html>"
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        current_app.logger.info(f"Placeholder product passport generated for product {product_id} at {filepath}")

        # except Exception as e:
        #     current_app.logger.error(f"Error generating passport for product {product_id} using external script: {e}")
        #     raise
        # --- End Placeholder ---

        return f"/{os.path.basename(self.passport_path)}/{filename}"

