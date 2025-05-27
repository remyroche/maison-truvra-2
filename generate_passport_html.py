# generate_passport_html.py
import os
# import datetime # Plus nécessaire ici si format_date_french est importé
from utils import format_date_french # Importation de la fonction partagée

# Constante pour le sous-dossier des passeports HTML
HTML_PASSPORT_SUBDIR = "passeports_html"
CONTACT_EMAIL = "contact@maisontruvra.com" 
INSTAGRAM_HANDLE = "@maisontruvra"
# Assurez-vous que le logo est accessible si vous décidez de l'intégrer dynamiquement
# Par exemple, copié dans le dossier du passeport ou lien absolu.
# Pour l'instant, le HTML généré n'inclut pas de tag <img> pour le logo dynamiquement.
# LOGO_PASSPORT_PATH = "image_6be700.png" # Chemin vers le logo si vous l'ajoutez au HTML

def get_product_specific_text(espece_truffe, nom_produit_affiche):
    """Génère le texte spécifique sur la culture des truffes."""
    return f"""Nos truffes {espece_truffe} sont cultivées avec un soin extrême dans nos installations uniques. 
Chez Maison Trüvra, nous maîtrisons chaque paramètre de notre environnement contrôlé pour permettre à chaque truffe 
d'atteindre sa parfaite maturité aromatique, loin des aléas extérieurs. C'est cet artisanat méticuleux et 
cette provenance maîtrisée qui garantissent la pureté et l'intensité de la truffe utilisée pour votre {nom_produit_affiche}.
<br><br>
Nous sommes fiers de cultiver nos truffes en respectant l'environnement, en utilisant des intrants respectueux 
de l'environnement et de l'énergie 100% renouvelable. Votre {nom_produit_affiche} est le fruit de notre travail 
artisanal et engagé."""

def create_and_save_passport(product_data, base_output_dir):
    try:
        html_output_path = os.path.join(base_output_dir, HTML_PASSPORT_SUBDIR)
        if not os.path.exists(html_output_path):
            os.makedirs(html_output_path)

        nom_produit = product_data.get("nom_produit_affiche", "N/A")
        num_identification = product_data.get("numero_identification", "N/A")
        num_lot = product_data.get("numero_lot_manuel") if product_data.get("numero_lot_manuel") else "Non fourni"
        
        date_conditionnement_raw = product_data.get("date_conditionnement", "N/A")
        date_conditionnement = format_date_french(date_conditionnement_raw)
        
        ddm_raw = product_data.get("ddm", "N/A") 
        ddm = format_date_french(ddm_raw) if ddm_raw != "N/A" else "N/A"

        poids_net = product_data.get("poids_net_final_g", "N/A")
        poids_net_str = f"{poids_net} g" if poids_net != "N/A" else "N/A"
        
        ingredients = product_data.get("ingredients_affichage", "Veuillez consulter l'emballage.")
        espece_truffe = product_data.get("espece_truffe", "de nos régions") 

        texte_passion = get_product_specific_text(espece_truffe, nom_produit)
        
        # Optionnel: si vous voulez inclure le logo dans le passeport
        # logo_filename = os.path.basename(LOGO_PASSPORT_PATH)
        # logo_destination_path = os.path.join(html_output_path, logo_filename)
        # if not os.path.exists(logo_destination_path) and os.path.exists(LOGO_PASSPORT_PATH):
        #     import shutil
        #     shutil.copy(LOGO_PASSPORT_PATH, logo_destination_path)
        # logo_tag = f'<img src="{logo_filename}" alt="Logo Maison Trüvra" class="logo">' if os.path.exists(logo_destination_path) else ''
        logo_tag = '<img src="https://www.maisontruvra.com/assets/images/image_6be700.png" alt="Logo Maison Trüvra" class="logo" style="max-width:180px; margin-bottom:15px;">' # Exemple avec URL


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
        /* header img.logo {{ max-width: 180px; margin-bottom:15px; }} */ /* Style pour le logo si utilisé */
        h1 {{ color: #5c4b3e; font-size: 2.2em; margin-bottom: 10px; }}
        h2 {{ color: #7a6a5d; font-size: 1.6em; margin-top: 30px; margin-bottom: 15px; border-bottom: 1px solid #eee; padding-bottom: 8px; }}
        p, li {{ font-size: 1.05em; margin-bottom: 12px; }}
        .product-info {{ background-color: #fdfbf7; padding: 20px; border-radius: 8px; margin-bottom: 25px; border: 1px solid #e0d8ce; }}
        .product-info strong {{ color: #5c4b3e; min-width: 220px; display: inline-block; }}
        .section {{ margin-bottom: 30px; }}
        .links-section a {{ display: block; margin-bottom: 10px; color: #8c6d52; text-decoration: none; font-weight: bold; transition: color 0.3s ease; }}
        .links-section a:hover {{ color: #5c4b3e; }}
        footer {{ text-align: center; margin-top: 40px; padding-top: 25px; border-top: 2px solid #e0d8ce; font-size: 0.95em; color: #7a6a5d; }}
        footer a {{ color: #7a6a5d; text-decoration: none; }}
        footer a:hover {{ text-decoration: underline; }}
        @media (max-width: 600px) {{
            .container {{ margin: 10px; padding: 15px; }}
            h1 {{ font-size: 1.8em; }}
            h2 {{ font-size: 1.4em; }}
            .product-info strong {{ min-width: 150px; }}
        }}
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
            <p>Une question, un commentaire ? Contactez-nous par email à <a href="mailto:{CONTACT_EMAIL}">{CONTACT_EMAIL}</a> 
            ou sur notre compte Instagram <a href="https://www.instagram.com/{INSTAGRAM_HANDLE.replace('@','')}" target="_blank">{INSTAGRAM_HANDLE}</a>.</p>
             <p><a href="https://www.maisontruvra.com/" target="_blank">www.maisontruvra.com</a></p>
        </footer>
    </div>
</body>
</html>
"""
        file_name = f"passeport_{num_identification}.html"
        full_file_path = os.path.join(html_output_path, file_name)

        with open(full_file_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"Page passeport HTML générée : {full_file_path}")
        return full_file_path

    except Exception as e:
        print(f"Erreur lors de la génération de la page HTML du passeport : {e}")
        return None

if __name__ == '__main__':
    mock_product_data_conserve = {
        "nom_produit_affiche": "Brisures de Truffe Noire du Périgord",
        "numero_identification": "MTID-20231027-ABCD",
        "numero_lot_manuel": "LOT2023-10A",
        "date_conditionnement": "2023-10-27",
        "ddm": "2025-10-27",
        "poids_net_final_g": 50,
        "ingredients_affichage": "Truffes Noires Tuber melanosporum, Jus de truffe Tuber melanosporum, Sel",
        "espece_truffe": "Tuber melanosporum"
    }
    mock_product_data_frais = {
        "nom_produit_affiche": "Truffe Noire du Périgord Entière fraîche",
        "numero_identification": "MTID-20231101-EFGH",
        "numero_lot_manuel": "LOT2023-FRAIS01",
        "date_conditionnement": "2023-11-01",
        "ddm": "2023-11-15", # DDM plus court pour frais
        "poids_net_final_g": 30,
        "ingredients_affichage": "100% Tuber melanosporum",
        "espece_truffe": "Tuber melanosporum",
        "date_cueillette": "2023-10-30"
    }
    
    test_output_dir = os.path.join(os.path.dirname(__file__), "output_test_passports")
    if not os.path.exists(test_output_dir):
        os.makedirs(test_output_dir)

    print("Génération d'un exemple de passeport pour conserve...")
    create_and_save_passport(mock_product_data_conserve, test_output_dir)
    
    print("\nGénération d'un exemple de passeport pour produit frais...")
    create_and_save_passport(mock_product_data_frais, test_output_dir)
