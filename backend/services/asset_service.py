# backend/services/asset_service.py
import os
import qrcode
from flask import current_app
from PIL import Image, ImageDraw, ImageFont
import uuid # For generating UIDs

# Assuming backend.utils has format_date_french
from ..utils import format_date_french

# --- Constants and Configs adapted from generate_label.py ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DEFAULT_FONT_PATH = os.path.join(PROJECT_ROOT, "assets", "fonts", "arial.ttf")
MAISON_TRUVRA_LOGO_PATH_LABEL = os.path.join(PROJECT_ROOT, "assets", "images", "image_6b84ab.png")
MAISON_TRUVRA_LOGO_URL_PASSPORT = "https://www.maisontruvra.com/assets/images/image_6be700.png"

DEFAULT_FONT_SIZE_TITLE = 24
DEFAULT_FONT_SIZE_TEXT = 16
DEFAULT_FONT_SIZE_SMALL = 12
TEXT_COLOR = (0, 0, 0)
LABEL_BACKGROUND_COLOR = (255, 255, 255)

POT_LABEL_CONFIG = { # Keep as is, labels might still be product-type based
    "Grand 200mL": {"avant": {"width": 300, "height": 200, "logo_area": (10, 10, 100, 50)}, "arriere": {"width": 300, "height": 200, "qr_code_area": (200, 130, 290, 190)}},
    "Carré 150mL": {"avant": {"width": 250, "height": 180, "logo_area": (10, 10, 90, 45)}, "arriere": {"width": 250, "height": 180, "qr_code_area": (160, 110, 230, 170)}},
    "Petit 100mL": {"avant": {"width": 200, "height": 150, "logo_area": (5, 5, 75, 35)}, "arriere": {"width": 200, "height": 150, "qr_code_area": (130, 90, 190, 140)}},
    "Sachet plastique": {"avant": {"width": 350, "height": 250, "logo_area": (15, 15, 120, 60), "qr_code_area": (250, 170, 340, 240)}, "arriere": None},
    "default": {"avant": {"width": 250, "height": 180, "logo_area": (10, 10, 90, 45)}, "arriere": {"width": 250, "height": 180, "qr_code_area": (160, 110, 230, 170)}}
}
PRODUCT_CONTENT_CONFIG = { # Keep as is
    "Truffe Noire du Périgord Entière fraîche": {"texte_avant_specifique": "L'excellence de la Truffe Noire Fraîche.", "image_produit_path": None, "ingredients_specifiques": None},
    "Brisures de Truffe Noire du Périgord": {"texte_avant_specifique": "L'intensité des brisures de Melanosporum.", "image_produit_path": None, "ingredients_specifiques": "Truffe Noire (Tuber melanosporum), jus de truffe Tuber melanosporum, sel."},
    "Huile infusée à la Truffe Noire du Périgord": {"texte_avant_specifique": "Subtilement parfumée.", "image_produit_path": None, "ingredients_specifiques": "Huile d'olive vierge extra, arôme naturel de truffe noire (Tuber melanosporum)."},
    "default": {"texte_avant_specifique": "Un délice Maison Trüvra.", "image_produit_path": None, "ingredients_specifiques": None}
}

PASSPORT_CONTACT_EMAIL = "contact@maisontruvra.com"
PASSPORT_INSTAGRAM_HANDLE = "@maisontruvra"

class AssetService:
    def __init__(self):
        self.qr_code_storage_path = current_app.config['PRODUCT_QR_CODE_PATH']
        self.label_storage_path = current_app.config['PRODUCT_LABEL_PATH']
        self.passport_storage_path = current_app.config['PRODUCT_PASSPORT_PATH']
        
        self.qr_code_url_base = f"/{os.path.basename(self.qr_code_storage_path)}"
        self.label_url_base = f"/{os.path.basename(self.label_storage_path)}"
        self.passport_url_base = f"/{os.path.basename(self.passport_storage_path)}"

        os.makedirs(self.qr_code_storage_path, exist_ok=True)
        os.makedirs(self.label_storage_path, exist_ok=True)
        os.makedirs(self.passport_storage_path, exist_ok=True)

        if not os.path.exists(DEFAULT_FONT_PATH):
            current_app.logger.warning(f"Default font not found at {DEFAULT_FONT_PATH}.")
        if not os.path.exists(MAISON_TRUVRA_LOGO_PATH_LABEL):
            current_app.logger.warning(f"Label logo not found at {MAISON_TRUVRA_LOGO_PATH_LABEL}.")

    def generate_item_uid(self):
        """Generates a unique item ID."""
        # Consider a more structured UID if needed, e.g., prefix + sequence
        return uuid.uuid4().hex[:16].upper() # Example: 16-char uppercase hex

    def generate_item_qr_code(self, item_uid: str, item_passport_url: str) -> tuple[str | None, str | None]:
        """Generates a QR code for a specific item, linking to its passport.
           Returns (absolute_fs_path, relative_url_path) or (None, None)."""
        filename = f"qr_item_{item_uid}.png"
        absolute_filepath = os.path.join(self.qr_code_storage_path, filename)
        relative_url = f"{self.qr_code_url_base}/{filename}" # This is URL to the QR image itself
        try:
            img = qrcode.make(item_passport_url) # QR code encodes the URL to the item's passport
            img.save(absolute_filepath)
            current_app.logger.info(f"Item QR code generated for item UID {item_uid} linking to {item_passport_url} at {absolute_filepath}")
            return absolute_filepath, relative_url
        except Exception as e:
            current_app.logger.error(f"Error generating QR code for item UID {item_uid}: {e}")
            return None, None

    def _load_font(self, size, weight="normal"):
        try:
            return ImageFont.truetype(DEFAULT_FONT_PATH, size)
        except IOError:
            current_app.logger.warning(f"Font {DEFAULT_FONT_PATH} not found. Using Pillow's default.")
            return ImageFont.load_default()

    def _draw_text_multiline(self, draw, text, position, font, max_width, text_color=TEXT_COLOR, spacing=4, align="left"):
        if not text: return position[1]
        lines = []
        words = text.split()
        if not words: return position[1]
        current_line = words[0]
        for word in words[1:]:
            test_line = f"{current_line} {word}"
            try: bbox = draw.textbbox((0,0), test_line, font=font); line_width = bbox[2] - bbox[0]
            except AttributeError: line_width, _ = draw.textsize(test_line, font=font)
            if line_width <= max_width: current_line = test_line
            else: lines.append(current_line); current_line = word
        lines.append(current_line)
        y_text = position[1]
        for line_idx, line in enumerate(lines):
            x_text = position[0]
            try: bbox_line = draw.textbbox((0,0), line, font=font); line_actual_width = bbox_line[2] - bbox_line[0]; line_height = bbox_line[3] - bbox_line[1]
            except AttributeError: line_actual_width, line_height = draw.textsize(line, font=font); line_height = font.getsize("A")[1] if line_idx == 0 else line_height
            if align == "center": x_text = position[0] + (max_width - line_actual_width) / 2
            elif align == "right": x_text = position[0] + (max_width - line_actual_width)
            draw.text((x_text, y_text), line, font=font, fill=text_color)
            y_text += line_height + spacing
        return y_text
        
    def _paste_image_in_area(self, base_image, image_to_paste_path, area_coords):
        if image_to_paste_path and os.path.exists(image_to_paste_path):
            try:
                img_to_paste = Image.open(image_to_paste_path)
                area_width = area_coords[2] - area_coords[0]; area_height = area_coords[3] - area_coords[1]
                img_to_paste.thumbnail((area_width, area_height), Image.Resampling.LANCZOS)
                paste_x = area_coords[0] + (area_width - img_to_paste.width) // 2
                paste_y = area_coords[1] + (area_height - img_to_paste.height) // 2
                if img_to_paste.mode == 'RGBA': base_image.paste(img_to_paste, (paste_x, paste_y), img_to_paste)
                else: base_image.paste(img_to_paste, (paste_x, paste_y))
                return True
            except Exception as e_img: current_app.logger.error(f"Error pasting image {image_to_paste_path}: {e_img}")
        elif image_to_paste_path: current_app.logger.warning(f"Image not found for pasting: {image_to_paste_path}")
        return False

    def generate_product_label(self, product_details: dict, item_specific_qr_abs_path: str | None) -> str | None:
        """
        Generates product label(s). If item_specific_qr_abs_path is provided, it's used.
        Otherwise, a generic product QR might be used or no QR on label.
        Labels are still primarily product-type based unless content is significantly altered for items.
        Returns relative_url_path to the front label or None.
        """
        try:
            # ... (label generation logic from previous version, largely unchanged) ...
            # Key change: Use item_specific_qr_abs_path if provided for the QR code on the label.
            # If labels themselves need to display the item_uid, that text needs to be added.
            
            pot_type = product_details.get("pot_selectionne", "default")
            label_spec_pot = POT_LABEL_CONFIG.get(pot_type, POT_LABEL_CONFIG["default"])
            product_name_for_config = product_details.get("name_fr", "default")
            content_spec_product = PRODUCT_CONTENT_CONFIG.get(product_name_for_config, PRODUCT_CONTENT_CONFIG["default"])
            
            # Using product_id_display for label filename, as labels are less item-specific than passports
            # If labels MUST be item_uid specific in filename, change this.
            label_identifier = product_details.get("product_id_display", f"MT{product_details.get('product_id','000'):05d}")
            if product_details.get("item_uid_for_label"): # If we decide labels are also item_uid specific
                 label_identifier = product_details.get("item_uid_for_label")


            font_title = self._load_font(DEFAULT_FONT_SIZE_TITLE)
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

            # ... (rest of front label drawing logic as before) ...
             # Display item_uid on label if provided and desired
            if product_details.get("item_uid"):
                item_uid_text = f"UID: {product_details.get('item_uid')}"
                # Decide where to put it, e.g., below product name or near DDM/Lot
                current_y = self._draw_text_multiline(draw_avant, item_uid_text,
                                            (padding_x, current_y), font_small, # Use small font
                                            spec_avant["width"] - 2 * padding_x, align="center")
                current_y += 5


            poids_net_str = f"Poids Net : {product_details.get('weight_grams', 'N/A')} g"
            try: bbox_poids = draw_avant.textbbox((0,0), poids_net_str, font=font_text); poids_height = bbox_poids[3] - bbox_poids[1]
            except AttributeError: _, poids_height = draw_avant.textsize(poids_net_str, font=font_text)
            y_poids = spec_avant["height"] - poids_height - 15 
            self._draw_text_multiline(draw_avant, poids_net_str, (padding_x, y_poids), font_text, spec_avant["width"] - 2 * padding_x, align="center")

            # Use the item_specific_qr_abs_path for the QR code on the label
            qr_path_for_label = item_specific_qr_abs_path
            if pot_type == "Sachet plastique" and spec_avant.get("qr_code_area") and qr_path_for_label:
                self._paste_image_in_area(img_avant, qr_path_for_label, spec_avant["qr_code_area"])

            filename_avant = f"LABEL_AVANT_{label_identifier}.png"
            filepath_avant_abs = os.path.join(self.label_storage_path, filename_avant)
            img_avant.save(filepath_avant_abs)
            url_avant = f"{self.label_url_base}/{filename_avant}"

            if label_spec_pot.get("arriere"):
                # ... (rear label drawing logic as before) ...
                # If using item_specific_qr_abs_path, pass it to paste_image_in_area for rear label QR too
                spec_arriere = label_spec_pot["arriere"]
                img_arriere = Image.new("RGB", (spec_arriere["width"], spec_arriere["height"]), LABEL_BACKGROUND_COLOR)
                draw_arriere = ImageDraw.Draw(img_arriere)
                # ... (add text to rear label) ...
                if spec_arriere.get("qr_code_area") and qr_path_for_label:
                    self._paste_image_in_area(img_arriere, qr_path_for_label, spec_arriere["qr_code_area"])
                
                filename_arriere = f"LABEL_ARRIERE_{label_identifier}.png"
                filepath_arriere_abs = os.path.join(self.label_storage_path, filename_arriere)
                img_arriere.save(filepath_arriere_abs)

            return url_avant
        except Exception as e:
            current_app.logger.error(f"Error generating product label for product ID {product_details.get('product_id')}: {e}", exc_info=True)
            return None

    def _get_product_specific_text_passport(self, espece_truffe, nom_produit_affiche):
        return f"""Nos truffes {espece_truffe} sont cultivées avec un soin extrême... Votre {nom_produit_affiche} est le fruit de notre travail artisanal et engagé."""


    def generate_item_passport(self, item_details: dict) -> str | None:
        """ Generates a product passport HTML file for a specific item UID.
            item_details must contain 'item_uid' and other product-specific info.
            Returns relative_url_path or None. """
        try:
            item_uid = item_details.get('item_uid')
            if not item_uid:
                raise ValueError("item_uid is required to generate an item-specific passport.")

            # General product info from item_details (should be merged by the caller)
            nom_produit = item_details.get("name_fr", "N/A")
            # num_identification is now item_uid for the passport context
            num_identification_display = item_uid # Display the item_uid
            
            num_lot = item_details.get("lot_number", "Non fourni")
            date_conditionnement_raw = item_details.get("date_conditionnement") # Item-specific or batch
            date_conditionnement = format_date_french(date_conditionnement_raw) if date_conditionnement_raw else "N/A"
            ddm_raw = item_details.get("ddm") # Item-specific or batch
            ddm = format_date_french(ddm_raw) if ddm_raw and ddm_raw != "N/A" else "N/A"
            poids_net = item_details.get("weight_grams", "N/A")
            poids_net_str = f"{poids_net} g" if poids_net != "N/A" else "N/A"
            ingredients = item_details.get("ingredients", "Veuillez consulter l'emballage.")
            espece_truffe = item_details.get("truffle_species", "de nos régions") 
            texte_passion = self._get_product_specific_text_passport(espece_truffe, nom_produit)
            logo_tag = f'<img src="{MAISON_TRUVRA_LOGO_URL_PASSPORT}" alt="Logo Maison Trüvra" class="logo" style="max-width:180px; margin-bottom:15px;">'

            # Construct the item-specific passport URL for display (if needed inside passport)
            # The actual serving URL will be like /passport/item/{item_uid}
            # passport_access_url = f"{current_app.config.get('APP_BASE_URL', 'https://www.maisontruvra.com')}/passport/item/{item_uid}"


            html_content = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Passeport de votre Produit - {nom_produit} (UID: {item_uid})</title>
    {self._get_passport_styles()} </head>
<body>
    <div class="container">
        <header>
            {logo_tag}
            <h1>Passeport de votre produit</h1>
            <p>Bienvenu(e) sur la page passeport de votre produit Maison Trüvra.</p>
        </header>
        <section class="intro-text section">
            <p>Chaque produit Maison Trüvra possède un numéro d'identification unique (UID). En scannant le QR code associé à votre article, vous accédez à cette page qui détaille les informations spécifiques de votre achat :</p>
        </section>
        <section class="product-info section">
            <h2>Informations de votre Article</h2>
            <p><strong>Produit :</strong> {nom_produit}</p>
            <p><strong>Numéro d'Identification Unique (UID) :</strong> {num_identification_display}</p>
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
            <h2>Explorez notre site :</h2>
            <a href="https://www.maisontruvra.com/notre-histoire.html" target="_blank">Notre Histoire</a>
            <a href="https://www.maisontruvra.com/" target="_blank">Retour à l'accueil</a>
        </section>
        <footer>
            <p>Merci d'avoir choisi Maison Trüvra !</p>
            <p>Contact : <a href="mailto:{PASSPORT_CONTACT_EMAIL}">{PASSPORT_CONTACT_EMAIL}</a> | Instagram: <a href="https://www.instagram.com/{PASSPORT_INSTAGRAM_HANDLE.replace('@','')}" target="_blank">{PASSPORT_INSTAGRAM_HANDLE}</a>.</p>
            <p><a href="https://www.maisontruvra.com/" target="_blank">www.maisontruvra.com</a></p>
        </footer>
    </div>
</body>
</html>"""
            # Filename is now item_uid specific
            filename = f"passport_item_{item_uid}.html"
            absolute_filepath = os.path.join(self.passport_storage_path, filename)

            with open(absolute_filepath, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            current_app.logger.info(f"Item Passport HTML generated for UID {item_uid}: {absolute_filepath}")
            # This URL needs to match how the public-facing route will serve it,
            # e.g. if served from a '/passport/item/<uid>' route, this path is just for storage reference.
            # The actual URL for the QR code will be constructed by the caller.
            # For consistency, we return the relative path within the asset serving system.
            return f"{self.passport_url_base}/{filename}" 

        except Exception as e:
            current_app.logger.error(f"Error generating HTML passport for item UID {item_details.get('item_uid')}: {e}", exc_info=True)
            return None

    def _get_passport_styles(self):
        # Helper to return the CSS styles for the passport, keeping HTML cleaner
        return """
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 0; background-color: #f9f6f2; color: #3a2d22; line-height: 1.6; }
        .container { max-width: 800px; margin: 20px auto; padding: 25px; background-color: #ffffff; border-radius: 12px; box-shadow: 0 6px 20px rgba(0,0,0,0.08); }
        header { text-align: center; margin-bottom: 30px; padding-bottom: 20px; border-bottom: 2px solid #e0d8ce; }
        h1 { color: #5c4b3e; font-size: 2.2em; margin-bottom: 10px; }
        h2 { color: #7a6a5d; font-size: 1.6em; margin-top: 30px; margin-bottom: 15px; border-bottom: 1px solid #eee; padding-bottom: 8px; }
        p, li { font-size: 1.05em; margin-bottom: 12px; }
        .product-info { background-color: #fdfbf7; padding: 20px; border-radius: 8px; margin-bottom: 25px; border: 1px solid #e0d8ce; }
        .product-info strong { color: #5c4b3e; min-width: 220px; display: inline-block; }
        .section { margin-bottom: 30px; }
        .links-section a { display: block; margin-bottom: 10px; color: #8c6d52; text-decoration: none; font-weight: bold; transition: color 0.3s ease; }
        .links-section a:hover { color: #5c4b3e; }
        footer { text-align: center; margin-top: 40px; padding-top: 25px; border-top: 2px solid #e0d8ce; font-size: 0.95em; color: #7a6a5d; }
        footer a { color: #7a6a5d; text-decoration: none; }
        footer a:hover { text-decoration: underline; }
        @media (max-width: 600px) {
            .container { margin: 10px; padding: 15px; }
            h1 { font-size: 1.8em; } h2 { font-size: 1.4em; }
            .product-info strong { min-width: 150px; }
        }
    </style>
"""
