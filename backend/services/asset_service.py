# backend/services/asset_service.py
import os
import qrcode
from flask import current_app
from PIL import Image, ImageDraw, ImageFont

# Assuming backend.utils has format_date_french
from ..utils import format_date_french

# --- Constants and Configs adapted from generate_label.py ---
# Ensure these paths are correct relative to the project structure or use absolute paths from config
# For fonts/logos, it's often best to place them in a dedicated 'assets' folder at the project root
# and construct paths from current_app.root_path or a config variable.

# Example: Get base project path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

DEFAULT_FONT_PATH = os.path.join(PROJECT_ROOT, "assets", "fonts", "arial.ttf") # Adjusted path
MAISON_TRUVRA_LOGO_PATH_LABEL = os.path.join(PROJECT_ROOT, "assets", "images", "image_6b84ab.png") # Adjusted path for label logo
MAISON_TRUVRA_LOGO_URL_PASSPORT = "https://www.maisontruvra.com/assets/images/image_6be700.png" # URL for passport

DEFAULT_FONT_SIZE_TITLE = 24
DEFAULT_FONT_SIZE_TEXT = 16
DEFAULT_FONT_SIZE_SMALL = 12
TEXT_COLOR = (0, 0, 0) # Noir
LABEL_BACKGROUND_COLOR = (255, 255, 255) # Blanc par défaut

POT_LABEL_CONFIG = {
    "Grand 200mL": {"avant": {"width": 300, "height": 200, "logo_area": (10, 10, 100, 50)}, "arriere": {"width": 300, "height": 200, "qr_code_area": (200, 130, 290, 190)}},
    "Carré 150mL": {"avant": {"width": 250, "height": 180, "logo_area": (10, 10, 90, 45)}, "arriere": {"width": 250, "height": 180, "qr_code_area": (160, 110, 230, 170)}},
    "Petit 100mL": {"avant": {"width": 200, "height": 150, "logo_area": (5, 5, 75, 35)}, "arriere": {"width": 200, "height": 150, "qr_code_area": (130, 90, 190, 140)}},
    "Sachet plastique": {"avant": {"width": 350, "height": 250, "logo_area": (15, 15, 120, 60), "qr_code_area": (250, 170, 340, 240)}, "arriere": None},
    "default": {"avant": {"width": 250, "height": 180, "logo_area": (10, 10, 90, 45)}, "arriere": {"width": 250, "height": 180, "qr_code_area": (160, 110, 230, 170)}}
}

PRODUCT_CONTENT_CONFIG = {
    "Truffe Noire du Périgord Entière fraîche": {"texte_avant_specifique": "L'excellence de la Truffe Noire Fraîche.", "image_produit_path": None, "ingredients_specifiques": None},
    "Brisures de Truffe Noire du Périgord": {"texte_avant_specifique": "L'intensité des brisures de Melanosporum.", "image_produit_path": None, "ingredients_specifiques": "Truffe Noire (Tuber melanosporum), jus de truffe Tuber melanosporum, sel."},
    "Huile infusée à la Truffe Noire du Périgord": {"texte_avant_specifique": "Subtilement parfumée.", "image_produit_path": None, "ingredients_specifiques": "Huile d'olive vierge extra, arôme naturel de truffe noire (Tuber melanosporum)."},
    "default": {"texte_avant_specifique": "Un délice Maison Trüvra.", "image_produit_path": None, "ingredients_specifiques": None}
}

# --- Constants from generate_passport_html.py ---
PASSPORT_CONTACT_EMAIL = "contact@maisontruvra.com"
PASSPORT_INSTAGRAM_HANDLE = "@maisontruvra"


class AssetService:
    def __init__(self):
        self.qr_code_storage_path = current_app.config['PRODUCT_QR_CODE_PATH'] # Absolute path for saving
        self.label_storage_path = current_app.config['PRODUCT_LABEL_PATH']     # Absolute path for saving
        self.passport_storage_path = current_app.config['PRODUCT_PASSPORT_PATH'] # Absolute path for saving
        
        # Relative base paths for URL construction (must match admin_api asset serving route)
        self.qr_code_url_base = f"/{os.path.basename(self.qr_code_storage_path)}"
        self.label_url_base = f"/{os.path.basename(self.label_storage_path)}"
        self.passport_url_base = f"/{os.path.basename(self.passport_storage_path)}"

        os.makedirs(self.qr_code_storage_path, exist_ok=True)
        os.makedirs(self.label_storage_path, exist_ok=True)
        os.makedirs(self.passport_storage_path, exist_ok=True)

        # Check for font file during initialization
        if not os.path.exists(DEFAULT_FONT_PATH):
            current_app.logger.warning(f"Default font not found at {DEFAULT_FONT_PATH}. Label generation might use Pillow's default.")
        if not os.path.exists(MAISON_TRUVRA_LOGO_PATH_LABEL):
            current_app.logger.warning(f"Label logo not found at {MAISON_TRUVRA_LOGO_PATH_LABEL}.")


    def generate_qr_code(self, product_id: int, data_to_encode: str) -> tuple[str | None, str | None]:
        """Generates a QR code, saves it. Returns (absolute_path, relative_url_path) or (None, None) on failure."""
        filename = f"qr_product_{product_id}.png"
        absolute_filepath = os.path.join(self.qr_code_storage_path, filename)
        relative_url = f"{self.qr_code_url_base}/{filename}"
        try:
            img = qrcode.make(data_to_encode)
            img.save(absolute_filepath)
            current_app.logger.info(f"QR code generated for product {product_id} at {absolute_filepath}")
            return absolute_filepath, relative_url
        except Exception as e:
            current_app.logger.error(f"Error generating QR code for product {product_id}: {e}")
            return None, None

    # --- Label Generation Logic (from generate_label.py) ---
    def _load_font(self, size, weight="normal"): #
        font_path_to_try = DEFAULT_FONT_PATH
        try:
            return ImageFont.truetype(font_path_to_try, size)
        except IOError:
            current_app.logger.warning(f"Font {font_path_to_try} not found. Using Pillow's default font.")
            return ImageFont.load_default()

    def _draw_text_multiline(self, draw, text, position, font, max_width, text_color=TEXT_COLOR, spacing=4, align="left"): #
        if not text: return position[1]
        lines = []
        words = text.split()
        if not words: return position[1]

        current_line = words[0]
        for word in words[1:]:
            test_line = f"{current_line} {word}"
            try:
                bbox = draw.textbbox((0,0), test_line, font=font)
                line_width = bbox[2] - bbox[0]
            except AttributeError: # Fallback for older Pillow
                line_width, _ = draw.textsize(test_line, font=font)

            if line_width <= max_width:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = word
        lines.append(current_line)

        y_text = position[1]
        for line_idx, line in enumerate(lines):
            x_text = position[0]
            line_actual_width = 0
            line_height = 0
            try:
                bbox_line = draw.textbbox((0,0), line, font=font)
                line_actual_width = bbox_line[2] - bbox_line[0]
                line_height = bbox_line[3] - bbox_line[1] 
            except AttributeError: # Fallback
                line_actual_width, line_height = draw.textsize(line, font=font)
                if line_idx == 0: # Estimate height only once for older Pillow if needed for y_text updates.
                    line_height = font.getsize("A")[1] # Rough height

            if align == "center":
                x_text = position[0] + (max_width - line_actual_width) / 2
            elif align == "right":
                x_text = position[0] + (max_width - line_actual_width)
            
            draw.text((x_text, y_text), line, font=font, fill=text_color)
            y_text += line_height + spacing
        return y_text
        
    def _paste_image_in_area(self, base_image, image_to_paste_path, area_coords): #
        if image_to_paste_path and os.path.exists(image_to_paste_path):
            try:
                img_to_paste = Image.open(image_to_paste_path)
                area_width = area_coords[2] - area_coords[0]
                area_height = area_coords[3] - area_coords[1]
                img_to_paste.thumbnail((area_width, area_height), Image.Resampling.LANCZOS)
                paste_x = area_coords[0] + (area_width - img_to_paste.width) // 2
                paste_y = area_coords[1] + (area_height - img_to_paste.height) // 2
                if img_to_paste.mode == 'RGBA':
                    base_image.paste(img_to_paste, (paste_x, paste_y), img_to_paste)
                else:
                    base_image.paste(img_to_paste, (paste_x, paste_y))
                return True
            except Exception as e_img:
                current_app.logger.error(f"Error loading/pasting image {image_to_paste_path}: {e_img}")
        else:
            if image_to_paste_path: current_app.logger.warning(f"Image not found for pasting: {image_to_paste_path}")
        return False

    def generate_product_label(self, product_details: dict, qr_code_abs_path: str | None) -> str | None: # Modified
        """ Generates product label(s). Returns relative_url_path to the front label or None. """
        try:
            pot_type = product_details.get("pot_selectionne") # From original script's data expectations
            if not pot_type:
                 pot_type = "Sachet plastique" if product_details.get("type_produit_detail") == "frais" else "default"
            
            label_spec_pot = POT_LABEL_CONFIG.get(pot_type, POT_LABEL_CONFIG["default"])
            product_name_key = product_details.get("name_fr", "default") # Using 'name_fr' from service data
            content_spec_product = PRODUCT_CONTENT_CONFIG.get(product_name_key, PRODUCT_CONTENT_CONFIG.get(product_details.get("nom_produit_affiche"), PRODUCT_CONTENT_CONFIG["default"])) # Fallback for compatibility
            
            num_identification = product_details.get("product_id_display", f"MT{product_details.get('product_id','000'):05d}")


            font_title = self._load_font(DEFAULT_FONT_SIZE_TITLE, weight="bold")
            font_text = self._load_font(DEFAULT_FONT_SIZE_TEXT)
            font_small = self._load_font(DEFAULT_FONT_SIZE_SMALL)

            spec_avant = label_spec_pot["avant"]
            img_avant = Image.new("RGB", (spec_avant["width"], spec_avant["height"]), LABEL_BACKGROUND_COLOR)
            draw_avant = ImageDraw.Draw(img_avant)
            current_y, padding_x = 15, 15

            if spec_avant.get("logo_area"):
                if self._paste_image_in_area(img_avant, MAISON_TRUVRA_LOGO_PATH_LABEL, spec_avant["logo_area"]):
                    current_y = max(current_y, spec_avant["logo_area"][3] + 10)
            
            nom_produit_affiche = product_details.get("name_fr", "Produit Maison Trüvra")
            current_y = self._draw_text_multiline(draw_avant, nom_produit_affiche, (padding_x, current_y), font_title, spec_avant["width"] - 2 * padding_x, align="center")
            current_y += 10

            if content_spec_product.get("texte_avant_specifique"):
                current_y = self._draw_text_multiline(draw_avant, content_spec_product["texte_avant_specifique"], (padding_x, current_y), font_text, spec_avant["width"] - 2 * padding_x, align="center")
                current_y += 10
            
            # Custom product image on label (if path provided in PRODUCT_CONTENT_CONFIG)
            # ... (logic for content_spec_product.get("image_produit_path") can be added here if needed)

            poids_net_str = f"Poids Net : {product_details.get('weight_grams', product_details.get('poids_net_final_g', 'N/A'))} g"
            try:
                bbox_poids = draw_avant.textbbox((0,0), poids_net_str, font=font_text)
                poids_height = bbox_poids[3] - bbox_poids[1]
            except AttributeError:
                _, poids_height = draw_avant.textsize(poids_net_str, font=font_text) # Fallback

            y_poids = spec_avant["height"] - poids_height - 15 
            self._draw_text_multiline(draw_avant, poids_net_str, (padding_x, y_poids), font_text, spec_avant["width"] - 2 * padding_x, align="center")

            if pot_type == "Sachet plastique" and spec_avant.get("qr_code_area") and qr_code_abs_path:
                self._paste_image_in_area(img_avant, qr_code_abs_path, spec_avant["qr_code_area"])

            filename_avant = f"LABEL_AVANT_{num_identification}.png"
            filepath_avant_abs = os.path.join(self.label_storage_path, filename_avant)
            img_avant.save(filepath_avant_abs)
            current_app.logger.info(f"Front label generated: {filepath_avant_abs}")
            url_avant = f"{self.label_url_base}/{filename_avant}"

            if label_spec_pot.get("arriere"):
                spec_arriere = label_spec_pot["arriere"]
                img_arriere = Image.new("RGB", (spec_arriere["width"], spec_arriere["height"]), LABEL_BACKGROUND_COLOR)
                draw_arriere = ImageDraw.Draw(img_arriere)
                current_y_arr = 10
                
                ingredients_text = product_details.get("ingredients_affichage", content_spec_product.get("ingredients_specifiques", "Voir emballage"))
                current_y_arr = self._draw_text_multiline(draw_arriere, f"Ingrédients : {ingredients_text}", (10, current_y_arr), font_small, spec_arriere["width"] - 20)
                
                # DDM: product_details might have 'ddm' or 'best_before_date'
                ddm_raw = product_details.get("ddm", product_details.get("best_before_date"))
                ddm_str = format_date_french(ddm_raw) if ddm_raw else "N/A" # Use backend.utils.format_date_french
                current_y_arr = self._draw_text_multiline(draw_arriere, f"DDM : {ddm_str}", (10, current_y_arr), font_small, spec_arriere["width"] - 20)
                
                current_y_arr = self._draw_text_multiline(draw_arriere, f"ID : {num_identification}", (10, current_y_arr), font_small, spec_arriere["width"] - 20)
                if product_details.get("numero_lot_manuel", product_details.get("lot_number")):
                    current_y_arr = self._draw_text_multiline(draw_arriere, f"Lot : {product_details.get('numero_lot_manuel', product_details.get('lot_number'))}", (10, current_y_arr), font_small, spec_arriere["width"] - 20)
                
                current_y_arr = self._draw_text_multiline(draw_arriere, "Maison Trüvra - contact@maisontruvra.com", (10, current_y_arr + 5), font_small, spec_arriere["width"] - 20)

                if spec_arriere.get("qr_code_area") and qr_code_abs_path:
                    self._paste_image_in_area(img_arriere, qr_code_abs_path, spec_arriere["qr_code_area"])

                filename_arriere = f"LABEL_ARRIERE_{num_identification}.png"
                filepath_arriere_abs = os.path.join(self.label_storage_path, filename_arriere)
                img_arriere.save(filepath_arriere_abs)
                current_app.logger.info(f"Rear label generated: {filepath_arriere_abs}")
            
            return url_avant # Return URL to front label
        except Exception as e:
            current_app.logger.error(f"Major error generating labels for product ID {product_details.get('product_id')}: {e}", exc_info=True)
            return None

    # --- Passport Generation Logic (from generate_passport_html.py) ---
    def _get_product_specific_text_passport(self, espece_truffe, nom_produit_affiche): #
        return f"""Nos truffes {espece_truffe} sont cultivées avec un soin extrême dans nos installations uniques. 
Chez Maison Trüvra, nous maîtrisons chaque paramètre de notre environnement contrôlé pour permettre à chaque truffe 
d'atteindre sa parfaite maturité aromatique, loin des aléas extérieurs. C'est cet artisanat méticuleux et 
cette provenance maîtrisée qui garantissent la pureté et l'intensité de la truffe utilisée pour votre {nom_produit_affiche}.
<br><br>
Nous sommes fiers de cultiver nos truffes en respectant l'environnement, en utilisant des intrants respectueux 
de l'environnement et de l'énergie 100% renouvelable. Votre {nom_produit_affiche} est le fruit de notre travail 
artisanal et engagé."""


    def generate_product_passport(self, product_details: dict) -> str | None: # Modified
        """ Generates a product passport HTML file. Returns relative_url_path or None. """
        try:
            # Adapt product_details keys to match those expected by original script if necessary
            # Or rely on a consistent structure passed to the service.
            nom_produit = product_details.get("name_fr", product_details.get("nom_produit_affiche", "N/A"))
            num_identification = product_details.get("product_id_display", f"MT{product_details.get('product_id','000'):05d}")
            num_lot = product_details.get("lot_number", product_details.get("numero_lot_manuel", "Non fourni"))
            
            date_conditionnement_raw = product_details.get("packaging_date", product_details.get("date_conditionnement"))
            date_conditionnement = format_date_french(date_conditionnement_raw) if date_conditionnement_raw else "N/A"
            
            ddm_raw = product_details.get("best_before_date", product_details.get("ddm"))
            ddm = format_date_french(ddm_raw) if ddm_raw and ddm_raw != "N/A" else "N/A"

            poids_net = product_details.get("weight_grams", product_details.get("poids_net_final_g", "N/A"))
            poids_net_str = f"{poids_net} g" if poids_net != "N/A" else "N/A"
            
            ingredients = product_details.get("ingredients", product_details.get("ingredients_affichage", "Veuillez consulter l'emballage."))
            espece_truffe = product_details.get("truffle_species", product_details.get("espece_truffe", "de nos régions")) 

            texte_passion = self._get_product_specific_text_passport(espece_truffe, nom_produit)
            
            logo_tag = f'<img src="{MAISON_TRUVRA_LOGO_URL_PASSPORT}" alt="Logo Maison Trüvra" class="logo" style="max-width:180px; margin-bottom:15px;">'

            html_content = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Passeport de ma Truffe - {nom_produit}</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 0; background-color: #f9f6f2; color: #3a2d22; line-height: 1.6; }}
        .container {{ max-width: 800px; margin: 20px auto; padding: 25px; background-color: #ffffff; border-radius: 12px; box-shadow: 0 6px 20px rgba(0,0,0,0.08); }}
        header {{ text-align: center; margin-bottom: 30px; padding-bottom: 20px; border-bottom: 2px solid #e0d8ce; }}
        h1 {{ color: #5c4b3e; font-size: 2.2em; margin-bottom: 10px; }}
        h2 {{ color: #7a6a5d; font-size: 1.6em; margin-top: 30px; margin-bottom: 15px; border-bottom: 1px solid #eee; padding-bottom: 8px; }}
        p, li {{ font-size: 1.05em; margin-bottom: 12px; }}
        .product-info {{ background-color: #fdfbf7; padding: 20px; border-radius: 8px; margin-bottom: 25px; border: 1px solid #e0d8ce; }}
        .product-info strong {{ color: #5c4b3e; min-width: 220px; display: inline-block; }}
        /* ... other styles from generate_passport_html.py ... */
    </style>
</head>
<body>
    <div class="container">
        <header>
            {logo_tag}
            <h1>Passeport de ma truffe</h1>
            <p>Bienvenu(e) sur la page passeport de votre produit Maison Trüvra.</p>
        </header>
        <section class="intro-text section">
            <p>Chaque produit créé par Maison Trüvra possède un numéro d'identification et un QR code. En scannant ce QR code, vous arrivez sur cette page sur laquelle vous retrouvez les informations spécifiques sur votre achat :</p>
        </section>
        <section class="product-info section">
            <h2>Informations de votre Produit</h2>
            <p><strong>Produit :</strong> {nom_produit}</p>
            <p><strong>Numéro d'identification du produit :</strong> {num_identification}</p>
            <p><strong>Numéro de lot :</strong> {num_lot}</p>
            <p><strong>Date de conditionnement :</strong> {date_conditionnement}</p>
            <p><strong>À consommer de préférence avant le :</strong> {ddm}</p>
            <p><strong>Poids Net :</strong> {poids_net_str}</p>
            <p><strong>Ingrédients :</strong> {ingredients}</p>
        </section>
        <section class="passion-text section">
            <h2>Des truffes cultivées avec passion</h2>
            <p>{texte_passion}</p>
        </section>
        <section class="links-section section">
            <h2>Explorez notre site pour en apprendre plus sur Maison Trüvra :</h2>
            <a href="https://www.maisontruvra.com/notre-histoire.html" target="_blank">Lien vers la page Notre Histoire</a>
            <a href="https://www.maisontruvra.com/" target="_blank">Retour à l'accueil</a>
        </section>
        <footer>
            <p>Merci d'avoir choisi Maison Trüvra et nous vous souhaitons une excellente dégustation !</p>
            <p>Une question, un commentaire ? Contactez-nous par email à <a href="mailto:{PASSPORT_CONTACT_EMAIL}">{PASSPORT_CONTACT_EMAIL}</a> 
            ou sur notre compte Instagram <a href="https://www.instagram.com/{PASSPORT_INSTAGRAM_HANDLE.replace('@','')}" target="_blank">{PASSPORT_INSTAGRAM_HANDLE}</a>.</p>
             <p><a href="https://www.maisontruvra.com/" target="_blank">www.maisontruvra.com</a></p>
        </footer>
    </div>
</body>
</html>"""
            filename = f"passport_{num_identification}.html"
            absolute_filepath = os.path.join(self.passport_storage_path, filename)

            with open(absolute_filepath, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            current_app.logger.info(f"Passport HTML generated: {absolute_filepath}")
            return f"{self.passport_url_base}/{filename}" # Return relative URL path

        except Exception as e:
            current_app.logger.error(f"Error generating HTML passport for product ID {product_details.get('product_id')}: {e}", exc_info=True)
            return None
