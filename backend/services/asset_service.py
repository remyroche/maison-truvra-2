import qrcode
from PIL import Image, ImageDraw, ImageFont
import os
import json
from flask import current_app, url_for # Added url_for

class AssetService:
    def __init__(self, app):
        self.app = app
        self.config = app.config # Store config for easy access

    def _ensure_dir(self, directory_path):
        if not os.path.exists(directory_path):
            os.makedirs(directory_path, exist_ok=True)

    def generate_qr_code(self, product_id, product_slug):
        """
        Generates a QR code for a given product ID that links to the product detail page.
        Saves the QR code image and returns its web-accessible path.
        """
        qr_output_dir = self.config['QR_CODES_OUTPUT_DIR']
        self._ensure_dir(qr_output_dir)

        # Construct the URL for the product detail page
        # Assuming your frontend product detail URL is something like /produit-detail.html?slug=<product_slug>
        # or /products/<product_slug>
        # This needs to match your actual frontend routing.
        # Using url_for requires the endpoint to be defined. If it's a static HTML page,
        # you might need to construct the URL manually or have a config for base URL.
        try:
            # Example if you have a route for product details in Flask (even if it serves static HTML)
            # product_url = url_for('products.get_product_by_slug', product_slug=product_slug, _external=True)
            # For now, let's assume a simpler structure if no such route exists:
            base_url = self.app.config.get('FRONTEND_BASE_URL', '/') # Add FRONTEND_BASE_URL to your config
            product_url = f"{base_url.rstrip('/')}/produit-detail.html?slug={product_slug}"

        except Exception as e:
            # Fallback if url_for fails or not applicable
            self.app.logger.warning(f"Could not generate product URL via url_for for slug {product_slug}: {e}. Using manual construction.")
            # Adjust this to your actual frontend URL structure
            product_url = f"/produit-detail.html?slug={product_slug}" 


        qr_filename = f"qr_product_{product_id}_{product_slug}.png"
        qr_filepath = os.path.join(qr_output_dir, qr_filename)
        
        qr_img = qrcode.make(product_url)
        qr_img.save(qr_filepath)
        
        # Return the web-accessible path
        # Assuming QR_CODES_OUTPUT_DIR is under 'website/static/assets/qr_codes'
        # The web path would be 'static/assets/qr_codes/qr_filename.png'
        # This needs to be relative to the static folder.
        static_base_path = os.path.join('static', 'assets', 'qr_codes') # Relative to website folder
        qr_web_path = os.path.join(static_base_path, qr_filename).replace("\\", "/") # Ensure forward slashes for web
        
        self.app.logger.info(f"Generated QR code for product {product_id} at {qr_filepath}, web path: {qr_web_path}")
        return qr_web_path


    def generate_product_label(self, product, variant=None):
        """
        Generates a product label image (e.g., for printing).
        Saves the label and returns its web-accessible path.
        This is a placeholder and needs actual label design implementation.
        """
        labels_output_dir = self.config['LABELS_OUTPUT_DIR']
        self._ensure_dir(labels_output_dir)

        product_name = product.get('name_fr', 'Nom Inconnu')
        sku = product.get('sku', 'SKU_INCONNU')
        variant_name = variant.get('name_fr', '') if variant else ''
        variant_sku = variant.get('sku', sku) if variant else sku # Use variant SKU if available

        label_filename = f"label_product_{product.get('id', '0')}_{variant_sku}.png"
        label_filepath = os.path.join(labels_output_dir, label_filename)

        # --- Placeholder for actual label generation ---
        try:
            img_width = 400
            img_height = 200
            img = Image.new('RGB', (img_width, img_height), color = 'white')
            d = ImageDraw.Draw(img)
            
            # Load fonts (ensure these paths are correct in config.py)
            try:
                font_regular_path = self.config['FONT_PATH_REGULAR']
                font_bold_path = self.config['FONT_PATH_BOLD']
                font_main = ImageFont.truetype(font_regular_path, 18)
                font_small = ImageFont.truetype(font_regular_path, 12)
                font_title = ImageFont.truetype(font_bold_path, 22)
            except IOError:
                self.app.logger.error(f"Font files not found at {self.config.get('FONT_PATH_REGULAR')} or {self.config.get('FONT_PATH_BOLD')}. Using default font.")
                # Pillow's default font is very basic. It's better to ensure fonts are available.
                font_main = ImageFont.load_default()
                font_small = ImageFont.load_default()
                font_title = ImageFont.load_default()


            # Simple label content
            d.text((10,10), "Maison Trüvra", fill=(0,0,0), font=font_title)
            d.text((10,50), f"Produit: {product_name}", fill=(0,0,0), font=font_main)
            if variant_name:
                d.text((10,80), f"Variante: {variant_name}", fill=(0,0,0), font=font_main)
            d.text((10,110), f"SKU: {variant_sku}", fill=(0,0,0), font=font_small)
            
            # Example: Add a QR code to the label (using the previously generated one if available)
            qr_code_path_on_label = product.get('qr_code_url') # This is the web path
            if qr_code_path_on_label:
                # Convert web path to filesystem path
                # Assuming qr_code_url is like 'static/assets/qr_codes/qr_file.png'
                # and BASE_DIR points to project root.
                qr_file_system_path = os.path.join(self.config['BASE_DIR'], 'website', qr_code_path_on_label)
                if os.path.exists(qr_file_system_path):
                    try:
                        qr_img_label = Image.open(qr_file_system_path)
                        qr_img_label = qr_img_label.resize((80, 80)) # Resize as needed
                        img.paste(qr_img_label, (img_width - 90, img_height - 90))
                    except Exception as e_qr:
                        self.app.logger.error(f"Could not embed QR code on label: {e_qr}")
                else:
                    self.app.logger.warning(f"QR code file not found for label embedding: {qr_file_system_path}")


            img.save(label_filepath)
        except Exception as e:
            self.app.logger.error(f"Error generating placeholder label for product {product.get('id')}: {e}")
            # Fallback: create a dummy file to avoid breaking if path is expected
            with open(label_filepath, 'w') as f:
                f.write("Error generating label.")
            # return None # Or handle error appropriately

        # Return the web-accessible path
        static_base_path = os.path.join('static', 'assets', 'labels')
        label_web_path = os.path.join(static_base_path, label_filename).replace("\\", "/")

        self.app.logger.info(f"Generated label for product {product.get('id')} at {label_filepath}, web path: {label_web_path}")
        return label_web_path

    def generate_product_passport(self, product, variant=None):
        """
        Generates an HTML product passport.
        Saves the HTML file and returns its web-accessible path.
        """
        passports_output_dir = self.config['PRODUCT_PASSPORTS_OUTPUT_DIR']
        self._ensure_dir(passports_output_dir)

        product_id = product.get('id', '0')
        product_slug = product.get('slug', 'produit-inconnu')
        variant_sku = variant.get('sku', product.get('sku', 'SKU_INCONNU')) if variant else product.get('sku', 'SKU_INCONNU')

        passport_filename = f"passport_product_{product_id}_{variant_sku}.html"
        passport_filepath = os.path.join(passports_output_dir, passport_filename)

        # --- HTML Content Generation ---
        product_name_fr = product.get('name_fr', 'N/A')
        description_fr = product.get('description_fr', 'N/A')
        main_image_url = product.get('main_image_url', '')
        qr_code_url = product.get('qr_code_url', '') # This should be the web path already

        # Adjust image and QR code paths to be absolute or correctly relative for the HTML file
        # If main_image_url and qr_code_url are already web paths (e.g., /static/...), they might work directly.
        # Otherwise, you might need to make them absolute URLs or adjust.
        # For simplicity, assuming they are web paths relative to the domain root.

        html_content = f"""
        <!DOCTYPE html>
        <html lang="fr">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Passeport Produit: {product_name_fr}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; padding: 0; background-color: #f9f9f9; color: #333; }}
                .container {{ background-color: #fff; padding: 30px; border-radius: 8px; box-shadow: 0 0 15px rgba(0,0,0,0.1); }}
                h1 {{ color: #2c3e50; border-bottom: 2px solid #e0ac69; padding-bottom: 10px; }}
                h2 {{ color: #e0ac69; margin-top: 20px; }}
                p {{ line-height: 1.6; }}
                .product-image {{ max-width: 300px; height: auto; border-radius: 4px; margin-bottom: 20px; border: 1px solid #ddd; }}
                .qr-code {{ max-width: 150px; height: auto; margin-top: 20px; }}
                .section {{ margin-bottom: 20px; }}
                .logo {{ max-width: 150px; margin-bottom: 20px; }}
                footer {{ margin-top: 30px; text-align: center; font-size: 0.9em; color: #777; }}
            </style>
        </head>
        <body>
            <div class="container">
                <img src="/static/images/logo/logo-TRUVRA-noir.png" alt="Maison Trüvra Logo" class="logo">
                <h1>Passeport Produit</h1>
                
                <div class="section">
                    <h2>{product_name_fr}</h2>
                    <p><strong>SKU:</strong> {variant_sku}</p>
                    {f'<img src="/{main_image_url}" alt="{product_name_fr}" class="product-image">' if main_image_url else ''}
                </div>

                <div class="section">
                    <h3>Description</h3>
                    <p>{description_fr}</p>
                </div>
                
                <div class="section">
                    <h3>Informations Complémentaires</h3>
                    <p><strong>Origine:</strong> (À compléter)</p>
                    <p><strong>Date de récolte/Lot:</strong> (À compléter)</p>
                    <p><strong>Conservation:</strong> (À compléter)</p>
                </div>

                {f'''
                <div class="section">
                    <h3>QR Code</h3>
                    <p>Scannez pour plus d'informations :</p>
                    <img src="/{qr_code_url}" alt="QR Code" class="qr-code">
                </div>
                ''' if qr_code_url else ''}

                <footer>
                    Maison Trüvra &copy; {os.path.basename(passport_filepath).split('_')[-1].split('.')[0]} <p>Pour toute question, contactez-nous à contact@maisontruvra.com</p>
                </footer>
            </div>
        </body>
        </html>
        """

        try:
            with open(passport_filepath, 'w', encoding='utf-8') as f:
                f.write(html_content)
        except Exception as e:
            self.app.logger.error(f"Error generating product passport for product {product_id}: {e}")
            # return None # Or handle error

        # Return the web-accessible path
        static_base_path = os.path.join('static', 'assets', 'product_passports')
        passport_web_path = os.path.join(static_base_path, passport_filename).replace("\\", "/")
        
        self.app.logger.info(f"Generated product passport for product {product_id} at {passport_filepath}, web path: {passport_web_path}")
        return passport_web_path

    def get_asset_paths(self, product_id, product_slug, variant_sku_part):
        """
        Helper to get expected asset paths for a product/variant.
        Used if you need to check existence or retrieve paths later.
        """
        qr_filename = f"qr_product_{product_id}_{product_slug}.png"
        label_filename = f"label_product_{product_id}_{variant_sku_part}.png"
        passport_filename = f"passport_product_{product_id}_{variant_sku_part}.html"

        qr_web_path = os.path.join('static', 'assets', 'qr_codes', qr_filename).replace("\\", "/")
        label_web_path = os.path.join('static', 'assets', 'labels', label_filename).replace("\\", "/")
        passport_web_path = os.path.join('static', 'assets', 'product_passports', passport_filename).replace("\\", "/")
        
        return {
            "qr_code_url": qr_web_path,
            "label_url": label_web_path,
            "product_passport_url": passport_web_path
        }

