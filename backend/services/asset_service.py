# backend/services/asset_service.py
import os
import qrcode
from PIL import Image, ImageDraw, ImageFont
from flask import current_app, url_for
import datetime

# --- Utility function (can be in backend/utils.py or here if very specific) ---
def format_date_french(date_iso_str, fmt="%d/%m/%Y"):
    if not date_iso_str:
        return "N/A"
    try:
        if isinstance(date_iso_str, (datetime.date, datetime.datetime)):
            dt_obj = date_iso_str# backend/services/asset_service.py
import os
import qrcode
from PIL import Image, ImageDraw, ImageFont
from flask import current_app, url_for
import datetime

# (Keep _draw_text_multiline, _paste_image_in_area, format_date_french as is)
def format_date_french(date_iso_str, fmt="%d/%m/%Y"): # Ensure this is available
    if not date_iso_str: return "N/A"
    try:
        if isinstance(date_iso_str, (datetime.date, datetime.datetime)): dt_obj = date_iso_str
        elif 'T' in str(date_iso_str): dt_obj = datetime.date.fromisoformat(str(date_iso_str).split('T')[0])
        else: dt_obj = datetime.date.fromisoformat(str(date_iso_str))
        return dt_obj.strftime(fmt)
    except: return str(date_iso_str)


def generate_qr_code_for_passport(passport_url, product_id):
    if not passport_url or not product_id:
        current_app.logger.error("Passport URL or Product ID missing for QR code generation.")
        return None

    qr_output_dir = current_app.config['QR_CODES_OUTPUT_DIR']
    qr_subdir_from_static = current_app.config['QR_CODES_SUBDIR']
    os.makedirs(qr_output_dir, exist_ok=True)

    qr_filename = f"QR_{product_id.replace('/', '_').replace(' ', '_')}.png"
    qr_filepath_absolute = os.path.join(qr_output_dir, qr_filename)
    qr_filepath_relative_to_static = os.path.join(qr_subdir_from_static, qr_filename).replace("\\", "/")

    try:
        img = qrcode.make(passport_url)
        img.save(qr_filepath_absolute)
        current_app.logger.info(f"QR Code generated for {product_id} at {qr_filepath_absolute}")
        return qr_filepath_relative_to_static
    except Exception as e:
        current_app.logger.error(f"Failed to generate QR code for {product_id}: {e}")
        return None

def generate_product_passport_html_content(product_data_fr, product_data_en):
    # Extract FR data
    nom_produit_fr = product_data_fr.get("name", "N/A")
    num_identification_fr = product_data_fr.get("id", "N/A") # Should be same for both
    num_lot_fr = product_data_fr.get("numero_lot_manuel", "Non fourni")
    date_conditionnement_fr = format_date_french(product_data_fr.get("date_conditionnement", datetime.date.today().isoformat()))
    ddm_fr = format_date_french(product_data_fr.get("ddm", (datetime.date.today() + datetime.timedelta(days=365*2)).isoformat()))
    poids_net_fr = product_data_fr.get("poids_net_final_g", "N/A")
    poids_net_str_fr = f"{poids_net_fr} g" if poids_net_fr not in ["N/A", None] else "N/A"
    ingredients_fr = product_data_fr.get("ingredients_affichage", "Veuillez consulter l'emballage.")
    espece_truffe_fr = product_data_fr.get("species", "de nos régions")
    texte_passion_fr = f"""Nos truffes {espece_truffe_fr} sont cultivées avec un soin extrême dans nos installations uniques.
Chez Maison Trüvra, nous maîtrisons chaque paramètre de notre environnement contrôlé pour permettre à chaque truffe
d'atteindre sa parfaite maturité aromatique. C'est cet artisanat méticuleux qui garantit la pureté et l'intensité
de la truffe utilisée pour votre {nom_produit_fr}.
<br><br>
Nous sommes fiers de cultiver nos truffes en respectant l'environnement, en utilisant des intrants respectueux
et de l'énergie 100% renouvelable."""

    # Extract EN data
    nom_produit_en = product_data_en.get("name", "N/A")
    num_identification_en = product_data_en.get("id", "N/A") # Should be same
    num_lot_en = product_data_en.get("numero_lot_manuel", "Not provided")
    date_conditionnement_en = format_date_french(product_data_en.get("date_conditionnement", datetime.date.today().isoformat()), fmt="%Y-%m-%d") # Standard EN format
    ddm_en = format_date_french(product_data_en.get("ddm", (datetime.date.today() + datetime.timedelta(days=365*2)).isoformat()), fmt="%Y-%m-%d")
    poids_net_en = product_data_en.get("poids_net_final_g", "N/A")
    poids_net_str_en = f"{poids_net_en} g" if poids_net_en not in ["N/A", None] else "N/A"
    ingredients_en = product_data_en.get("ingredients_affichage", "Please see packaging.")
    espece_truffe_en = product_data_en.get("species", "from our regions")
    texte_passion_en = f"""Our {espece_truffe_en} truffles are cultivated with extreme care in our unique facilities.
At Maison Trüvra, we control every parameter of our environment to allow each truffle
to reach its perfect aromatic maturity. This meticulous craftsmanship guarantees the purity and intensity
of the truffle used for your {nom_produit_en}.
<br><br>
We are proud to cultivate our truffles respecting the environment, using eco-friendly inputs
and 100% renewable energy."""


    logo_url = product_data_fr.get("logo_url") or url_for('static', filename=current_app.config.get('LABEL_LOGO_PATH_STATIC_RELATIVE', 'images/image_6be700.png'), _external=True)
    logo_tag = f'<img src="{logo_url}" alt="Logo Maison Trüvra" class="logo" style="max-width:180px; margin-bottom:15px;">'

    contact_email = current_app.config.get('CONTACT_EMAIL', 'contact@example.com')
    instagram_handle = current_app.config.get('INSTAGRAM_HANDLE', "@maisontruvra")
    site_base_url = current_app.config.get('SITE_BASE_URL', 'http://127.0.0.1:5001')

    html_content = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Passeport Produit / Product Passport - {nom_produit_fr} / {nom_produit_en}</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 0; background-color: #f9f6f2; color: #3a2d22; line-height: 1.6; }}
        .container {{ max-width: 800px; margin: 20px auto; padding: 25px; background-color: #ffffff; border-radius: 12px; box-shadow: 0 6px 20px rgba(0,0,0,0.08); }}
        header {{ text-align: center; margin-bottom: 30px; padding-bottom: 20px; border-bottom: 2px solid #e0d8ce; }}
        h1 {{ color: #5c4b3e; font-size: 2.2em; margin-bottom: 10px; }}
        h2 {{ color: #7a6a5d; font-size: 1.6em; margin-top: 30px; margin-bottom: 15px; border-bottom: 1px solid #eee; padding-bottom: 8px; }}
        p, li {{ font-size: 1.05em; margin-bottom: 12px; }}
        .product-info {{ background-color: #fdfbf7; padding: 20px; border-radius: 8px; margin-bottom: 25px; border: 1px solid #e0d8ce; }}
        .product-info strong {{ color: #5c4b3e; min-width: 220px; display: inline-block; }}
        .section {{ margin-bottom: 30px; }}
        .links-section a {{ display: block; margin-bottom: 10px; color: #8c6d52; text-decoration: none; font-weight: bold; }}
        .links-section a:hover {{ color: #5c4b3e; }}
        footer {{ text-align: center; margin-top: 40px; padding-top: 25px; border-top: 2px solid #e0d8ce; font-size: 0.95em; color: #7a6a5d; }}
        footer a {{ color: #7a6a5d; }}
        .lang-toggle {{ text-align: center; margin-bottom: 20px; }}
        .lang-toggle button {{ padding: 8px 15px; margin: 0 5px; cursor: pointer; background-color: #e0d8ce; border: 1px solid #c8bfae; border-radius: 5px; font-weight: bold; }}
        .lang-toggle button.active {{ background-color: #7D6A4F; color: #F5EEDE; }}
        .lang-content {{ display: none; }}
        .lang-content.active {{ display: block; }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            {logo_tag}
            <div class="lang-toggle">
                <button id="btn-fr" onclick="showLang('fr')" class="active">Français</button>
                <button id="btn-en" onclick="showLang('en')">English</button>
            </div>
            <div class="lang-content active" lang="fr"><h1>Passeport de Votre Produit</h1></div>
            <div class="lang-content" lang="en"><h1>Your Product Passport</h1></div>
        </header>

        <div class="lang-content active" lang="fr">
            <section class="product-info section">
                <h2>Informations du Produit</h2>
                <p><strong>Produit :</strong> {nom_produit_fr}</p>
                <p><strong>Numéro d'identification :</strong> {num_identification_fr}</p>
                <p><strong>Numéro de lot :</strong> {num_lot_fr}</p>
                <p><strong>Date de conditionnement :</strong> {date_conditionnement_fr}</p>
                <p><strong>À consommer de préférence avant le :</strong> {ddm_fr}</p>
                <p><strong>Poids Net :</strong> {poids_net_str_fr}</p>
                <p><strong>Ingrédients :</strong> {ingredients_fr}</p>
            </section>
            <section class="passion-text section">
                <h2>Cultivé avec Passion</h2><p>{texte_passion_fr}</p>
            </section>
        </div>

        <div class="lang-content" lang="en">
            <section class="product-info section">
                <h2>Product Information</h2>
                <p><strong>Product:</strong> {nom_produit_en}</p>
                <p><strong>Identification Number:</strong> {num_identification_en}</p>
                <p><strong>Lot Number:</strong> {num_lot_en}</p>
                <p><strong>Packaging Date:</strong> {date_conditionnement_en}</p>
                <p><strong>Best Before Date:</strong> {ddm_en}</p>
                <p><strong>Net Weight:</strong> {poids_net_str_en}</p>
                <p><strong>Ingredients:</strong> {ingredients_en}</p>
            </section>
            <section class="passion-text section">
                <h2>Cultivated with Passion</h2><p>{texte_passion_en}</p>
            </section>
        </div>

        <section class="links-section section">
            <div class="lang-content active" lang="fr">
                <h2>Explorer Plus</h2>
                <a href="{site_base_url}/notre-histoire.html" target="_blank">Notre Histoire</a>
                <a href="{site_base_url}" target="_blank">Retour à l'Accueil</a>
            </div>
            <div class="lang-content" lang="en">
                <h2>Explore More</h2>
                <a href="{site_base_url}/notre-histoire.html?lang=en" target="_blank">Our Story</a>
                <a href="{site_base_url}/index.html?lang=en" target="_blank">Back to Home</a>
            </div>
        </section>
        <footer>
            <div class="lang-content active" lang="fr">
                <p>Merci d'avoir choisi Maison Trüvra !</p>
                <p>Contact : <a href="mailto:{contact_email}">{contact_email}</a> | Instagram: <a href="https://www.instagram.com/{instagram_handle.replace('@','')}" target="_blank">{instagram_handle}</a></p>
                <p><a href="{site_base_url}" target="_blank">{site_base_url.replace('http://','').replace('https://','')}</a></p>
            </div>
            <div class="lang-content" lang="en">
                <p>Thank you for choosing Maison Trüvra!</p>
                <p>Contact: <a href="mailto:{contact_email}">{contact_email}</a> | Instagram: <a href="https://www.instagram.com/{instagram_handle.replace('@','')}" target="_blank">{instagram_handle}</a></p>
                <p><a href="{site_base_url}" target="_blank">{site_base_url.replace('http://','').replace('https://','')}</a></p>
            </div>
        </footer>
    </div>
    <script>
        function showLang(lang) {{
            document.querySelectorAll('.lang-content').forEach(el => {{
                if (el.getAttribute('lang') === lang) {{
                    el.style.display = 'block';
                    el.classList.add('active');
                }} else {{
                    el.style.display = 'none';
                    el.classList.remove('active');
                }}
            }});
            document.querySelectorAll('.lang-toggle button').forEach(btn => {{
                if (btn.id === 'btn-' + lang) {{
                    btn.classList.add('active');
                }} else {{
                    btn.classList.remove('active');
                }}
            }});
            document.documentElement.lang = lang;
        }}
        var userLang = navigator.language || navigator.userLanguage;
        if (userLang.startsWith('en')) {{
            showLang('en');
        }} else {{
            showLang('fr'); // Default to French
        }}
    </script>
</body>
</html>"""
    return html_content

def save_product_passport_html(html_content, product_id):
    passport_output_dir = current_app.config['PASSPORTS_OUTPUT_DIR']
    passport_subdir_from_static = current_app.config['PASSPORTS_SUBDIR']
    os.makedirs(passport_output_dir, exist_ok=True)

    passport_filename = f"passport_{product_id.replace('/', '_').replace(' ', '_')}.html"
    passport_filepath_absolute = os.path.join(passport_output_dir, passport_filename)
    passport_filepath_relative_to_static = os.path.join(passport_subdir_from_static, passport_filename).replace("\\", "/")

    try:
        with open(passport_filepath_absolute, 'w', encoding='utf-8') as f:
            f.write(html_content)
        current_app.logger.info(f"Passport HTML generated for {product_id} at {passport_filepath_absolute}")
        return passport_filepath_relative_to_static
    except Exception as e:
        current_app.logger.error(f"Failed to save passport HTML for {product_id}: {e}")
        return None

# Ensure generate_product_label_image and other helper functions like _draw_text_multiline, _paste_image_in_area are defined above or imported.
# The label generation logic would also need to accept localized data if labels are to be bilingual.
# For simplicity, label generation is omitted from this direct update but would follow a similar pattern.
# Make sure POT_LABEL_CONFIG and PRODUCT_CONTENT_CONFIG are defined or imported if used by label generation.

def _draw_text_multiline(draw, text, position, font, max_width, text_color, spacing=4, align="left"):
    """Internal helper for drawing multiline text, adapted from generate_label.py"""
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
        except AttributeError:
            line_width, _ = draw.textsize(test_line, font=font)

        if line_width <= max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word
    lines.append(current_line)

    y_text = position[1]
    for line in lines:
        x_text = position[0]
        line_actual_width = 0
        line_height = 0
        try:
            bbox_line = draw.textbbox((0,0), line, font=font)
            line_actual_width = bbox_line[2] - bbox_line[0]
            line_height = bbox_line[3] - bbox_line[1]
        except AttributeError: # Fallback
            line_actual_width, line_height = draw.textsize(line, font=font)

        if align == "center":
            x_text = position[0] + (max_width - line_actual_width) / 2
        elif align == "right":
            x_text = position[0] + (max_width - line_actual_width)

        draw.text((x_text, y_text), line, font=font, fill=text_color)
        y_text += line_height + spacing
    return y_text

def _paste_image_in_area(base_image, image_to_paste_path, area_coords):
    """Internal helper for pasting an image into a defined area, adapted from generate_label.py"""
    if image_to_paste_path and os.path.exists(image_to_paste_path):
        try:
            img_to_paste = Image.open(image_to_paste_path)
            area_width = area_coords[2] - area_coords[0]
            area_height = area_coords[3] - area_coords[1]

            img_to_paste.thumbnail((area_width, area_height), Image.Resampling.LANCZOS)

            paste_x = area_coords[0] + (area_width - img_to_paste.width) // 2
            paste_y = area_coords[1] + (area_height - img_to_paste.height) // 2

            if img_to_paste.mode == 'RGBA': # Handle transparency
                base_image.paste(img_to_paste, (paste_x, paste_y), img_to_paste)
            else:
                base_image.paste(img_to_paste, (paste_x, paste_y))
            return True
        except Exception as e_img:
            current_app.logger.error(f"Error loading/pasting image {image_to_paste_path}: {e_img}")
    else:
        if image_to_paste_path: current_app.logger.warning(f"Image not found for pasting: {image_to_paste_path}")
    return False

# --- Product Label Generation ---
POT_LABEL_CONFIG = {
    "default": {
        "avant": {"width": 300, "height": 180, "logo_area": (10, 10, 90, 45)},
        "arriere": {"width": 300, "height": 180, "qr_code_area": (220, 110, 290, 170)},
    },
     "Sachet plastique": {
        "avant": {"width": 350, "height": 200, "logo_area": (15, 15, 100, 50), "qr_code_area": (260, 130, 340, 190)},
        "arriere": None,
    },
}
PRODUCT_CONTENT_CONFIG = { # Simplified, should be populated with actual product specific texts per language
    "default_fr": { "texte_avant_specifique": "Un délice Maison Trüvra.", "ingredients_specifiques": None },
    "default_en": { "texte_avant_specifique": "A Maison Trüvra delight.", "ingredients_specifiques": None }
}


def generate_product_label_image(product_data_fr, product_data_en, qr_code_relative_path=None):
    # This function would also need significant updates for bilingual labels.
    # For simplicity, let's assume it generates a label primarily in French for now,
    # or you might decide to generate two separate labels (label_fr.png, label_en.png).
    # Here, we'll just use French data for a single label.
    label_output_dir = current_app.config['LABELS_OUTPUT_DIR']
    label_subdir_from_static = current_app.config['LABELS_SUBDIR']
    font_path = current_app.config.get('LABEL_FONT_PATH', 'arial.ttf')
    logo_path_abs = current_app.config.get('LABEL_LOGO_PATH')

    os.makedirs(label_output_dir, exist_ok=True)

    product_id = product_data_fr.get("id", "UNKNOWN_ID")
    label_filename = f"label_{product_id.replace('/', '_').replace(' ', '_')}.png" # Potentially add lang suffix
    label_filepath_absolute = os.path.join(label_output_dir, label_filename)
    label_filepath_relative_to_static = os.path.join(label_subdir_from_static, label_filename).replace("\\", "/")

    pot_type = product_data_fr.get("pot_selectionne", "default") # Assuming pot_selectionne is not lang specific
    label_spec_pot = POT_LABEL_CONFIG.get(pot_type, POT_LABEL_CONFIG["default"])

    # Using French data for the label example
    product_name_key_fr = product_data_fr.get("name", "default_fr")
    content_spec_product_fr = PRODUCT_CONTENT_CONFIG.get(product_name_key_fr, PRODUCT_CONTENT_CONFIG["default_fr"])


    text_color = (17, 18, 13)
    bg_color = (245, 238, 222)

    try:
        font_title = ImageFont.truetype(font_path, 18) if os.path.exists(font_path) else ImageFont.load_default()
        font_text = ImageFont.truetype(font_path, 12) if os.path.exists(font_path) else ImageFont.load_default()
        font_small = ImageFont.truetype(font_path, 9) if os.path.exists(font_path) else ImageFont.load_default()
    except IOError:
        current_app.logger.warning(f"Label font not found at {font_path}. Using default.")
        font_title, font_text, font_small = ImageFont.load_default(), ImageFont.load_default(), ImageFont.load_default()

    spec_avant = label_spec_pot["avant"]
    img_avant = Image.new("RGB", (spec_avant["width"], spec_avant["height"]), bg_color)
    draw_avant = ImageDraw.Draw(img_avant)

    current_y = 10
    padding_x = 10

    if spec_avant.get("logo_area") and logo_path_abs:
        if _paste_image_in_area(img_avant, logo_path_abs, spec_avant["logo_area"]):
            current_y = max(current_y, spec_avant["logo_area"][3] + 5)
        else:
            _draw_text_multiline(draw_avant, "Maison Trüvra", (padding_x, current_y), font_text, spec_avant["width"] - 2 * padding_x, text_color, align="center")
            current_y += 20

    nom_produit_affiche_fr = product_data_fr.get("name", "Produit")
    current_y = _draw_text_multiline(draw_avant, nom_produit_affiche_fr, (padding_x, current_y), font_title, spec_avant["width"] - 2 * padding_x, text_color, align="center", spacing=2)
    current_y += 5

    if content_spec_product_fr.get("texte_avant_specifique"):
        current_y = _draw_text_multiline(draw_avant, content_spec_product_fr["texte_avant_specifique"], (padding_x, current_y), font_text, spec_avant["width"] - 2 * padding_x, text_color, align="center", spacing=2)
        current_y += 10

    poids_net_str_fr = f"Poids Net: {product_data_fr.get('poids_net_final_g', 'N/A')}"
    if product_data_fr.get('poids_net_final_g') not in [None, "N/A"]: poids_net_str_fr += "g"

    poids_bbox = draw_avant.textbbox((0,0), poids_net_str_fr, font=font_text)
    poids_height = poids_bbox[3] - poids_bbox[1] if len(poids_bbox) == 4 else 12 # default height
    y_poids = spec_avant["height"] - poids_height - 10
    _draw_text_multiline(draw_avant, poids_net_str_fr, (padding_x, y_poids), font_text, spec_avant["width"] - 2 * padding_x, text_color, align="center")

    if pot_type == "Sachet plastique" and spec_avant.get("qr_code_area") and qr_code_relative_path:
        qr_code_abs_path = os.path.join(current_app.static_folder, qr_code_relative_path)
        _paste_image_in_area(img_avant, qr_code_abs_path, spec_avant["qr_code_area"])

    try:
        img_avant.save(label_filepath_absolute)
        current_app.logger.info(f"Label (avant, FR) générée : {label_filepath_absolute}")
    except Exception as e_save:
        current_app.logger.error(f"Erreur sauvegarde étiquette avant: {e_save}")
        return None

    if label_spec_pot.get("arriere"):
        spec_arriere = label_spec_pot["arriere"]
        img_arriere = Image.new("RGB", (spec_arriere["width"], spec_arriere["height"]), bg_color)
        draw_arriere = ImageDraw.Draw(img_arriere)
        current_y_arr = 10

        ingredients_text_fr = product_data_fr.get("ingredients_affichage", "Voir emballage")
        if content_spec_product_fr.get("ingredients_specifiques"):
            ingredients_text_fr = content_spec_product_fr["ingredients_specifiques"]
        current_y_arr = _draw_text_multiline(draw_arriere, f"Ingrédients: {ingredients_text_fr}", (padding_x, current_y_arr), font_small, spec_arriere["width"] - 2 * padding_x, text_color, spacing=1)

        ddm_str_fr = format_date_french(product_data_fr.get("ddm"))
        current_y_arr = _draw_text_multiline(draw_arriere, f"DDM: {ddm_str_fr}", (padding_x, current_y_arr), font_small, spec_arriere["width"] - 2 * padding_x, text_color, spacing=1)

        current_y_arr = _draw_text_multiline(draw_arriere, f"ID: {product_id}", (padding_x, current_y_arr), font_small, spec_arriere["width"] - 2 * padding_x, text_color, spacing=1)
        if product_data_fr.get("numero_lot_manuel"):
            current_y_arr = _draw_text_multiline(draw_arriere, f"Lot: {product_data_fr['numero_lot_manuel']}", (padding_x, current_y_arr), font_small, spec_arriere["width"] - 2 * padding_x, text_color, spacing=1)

        contact_info = f"Maison Trüvra - {current_app.config.get('CONTACT_EMAIL', 'contact@example.com')}"
        current_y_arr = _draw_text_multiline(draw_arriere, contact_info, (padding_x, current_y_arr + 5), font_small, spec_arriere["width"] - 2 * padding_x, text_color, spacing=1)

        if spec_arriere.get("qr_code_area") and qr_code_relative_path:
            qr_code_abs_path = os.path.join(current_app.static_folder, qr_code_relative_path)
            _paste_image_in_area(img_arriere, qr_code_abs_path, spec_arriere["qr_code_area"])

        label_filepath_arriere_absolute = os.path.join(label_output_dir, f"label_arriere_{product_id.replace('/', '_').replace(' ', '_')}.png")
        try:
            img_arriere.save(label_filepath_arriere_absolute)
            current_app.logger.info(f"Étiquette arrière (FR) générée : {label_filepath_arriere_absolute}")
        except Exception as e_save_arr:
            current_app.logger.error(f"Erreur sauvegarde étiquette arrière: {e_save_arr}")

    return label_filepath_relative_to_static
