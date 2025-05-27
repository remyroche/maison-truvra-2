# backend/auth/routes.py
from flask import Blueprint, request, jsonify, current_app
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import datetime
import sqlite3 

from ..database import get_db
from ..utils import is_valid_email

auth_bp = Blueprint('auth_bp', __name__, url_prefix='/api/auth')

 I have this website. How can I 1/ have it in both French and English and

2/ create a webpage assocaited with the QR code in both FR and EN?

Okay, making your Maison Trüvra website bilingual (French and English) and creating bilingual QR code passport pages involves changes at both the backend (Flask) and frontend (HTML, JavaScript) levels.

Here's a structured approach:
1. Internationalization (i18n) and Localization (l10n) Strategy

This is the process of designing and developing your application to support multiple languages.
Backend (Flask) Modifications:

    Database Schema Updates:
        You'll need to store translatable content for both languages. For your products table (and any other tables with text content like categories, descriptions), add language-specific columns. For example, name becomes name_fr and name_en; short_description becomes short_description_fr and short_description_en, and so on.
        Update backend/database.py (init_db function) to reflect these changes in your CREATE TABLE statements.
        The populate_initial_data function will also need to provide data for these new language-specific columns.

    API Endpoint Adjustments:
        Your API endpoints (in backend/products/routes.py and backend/admin_api/routes.py) will need to handle language preferences.
            Reading Data (GET requests): Endpoints should ideally accept a language parameter (e.g., /api/products?lang=en) or inspect the Accept-Language HTTP header to return data in the requested language. You'll need to adjust your SQL queries to select the correct language columns.
            Writing Data (POST/PUT requests in Admin): The admin API for creating/updating products (backend/admin_api/routes.py) must be modified to accept and save data for both French and English fields (e.g., name_fr, name_en).

    Serving Localized Content:
        Consider using a Flask extension like Flask-Babel for more robust i18n support, especially for handling date formats, numbers, and static text within backend-generated templates if you have any. For a primarily API-driven backend, manually handling language selection in your routes might suffice.

    Asset Generation (Labels & Passports):
        The generate_product_passport_html_content and generate_product_label_image functions in backend/services/asset_service.py (which appears to be the correct location for this logic, though you named the file asset_generators.py in the upload) will need to:
            Accept a language parameter (lang).
            Fetch the correct localized product data from the database based on this language parameter.
            The passport generation will be adapted to create bilingual HTML content directly (see section 2).
            Label generation might require choosing one language for the physical label or designing a compact bilingual label.

Frontend (HTML, CSS, JavaScript) Modifications:

    Language Switching Mechanism:
        Add a language switcher UI element, typically in the header (website/header.html). This could be a dropdown or simple links (FR | EN).
        Store the user's selected language, for example, in localStorage.
        On page load, and when the language is switched, update the content dynamically.

    Localizing Static Text:
        For all hardcoded text in your HTML files (e.g., "Nos Produits", "Mon Compte", "Ajouter au Panier") and in your JavaScript files (e.g., messages in showGlobalMessage), you'll need a translation system.
        Strategy: JSON Locale Files: Create JSON files for each language:
            website/js/locales/fr.json
            website/js/locales/en.json
        Example en.json:
        JSON

{
  "Accueil": "Home",
  "Nos_Produits": "Our Products",
  "Notre_Histoire": "Our Story",
  "Professionnels": "Professionals",
  "Mon_Compte": "My Account",
  "Voir_le_panier": "View Cart",
  "Produit_ajoute_au_panier": "Product added to cart!",
  // ... and so on for all text elements
}

JavaScript Translation Function: In website/js/ui.js (or a new i18n.js), create a function to load the current language's JSON file and another function to get a translated string by its key.
JavaScript

// In ui.js or i18n.js
let currentTranslations = {};
let currentLang = localStorage.getItem('preferredLang') || 'fr'; // Default to French

async function loadTranslations(lang = 'fr') {
    try {
        const response = await fetch(`js/locales/${lang}.json`);
        if (!response.ok) throw new Error(`Could not load ${lang}.json`);
        currentTranslations = await response.json();
        currentLang = lang;
        localStorage.setItem('preferredLang', lang);
        translatePage();
    } catch (error) {
        console.error("Error loading translations:", error);
        // Fallback or error handling
    }
}

function t(key) {
    return currentTranslations[key] || key; // Return key if translation not found
}

function translatePage() {
    document.querySelectorAll('[data-translate-key]').forEach(element => {
        const key = element.getAttribute('data-translate-key');
        element.textContent = t(key);
    });
    // Update other dynamic text, placeholders, titles etc.
    document.title = t(document.title); // If you want to translate page titles
    // Example for placeholders
    const emailNewsletterInput = document.getElementById('email-newsletter');
    if (emailNewsletterInput) {
         emailNewsletterInput.placeholder = t('Votre_adresse_e-mail');
    }
}

HTML Markup: Add data-translate-key attributes to your HTML elements:
HTML

        // In header.html
        <a href="index.html" id="nav-homepage" class="nav-link ..." data-translate-key="Accueil">Accueil</a>
        // In nos-produits.html
        <h1 class="page-header" data-translate-key="Nos_Produits_Titre">Nos Produits d'Exception</h1>

        Initial Load and Switching: Call loadTranslations(localStorage.getItem('preferredLang') || 'fr') on initial page load. Your language switcher should call loadTranslations('en') or loadTranslations('fr') and then translatePage().

    Localizing Dynamic Content (Product Data, etc.):
        Modify your JavaScript functions in website/js/product.js, website/js/cart.js, etc., that fetch and display product data.
        When calling makeApiRequest (in website/js/api.js), include the current language preference (e.g., by adding ?lang=${currentLang} to the endpoint). The backend should then return data in the correct language.
        Ensure your display functions (e.g., WorkspaceAndDisplayProducts, loadProductDetail) use the localized fields returned by the API (e.g., product.name_en instead of product.name).

    Admin Panel Updates:
        In admin/admin_manage_products.html, add input fields for the English versions of product attributes (e.g., "Nom du Produit (EN)", "Description Courte (EN)").
        In website/admin/js/admin_products.js, update handleProductFormSubmit to collect these English fields and send them to the backend. editProduct should also populate these fields when editing.

2. Bilingual QR Code Passport Page

The QR code itself will still point to a single HTML file (e.g., passport_PRODID.html). This HTML file will now contain content for both languages.

    Backend (backend/services/asset_service.py):
        The generate_product_passport_html_content function will need to fetch both French and English details for the given product.
        The HTML template string within this function needs to be structured to include both language versions. You could have:
            Separate sections for each language.
            A simple JavaScript toggle within the passport HTML to switch between languages.
        Example structure for generate_product_passport_html_content:
        Python

        # In backend/services/asset_service.py
        def generate_product_passport_html_content(product_data_fr, product_data_en):
            # product_data_fr might be {'name': 'Truffe Noire Fraîche', 'id': '...', ...}
            # product_data_en might be {'name': 'Fresh Black Truffle', 'id': '...', ...}

            nom_produit_fr = product_data_fr.get("name", "N/A")
            nom_produit_en = product_data_en.get("name", "N/A")
            # ... fetch all other fr and en fields ...

            html_content = f"""<!DOCTYPE html>
        <html lang="fr">
        <head>
            <meta charset="UTF-8">
            <title>Passeport Produit / Product Passport - {nom_produit_fr} / {nom_produit_en}</title>
            <style>
                body {{ font-family: sans-serif; margin: 20px; }}
                .lang-section {{ margin-bottom: 20px; padding: 10px; border: 1px solid #eee; }}
                .lang-en {{ display: none; }} /* Initially hide English */
                .lang-toggle button {{ padding: 5px 10px; margin: 0 5px; cursor: pointer; }}
            </style>
        </head>
        <body>
            <div class="lang-toggle">
                <button onclick="showLang('fr')">Français</button>
                <button onclick="showLang('en')">English</button>
            </div>

            <div id="passport-content-fr" class="lang-section lang-fr">
                <h1>Passeport de Votre Produit</h1>
                <p><strong>Produit :</strong> {nom_produit_fr}</p>
                <p><strong>Numéro d'identification :</strong> {product_data_fr.get("id", "N/A")}</p>
                {'''
                '''}
            </div>

            <div id="passport-content-en" class="lang-section lang-en">
                <h1>Your Product Passport</h1>
                <p><strong>Product :</strong> {nom_produit_en}</p>
                <p><strong>Identification Number :</strong> {product_data_en.get("id", "N/A")}</p>
                {'''
                '''}
            </div>

            <footer>
                <div class="lang-fr">
                    <p>Merci d'avoir choisi Maison Trüvra !</p>
                    <p><a href="{current_app.config.get('SITE_BASE_URL')}/notre-histoire.html" target="_blank">Notre Histoire</a></p>
                </div>
                <div class="lang-en" style="display:none;">
                    <p>Thank you for choosing Maison Trüvra!</p>
                    <p><a href="{current_app.config.get('SITE_BASE_URL')}/our-story.html" target="_blank">Our Story</a></p> 
                </div>
            </footer>

            <script>
                function showLang(lang) {{
                    document.querySelectorAll('.lang-section').forEach(el => el.style.display = 'none');
                    document.querySelectorAll('.lang-' + lang).forEach(el => el.style.display = 'block');
                    if (lang === 'en') {{
                        document.documentElement.lang = 'en';
                    }} else {{
                        document.documentElement.lang = 'fr';
                    }}
                }}
                // Detect browser language or default
                var userLang = navigator.language || navigator.userLanguage;
                if (userLang.startsWith('en')) {{
                    showLang('en');
                }} else {{
                    showLang('fr'); // Default to French
                }}
            </script>
        </body>
        </html>
            """
            return html_content

        The endpoint that calls this function (likely in backend/admin_api/routes.py when a product is created/updated) will need to fetch product_data_fr and product_data_en.

    QR Code Generation:
        No change is needed for the QR code generation itself (generate_qr_code_for_passport). It will still point to the URL of the (now bilingual) HTML passport file.

Summary of Key File Changes:

    backend/database.py: Update table schemas.
    backend/products/routes.py: Modify GET endpoints for localization.
    backend/admin_api/routes.py: Modify GET, POST, PUT endpoints for localization.
    backend/services/asset_service.py: Update passport generation to be bilingual.
    website/header.html: Add language switcher.
    All website/*.html files: Add data-translate-key attributes for static text.
    website/js/locales/fr.json, website/js/locales/en.json: Create these new files.
    website/js/ui.js (or i18n.js): Add translation functions (loadTranslations, t, translatePage).
    website/js/main.js: Initialize loadTranslations and call translatePage on language switch.
    website/js/api.js: Modify makeApiRequest to potentially send language preference.
    website/js/product.js, cart.js, etc.: Update to use localized data from API and t() for UI strings.
    admin/admin_manage_products.html: Add English input fields.
    website/admin/js/admin_products.js: Update form handling for English fields.

This is a substantial update. It's recommended to implement and test these changes incrementally, starting with the backend database and API modifications, then moving to the frontend translation mechanism, and finally updating specific pages and the passport generation.

Send me the updated files

I understand you're looking to make your website bilingual and create bilingual QR code passport pages. This is a significant update that involves changes across many files.

I'll provide the updated versions of the most critical files and the content for the new files you'll need to create. Due to the breadth of changes, I will focus on the core logic for internationalization (i18n). You'll need to apply the pattern of adding data-translate-key attributes and using the translation function t('KEY') throughout your HTML and JavaScript files for all static text.

Here's a breakdown of the updates:

I. New Frontend Files to Create:

    website/js/locales/fr.json (Create this file)
        This will hold your French translations. Start with common terms.
    JSON

{
  "Accueil": "Accueil",
  "Nos_Produits": "Nos Produits",
  "Notre_Histoire": "Notre Histoire",
  "Professionnels": "Professionnels",
  "Mon_Compte": "Mon Compte",
  "Panier": "Panier",
  "Voir_le_panier": "Voir le panier",
  "Produit_ajoute_au_panier": "Produit ajouté au panier !",
  "Continuer_mes_achats": "Continuer mes achats",
  "Finaliser_ma_Commande": "Finaliser ma Commande",
  "Informations_de_Contact": "Informations de Contact",
  "Adresse_e-mail": "Adresse e-mail",
  "Adresse_de_Livraison": "Adresse de Livraison",
  "Prenom": "Prénom",
  "Nom": "Nom",
  "Adresse": "Adresse",
  "Appartement_suite_etc_optionnel": "Appartement, suite, etc. (optionnel)",
  "Code_Postal": "Code Postal",
  "Ville": "Ville",
  "Pays": "Pays",
  "Telephone_optionnel_pour_la_livraison": "Téléphone (optionnel, pour la livraison)",
  "Informations_de_Paiement": "Informations de Paiement",
  "Payer_et_Valider_la_Commande": "Payer et Valider la Commande",
  "Recapitulatif_de_votre_commande": "Récapitulatif de votre commande",
  "Sous-total": "Sous-total:",
  "Livraison": "Livraison:",
  "Total": "Total:",
  "Votre_panier_est_actuellement_vide": "Votre panier est actuellement vide.",
  "Espace_professionnels_Titre": "Espace professionnels",
  "Politique_de_Confidentialite_Titre": "Politique de Confidentialité",
  "Retour_au_catalogue": "Retour au catalogue",
  "Chargement_des_details_du_produit": "Chargement des détails du produit...",
  "Poids": "Poids :",
  "Quantite": "Quantité :",
  "Ajouter_au_Panier": "Ajouter au Panier",
  "Espece": "Espèce :",
  "Origine": "Origine :",
  "Saisonnalite": "Saisonnalité :",
  "Utilisations_ideales": "Utilisations idéales :",
  "Description_Sensorielle": "Description Sensorielle",
  "Suggestions_dAccords": "Suggestions d'Accords",
  "Avis_Clients": "Avis Clients",
  "Aucun_avis_pour_le_moment": "Aucun avis pour le moment. Soyez le premier à partager votre expérience !",
  "Mon_Panier_Titre": "Mon Panier",
  "Resume_de_la_commande": "Résumé de la commande",
  "Passer_la_Commande": "Passer la Commande",
  "Mon_Compte_Titre": "Mon Compte",
  "Deja_client_Connectez-vous": "Déjà client ? Connectez-vous",
  "Mot_de_passe_oublie": "Mot de passe oublié ?",
  "Se_connecter": "Se connecter",
  "Nouveau_client": "Nouveau client ?",
  "Creer_un_compte_texte": "Créez un compte pour suivre vos commandes, enregistrer vos informations et plus encore.",
  "Creer_un_compte_bouton": "Créer un compte",
  "Mon_Espace_Client": "Mon Espace Client",
  "Bonjour": "Bonjour",
  "Email": "Email :",
  "Mes_Commandes": "Mes Commandes",
  "Votre_historique_de_commandes_apparaitra_ici": "Votre historique de commandes apparaîtra ici.",
  "Mes_Informations": "Mes Informations",
  "Modifier_mes_informations": "Modifier mes informations",
  "Se_deconnecter": "Se déconnecter",
  "Merci_pour_votre_commande": "Merci pour votre commande !",
  "Votre_commande_a_ete_passee_avec_succes": "Votre commande a été passée avec succès.",
  "Un_e-mail_de_confirmation_vous_a_ete_envoye": "Un e-mail de confirmation vous a été envoyé.",
  "Numero_de_commande": "Numéro de commande :",
  "Montant_total": "Montant total :",
  "Chargement": "Chargement...",
  "FR": "FR",
  "EN": "EN",
  "Connexion_en_cours": "Connexion en cours...",
  "Deconnecte_message": "Vous avez été déconnecté.",
  "Erreur_lors_du_parsing_des_donnees_utilisateur": "Erreur lors du parsing des données utilisateur:",
  "Authentification_requise": "Authentification requise.",
  "Erreur_HTTP": "Erreur HTTP:",
  "Erreur_API_pour": "Erreur API pour",
  "Une_erreur_reseau_est_survenue": "Une erreur réseau est survenue.",
  "Vous_netes_pas_authentifie": "Vous n'êtes pas authentifié.",
  "Echec_de_la_connexion_Verifiez_vos_identifiants": "Échec de la connexion. Vérifiez vos identifiants.",
  "Erreur_de_connexion_au_serveur": "Erreur de connexion au serveur.",
  "Veuillez_entrer_une_adresse_e-mail_valide": "Veuillez entrer une adresse e-mail valide.",
  "Veuillez_entrer_votre_mot_de_passe": "Veuillez entrer votre mot de passe.",
  "Veuillez_corriger_les_erreurs_dans_le_formulaire": "Veuillez corriger les erreurs dans le formulaire.",
  "Compte_cree_avec_succes_Veuillez_vous_connecter": "Compte créé avec succès ! Veuillez vous connecter.",
  "Erreur_lors_de_linscription": "Erreur lors de l'inscription.",
  "Veuillez_vous_connecter_pour_voir_votre_historique": "Veuillez vous connecter pour voir votre historique.",
  "Chargement_de_lhistorique_des_commandes": "Chargement de l'historique des commandes...",
  "Vous_navez_aucune_commande_pour_le_moment": "Vous n'avez aucune commande pour le moment.",
  "Impossible_de_charger_lhistorique_des_commandes": "Impossible de charger l'historique des commandes:",
  "Enregistrement_en_cours": "Enregistrement en cours...",
  "Merci_Votre_adresse_a_ete_enregistree": "Merci ! Votre adresse a été enregistrée.",
  "Erreur_dinscription": "Erreur d'inscription.",
  "Une_erreur_sest_produite": "Une erreur s'est produite.",
  "Erreur_serveur": "Erreur serveur.",
  "Global_message_toast_elements_not_found": "Global message toast elements not found.",
  "Chargement_des_produits": "Chargement des produits...",
  "Aucun_produit_trouve_dans_cette_categorie": "Aucun produit trouvé dans cette catégorie.",
  "Aucun_produit_a_afficher": "Aucun produit à afficher.",
  "Impossible_de_charger_les_produits": "Impossible de charger les produits.",
  "En_stock": "En stock",
  "Stock_limite": "Stock limité!",
  "Epuise": "Épuisé",
  "A_partir_de": "À partir de",
  "Prix_sur_demande": "Prix sur demande",
  "Voir_le_produit": "Voir le produit",
  "Aucun_produit_specifie": "Aucun produit spécifié.",
  "Indisponible": "Indisponible",
  "Description_sensorielle_a_venir": "Description sensorielle à venir...",
  "Suggestions_daccords_a_venir": "Suggestions d'accords à venir...",
  "Impossible_de_charger_les_details_du_produit": "Impossible de charger les détails du produit:",
  "Details_du_produit_non_charges": "Détails du produit non chargés.",
  "Veuillez_selectionner_une_option_de_poids_valide_et_en_stock": "Veuillez sélectionner une option de poids valide et en stock.",
  "Stock_insuffisant_pour_MAX": "Stock insuffisant pour {productName}. Max: {stock}",
  "Stock_insuffisant_MAX_pour": "Stock insuffisant. Max: {stock} pour {productName}.",
  "Quantite_maximale_de_ atteinte_pour": "Quantité maximale de {stock} atteinte pour {productName}.",
  "Votre_panier_est_vide_Impossible_de_proceder_au_paiement": "Votre panier est vide. Impossible de procéder au paiement.",
  "E-mail_invalide": "E-mail invalide.",
  "Prenom_requis": "Prénom requis.",
  "Nom_requis": "Nom requis.",
  "Adresse_requise": "Adresse requise.",
  "Code_postal_requis": "Code postal requis.",
  "Ville_requise": "Ville requise.",
  "Pays_requis": "Pays requis.",
  "Ce_champ_de_paiement_est_requis": "Ce champ de paiement est requis.",
  "Veuillez_corriger_les_erreurs_dans_le_formulaire_de_paiement": "Veuillez corriger les erreurs dans le formulaire de paiement.",
  "Traitement_de_la_commande": "Traitement de la commande...",
  "Commande_passee_avec_succes_Montant_total": "Commande {orderId} passée avec succès! Montant total: {totalAmount} €",
  "Echec_de_la_commande": "Échec de la commande.",
  "Details_de_la_commande_non_trouves": "Détails de la commande non trouvés. Veuillez vérifier vos e-mails ou contacter le support."
}

website/js/locales/en.json (Create this file)

    This will hold your English translations.

JSON

{
  "Accueil": "Home",
  "Nos_Produits": "Our Products",
  "Notre_Histoire": "Our Story",
  "Professionnels": "Professionals",
  "Mon_Compte": "My Account",
  "Panier": "Cart",
  "Voir_le_panier": "View Cart",
  "Produit_ajoute_au_panier": "Product added to cart!",
  "Continuer_mes_achats": "Continue Shopping",
  "Finaliser_ma_Commande": "Finalize My Order",
  "Informations_de_Contact": "Contact Information",
  "Adresse_e-mail": "Email Address",
  "Adresse_de_Livraison": "Delivery Address",
  "Prenom": "First Name",
  "Nom": "Last Name",
  "Adresse": "Address",
  "Appartement_suite_etc_optionnel": "Apartment, suite, etc. (optional)",
  "Code_Postal": "Postal Code",
  "Ville": "City",
  "Pays": "Country",
  "Telephone_optionnel_pour_la_livraison": "Phone (optional, for delivery)",
  "Informations_de_Paiement": "Payment Information",
  "Payer_et_Valider_la_Commande": "Pay and Confirm Order",
  "Recapitulatif_de_votre_commande": "Your Order Summary",
  "Sous-total": "Subtotal:",
  "Livraison": "Shipping:",
  "Total": "Total:",
  "Votre_panier_est_actuellement_vide": "Your cart is currently empty.",
  "Espace_professionnels_Titre": "Professionals Area",
  "Politique_de_Confidentialite_Titre": "Privacy Policy",
  "Retour_au_catalogue": "Back to catalog",
  "Chargement_des_details_du_produit": "Loading product details...",
  "Poids": "Weight:",
  "Quantite": "Quantity:",
  "Ajouter_au_Panier": "Add to Cart",
  "Espece": "Species:",
  "Origine": "Origin:",
  "Saisonnalite": "Seasonality:",
  "Utilisations_ideales": "Ideal Uses:",
  "Description_Sensorielle": "Sensory Description",
  "Suggestions_dAccords": "Pairing Suggestions",
  "Avis_Clients": "Customer Reviews",
  "Aucun_avis_pour_le_moment": "No reviews yet. Be the first to share your experience!",
  "Mon_Panier_Titre": "My Cart",
  "Resume_de_la_commande": "Order Summary",
  "Passer_la_Commande": "Proceed to Checkout",
  "Mon_Compte_Titre": "My Account",
  "Deja_client_Connectez-vous": "Already a customer? Log in",
  "Mot_de_passe_oublie": "Forgot password?",
  "Se_connecter": "Log In",
  "Nouveau_client": "New customer?",
  "Creer_un_compte_texte": "Create an account to track your orders, save your information, and more.",
  "Creer_un_compte_bouton": "Create Account",
  "Mon_Espace_Client": "My Customer Area",
  "Bonjour": "Hello",
  "Email": "Email:",
  "Mes_Commandes": "My Orders",
  "Votre_historique_de_commandes_apparaitra_ici": "Your order history will appear here.",
  "Mes_Informations": "My Information",
  "Modifier_mes_informations": "Edit my information",
  "Se_deconnecter": "Log Out",
  "Merci_pour_votre_commande": "Thank you for your order!",
  "Votre_commande_a_ete_passee_avec_succes": "Your order has been placed successfully.",
  "Un_e-mail_de_confirmation_vous_a_ete_envoye": "A confirmation email has been sent to you.",
  "Numero_de_commande": "Order Number:",
  "Montant_total": "Total Amount:",
  "Chargement": "Loading...",
  "FR": "FR",
  "EN": "EN",
  "Connexion_en_cours": "Logging in...",
  "Deconnecte_message": "You have been logged out.",
  "Erreur_lors_du_parsing_des_donnees_utilisateur": "Error parsing user data:",
  "Authentification_requise": "Authentication required.",
  "Erreur_HTTP": "HTTP Error:",
  "Erreur_API_pour": "API Error for",
  "Une_erreur_reseau_est_survenue": "A network error occurred.",
  "Vous_netes_pas_authentifie": "You are not authenticated.",
  "Echec_de_la_connexion_Verifiez_vos_identifiants": "Login failed. Check your credentials.",
  "Erreur_de_connexion_au_serveur": "Server connection error.",
  "Veuillez_entrer_une_adresse_e-mail_valide": "Please enter a valid email address.",
  "Veuillez_entrer_votre_mot_de_passe": "Please enter your password.",
  "Veuillez_corriger_les_erreurs_dans_le_formulaire": "Please correct the errors in the form.",
  "Compte_cree_avec_succes_Veuillez_vous_connecter": "Account created successfully! Please log in.",
  "Erreur_lors_de_linscription": "Error during registration.",
  "Veuillez_vous_connecter_pour_voir_votre_historique": "Please log in to see your history.",
  "Chargement_de_lhistorique_des_commandes": "Loading order history...",
  "Vous_navez_aucune_commande_pour_le_moment": "You have no orders at the moment.",
  "Impossible_de_charger_lhistorique_des_commandes": "Could not load order history:",
  "Enregistrement_en_cours": "Saving...",
  "Merci_Votre_adresse_a_ete_enregistree": "Thank you! Your address has been saved.",
  "Erreur_dinscription": "Subscription error.",
  "Une_erreur_sest_produite": "An error occurred.",
  "Erreur_serveur": "Server error.",
  "Global_message_toast_elements_not_found": "Global message toast elements not found.",
  "Chargement_des_produits": "Loading products...",
  "Aucun_produit_trouve_dans_cette_categorie": "No products found in this category.",
  "Aucun_produit_a_afficher": "No products to display.",
  "Impossible_de_charger_les_produits": "Could not load products.",
  "En_stock": "In stock",
  "Stock_limite": "Limited stock!",
  "Epuise": "Out of stock",
  "A_partir_de": "From",
  "Prix_sur_demande": "Price on request",
  "Voir_le_produit": "View product",
  "Aucun_produit_specifie": "No product specified.",
  "Indisponible": "Unavailable",
  "Description_sensorielle_a_venir": "Sensory description coming soon...",
  "Suggestions_daccords_a_venir": "Pairing suggestions coming soon...",
  "Impossible_de_charger_les_details_du_produit": "Could not load product details:",
  "Details_du_produit_non_charges": "Product details not loaded.",
  "Veuillez_selectionner_une_option_de_poids_valide_et_en_stock": "Please select a valid and in-stock weight option.",
  "Stock_insuffisant_pour_MAX": "Insufficient stock for {productName}. Max: {stock}",
  "Stock_insuffisant_MAX_pour": "Insufficient stock. Max: {stock} for {productName}.",
  "Quantite_maximale_de_ atteinte_pour": "Maximum quantity of {stock} reached for {productName}.",
  "Votre_panier_est_vide_Impossible_de_proceder_au_paiement": "Your cart is empty. Cannot proceed to payment.",
  "E-mail_invalide": "Invalid email.",
  "Prenom_requis": "First name required.",
  "Nom_requis": "Last name required.",
  "Adresse_requise": "Address required.",
  "Code_postal_requis": "Postal code required.",
  "Ville_requise": "City required.",
  "Pays_requis": "Country required.",
  "Ce_champ_de_paiement_est_requis": "This payment field is required.",
  "Veuillez_corriger_les_erreurs_dans_le_formulaire_de_paiement": "Please correct the errors in the payment form.",
  "Traitement_de_la_commande": "Processing order...",
  "Commande_passee_avec_succes_Montant_total": "Order {orderId} placed successfully! Total amount: {totalAmount} €",
  "Echec_de_la_commande": "Order failed.",
  "Details_de_la_commande_non_trouves": "Order details not found. Please check your emails or contact support."
}

website/js/i18n.js (Create this new file for translation logic)
JavaScript

    // website/js/i18n.js
    let currentTranslations = {};
    let currentLang = localStorage.getItem('maisonTruvraLang') || 'fr'; // Default to French

    async function loadTranslations(lang = 'fr') {
        try {
            const response = await fetch(`js/locales/<span class="math-inline">\{lang\}\.json?v\=</span>{new Date().getTime()}`); // Cache buster
            if (!response.ok) {
                console.error(`Could not load ${lang}.json. Status: ${response.status}`);
                // Fallback to French if English fails or vice-versa, or load default empty
                if (lang !== 'fr') return loadTranslations('fr'); // Attempt to load default
                currentTranslations = {}; // Load empty if default also fails
                return;
            }
            currentTranslations = await response.json();
            currentLang = lang;
            localStorage.setItem('maisonTruvraLang', lang);
            document.documentElement.lang = currentLang; // Set lang attribute on <html>
            translatePageElements();
        } catch (error) {
            console.error("Error loading translations for " + lang + ":", error);
            if (lang !== 'fr') { // Avoid infinite loop if fr.json is missing
                console.warn("Falling back to French translations.");
                await loadTranslations('fr');
            } else {
                currentTranslations = {}; // Ensure it's an object
            }
        }
    }

    function t(key, replacements = {}) {
        let translation = currentTranslations[key] || key;
        for (const placeholder in replacements) {
            translation = translation.replace(new RegExp(`{${placeholder}}`, 'g'), replacements[placeholder]);
        }
        return translation;
    }

    function translatePageElements() {
        document.querySelectorAll('[data-translate-key]').forEach(element => {
            const key = element.getAttribute('data-translate-key');
            if (key) {
                const translatedText = t(key);
                if (element.tagName === 'INPUT' || element.tagName === 'TEXTAREA') {
                    if (element.type === 'submit' || element.type === 'button') {
                        element.value = translatedText;
                    } else {
                        element.placeholder = translatedText;
                    }
                } else if (element.hasAttribute('title')) {
                     element.title = translatedText;
                }
                else {
                    element.innerHTML = translatedText; // Use innerHTML to allow for simple HTML in translations if needed
                }
            }
        });
        // Special handling for page titles if needed
        const pageTitleKey = document.body.getAttribute('data-page-title-key');
        if (pageTitleKey) {
            document.title = t(pageTitleKey);
        }
    }

    // Function to change language and reload translations
    async function setLanguage(lang) {
        await loadTranslations(lang);
        // Potentially re-initialize parts of the page that depend on language
        // For example, if product lists are already loaded, they might need to be re-fetched or re-rendered.
        // This depends on how your dynamic content loading is structured.
        // A simple approach for now is that dynamic content fetching should already include language.
        if (typeof updateLoginState === "function") updateLoginState(); // To update "Mon Compte (Prénom)"
        if (document.body.id === 'page-nos-produits' && typeof fetchAndDisplayProducts === "function") {
            const activeFilter = document.querySelector('#product-categories-filter button.filter-active');
            fetchAndDisplayProducts(activeFilter ? activeFilter.dataset.category : 'all');
        }
        if (document.body.id === 'page-produit-detail' && typeof loadProductDetail === "function") {
            loadProductDetail();
        }
        if (document.body.id === 'page-panier' && typeof displayCartItems === "function") {
            displayCartItems(); // Re-render cart items if text like "Remove" needs translation
        }
         if (document.body.id === 'page-compte' && typeof displayAccountDashboard === "function") {
            displayAccountDashboard();
        }
    }

    // Expose functions to global scope if needed, or handle through event listeners in main.js
    window.setLanguage = setLanguage;
    window.t = t;
    window.loadTranslations = loadTranslations;
    window.translatePageElements = translatePageElements;
    window.getCurrentLang = () => currentLang;

II. Updated Backend Files:

    backend/database.py
        Modify products table and init_db and populate_initial_data.
    Python

# backend/database.py
import sqlite3
import os
import datetime
from werkzeug.security import generate_password_hash
from flask import current_app

def get_db():
    db_path = current_app.config['DATABASE_PATH']
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    return db

def init_db_command(app_context):
    with app_context:
        init_db()
        current_app.logger.info("Base de données initialisée via la commande CLI.")

def init_db():
    db = get_db()
    cursor = db.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        nom TEXT,
        prenom TEXT,
        is_admin BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS newsletter_subscriptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        nom TEXT,
        prenom TEXT,
        consentement TEXT CHECK(consentement IN ('Y', 'N')) NOT NULL,
        subscribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS products (
        id TEXT PRIMARY KEY,
        name_fr TEXT NOT NULL,
        name_en TEXT NOT NULL,
        category TEXT NOT NULL,
        short_description_fr TEXT,
        short_description_en TEXT,
        long_description_fr TEXT,
        long_description_en TEXT,
        image_url_main TEXT,
        image_urls_thumb TEXT,
        species_fr TEXT,
        species_en TEXT,
        origin_fr TEXT,
        origin_en TEXT,
        seasonality_fr TEXT,
        seasonality_en TEXT,
        ideal_uses_fr TEXT,
        ideal_uses_en TEXT,
        sensory_description_fr TEXT,
        sensory_description_en TEXT,
        pairing_suggestions_fr TEXT,
        pairing_suggestions_en TEXT,
        base_price REAL,
        stock_quantity INTEGER DEFAULT 0,
        is_published BOOLEAN DEFAULT TRUE,
        passport_url TEXT,
        qr_code_path TEXT,
        label_path TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS update_products_updated_at
        AFTER UPDATE ON products FOR EACH ROW
        BEGIN
            UPDATE products SET updated_at = CURRENT_TIMESTAMP WHERE id = OLD.id;
        END;
    """)

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS product_weight_options (
        option_id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id TEXT NOT NULL,
        weight_grams INTEGER NOT NULL,
        price REAL NOT NULL,
        stock_quantity INTEGER DEFAULT 0,
        FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE CASCADE
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS orders (
        order_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        customer_email TEXT NOT NULL,
        customer_name TEXT,
        shipping_address TEXT NOT NULL,
        total_amount REAL NOT NULL,
        order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status TEXT DEFAULT 'Pending',
        tracking_number TEXT,
        carrier TEXT,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS order_items (
        item_id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        product_id TEXT NOT NULL,
        product_name_fr TEXT NOT NULL, 
        product_name_en TEXT NOT NULL, 
        quantity INTEGER NOT NULL,
        price_at_purchase REAL NOT NULL,
        variant TEXT,
        variant_option_id INTEGER,
        FOREIGN KEY (order_id) REFERENCES orders (order_id) ON DELETE CASCADE,
        FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE RESTRICT,
        FOREIGN KEY (variant_option_id) REFERENCES product_weight_options (option_id) ON DELETE RESTRICT
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS inventory_movements (
        movement_id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id TEXT NOT NULL,
        variant_option_id INTEGER,
        quantity_change INTEGER NOT NULL,
        movement_type TEXT NOT NULL CHECK(movement_type IN ('initial_stock', 'addition', 'vente', 'ajustement_manuel', 'creation_lot', 'retour_client', 'perte', 'correction')),
        movement_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        order_id INTEGER,
        notes TEXT,
        user_id INTEGER,
        FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE CASCADE,
        FOREIGN KEY (variant_option_id) REFERENCES product_weight_options (option_id) ON DELETE CASCADE,
        FOREIGN KEY (order_id) REFERENCES orders (order_id) ON DELETE SET NULL,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS order_notes (
        note_id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        admin_user_id INTEGER,
        content TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (order_id) REFERENCES orders (order_id) ON DELETE CASCADE,
        FOREIGN KEY (admin_user_id) REFERENCES users (id) ON DELETE SET NULL
    )
    ''')

    db.commit()
    current_app.logger.info("Base de données initialisée (tables vérifiées/créées avec champs localisés).")

def populate_initial_data():
    db = get_db()
    cursor = db.cursor()
    populated_something = False

    admin_email_config = current_app.config.get('ADMIN_EMAIL', 'admin@maisontruvra.com')
    cursor.execute("SELECT COUNT(*) FROM users WHERE email = ?", (admin_email_config,))
    if cursor.fetchone()[0] == 0:
        try:
            admin_password_config = current_app.config.get('ADMIN_PASSWORD', 'SecureAdminP@ss1')
            cursor.execute(
                "INSERT INTO users (email, password_hash, nom, prenom, is_admin) VALUES (?, ?, ?, ?, ?)",
                (admin_email_config, generate_password_hash(admin_password_config), "Admin", "MaisonTrüvra", True)
            )
            current_app.logger.info(f"Utilisateur Admin créé ({admin_email_config}).")
            populated_something = True
        except sqlite3.IntegrityError:
            current_app.logger.info("L'utilisateur Admin existe déjà.")

    cursor.execute("SELECT COUNT(*) FROM products")
    if cursor.fetchone()[0] == 0:
        products_data = [
            {
                "id": "tuber-melanosporum-frais",
                "name_fr": "Truffe Noire Fraîche (Tuber Melanosporum)", "name_en": "Fresh Black Truffle (Tuber Melanosporum)",
                "category": "Fresh Truffles",
                "short_description_fr": "Le diamant noir de la gastronomie, récolté à pleine maturité.",
                "short_description_en": "The black diamond of gastronomy, harvested at full maturity.",
                "image_url_main": "https://placehold.co/600x500/7D6A4F/F5EEDE?text=Truffe+Noire",
                "base_price": None, "stock_quantity": 0, "is_published": True,
                "long_description_fr": "Description longue en français.", "long_description_en": "Long description in English."
                # ... add other _fr and _en fields
            },
            {
                "id": "huile-truffe-noire",
                "name_fr": "Huile d'Olive Vierge Extra à la Truffe Noire", "name_en": "Extra Virgin Olive Oil with Black Truffle",
                "category": "Truffle Oils",
                "short_description_fr": "Notre huile d'olive infusée avec l'arôme délicat de la truffe noire.",
                "short_description_en": "Our olive oil infused with the delicate aroma of black truffle.",
                "image_url_main": "https://placehold.co/400x300/A28C6A/F5EEDE?text=Huile+Truffe",
                "base_price": 25.00, "stock_quantity": 50, "is_published": True,
                "long_description_fr": "Description longue en français pour huile.", "long_description_en": "Long description in English for oil."
                # ... add other _fr and _en fields
            }
        ]
        for p_data in products_data:
            # Ensure all localized fields are present in p_data or provide defaults
            p_data.setdefault('image_urls_thumb', '[]')
            for lang in ['fr', 'en']:
                p_data.setdefault(f'species_{lang}', None)
                p_data.setdefault(f'origin_{lang}', None)
                p_data.setdefault(f'seasonality_{lang}', None)
                p_data.setdefault(f'ideal_uses_{lang}', None)
                p_data.setdefault(f'sensory_description_{lang}', None)
                p_data.setdefault(f'pairing_suggestions_{lang}', None)
            p_data.setdefault('passport_url', None)
            p_data.setdefault('qr_code_path', None)
            p_data.setdefault('label_path', None)


            cursor.execute('''
            INSERT INTO products (
                id, name_fr, name_en, category, short_description_fr, short_description_en,
                long_description_fr, long_description_en, image_url_main, image_urls_thumb,
                species_fr, species_en, origin_fr, origin_en, seasonality_fr, seasonality_en,
                ideal_uses_fr, ideal_uses_en, sensory_description_fr, sensory_description_en,
                pairing_suggestions_fr, pairing_suggestions_en, base_price, stock_quantity, is_published,
                passport_url, qr_code_path, label_path, updated_at
            ) VALUES (
                :id, :name_fr, :name_en, :category, :short_description_fr, :short_description_en,
                :long_description_fr, :long_description_en, :image_url_main, :image_urls_thumb,
                :species_fr, :species_en, :origin_fr, :origin_en, :seasonality_fr, :seasonality_en,
                :ideal_uses_fr, :ideal_uses_en, :sensory_description_fr, :sensory_description_en,
                :pairing_suggestions_fr, :pairing_suggestions_en, :base_price, :stock_quantity, :is_published,
                :passport_url, :qr_code_path, :label_path, CURRENT_TIMESTAMP
            )
            ''', p_data)
            if p_data['base_price'] is not None and p_data['stock_quantity'] > 0:
                record_stock_movement(cursor, p_data['id'], p_data['stock_quantity'], 'initial_stock', notes="Stock initial")
        current_app.logger.info("Données initiales des produits (localisées) peuplées.")
        populated_something = True

    cursor.execute("SELECT COUNT(*) FROM product_weight_options WHERE product_id = 'tuber-melanosporum-frais'")
    if cursor.fetchone()[0] == 0:
        weight_options_data = [
            {"product_id": "tuber-melanosporum-frais", "weight_grams": 20, "price": 75.00, "stock_quantity": 10},
            {"product_id": "tuber-melanosporum-frais", "weight_grams": 30, "price": 110.00, "stock_quantity": 15},
        ]
        for wo_data in weight_options_data:
            cursor.execute('''
            INSERT INTO product_weight_options (product_id, weight_grams, price, stock_quantity)
            VALUES (:product_id, :weight_grams, :price, :stock_quantity)
            ''', wo_data)
            record_stock_movement(cursor, wo_data['product_id'], wo_data['stock_quantity'], 'initial_stock',
                                  variant_option_id=cursor.lastrowid,
                                  notes=f"Stock initial variante {wo_data['weight_grams']}g")
        current_app.logger.info("Options de poids initiales pour 'tuber-melanosporum-frais' peuplées.")
        populated_something = True

    if populated_something:
        db.commit()

def record_stock_movement(db_cursor, product_id, quantity_change, movement_type,
                          variant_option_id=None, order_id=None, notes=None, user_id=None):
    current_stock = 0
    new_stock = 0

    if variant_option_id:
        db_cursor.execute("SELECT stock_quantity FROM product_weight_options WHERE option_id = ? AND product_id = ?",
                          (variant_option_id, product_id))
        current_stock_row = db_cursor.fetchone()
        if not current_stock_row:
            raise ValueError(f"Option de produit (ID: {variant_option_id} pour Produit ID: {product_id}) non trouvée.")

        current_stock = current_stock_row['stock_quantity']
        new_stock = current_stock + quantity_change

        if new_stock < 0:
             raise ValueError(f"Stock insuffisant pour l'option de produit ID {variant_option_id}. Actuel: {current_stock}, Tentative de retrait: {abs(quantity_change)}")

        db_cursor.execute("UPDATE product_weight_options SET stock_quantity = ? WHERE option_id = ?",
                       (new_stock, variant_option_id))
    else:
        db_cursor.execute("SELECT stock_quantity, base_price FROM products WHERE id = ?", (product_id,))
        current_stock_row = db_cursor.fetchone()
        if not current_stock_row:
            raise ValueError(f"Produit (ID: {product_id}) non trouvé.")
        if current_stock_row['base_price'] is None and movement_type != 'initial_stock':
             db_cursor.execute("SELECT COUNT(*) FROM product_weight_options WHERE product_id = ?", (product_id,))
             if db_cursor.fetchone()[0] > 0: # If variants exist
                raise ValueError(f"Tentative de modification de stock sur produit principal '{product_id}' qui est géré par variantes. Ajustez les variantes.")

        current_stock = current_stock_row['stock_quantity']
        new_stock = current_stock + quantity_change

        if new_stock < 0:
            raise ValueError(f"Stock insuffisant pour le produit ID {product_id}. Actuel: {current_stock}, Tentative de retrait: {abs(quantity_change)}")

        db_cursor.execute("UPDATE products SET stock_quantity = ? WHERE id = ?",
                       (new_stock, product_id))

    db_cursor.execute('''
        INSERT INTO inventory_movements (product_id, variant_option_id, quantity_change, movement_type, order_id, notes, user_id, movement_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    ''', (product_id, variant_option_id, quantity_change, movement_type, order_id, notes, user_id))

    current_app.logger.info(f"Mouvement de stock: Produit {product_id}, Variante {variant_option_id or 'N/A'}, Qté Changement {quantity_change}, Type {movement_type}, Nouveau Stock: {new_stock}, User: {user_id or 'System'}")

backend/products/routes.py

    Adapt get_all_products and get_product_by_id to select and return localized fields based on a lang query parameter.

Python

# backend/products/routes.py
from flask import Blueprint, request, jsonify, current_app
import json
from ..database import get_db

products_bp = Blueprint('products_bp', __name__, url_prefix='/api/products')

def get_localized_field(lang, field_name_fr, field_name_en, row_data):
    """Helper to get localized field, defaulting to French if lang='en' is missing."""
    if lang == 'en' and row_data.get(field_name_en):
        return row_data[field_name_en]
    return row_data.get(field_name_fr) # Default to French

@products_bp.route('', methods=['GET'])
def get_all_products():
    db = None
    try:
        lang = request.args.get('lang', 'fr') # Default to French
        db = get_db()
        cursor = db.cursor()
        category_filter = request.args.get('category')

        # Select all necessary localized and non-localized fields
        query = f"""SELECT id, name_{lang} as name, category,
                    short_description_{lang} as short_description,
                    image_url_main, base_price, stock_quantity
                    FROM products"""
        params = []

        if category_filter:
            query += " WHERE category = ?"
            params.append(category_filter)

        cursor.execute(query, params)
        products_rows = cursor.fetchall()

        products_list = []
        for row in products_rows:
            product_dict = dict(row)
            if product_dict['base_price'] is None:
                cursor.execute("SELECT MIN(price) as min_price, SUM(stock_quantity) as total_stock FROM product_weight_options WHERE product_id = ?", (product_dict['id'],))
                option_info = cursor.fetchone()
                product_dict['starting_price'] = option_info['min_price'] if option_info and option_info['min_price'] is not None else "N/A"
                product_dict['stock_quantity'] = option_info['total_stock'] if option_info and option_info['total_stock'] is not None else 0
            else:
                product_dict['starting_price'] = product_dict['base_price']
            products_list.append(product_dict)

        return jsonify(products_list)
    except Exception as e:
        current_app.logger.error(f"Erreur lors de la récupération des produits (lang={lang}): {e}", exc_info=True)
        return jsonify({"success": False, "message": "Erreur serveur lors de la récupération des produits."}), 500
    finally:
        if db:
            db.close()

@products_bp.route('/<string:product_id>', methods=['GET'])
def get_product_by_id(product_id):
    db = None
    try:
        lang = request.args.get('lang', 'fr') # Default to French
        db = get_db()
        cursor = db.cursor()

        # Dynamically select localized fields
        fields_to_select = [
            "id", f"name_{lang} as name", "category",
            f"short_description_{lang} as short_description",
            f"long_description_{lang} as long_description",
            "image_url_main", "image_urls_thumb",
            f"species_{lang} as species", f"origin_{lang} as origin",
            f"seasonality_{lang} as seasonality", f"ideal_uses_{lang} as ideal_uses",
            f"sensory_description_{lang} as sensory_description",
            f"pairing_suggestions_{lang} as pairing_suggestions",
            "base_price", "stock_quantity", "is_published",
            "passport_url", "qr_code_path", "label_path"
        ]
        query = f"SELECT {', '.join(fields_to_select)} FROM products WHERE id = ?"
        cursor.execute(query, (product_id,))
        product_row = cursor.fetchone()

        if product_row is None:
            return jsonify({"success": False, "message": "Produit non trouvé"}), 404

        product_dict = dict(product_row)

        if product_dict['category'] == 'Fresh Truffles' or product_dict['base_price'] is None:
            cursor.execute("SELECT option_id, weight_grams, price, stock_quantity FROM product_weight_options WHERE product_id = ? ORDER BY weight_grams ASC", (product_id,))
            weight_options_rows = cursor.fetchall()
            product_dict['weight_options'] = [dict(row_option) for row_option in weight_options_rows]
            product_dict['stock_quantity'] = sum(wo['stock_quantity'] for wo in product_dict['weight_options'])

        if product_dict.get('image_urls_thumb'):
            try:
                product_dict['image_urls_thumb'] = json.loads(product_dict['image_urls_thumb'])
            except (json.JSONDecodeError, TypeError):
                product_dict['image_urls_thumb'] = []

        return jsonify(product_dict)
    except Exception as e:
        current_app.logger.error(f"Erreur lors de la récupération du produit {product_id} (lang={lang}): {e}", exc_info=True)
        return jsonify({"success": False, "message": "Erreur serveur lors de la récupération du produit."}), 500
    finally:
        if db:
            db.close()

backend/services/asset_service.py

    Modify generate_product_passport_html_content to accept product data for both languages.

Python

# backend/services/asset_service.py
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

backend/admin_api/routes.py

    Update create_product and update_product to handle new _fr and _en fields.
    When calling generate_product_passport_html_content, you'll need to prepare product_data_fr and product_data_en dictionaries.

Python

    # backend/admin_api/routes.py
    from flask import Blueprint, request, jsonify, current_app, url_for, g
    from ..database import get_db, record_stock_movement
    from ..auth.routes import admin_required
    import sqlite3
    import json
    import os
    import datetime

    from ..services.asset_service import (
        generate_product_passport_html_content,
        save_product_passport_html,
        generate_qr_code_for_passport,
        generate_product_label_image
    )

    admin_api_bp = Blueprint('admin_api_bp_routes', __name__) # Ensure this name is unique

    @admin_api_bp.route('/products', methods=['POST'])
    @admin_required
    def create_product():
        data = request.get_json()
        # Ensure all required base fields and at least one language for name are present
        required_fields = ['id', 'category', 'image_url_main'] # Base requirements
        if not all(field in data for field in required_fields) or not (data.get('name_fr') or data.get('name_en')):
            return jsonify({"success": False, "message": "Champs requis manquants (id, category, image_url_main, name_fr ou name_en)."}), 400

        product_id = data['id']
        # Prepare localized data, defaulting one to the other if one is missing
        name_fr = data.get('name_fr', data.get('name_en', 'Nom non fourni'))
        name_en = data.get('name_en', data.get('name_fr', 'Name not provided'))
        short_description_fr = data.get('short_description_fr', data.get('short_description_en', ''))
        short_description_en = data.get('short_description_en', data.get('short_description_fr', ''))
        # ... repeat for all translatable fields ...
        long_description_fr = data.get('long_description_fr', data.get('long_description_en', ''))
        long_description_en = data.get('long_description_en', data.get('long_description_fr', ''))
        species_fr = data.get('species_fr', data.get('species_en', None))
        species_en = data.get('species_en', data.get('species_fr', None))
        origin_fr = data.get('origin_fr', data.get('origin_en', None))
        origin_en = data.get('origin_en', data.get('origin_fr', None))
        seasonality_fr = data.get('seasonality_fr', data.get('seasonality_en', None))
        seasonality_en = data.get('seasonality_en', data.get('seasonality_fr', None))
        ideal_uses_fr = data.get('ideal_uses_fr', data.get('ideal_uses_en', None))
        ideal_uses_en = data.get('ideal_uses_en', data.get('ideal_uses_fr', None))
        sensory_description_fr = data.get('sensory_description_fr', data.get('sensory_description_en', None))
        sensory_description_en = data.get('sensory_description_en', data.get('sensory_description_fr', None))
        pairing_suggestions_fr = data.get('pairing_suggestions_fr', data.get('pairing_suggestions_en', None))
        pairing_suggestions_en = data.get('pairing_suggestions_en', data.get('pairing_suggestions_fr', None))

        category = data['category']
        image_url_main = data['image_url_main']
        image_urls_thumb_list = data.get('image_urls_thumb', [])
        image_urls_thumb_json = json.dumps(image_urls_thumb_list) if isinstance(image_urls_thumb_list, list) else '[]'

        base_price = data.get('base_price')
        initial_stock_quantity = int(data.get('initial_stock_quantity', 0))
        is_published = bool(data.get('is_published', True))
        weight_options = data.get('weight_options', [])

        # Asset data preparation
        numero_lot_manuel = data.get('numero_lot_manuel', f"LOT-{product_id}-{datetime.date.today().strftime('%Y%m%d')}")
        date_conditionnement = data.get('date_conditionnement', datetime.date.today().isoformat())
        default_ddm = (datetime.date.today() + datetime.timedelta(days=365*2)).isoformat()
        ddm = data.get('ddm', default_ddm)
        poids_net_final_g = data.get('specific_weight_for_label', "Voir emballage" if weight_options else "N/A")


        # Create dicts for passport generation
        asset_product_data_fr = {
            "id": product_id, "name": name_fr, "species": species_fr, "origin": origin_fr,
            "seasonality": seasonality_fr, "ideal_uses": ideal_uses_fr,
            "sensory_description": sensory_description_fr, "pairing_suggestions": pairing_suggestions_fr,
            "numero_lot_manuel": numero_lot_manuel, "date_conditionnement": date_conditionnement, "ddm": ddm,
            "poids_net_final_g": poids_net_final_g,
            "ingredients_affichage": data.get('ingredients_for_label_fr', "Consultez l'emballage du produit."),
            "logo_url": url_for('static', filename=current_app.config.get('LABEL_LOGO_PATH_STATIC_RELATIVE', 'images/image_6be700.png'), _external=True)
        }
        asset_product_data_en = {
            "id": product_id, "name": name_en, "species": species_en, "origin": origin_en,
            "seasonality": seasonality_en, "ideal_uses": ideal_uses_en,
            "sensory_description": sensory_description_en, "pairing_suggestions": pairing_suggestions_en,
            "numero_lot_manuel": numero_lot_manuel, "date_conditionnement": date_conditionnement, "ddm": ddm,
            "poids_net_final_g": poids_net_final_g, # Assuming poids_net_final_g is not language specific for this asset
            "ingredients_affichage": data.get('ingredients_for_label_en', "Please see packaging."),
            "logo_url": url_for('static', filename=current_app.config.get('LABEL_LOGO_PATH_STATIC_RELATIVE', 'images/image_6be700.png'), _external=True)
        }


        db = None
        try:
            db = get_db()
            cursor = db.cursor()
            admin_user_id = getattr(g, 'admin_user_id', None)

            cursor.execute("SELECT id FROM products WHERE id = ?", (product_id,))
            if cursor.fetchone():
                return jsonify({"success": False, "message": f"L'ID produit '{product_id}' existe déjà."}), 409

            passport_public_url, qr_code_relative_path, label_relative_path = None, None, None
            passport_html_content = generate_product_passport_html_content(asset_product_data_fr, asset_product_data_en) # Pass both lang data
            passport_file_rel_path = save_product_passport_html(passport_html_content, product_id)

            if passport_file_rel_path:
                passport_public_url = f"{current_app.config['PASSPORT_BASE_URL'].rstrip('/')}/{os.path.basename(passport_file_rel_path)}"
                qr_code_relative_path = generate_qr_code_for_passport(passport_public_url, product_id)
                if qr_code_relative_path:
                    # Label generation might also need localized data or a strategy for bilingual labels
                    label_relative_path = generate_product_label_image(asset_product_data_fr, asset_product_data_en, qr_code_relative_path)


            cursor.execute("""
                INSERT INTO products (
                    id, name_fr, name_en, category,
                    short_description_fr, short_description_en,
                    long_description_fr, long_description_en,
                    image_url_main, image_urls_thumb,
                    species_fr, species_en, origin_fr, origin_en,
                    seasonality_fr, seasonality_en, ideal_uses_fr, ideal_uses_en,
                    sensory_description_fr, sensory_description_en,
                    pairing_suggestions_fr, pairing_suggestions_en,
                    base_price, stock_quantity, is_published,
                    passport_url, qr_code_path, label_path,
                    created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (
                product_id, name_fr, name_en, category,
                short_description_fr, short_description_en,
                long_description_fr, long_description_en,
                image_url_main, image_urls_thumb_json,
                species_fr, species_en, origin_fr, origin_en,
                seasonality_fr, seasonality_en, ideal_uses_fr, ideal_uses_en,
                sensory_description_fr, sensory_description_en,
                pairing_suggestions_fr, pairing_suggestions_en,
                base_price, 0 if weight_options else initial_stock_quantity, is_published,
                passport_public_url, qr_code_relative_path, label_relative_path
            ))

            if not weight_options and base_price is not None and initial_stock_quantity > 0:
                record_stock_movement(cursor, product_id, initial_stock_quantity, 'initial_stock',
                                      notes=f"Stock initial pour {product_id}", user_id=admin_user_id)
                cursor.execute("UPDATE products SET stock_quantity = ? WHERE id = ?", (initial_stock_quantity, product_id))

            if weight_options:
                total_variant_stock = 0
                for option in weight_options:
                    if not all(k in option for k in ['weight_grams', 'price', 'initial_stock']):
                        raise ValueError("Option de poids mal formatée.")
                    opt_stock = int(option['initial_stock'])
                    cursor.execute("""
                        INSERT INTO product_weight_options (product_id, weight_grams, price, stock_quantity)
                        VALUES (?, ?, ?, ?)
                    """, (product_id, int(option['weight_grams']), float(option['price']), 0 ))
                    variant_option_id = cursor.lastrowid
                    if opt_stock > 0:
                        record_stock_movement(cursor, product_id, opt_stock, 'initial_stock',
                                              variant_option_id=variant_option_id,
                                              notes=f"Stock initial pour variante {option['weight_grams']}g de {product_id}",
                                              user_id=admin_user_id)
                        cursor.execute("UPDATE product_weight_options SET stock_quantity = ? WHERE option_id = ?", (opt_stock, variant_option_id))
                    total_variant_stock += opt_stock
                cursor.execute("UPDATE products SET stock_quantity = ? WHERE id = ?", (total_variant_stock, product_id))

            db.commit()
            current_app.logger.info(f"Produit '{product_id}' (localisé) créé par admin {admin_user_id or 'System'}. Actifs générés.")

            cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
            created_product_row = cursor.fetchone()
            if not created_product_row: # Should not happen if insert was successful
                 return jsonify({"success": False, "message": "Erreur lors de la récupération du produit créé."}), 500
            created_product_dict = dict(created_product_row)

            if weight_options:
                 cursor.execute("SELECT * FROM product_weight_options WHERE product_id = ?", (product_id,))
                 created_product_dict['weight_options'] = [dict(row) for row in cursor.fetchall()]

            created_product_dict['assets'] = {
                "passport_url": passport_public_url,
                "qr_code_file_path": qr_code_relative_path,
                "label_file_path": label_relative_path
            }
            return jsonify({"success": True, "message": "Produit créé et actifs générés avec succès.", "product": created_product_dict}), 201

        except sqlite3.IntegrityError as e:
            if db: db.rollback()
            current_app.logger.error(f"Erreur d'intégrité DB: {e}", exc_info=True)
            return jsonify({"success": False, "message": f"Erreur de base de données: {e}"}), 409
        except ValueError as ve:
            if db: db.rollback()
            current_app.logger.error(f"Erreur de valeur: {ve}", exc_info=True)
            return jsonify({"success": False, "message": str(ve)}), 400
        except Exception as e:
            if db: db.rollback()
            current_app.logger.error(f"Erreur serveur: {e}", exc_info=True)
            return jsonify({"success": False, "message": "Erreur serveur interne lors de la création du produit ou des actifs."}), 500
        finally:
            if db: db.close()


    @admin_api_bp.route('/products/<string:product_id_to_update>', methods=['PUT'])
    @admin_required
    def update_product(product_id_to_update):
        data = request.get_json()
        db = None
        admin_user_id = getattr(g, 'admin_user_id', None)
        try:
            db = get_db()
            cursor = db.cursor()

            cursor.execute("SELECT * FROM products WHERE id = ?", (product_id_to_update,))
            product = cursor.fetchone()
            if not product:
                return jsonify({"success": False, "message": "Produit non trouvé."}), 404

            update_fields_sql_parts = []
            update_values = []

            # Define allowed fields for direct update on 'products' table, including localized versions
            allowed_product_fields = [
                'name_fr', 'name_en', 'category',
                'short_description_fr', 'short_description_en',
                'long_description_fr', 'long_description_en',
                'image_url_main',
                'species_fr', 'species_en', 'origin_fr', 'origin_en',
                'seasonality_fr', 'seasonality_en', 'ideal_uses_fr', 'ideal_uses_en',
                'sensory_description_fr', 'sensory_description_en',
                'pairing_suggestions_fr', 'pairing_suggestions_en',
                'base_price', 'is_published'
            ]

            for field in allowed_product_fields:
                if field in data:
                    update_fields_sql_parts.append(f"{field} = ?")
                    update_values.append(data[field])

            if 'image_urls_thumb' in data:
                if isinstance(data['image_urls_thumb'], list):
                    update_fields_sql_parts.append("image_urls_thumb = ?")
                    update_values.append(json.dumps(data['image_urls_thumb']))
                elif data['image_urls_thumb'] is None:
                    update_fields_sql_parts.append("image_urls_thumb = ?")
                    update_values.append('[]')

            if update_fields_sql_parts:
                update_fields_sql_parts.append("updated_at = CURRENT_TIMESTAMP")
                update_values.append(product_id_to_update)
                sql_update_product = f"UPDATE products SET {', '.join(update_fields_sql_parts)} WHERE id = ?"
                cursor.execute(sql_update_product, tuple(update_values))

            # (Weight options handling remains largely the same as before, ensure it uses product_id_to_update)
            # ... (Keep existing weight option logic, making sure it uses product_id_to_update)

            db.commit()
            current_app.logger.info(f"Produit '{product_id_to_update}' (localisé) mis à jour par admin {admin_user_id or 'System'}.")

            cursor.execute("SELECT * FROM products WHERE id = ?", (product_id_to_update,))
            updated_product_row = cursor.fetchone()
            if not updated_product_row:
                 return jsonify({"success": False, "message": "Erreur lors de la récupération du produit mis à jour."}), 500
            updated_product_dict = dict(updated_product_row)

            cursor.execute("SELECT * FROM product_weight_options WHERE product_id = ?", (product_id_to_update,))
            updated_product_dict['weight_options'] = [dict(row) for row in cursor.fetchall()]

            # Re-generate assets if relevant fields changed (name, descriptions for passport/label etc.)
            # For simplicity, we can choose to regenerate them on every update, or add more complex logic
            # to detect changes. Here we regenerate:
            asset_product_data_fr_upd = {key.replace('_fr',''): val for key, val in updated_product_dict.items() if key.endswith('_fr')}
            asset_product_data_fr_upd['id'] = updated_product_dict['id']
            asset_product_data_fr_upd['name'] = updated_product_dict['name_fr'] # Ensure 'name' key exists
            # ... populate other necessary fields for asset_product_data_fr_upd from updated_product_dict ...
            asset_product_data_fr_upd['logo_url'] = url_for('static', filename=current_app.config.get('LABEL_LOGO_PATH_STATIC_RELATIVE', 'images/image_6be700.png'), _external=True)


            asset_product_data_en_upd = {key.replace('_en',''): val for key, val in updated_product_dict.items() if key.endswith('_en')}
            asset_product_data_en_upd['id'] = updated_product_dict['id']
            asset_product_data_en_upd['name'] = updated_product_dict['name_en'] # Ensure 'name' key exists
            # ... populate other necessary fields for asset_product_data_en_upd ...
            asset_product_data_en_upd['logo_url'] = url_for('static', filename=current_app.config.get('LABEL_LOGO_PATH_STATIC_RELATIVE', 'images/image_6be700.png'), _external=True)


            # Use existing or default values if not present in updated_product_dict for asset generation
            default_asset_values = {
                "numero_lot_manuel": f"LOT-{product_id_to_update}-{datetime.date.today().strftime('%Y%m%d')}",
                "date_conditionnement": datetime.date.today().isoformat(),
                "ddm": (datetime.date.today() + datetime.timedelta(days=365*2)).isoformat(),
                "poids_net_final_g": "Voir emballage" if updated_product_dict.get('weight_options') else "N/A",
                "ingredients_affichage": "Consultez l'emballage"
            }
            for key, val in default_asset_values.items():
                asset_product_data_fr_upd.setdefault(key, val)
                asset_product_data_en_upd.setdefault(key, val)


            passport_html_content_upd = generate_product_passport_html_content(asset_product_data_fr_upd, asset_product_data_en_upd)
            passport_file_rel_path_upd = save_product_passport_html(passport_html_content_upd, product_id_to_update)
            passport_public_url_upd, qr_code_relative_path_upd, label_relative_path_upd = None, None, None

            if passport_file_rel_path_upd:
                passport_public_url_upd = f"{current_app.config['PASSPORT_BASE_URL'].rstrip('/')}/{os.path.basename(passport_file_rel_path_upd)}"
                qr_code_relative_path_upd = generate_qr_code_for_passport(passport_public_url_upd, product_id_to_update)
                if qr_code_relative_path_upd:
                    label_relative_path_upd = generate_product_label_image(asset_product_data_fr_upd,asset_product_data_en_upd, qr_code_relative_path_upd)

                cursor.execute("""
                    UPDATE products SET passport_url = ?, qr_code_path = ?, label_path = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (passport_public_url_upd, qr_code_relative_path_upd, label_relative_path_upd, product_id_to_update))
                db.commit()
                updated_product_dict['passport_url'] = passport_public_url_upd
                updated_product_dict['qr_code_path'] = qr_code_relative_path_upd
                updated_product_dict['label_path'] = label_relative_path_upd


            updated_product_dict['assets'] = {
                "passport_url": passport_public_url_upd,
                "qr_code_file_path": qr_code_relative_path_upd,
                "label_file_path": label_relative_path_upd
            }

            return jsonify({"success": True, "message": "Produit mis à jour et actifs regénérés.", "product": updated_product_dict})

        except ValueError as ve:
            if db: db.rollback()
            return jsonify({"success": False, "message": str(ve)}), 400
        except Exception as e:
            if db: db.rollback()
            current_app.logger.error(f"Erreur serveur MAJ produit {product_id_to_update}: {e}", exc_info=True)
            return jsonify({"success": False, "message": "Erreur serveur interne."}), 500
        finally:
            if db: db.close()


    # Ensure other admin routes (/products GET, /products/<id> GET, inventory, users, orders) are similarly
    # adapted if they need to display or handle localized product names or descriptions.
    # For example, when listing products in the admin panel, you might choose to display only the French name
    # or allow the admin to select a display language for the panel itself.

    @admin_api_bp.route('/products', methods=['GET'])
    @admin_required
    def list_admin_products():
        db = None
        try:
            db = get_db()
            cursor = db.cursor()
            # Fetch both fr and en names, and other relevant fields
            cursor.execute("""
                SELECT p.id, p.name_fr, p.name_en, p.category, p.base_price, p.is_published, p.updated_at,
                       (SELECT COUNT(*) FROM product_weight_options WHERE product_id = p.id) as variant_count,
                       (SELECT SUM(stock_quantity) FROM product_weight_options WHERE product_id = p.id) as total_variant_stock
                FROM products p
                ORDER BY p.updated_at DESC
            """)
            products_rows = cursor.fetchall()
            products_list = []
            for row_data in products_rows:
                prod_dict = dict(row_data)
                if prod_dict['base_price'] is None and prod_dict['variant_count'] > 0:
                     prod_dict['stock_quantity'] = prod_dict['total_variant_stock'] if prod_dict['total_variant_stock'] is not None else 0
                else: # For simple products, get stock_quantity from products table (already selected as part of p.*)
                     cursor.execute("SELECT stock_quantity FROM products WHERE id = ?", (prod_dict['id'],))
                     simple_stock_row = cursor.fetchone()
                     prod_dict['stock_quantity'] = simple_stock_row['stock_quantity'] if simple_stock_row else 0


                prod_dict.pop('total_variant_stock', None)
                products_list.append(prod_dict)

            return jsonify(products_list)
        except Exception as e:
            current_app.logger.error(f"Erreur listage produits admin: {e}", exc_info=True)
            return jsonify({"success": False, "message": "Erreur serveur."}), 500
        finally:
            if db: db.close()


    @admin_api_bp.route('/products/<string:product_id_param>', methods=['GET'])
    @admin_required
    def get_admin_product_details(product_id_param): # Renamed param to avoid conflict
        db = None
        try:
            db = get_db()
            cursor = db.cursor()
            # Fetch all fields, including new localized ones and asset paths
            cursor.execute("SELECT * FROM products WHERE id = ?", (product_id_param,))
            product_row = cursor.fetchone()

            if not product_row:
                return jsonify({"success": False, "message": "Produit non trouvé"}), 404

            product_dict = dict(product_row)

            cursor.execute("SELECT * FROM product_weight_options WHERE product_id = ? ORDER BY weight_grams ASC", (product_id_param,))
            product_dict['weight_options'] = [dict(row_option) for row_option in cursor.fetchall()]

            if product_dict.get('image_urls_thumb'):
                try:
                    product_dict['image_urls_thumb'] = json.loads(product_dict['image_urls_thumb'])
                except (json.JSONDecodeError, TypeError):
                    product_dict['image_urls_thumb'] = []
            else:
                product_dict['image_urls_thumb'] = []

            product_dict['assets'] = {
                "passport_url": product_dict.get("passport_url"),
                "qr_code_file_path": product_dict.get("qr_code_path"),
                "label_file_path": product_dict.get("label_path")
            }

            return jsonify(product_dict)
        except Exception as e:
            current_app.logger.error(f"Erreur récupération produit admin {product_id_param}: {e}", exc_info=True)
            return jsonify({"success": False, "message": "Erreur serveur."}), 500
        finally:
            if db: db.close()


    # Other admin routes (inventory, users, orders) are kept as is for brevity,
    # but would need similar i18n considerations if they display product names.
    # (Keep existing /inventory/adjust, /inventory/product/<id>, /users, /users/<id>, /orders, /orders/<id>, /orders/<id>/status, /orders/<id>/notes)

    @admin_api_bp.route('/inventory/adjust', methods=['POST'])
    @admin_required
    def adjust_inventory():
        data = request.get_json()
        product_id = data.get('product_id')
        variant_option_id = data.get('variant_option_id')
        quantity_change_str = data.get('quantity_change')
        movement_type = data.get('movement_type')
        notes = data.get('notes', '')
        admin_user_id = getattr(g, 'admin_user_id', None)

        if not all([product_id, quantity_change_str is not None, movement_type]):
            return jsonify({"success": False, "message": "Champs product_id, quantity_change, et movement_type sont requis."}), 400
        try:
            quantity_change = int(quantity_change_str)
        except ValueError:
            return jsonify({"success": False, "message": "quantity_change doit être un nombre entier."}), 400

        allowed_adjustment_types = ['initial_stock', 'addition', 'vente', 'ajustement_manuel', 'creation_lot', 'retour_client', 'perte', 'correction']
        if movement_type not in allowed_adjustment_types:
            return jsonify({"success": False, "message": f"Type de mouvement '{movement_type}' invalide."}), 400

        db = None
        try:
            db = get_db()
            cursor = db.cursor()

            if quantity_change > 0 and movement_type in ['perte', 'vente']:
                 return jsonify({"success": False, "message": f"Pour '{movement_type}', quantity_change doit être négatif ou nul."}), 400
            if quantity_change < 0 and movement_type in ['initial_stock', 'addition', 'creation_lot', 'retour_client']:
                 return jsonify({"success": False, "message": f"Pour '{movement_type}', quantity_change doit être positif ou nul."}), 400

            record_stock_movement(cursor, product_id, quantity_change, movement_type,
                                  variant_option_id=variant_option_id or None, notes=notes, user_id=admin_user_id)
            db.commit()
            return jsonify({"success": True, "message": "Stock ajusté avec succès."}), 200
        except ValueError as ve:
            if db: db.rollback()
            return jsonify({"success": False, "message": str(ve)}), 400
        except Exception as e:
            if db: db.rollback()
            current_app.logger.error(f"Erreur ajustement stock: {e}", exc_info=True)
            return jsonify({"success": False, "message": "Erreur serveur interne."}), 500
        finally:
            if db: db.close()

    @admin_api_bp.route('/inventory/product/<string:product_id_param>', methods=['GET'])
    @admin_required
    def get_admin_inventory_for_product(product_id_param):
        from ..inventory.routes import get_product_inventory_details
        return get_product_inventory_details(product_id_param)


    @admin_api_bp.route('/users', methods=['GET'])
    @admin_required
    def list_users():
        db = None
        try:
            db = get_db()
            cursor = db.cursor()
            cursor.execute("SELECT id, email, nom, prenom, is_admin, created_at FROM users ORDER BY created_at DESC")
            users = [dict(row) for row in cursor.fetchall()]
            return jsonify(users)
        except Exception as e:
            current_app.logger.error(f"Erreur listage utilisateurs: {e}", exc_info=True)
            return jsonify({"success": False, "message": "Erreur serveur."}), 500
        finally:
            if db: db.close()

    @admin_api_bp.route('/users/<int:user_id_param>', methods=['GET'])
    @admin_required
    def get_user_details(user_id_param):
        db = None
        try:
            db = get_db()
            cursor = db.cursor()
            cursor.execute("SELECT id, email, nom, prenom, is_admin, created_at FROM users WHERE id = ?", (user_id_param,))
            user = cursor.fetchone()
            if not user:
                return jsonify({"success": False, "message": "Utilisateur non trouvé."}), 404

            cursor.execute("SELECT order_id, total_amount, order_date, status FROM orders WHERE user_id = ? ORDER BY order_date DESC", (user_id_param,))
            orders = [dict(row) for row in cursor.fetchall()]

            user_details_dict = dict(user)
            user_details_dict['orders'] = orders

            return jsonify(user_details_dict)
        except Exception as e:
            current_app.logger.error(f"Erreur récupération détails utilisateur {user_id_param}: {e}", exc_info=True)
            return jsonify({"success": False, "message": "Erreur serveur."}), 500
        finally:
            if db: db.close()

    @admin_api_bp.route('/orders', methods=['GET'])
    @admin_required
    def list_admin_orders():
        db = None
        try:
            db = get_db()
            cursor = db.cursor()

            search_query = request.args.get('search', '')
            status_filter = request.args.get('status', '')
            date_filter = request.args.get('date', '')

            query = "SELECT order_id, user_id, customer_email, customer_name, total_amount, order_date, status FROM orders"
            conditions = []
            params = []

            if search_query:
                conditions.append("(CAST(order_id AS TEXT) LIKE ? OR customer_email LIKE ? OR customer_name LIKE ?)") # Cast order_id to TEXT for LIKE
                like_search = f"%{search_query}%"
                params.extend([like_search, like_search, like_search])
            if status_filter:
                conditions.append("status = ?")
                params.append(status_filter)
            if date_filter:
                conditions.append("date(order_date) = ?")
                params.append(date_filter)

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            query += " ORDER BY order_date DESC"

            cursor.execute(query, tuple(params))
            orders = [dict(row) for row in cursor.fetchall()]
            return jsonify(orders)
        except Exception as e:
            current_app.logger.error(f"Erreur listage commandes admin: {e}", exc_info=True)
            return jsonify({"success": False, "message": "Erreur serveur."}), 500
        finally:
            if db: db.close()


    @admin_api_bp.route('/orders/<string:order_id_param>', methods=['GET'])
    @admin_required
    def get_admin_order_details(order_id_param): # order_id can be TRUVRAXXXXX
        db = None
        actual_order_id = order_id_param
        if isinstance(order_id_param, str) and order_id_param.upper().startswith("TRUVRA"):
            try:
                actual_order_id = int(order_id_param[len("TRUVRA"):])
            except ValueError:
                return jsonify({"success": False, "message": "Format ID de commande invalide."}), 400
        else:
            try:
                actual_order_id = int(order_id_param)
            except ValueError:
                 return jsonify({"success": False, "message": "ID de commande doit être numérique ou formaté TRUVRAXXXXX."}), 400
        try:
            db = get_db()
            cursor = db.cursor()
            cursor.execute("SELECT * FROM orders WHERE order_id = ?", (actual_order_id,))
            order = cursor.fetchone()
            if not order:
                return jsonify({"success": False, "message": "Commande non trouvée."}), 404

            order_dict = dict(order)
            # Fetch items with localized names, assuming 'fr' as primary for admin display for now
            # For a truly bilingual admin, this might also take a lang param
            cursor.execute("""
                SELECT oi.item_id, oi.product_id, oi.product_name_fr, oi.product_name_en, oi.quantity, oi.price_at_purchase, oi.variant, pwo.weight_grams
                FROM order_items oi
                LEFT JOIN product_weight_options pwo ON oi.variant_option_id = pwo.option_id
                WHERE oi.order_id = ?
            """, (actual_order_id,))
            order_dict['items'] = [dict(row) for row in cursor.fetchall()]

            cursor.execute("SELECT note_id, content, created_at, admin_user_id FROM order_notes WHERE order_id = ? ORDER BY created_at ASC", (actual_order_id,))
            notes_raw = cursor.fetchall()
            order_dict['notes'] = []
            for note_row in notes_raw:
                note_dict = dict(note_row)
                note_dict['admin_user'] = f"Admin ID {note_row['admin_user_id']}" if note_row['admin_user_id'] else "Système"
                order_dict['notes'].append(note_dict)

            return jsonify(order_dict)
        except Exception as e:
            current_app.logger.error(f"Erreur récupération détails commande admin {actual_order_id}: {e}", exc_info=True)
            return jsonify({"success": False, "message": "Erreur serveur."}), 500
        finally:
            if db: db.close()

    @admin_api_bp.route('/orders/<int:order_id_param>/status', methods=['PUT'])
    @admin_required
    def update_order_status(order_id_param):
        data = request.get_json()
        new_status = data.get('status')
        tracking_number = data.get('tracking_number')
        carrier = data.get('carrier')
        admin_user_id = getattr(g, 'admin_user_id', None)


        if not new_status:
            return jsonify({"success": False, "message": "Nouveau statut manquant."}), 400

        allowed_statuses = ['Pending', 'Paid', 'Shipped', 'Delivered', 'Cancelled']
        if new_status not in allowed_statuses:
            return jsonify({"success": False, "message": "Statut invalide."}), 400

        db = None
        try:
            db = get_db()
            cursor = db.cursor()
            cursor.execute("SELECT status FROM orders WHERE order_id = ?", (order_id_param,))
            current_order = cursor.fetchone()
            if not current_order:
                return jsonify({"success": False, "message": "Commande non trouvée."}), 404

            cursor.execute("UPDATE orders SET status = ?, tracking_number = ?, carrier = ? WHERE order_id = ?",
                           (new_status, tracking_number, carrier, order_id_param))

            note_content = f"Statut changé à '{new_status}'."
            if new_status == 'Shipped':
                note_content += f" Suivi: {tracking_number or 'N/A'} via {carrier or 'N/A'}."

            cursor.execute(
                "INSERT INTO order_notes (order_id, content, admin_user_id) VALUES (?, ?, ?)",
                (order_id_param, note_content, admin_user_id)
            )
            db.commit()
            current_app.logger.info(f"Statut commande {order_id_param} mis à jour à '{new_status}' par admin {admin_user_id or 'System'}.")
            return jsonify({"success": True, "message": "Statut de la commande mis à jour."})
        except Exception as e:
            if db: db.rollback()
            current_app.logger.error(f"Erreur MAJ statut commande {order_id_param}: {e}", exc_info=True)
            return jsonify({"success": False, "message": "Erreur serveur."}), 500
        finally:
            if db: db.close()

    @admin_api_bp.route('/orders/<int:order_id_param>/notes', methods=['POST'])
    @admin_required
    def add_order_note(order_id_param):
        data = request.get_json()
        note_content = data.get('note')
        admin_user_id = getattr(g, 'admin_user_id', None)

        if not note_content or not note_content.strip():
            return jsonify({"success": False, "message": "Contenu de la note manquant."}), 400

        db = None
        try:
            db = get_db()
            cursor = db.cursor()
            cursor.execute("SELECT 1 FROM orders WHERE order_id = ?", (order_id_param,))
            if not cursor.fetchone():
                return jsonify({"success": False, "message": "Commande non trouvée."}), 404

            cursor.execute(
                "INSERT INTO order_notes (order_id, content, admin_user_id) VALUES (?, ?, ?)",
                (order_id_param, note_content, admin_user_id)
            )
            db.commit()
            current_app.logger.info(f"Note ajoutée à la commande {order_id_param} par admin {admin_user_id or 'System'}.")
            return jsonify({"success": True, "message": "Note ajoutée avec succès."}), 201
        except Exception as e:
            if db: db.rollback()
            current_app.logger.error(f"Erreur ajout note commande {order_id_param}: {e}", exc_info=True)
            return jsonify({"success": False, "message": "Erreur serveur."}), 500
        finally:
            if db: db.close()

III. Updated Frontend (Website) Files:

    website/header.html
        Add language switcher.
    HTML

<header class="bg-brand-cream shadow-md sticky top-0 z-40">
    <div class="container mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex items-center justify-between h-24">
            <div class="flex-shrink-0">
                <a href="index.html">
                    <img class="h-16 w-auto" src="image_6be700.png" alt="Logo Maison Trüvra" onerror="this.alt='Logo Maison Trüvra'; this.src='https://placehold.co/150x60/F5EEDE/7D6A4F?text=Maison+Trüvra';">
                </a>
            </div>
            <nav class="hidden md:flex items-center space-x-8">
                <a href="index.html" id="nav-homepage" class="nav-link text-brand-earth-brown hover:text-brand-near-black px-3 py-2 text-base font-medium" data-translate-key="Accueil">Accueil</a>
                <a href="nos-produits.html" id="nav-products-list" class="nav-link text-brand-earth-brown hover:text-brand-near-black px-3 py-2 text-base font-medium" data-translate-key="Nos_Produits">Nos Produits</a>
                <a href="notre-histoire.html" id="nav-about" class="nav-link text-brand-earth-brown hover:text-brand-near-black px-3 py-2 text-base font-medium" data-translate-key="Notre_Histoire">Notre Histoire</a>
                <a href="professionnels.html" id="nav-professionals" class="nav-link text-brand-earth-brown hover:text-brand-near-black px-3 py-2 text-base font-medium" data-translate-key="Professionnels">Professionnels</a>
            </nav>
            <div class="hidden md:flex items-center space-x-5">
                <a href="compte.html" title="Mon Compte" class="text-brand-earth-brown hover:text-brand-near-black" data-translate-key-title="Mon_Compte">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-7 h-7"><path stroke-linecap="round" stroke-linejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" /></svg>
                    <span id="account-link-text-desktop" class="ml-1 text-xs" data-translate-key="Mon_Compte_Menu">Mon Compte</span>
                </a>
                <a href="panier.html" title="Panier" class="text-brand-earth-brown hover:text-brand-near-black relative" data-translate-key-title="Panier">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-7 h-7"><path stroke-linecap="round" stroke-linejoin="round" d="M15.75 10.5V6a3.75 3.75 0 10-7.5 0v4.5m11.356-1.993l1.263 12c.07.665-.45 1.243-1.119 1.243H4.25a1.125 1.125 0 01-1.12-1.243l1.264-12A1.125 1.125 0 015.513 7.5h12.974c.576 0 1.059.435 1.119 1.007zM8.625 10.5a.375.375 0 11-.75 0 .375.375 0 01.75 0zm7.5 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z" /></svg>
                    <span id="cart-item-count" class="absolute -top-2 -right-2 bg-brand-truffle-burgundy text-brand-cream text-xs font-bold rounded-full h-5 w-5 flex items-center justify-center">0</span>
                </a>
                <div class="relative lang-switcher">
                    <button type="button" class="text-brand-earth-brown hover:text-brand-near-black px-2 py-1 text-sm font-medium border border-brand-warm-taupe rounded-md" onclick="toggleLangDropdown()">
                        <span id="current-lang-display">FR</span> <svg class="w-4 h-4 inline-block" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clip-rule="evenodd"></path></svg>
                    </button>
                    <div id="lang-dropdown" class="absolute right-0 mt-2 w-20 rounded-md shadow-lg bg-white ring-1 ring-black ring-opacity-5 hidden">
                        <div class="py-1" role="menu" aria-orientation="vertical" aria-labelledby="options-menu">
                            <a href="#" class="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100" role="menuitem" onclick="changeLanguage('fr'); return false;">FR</a>
                            <a href="#" class="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100" role="menuitem" onclick="changeLanguage('en'); return false;">EN</a>
                        </div>
                    </div>
                </div>
            </div>
            <div class="md:hidden flex items-center">
                 <a href="panier.html" title="Panier" class="text-brand-earth-brown hover:text-brand-near-black relative mr-4" data-translate-key-title="Panier">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-7 h-7"><path stroke-linecap="round" stroke-linejoin="round" d="M15.75 10.5V6a3.75 3.75 0 10-7.5 0v4.5m11.356-1.993l1.263 12c.07.665-.45 1.243-1.119 1.243H4.25a1.125 1.125 0 01-1.12-1.243l1.264-12A1.125 1.125 0 015.513 7.5h12.974c.576 0 1.059.435 1.119 1.007zM8.625 10.5a.375.375 0 11-.75 0 .375.375 0 01.75 0zm7.5 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z" /></svg>
                    <span id="mobile-cart-item-count" class="absolute -top-2 -right-2 bg-brand-truffle-burgundy text-brand-cream text-xs font-bold rounded-full h-5 w-5 flex items-center justify-center">0</span>
                </a>
                <div class="relative lang-switcher-mobile mr-2">
                    <button type="button" class="text-brand-earth-brown hover:text-brand-near-black px-2 py-1 text-sm font-medium border border-brand-warm-taupe rounded-md" onclick="toggleLangDropdownMobile()">
                        <span id="current-lang-display-mobile">FR</span> <svg class="w-4 h-4 inline-block" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clip-rule="evenodd"></path></svg>
                    </button>
                    <div id="lang-dropdown-mobile" class="absolute right-0 mt-2 w-20 rounded-md shadow-lg bg-white ring-1 ring-black ring-opacity-5 hidden">
                        <div class="py-1" role="menu" aria-orientation="vertical" aria-labelledby="options-menu-mobile">
                            <a href="#" class="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100" role="menuitem" onclick="changeLanguage('fr'); return false;">FR</a>
                            <a href="#" class="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100" role="menuitem" onclick="changeLanguage('en'); return false;">EN</a>
                        </div>
                    </div>
                </div>
                <button type="button" id="mobile-menu-button" class="text-brand-earth-brown hover:text-brand-near-black focus:outline-none">
                    <span class="sr-only" data-translate-key="Ouvrir_menu_principal">Ouvrir le menu principal</span>
                    <svg class="h-7 w-7" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16m-7 6h7" /></svg>
                </button>
            </div>
        </div>
    </div>
    <div class="md:hidden hidden" id="mobile-menu-dropdown">
        <div class="px-2 pt-2 pb-3 space-y-1 sm:px-3">
            <a href="index.html" class="nav-link text-brand-earth-brown hover:bg-brand-warm-taupe hover:text-brand-cream block px-3 py-2 rounded-md text-base font-medium" data-translate-key="Accueil">Accueil</a>
            <a href="nos-produits.html" class="nav-link text-brand-earth-brown hover:bg-brand-warm-taupe hover:text-brand-cream block px-3 py-2 rounded-md text-base font-medium" data-translate-key="Nos_Produits">Nos Produits</a>
            <a href="notre-histoire.html" class="nav-link text-brand-earth-brown hover:bg-brand-warm-taupe hover:text-brand-cream block px-3 py-2 rounded-md text-base font-medium" data-translate-key="Notre_Histoire">Notre Histoire</a>
            <a href="professionnels.html" class="nav-link text-brand-earth-brown hover:bg-brand-warm-taupe hover:text-brand-cream block px-3 py-2 rounded-md text-base font-medium" data-translate-key="Professionnels">Professionnels</a>
            <a href="compte.html" id="account-link-text-mobile" class="nav-link text-brand-earth-brown hover:bg-brand-warm-taupe hover:text-brand-cream block px-3 py-2 rounded-md text-base font-medium" data-translate-key="Mon_Compte_Menu">Mon Compte</a>
        </div>
    </div>
</header>
<script>
    function toggleLangDropdown() {
        document.getElementById('lang-dropdown').classList.toggle('hidden');
    }
    function toggleLangDropdownMobile() {
        document.getElementById('lang-dropdown-mobile').classList.toggle('hidden');
    }
    async function changeLanguage(lang) {
        await window.setLanguage(lang); // Assuming setLanguage is exposed from i18n.js
        document.getElementById('current-lang-display').textContent = lang.toUpperCase();
        document.getElementById('current-lang-display-mobile').textContent = lang.toUpperCase();
        toggleLangDropdown(); // Close dropdown
        if(document.getElementById('lang-dropdown-mobile')) toggleLangDropdownMobile();

        // Add this line to update nav link texts immediately as they are not covered by data-translate-key
        if(typeof setActiveNavLink === 'function') setActiveNavLink(); // This might also re-trigger some UI updates based on active class
    }
</script>

website/js/main.js

    Integrate i18n.js and initialize translations.

JavaScript

// website/js/main.js
// Ensure i18n.js is loaded before main.js in your HTML files:
// <script src="js/i18n.js"></script>
// <script src="js/main.js"></script>

document.addEventListener('DOMContentLoaded', async () => {
    // --- Global Initializations ---
    await loadTranslations(localStorage.getItem('maisonTruvraLang') || 'fr'); // Load translations first
    initializeMobileMenu();     // From ui.js
    initializeNewsletterForm(); // From newsletter.js
    setActiveNavLink();         // From ui.js
    updateLoginState();         // From auth.js
    updateCartCountDisplay();   // From cart.js

    // Update language display in switcher
    const currentLangInitial = getCurrentLang(); // from i18n.js
    const langDisplay = document.getElementById('current-lang-display');
    const langDisplayMobile = document.getElementById('current-lang-display-mobile');
    if (langDisplay) langDisplay.textContent = currentLangInitial.toUpperCase();
    if (langDisplayMobile) langDisplayMobile.textContent = currentLangInitial.toUpperCase();


    const currentYearEl = document.getElementById('currentYear');
    if (currentYearEl) {
        currentYearEl.textContent = new Date().getFullYear();
    }

    const bodyId = document.body.id;

    if (bodyId === 'page-nos-produits') {
        if (typeof fetchAndDisplayProducts === 'function') fetchAndDisplayProducts('all');
        if (typeof setupCategoryFilters === 'function') setupCategoryFilters();
    } else if (bodyId === 'page-produit-detail') {
        if (typeof loadProductDetail === 'function') loadProductDetail();
        const addToCartDetailButton = document.getElementById('add-to-cart-button');
        if (addToCartDetailButton && typeof handleAddToCartFromDetail === 'function') {
            addToCartDetailButton.addEventListener('click', (event) => {
                event.preventDefault();
                handleAddToCartFromDetail();
            });
        }
        const quantityControls = document.getElementById('quantity-select-controls');
        if (quantityControls) {
            const decreaseButton = quantityControls.querySelector('button:first-child');
            const increaseButton = quantityControls.querySelector('button:last-child');
            if(decreaseButton && typeof updateDetailQuantity === 'function') decreaseButton.addEventListener('click', () => updateDetailQuantity(-1));
            if(increaseButton && typeof updateDetailQuantity === 'function') increaseButton.addEventListener('click', () => updateDetailQuantity(1));
        }
    } else if (bodyId === 'page-panier') {
        if (typeof displayCartItems === 'function') displayCartItems();
    } else if (bodyId === 'page-compte') {
        if (typeof displayAccountDashboard === 'function') displayAccountDashboard();
        const loginForm = document.getElementById('login-form');
        if (loginForm && typeof handleLogin === 'function') {
            loginForm.addEventListener('submit', handleLogin);
        }
        const createAccountButton = document.querySelector('#login-register-section button.btn-secondary'); // More specific selector
        if(createAccountButton && typeof showGlobalMessage === 'function'){
            createAccountButton.addEventListener('click', (e) => {
                e.preventDefault();
                showGlobalMessage(t('Feature_not_implemented_contact_admin'), 'info'); // Example of using t()
            });
        }
    } else if (bodyId === 'page-paiement') {
        if (typeof initializeCheckoutPage === 'function') initializeCheckoutPage();
    } else if (bodyId === 'page-confirmation-commande') {
        if (typeof initializeConfirmationPage === 'function') initializeConfirmationPage();
    }


    document.querySelectorAll('.modal-overlay').forEach(modalOverlay => {
        modalOverlay.addEventListener('click', function(event) {
            if (event.target === modalOverlay && typeof closeModal === 'function') {
                closeModal(modalOverlay.id);
            }
        });
    });
    document.querySelectorAll('.modal-close-button').forEach(button => {
        button.addEventListener('click', function() {
            const modal = this.closest('.modal-overlay');
            if (modal && typeof closeModal === 'function') {
                closeModal(modal.id);
            }
        });
    });

    // Load header and footer, then translate them if translatePageElements wasn't called yet or needs re-run for dynamic parts
    await Promise.all([loadHeader(), loadFooter()]);
    // Re-translate after header/footer are loaded to catch their keys
    if(window.translatePageElements) window.translatePageElements();


}); // End DOMContentLoaded


async function loadHeader() {
    const headerPlaceholder = document.getElementById('header-placeholder');
    if (!headerPlaceholder) {
        console.error("L'élément #header-placeholder est introuvable.");
        return;
    }
    try {
        const response = await fetch('header.html');
        if (!response.ok) throw new Error(`Erreur de chargement du header: ${response.status}`);
        headerPlaceholder.innerHTML = await response.text();

        if (typeof initializeMobileMenu === 'function') initializeMobileMenu();
        if (typeof setActiveNavLink === 'function') setActiveNavLink();
        if (typeof updateLoginState === 'function') updateLoginState();
        if (typeof updateCartCountDisplay === 'function') updateCartCountDisplay();
        // Translate newly loaded header content
        if(window.translatePageElements) window.translatePageElements();
        // Update language display in switcher (as it's part of header.html)
        const currentLangInitial = getCurrentLang();
        const langDisplay = document.getElementById('current-lang-display');
        const langDisplayMobile = document.getElementById('current-lang-display-mobile');
        if (langDisplay) langDisplay.textContent = currentLangInitial.toUpperCase();
        if (langDisplayMobile) langDisplayMobile.textContent = currentLangInitial.toUpperCase();

    } catch (error) {
        console.error("Impossible de charger l'en-tête:", error);
    }
}

async function loadFooter() {
    const footerPlaceholder = document.getElementById('footer-placeholder');
    if (!footerPlaceholder) {
        console.error("L'élément #footer-placeholder est introuvable.");
        return;
    }
    try {
        const response = await fetch('footer.html');
        if (!response.ok) throw new Error(`Erreur de chargement du footer: ${response.status}`);
        footerPlaceholder.innerHTML = await response.text();

        if (typeof initializeNewsletterForm === 'function' && footerPlaceholder.querySelector('#newsletter-form')) {
            initializeNewsletterForm();
        }
        const currentYearEl = footerPlaceholder.querySelector('#currentYear');
        if (currentYearEl) currentYearEl.textContent = new Date().getFullYear();
        // Translate newly loaded footer content
        if(window.translatePageElements) window.translatePageElements();
    } catch (error) {
        console.error("Impossible de charger le pied de page:", error);
    }
}

website/js/api.js

    Modify makeApiRequest to include the current language.

JavaScript

// website/js/api.js
// Assumes API_BASE_URL is from config.js and getCurrentLang is from i18n.js

async function makeApiRequest(endpoint, method = 'GET', body = null, requiresAuth = false) {
    const headers = { 'Content-Type': 'application/json' };
    const lang = typeof getCurrentLang === 'function' ? getCurrentLang() : 'fr'; // Get current language

    if (requiresAuth) {
        const token = getAuthToken(); // Assumes getAuthToken is available (from auth.js)
        if (!token) {
            if(typeof showGlobalMessage === 'function' && typeof t === 'function') showGlobalMessage(t('Vous_netes_pas_authentifie'), "error");
            else console.error("User not authenticated and showGlobalMessage or t is not available.");
            throw new Error("Authentification requise.");
        }
        headers['Authorization'] = `Bearer ${token}`;
    }

    const config = {
        method: method,
        headers: headers,
    };

    if (body) {
        config.body = JSON.stringify(body);
    }

    // Add lang parameter to GET requests
    let url = `<span class="math-inline">\{API\_BASE\_URL\}</span>{endpoint}`;
    if (method === 'GET') {
        url += (url.includes('?') ? '&' : '?') + `lang=${lang}`;
    }

    try {
        const response = await fetch(url, config);
        if (!response.ok) {
            const errorResult = await response.json().catch(() => ({ message: t('Erreur_de_communication_avec_le_serveur') || "Erreur de communication avec le serveur." }));
            throw new Error(errorResult.message || `${t('Erreur_HTTP') || 'HTTP Error:'} ${response.status}`);
        }
        if (response.status === 204) {
            return { success: true, message: "Opération réussie (pas de contenu)." };
        }
        return await response.json();
    } catch (error) {
        console.error(`${t('Erreur_API_pour') || 'API Error for'} ${method} <span class="math-inline">\{API\_BASE\_URL\}</span>{endpoint}:`, error);
        if(typeof showGlobalMessage === 'function' && typeof t === 'function') {
            showGlobalMessage(error.message || t('Une_erreur_reseau_est_survenue'), "error");
        } else {
             console.error(error.message || "A network error occurred.");
        }
        throw error;
    }
}

website/js/product.js (and similar files like cart.js, checkout.js, auth.js)

    Ensure these files use the t() function for any user-facing strings.
    Ensure they rely on the API to send back already localized data for product names, descriptions, etc.
    Example snippet from product.js in WorkspaceAndDisplayProducts:
    JavaScript

        // ... inside fetchAndDisplayProducts ...
        // The product data from API should now contain localized fields e.g. product.name, product.short_description based on lang param sent in API call
        const productCard = `
            <div class="product-card">
                <a href="produit-detail.html?id=<span class="math-inline">\{product\.id\}"\>

<img src="{product.image_url_main || 'https://placehold.co/400x300/F5EEDE/7D6A4F?text=Image+Indisponible'}" alt="product.name"class="w−fullh−64object−cover"></a><divclass="product−card−content"><h3class="text−xlfont−seriffont−semiboldtext−brand−near−blackmb−2">{product.name}</h3>
<p class="text-brand-earth-brown text-sm mb-3 h-16 overflow-hidden">${product.short_description || ''}</p>
<p class="text-lg font-semibold text-brand-truffle-burgundy mb-4">
${product.starting_price !== "N/A" && product.starting_price !== null ? ${t('A_partir_de')} ${parseFloat(product.starting_price).toFixed(2)} € : (product.base_price ? ${parseFloat(product.base_price).toFixed(2)} € : t('Prix_sur_demande'))}
</p>
<p class="text-xs stockClassmb−4">{stock_quantity > 5 ? t('En_stock') : (stock_quantity > 0 ? t('Stock_limite') : t('Epuise'))}</p>
</div>
<div class="product-card-footer p-4">
<a href="produit-detail.html?id=${product.id}" class="btn-primary block text-center text-sm py-2.5 product.stockq​uantity<=0?′opacity−50cursor−not−allowed′:′′">{product.stock_quantity <= 0 ? t('Epuise') : t('Voir_le_produit')}</a>
</div>
</div>
`;
// ...
```

    HTML Files (index.html, nos-produits.html, etc.)
        Include i18n.js before main.js.
        HTML

<script src="js/config.js"></script>
<script src="js/i18n.js"></script> <script src="js/ui.js"></script>
<script src="js/api.js"></script>
<script src="js/main.js"></script>

Add data-translate-key to all static text elements. I've shown examples in header.html. You need to go through each HTML file and add these keys. For example, in index.html:
HTML

<h1 class="text-4xl sm:text-5xl font-bold font-serif mb-6 leading-tight text-brand-near-black" data-translate-key="Maison_Truvra_Titre_Accueil">Maison Trüvra</h1>
<p class="text-xl sm:text-2xl font-serif italic text-brand-earth-brown mb-8" data-translate-key="Slogan_Accueil">Producteur - récolteur de truffes de qualité</p>

Add data-page-title-key to the <body> tag of each page if you want to translate page titles dynamically:
HTML

<body id="page-index" class="antialiased" data-page-title-key="Titre_Page_Accueil">

And in your locale files:
JSON

        {
          "Titre_Page_Accueil": "Maison Trüvra - Producteur de Truffes d'Exception",
          // ...
        }

IV. Updated Admin Frontend Files:

    admin/admin_manage_products.html
        Duplicate input fields for all translatable product attributes, adding _fr and _en suffixes to their id and name attributes.
        Example for product name:
        HTML

    <div>
        <label for="product-name-fr" class="form-label-admin">Nom du Produit (FR)</label>
        <input type="text" id="product-name-fr" name="name_fr" class="form-input-admin" required>
    </div>
    <div>
        <label for="product-name-en" class="form-label-admin">Product Name (EN)</label>
        <input type="text" id="product-name-en" name="name_en" class="form-input-admin" required>
    </div>

website/admin/js/admin_products.js

    Modify handleProductFormSubmit to collect data from the new _fr and _en fields.
    Modify editProduct to populate these _fr and _en fields when loading a product for editing.
    When listing products, you might choose to display only the French or English name, or both.

JavaScript

    // website/admin/js/admin_products.js
    // ... (keep existing code)

    async function handleProductFormSubmit(event) {
        event.preventDefault();
        const form = event.target;
        // ... (clearFormErrors, validateProductForm - validation needs to check new fr/en fields)

        const formData = new FormData(form);
        const productData = {};

        // Collect all fields, including localized ones
        const fieldsToCollect = [
            'id', 'name_fr', 'name_en', 'category',
            'short_description_fr', 'short_description_en',
            'long_description_fr', 'long_description_en',
            'image_url_main', 'image_urls_thumb', // image_urls_thumb needs parsing
            'species_fr', 'species_en', 'origin_fr', 'origin_en',
            'seasonality_fr', 'seasonality_en', 'ideal_uses_fr', 'ideal_uses_en',
            'sensory_description_fr', 'sensory_description_en',
            'pairing_suggestions_fr', 'pairing_suggestions_en',
            'base_price', 'initial_stock_quantity', 'is_published'
            // Add other specific fields like numero_lot_manuel, date_conditionnement, ddm for asset generation if they are part of the form
        ];

        for (const fieldName of fieldsToCollect) {
            if (formData.has(fieldName)) {
                if (['base_price', 'initial_stock_quantity'].includes(fieldName)) {
                    productData[fieldName] = formData.get(fieldName) ? parseFloat(formData.get(fieldName)) : null;
                    if (fieldName === 'initial_stock_quantity' && productData[fieldName] === null) productData[fieldName] = 0;
                } else if (fieldName === 'is_published') {
                    productData[fieldName] = form.querySelector(`#product-${fieldName.replace('_', '-')}`).checked;
                } else if (fieldName === 'image_urls_thumb') {
                    try {
                        const thumbString = formData.get('image_urls_thumb');
                        productData.image_urls_thumb = thumbString.trim() ? JSON.parse(thumbString) : [];
                        if (!Array.isArray(productData.image_urls_thumb)) productData.image_urls_thumb = [];
                    } catch (e) {
                        productData.image_urls_thumb = [];
                        setFieldError(form.querySelector('#product-image-urls-thumb'), "Format JSON invalide pour les miniatures.");
                        // consider returning or setting a flag to stop submission
                    }
                }
                else {
                    productData[fieldName] = formData.get(fieldName);
                }
            }
        }
        // ... (rest of the weight_options logic) ...
        // The endpoint in admin_api/routes.py is already adapted to receive _fr and _en fields.
        // ... (API call logic) ...
         try {
            showAdminToast("Enregistrement du produit...", "info");
            const result = await adminApiRequest(endpoint, method, productData);

            if (result.success && result.product) {
                showAdminToast(result.message || "Produit enregistré avec succès!", "success");
                // ... (rest of asset display and form update logic)
                loadAdminProductsList(); // Refresh product list
            } // No else needed here as adminApiRequest throws on error and shows toast
        } catch (error) {
            // Error is already handled by adminApiRequest and showAdminToast
            console.error("Erreur soumission formulaire produit:", error);
        }
    }

    function validateProductForm(form) {
        let isValid = true;
        // Update requiredFields to check for at least one language version of name, description etc.
        const requiredBaseFields = [
            { id: 'product-name-fr', message: "Le nom du produit (FR) est requis." }, // Or check name_en
            { id: 'product-category', message: "La catégorie est requise." },
            { id: 'product-short-description-fr', message: "Description courte (FR) requise."} // Or check en
            // ...
        ];
        // ... (rest of validation logic, adapting for _fr/_en fields) ...
        return isValid;
    }


    async function editProduct(productId) {
        editingProductId = productId;
        let productToEdit;
        // ... (asset preview reset) ...

        try {
            // API should return all localized fields
            productToEdit = await adminApiRequest(`/products/${productId}`);
            if (!productToEdit) throw new Error("Produit non trouvé pour l'édition.");
        } catch (e) {
            showAdminToast("Impossible de charger les détails du produit pour l'édition.", "error");
            return;
        }

        const form = document.getElementById('product-form');
        // ... (form reset, clear errors) ...

        document.getElementById('product-form-title').textContent = `Modifier le Produit: ${productToEdit.name_fr || productToEdit.name_en}`;
        document.getElementById('product-id').value = productToEdit.id;
        document.getElementById('product-id').readOnly = true;

        // Populate all _fr and _en fields
        const fieldsToPopulate = [
            'name_fr', 'name_en', 'category',
            'short_description_fr', 'short_description_en',
            'long_description_fr', 'long_description_en',
            'image_url_main', 'image_urls_thumb', // image_urls_thumb needs stringifying
            'species_fr', 'species_en', 'origin_fr', 'origin_en',
            'seasonality_fr', 'seasonality_en', 'ideal_uses_fr', 'ideal_uses_en',
            'sensory_description_fr', 'sensory_description_en',
            'pairing_suggestions_fr', 'pairing_suggestions_en',
            'base_price' // initial_stock_quantity is handled by weight options or base_price context
        ];

        fieldsToPopulate.forEach(fieldName => {
            const element = document.getElementById(`product-${fieldName.replace(/_/g, '-')}`);
            if (element) {
                if (fieldName === 'image_urls_thumb') {
                    element.value = productToEdit.image_urls_thumb ? JSON.stringify(productToEdit.image_urls_thumb) : '[]';
                } else {
                    element.value = productToEdit[fieldName] || '';
                }
            }
        });
        document.getElementById('product-is-published').checked = productToEdit.is_published;
        // ... (rest of weight options and asset display logic) ...
        window.scrollTo(0, 0);
    }

    async function loadAdminProductsList() {
        const tableBody = document.getElementById('products-table-body');
        // ... (loading message) ...
        try {
            productsForAdmin = await adminApiRequest('/products'); // API now returns localized names
            // ...
            productsForAdmin.forEach(product => {
                // Display name_fr or name_en based on an admin panel preference or default to fr
                let displayName = product.name_fr || product.name_en || product.id;
                // ...
                rowsHtml += `
                    <tr>
                        <td class="px-6 py-3 text-xs"><span class="math-inline">\{product\.id\}</td\>

<td class="px-6 py-3 font-medium text-brand-near-black">{displayName}</td>
{/* ... other columns ... */}
</tr>
`;
});
// ...
} catch (error) {
// ...
}
}

// ... (rest of the file)
```

This is a high-level guide. Each JavaScript function that manipulates text or fetches data will require careful review and adaptation for localization. Remember to thoroughly test the language switching and data display in both languages.

website/js/product.js (and similar files like cart.js, checkout.js, auth.js) : send me the updated files

data-translate-key, data-page-title-key, admin/admin_manage_products.html : send me the updated files

website/admin/js/admin_products.js : we display only the FR or EN name. Send me the updated file

Okay, I'll provide the updated versions of the key JavaScript files and the HTML for the admin product management page, incorporating the internationalization (i18n) changes.

Remember to create the following new files as previously discussed:

    website/js/locales/fr.json: (Content provided in the previous response)
    website/js/locales/en.json: (Content provided in the previous response)
    website/js/i18n.js: (Content provided in the previous response)

Make sure these new files are in the correct paths. Also, ensure that in your HTML files, you include <script src="js/i18n.js"></script> before <script src="js/main.js"></script>.

Here are the updated files:
Updated JavaScript Files

These files assume you have the i18n.js file in place, which defines t(), loadTranslations(), setLanguage(), translatePageElements(), and getCurrentLang().

website/js/product.js
JavaScript

// website/js/product.js
// Handles fetching and displaying products on listing and detail pages.

let allProducts = []; // Cache for all products
let currentProductDetail = null; // Holds the data for the currently viewed product detail

/**
 * Fetches products from the API and displays them on the product listing page.
 * @param {string} [category='all'] - The category to filter by. 'all' fetches all products.
 */
async function fetchAndDisplayProducts(category = 'all') {
    const productsGrid = document.getElementById('products-grid');
    const loadingMessageElement = document.getElementById('products-loading-message');

    if (!productsGrid || !loadingMessageElement) {
        console.error("Éléments de la grille de produits ou message de chargement non trouvés.");
        return;
    }

    loadingMessageElement.textContent = t('Chargement_des_produits'); // i18n
    loadingMessageElement.style.display = 'block';
    productsGrid.innerHTML = '';

    try {
        // API call now includes lang, makeApiRequest handles adding it
        const products = await makeApiRequest(
            category === 'all' ? '/products' : `/products?category=${encodeURIComponent(category)}`
        );

        if (category === 'all' && products.length > 0) {
            allProducts = products;
        }

        const productsToDisplay = products;

        if (productsToDisplay.length === 0) {
            loadingMessageElement.textContent = t('Aucun_produit_trouve_dans_cette_categorie'); // i18n
            productsGrid.innerHTML = `<p class="col-span-full text-center text-brand-earth-brown py-8">${t('Aucun_produit_a_afficher')}</p>`; // i18n
        } else {
            loadingMessageElement.style.display = 'none';
            productsToDisplay.forEach(product => {
                // Product name and description are now localized from the API
                const stock_quantity = product.stock_quantity !== undefined ? product.stock_quantity : 0;
                const stockMessage = stock_quantity > 5 ? t('En_stock') : (stock_quantity > 0 ? t('Stock_limite') : t('Epuise'));
                const stockClass = stock_quantity > 0 ? 'text-brand-deep-sage-green' : 'text-brand-truffle-burgundy';

                const productCard = `
                    <div class="product-card">
                        <a href="produit-detail.html?id=${product.id}">
                            <img src="${product.image_url_main || 'https://placehold.co/400x300/F5EEDE/7D6A4F?text=Image+Indisponible'}" alt="${product.name}" class="w-full h-64 object-cover" onerror="this.onerror=null;this.src='https://placehold.co/400x300/F5EEDE/7D6A4F?text=Image+Error';">
                        </a>
                        <div class="product-card-content">
                            <h3 class="text-xl font-serif font-semibold text-brand-near-black mb-2">${product.name}</h3>
                            <p class="text-brand-earth-brown text-sm mb-3 h-16 overflow-hidden">${product.short_description || ''}</p>
                            <p class="text-lg font-semibold text-brand-truffle-burgundy mb-4">
                                ${product.starting_price !== "N/A" && product.starting_price !== null ? `${t('A_partir_de')} ${parseFloat(product.starting_price).toFixed(2)} €` : (product.base_price ? `${parseFloat(product.base_price).toFixed(2)} €` : t('Prix_sur_demande'))}
                            </p>
                             <p class="text-xs ${stockClass} mb-4">${stockMessage}</p>
                        </div>
                        <div class="product-card-footer p-4">
                            <a href="produit-detail.html?id=${product.id}" class="btn-primary block text-center text-sm py-2.5 ${stock_quantity <=0 ? 'opacity-50 cursor-not-allowed' : ''}">${stock_quantity <= 0 ? t('Epuise') : t('Voir_le_produit')}</a>
                        </div>
                    </div>
                `;
                productsGrid.insertAdjacentHTML('beforeend', productCard);
            });
        }
    } catch (error) {
        loadingMessageElement.textContent = t('Impossible_de_charger_les_produits'); // i18n
        productsGrid.innerHTML = `<p class="col-span-full text-center text-brand-truffle-burgundy py-8">${t('Impossible_de_charger_les_produits')}. ${error.message}</p>`;
    }
}

/**
 * Sets up event listeners for category filter buttons on the product listing page.
 */
function setupCategoryFilters() {
    const filterContainer = document.getElementById('product-categories-filter');
    if (filterContainer) {
        const buttons = filterContainer.querySelectorAll('button');
        buttons.forEach(button => {
            button.addEventListener('click', () => {
                buttons.forEach(btn => btn.classList.remove('filter-active', 'bg-brand-earth-brown', 'text-brand-cream'));
                button.classList.add('filter-active', 'bg-brand-earth-brown', 'text-brand-cream');
                const category = button.dataset.category;
                fetchAndDisplayProducts(category);
            });
        });
        // Translate filter button texts if they have data-translate-key
        translatePageElements();
    }
}

/**
 * Loads and displays the details of a single product on the product detail page.
 */
async function loadProductDetail() {
    const params = new URLSearchParams(window.location.search);
    const productId = params.get('id');
    const loadingDiv = document.getElementById('product-detail-loading');
    const contentDiv = document.getElementById('product-detail-content');

    if (!productId) {
        if(loadingDiv) loadingDiv.textContent = t('Aucun_produit_specifie'); // i18n
        if(contentDiv) contentDiv.style.display = 'none';
        return;
    }

    if(loadingDiv) {
        loadingDiv.textContent = t('Chargement_des_details_du_produit'); // i18n
        loadingDiv.style.display = 'block';
    }
    if(contentDiv) contentDiv.style.display = 'none';

    try {
        // API call now includes lang
        const product = await makeApiRequest(`/products/${productId}`);
        currentProductDetail = product;

        // Product name, descriptions etc. are now localized from API
        document.getElementById('product-name').textContent = product.name;
        const mainImage = document.getElementById('main-product-image');
        mainImage.src = product.image_url_main || 'https://placehold.co/600x500/F5EEDE/7D6A4F?text=Image';
        mainImage.alt = product.name;
        mainImage.onerror = () => { mainImage.src = 'https://placehold.co/600x500/F5EEDE/7D6A4F?text=Image+Erreur'; };

        document.getElementById('product-short-description').textContent = product.short_description || '';

        const priceDisplay = document.getElementById('product-price-display');
        const priceUnit = document.getElementById('product-price-unit');
        const weightOptionsContainer = document.getElementById('weight-options-container');
        const weightOptionsSelect = document.getElementById('weight-options-select');
        const addToCartButton = document.getElementById('add-to-cart-button');
        addToCartButton.textContent = t('Ajouter_au_Panier'); // i18n

        if (product.weight_options && product.weight_options.length > 0) {
            weightOptionsContainer.classList.remove('hidden');
            weightOptionsSelect.innerHTML = '';
            product.weight_options.forEach(opt => {
                const optionElement = document.createElement('option');
                optionElement.value = opt.option_id;
                const stockText = opt.stock_quantity <= 0 ? `(${t('Epuise')})` : `(Stock: ${opt.stock_quantity})`;
                optionElement.textContent = `${opt.weight_grams}g - ${parseFloat(opt.price).toFixed(2)} € ${stockText}`;
                optionElement.dataset.price = opt.price;
                optionElement.dataset.stock = opt.stock_quantity;
                optionElement.dataset.weightGrams = opt.weight_grams;
                if(opt.stock_quantity <= 0) optionElement.disabled = true;
                weightOptionsSelect.appendChild(optionElement);
            });

            let firstEnabledIndex = -1;
            for(let i=0; i<weightOptionsSelect.options.length; i++) {
                if(!weightOptionsSelect.options[i].disabled) {
                    firstEnabledIndex = i;
                    break;
                }
            }
            if(firstEnabledIndex !== -1) weightOptionsSelect.selectedIndex = firstEnabledIndex;

            updatePriceFromSelection();
            weightOptionsSelect.addEventListener('change', updatePriceFromSelection);
        } else if (product.base_price !== null) {
            priceDisplay.textContent = `${parseFloat(product.base_price).toFixed(2)} €`;
            priceUnit.textContent = '';
            weightOptionsContainer.classList.add('hidden');
             if (product.stock_quantity <= 0) {
                addToCartButton.textContent = t('Epuise'); // i18n
                addToCartButton.disabled = true;
                addToCartButton.classList.replace('btn-gold','btn-secondary');
                addToCartButton.classList.add('opacity-50', 'cursor-not-allowed');
            }
        } else {
            priceDisplay.textContent = t('Prix_sur_demande'); // i18n
            priceUnit.textContent = '';
            weightOptionsContainer.classList.add('hidden');
            addToCartButton.textContent = t('Indisponible'); // i18n
            addToCartButton.disabled = true;
            addToCartButton.classList.add('opacity-50', 'cursor-not-allowed');
        }

        // Localized fields from API
        document.getElementById('product-species').textContent = product.species || 'N/A';
        document.getElementById('product-origin').textContent = product.origin || 'N/A';
        document.getElementById('product-seasonality').textContent = product.seasonality || 'N/A';
        document.getElementById('product-uses').textContent = product.ideal_uses || 'N/A';
        document.getElementById('product-sensory-description').innerHTML = product.long_description || product.sensory_description || t('Description_sensorielle_a_venir'); // i18n
        document.getElementById('product-pairing-suggestions').textContent = product.pairing_suggestions || t('Suggestions_daccords_a_venir'); // i18n

        const thumbnailGallery = document.getElementById('product-thumbnail-gallery');
        thumbnailGallery.innerHTML = '';
        if (product.image_urls_thumb && Array.isArray(product.image_urls_thumb) && product.image_urls_thumb.length > 0) {
            product.image_urls_thumb.forEach(thumbUrl => {
                if (typeof thumbUrl === 'string') {
                    const img = document.createElement('img');
                    img.src = thumbUrl;
                    img.alt = `${product.name} miniature`;
                    img.className = 'w-full h-24 object-cover rounded cursor-pointer hover:opacity-75 transition-opacity';
                    img.onclick = () => {
                        const mainImgToUpdate = document.getElementById('main-product-image');
                        if (mainImgToUpdate) mainImgToUpdate.src = thumbUrl;
                    };
                    img.onerror = () => { img.style.display='none'; };
                    thumbnailGallery.appendChild(img);
                }
            });
        }
        document.getElementById('product-reviews').textContent = t('Aucun_avis_pour_le_moment');


        if(loadingDiv) loadingDiv.style.display = 'none';
        if(contentDiv) contentDiv.style.display = 'grid';
    } catch (error) {
        if(loadingDiv) loadingDiv.innerHTML = `<p class="text-brand-truffle-burgundy">${t('Impossible_de_charger_les_details_du_produit')} ${error.message}</p>`; // i18n
        if(contentDiv) contentDiv.style.display = 'none';
    }
}

/**
 * Updates the displayed price and add-to-cart button state based on the selected weight option.
 */
function updatePriceFromSelection() {
    const weightOptionsSelect = document.getElementById('weight-options-select');
    const priceDisplay = document.getElementById('product-price-display');
    const priceUnit = document.getElementById('product-price-unit');
    const addToCartButton = document.getElementById('add-to-cart-button');

    if (!weightOptionsSelect || !priceDisplay || !priceUnit || !addToCartButton) {
        console.error("Un ou plusieurs éléments UI pour la sélection de prix sont manquants.");
        return;
    }

    const selectedOption = weightOptionsSelect.options[weightOptionsSelect.selectedIndex];

    if (selectedOption && selectedOption.value) {
        priceDisplay.textContent = `${parseFloat(selectedOption.dataset.price).toFixed(2)} €`;
        priceUnit.textContent = `/ ${selectedOption.dataset.weightGrams}g`;
        if (parseInt(selectedOption.dataset.stock) <= 0 || selectedOption.disabled) {
            addToCartButton.textContent = t('Epuise'); // i18n
            addToCartButton.disabled = true;
            addToCartButton.classList.replace('btn-gold','btn-secondary');
            addToCartButton.classList.add('opacity-50', 'cursor-not-allowed');
        } else {
            addToCartButton.textContent = t('Ajouter_au_Panier'); // i18n
            addToCartButton.disabled = false;
            addToCartButton.classList.replace('btn-secondary','btn-gold');
            addToCartButton.classList.remove('opacity-50', 'cursor-not-allowed');
        }
    } else if (currentProductDetail && currentProductDetail.base_price === null && (!currentProductDetail.weight_options || currentProductDetail.weight_options.length === 0)) {
        addToCartButton.textContent = t('Indisponible'); // i18n
        addToCartButton.disabled = true;
        addToCartButton.classList.replace('btn-gold','btn-secondary');
        addToCartButton.classList.add('opacity-50', 'cursor-not-allowed');
    } else if (currentProductDetail && currentProductDetail.base_price !== null) {
        if (currentProductDetail.stock_quantity <= 0) {
            addToCartButton.textContent = t('Epuise'); // i18n
            addToCartButton.disabled = true;
            addToCartButton.classList.replace('btn-gold','btn-secondary');
            addToCartButton.classList.add('opacity-50', 'cursor-not-allowed');
        } else {
             addToCartButton.textContent = t('Ajouter_au_Panier'); // i18n
            addToCartButton.disabled = false;
            addToCartButton.classList.replace('btn-secondary','btn-gold');
            addToCartButton.classList.remove('opacity-50', 'cursor-not-allowed');
        }
    }
}

/**
 * Updates the quantity input on the product detail page.
 * @param {number} change - The amount to change the quantity by (+1 or -1).
 */
function updateDetailQuantity(change) {
    const quantityInput = document.getElementById('quantity-select');
    if (!quantityInput) return;
    let currentValue = parseInt(quantityInput.value);
    currentValue += change;
    if (currentValue < 1) currentValue = 1;
    if (currentValue > 10) currentValue = 10;
    quantityInput.value = currentValue;
}

website/js/cart.js
JavaScript

// website/js/cart.js
// Manages shopping cart functionality using localStorage.

/**
 * Retrieves the cart from localStorage.
 * @returns {Array<object>} The cart items array.
 */
function getCart() {
    const cartString = localStorage.getItem('maisonTruvraCart');
    try {
        return cartString ? JSON.parse(cartString) : [];
    } catch (e) {
        console.error("Erreur parsing du panier depuis localStorage:", e);
        localStorage.removeItem('maisonTruvraCart');
        return [];
    }
}

/**
 * Saves the cart to localStorage and updates UI elements.
 * @param {Array<object>} cart - The cart items array to save.
 */
function saveCart(cart) {
    localStorage.setItem('maisonTruvraCart', JSON.stringify(cart));
    updateCartCountDisplay(); // Assumes in ui.js or main.js
    if (document.body.id === 'page-panier') {
        displayCartItems();
    }
}

/**
 * Adds a product to the shopping cart or updates its quantity if it already exists.
 * @param {object} product - The product object (should contain localized name).
 * @param {number} quantity - The quantity to add.
 * @param {object|null} [selectedOptionDetails=null] - Details of the selected weight option.
 * @returns {boolean} True if the item was added/updated successfully, false otherwise.
 */
function addToCart(product, quantity, selectedOptionDetails = null) {
    let cart = getCart();
    const productId = product.id;
    const cartItemId = selectedOptionDetails ? `${productId}_${selectedOptionDetails.option_id}` : productId.toString();

    const existingItemIndex = cart.findIndex(item => item.cartId === cartItemId);

    const stockAvailable = selectedOptionDetails ? parseInt(selectedOptionDetails.stock) : parseInt(product.stock_quantity);
    // product.name is already localized from the API response
    const itemNameForMessage = product.name + (selectedOptionDetails ? ` (${selectedOptionDetails.weight_grams}g)` : '');


    if (existingItemIndex > -1) {
        const newQuantity = cart[existingItemIndex].quantity + quantity;
        if (newQuantity > stockAvailable) {
            showGlobalMessage(t('Stock_insuffisant_MAX_pour', { productName: itemNameForMessage, stock: stockAvailable }), "error"); // i18n
            return false;
        }
        cart[existingItemIndex].quantity = newQuantity;
    } else {
        if (quantity > stockAvailable) {
            showGlobalMessage(t('Stock_insuffisant_pour_MAX', { productName: itemNameForMessage, stock: stockAvailable }), "error"); // i18n
            return false;
        }
        const cartItem = {
            cartId: cartItemId,
            id: productId,
            name: product.name, // Already localized
            price: selectedOptionDetails ? parseFloat(selectedOptionDetails.price) : parseFloat(product.base_price),
            quantity: quantity,
            image: product.image_url_main || 'https://placehold.co/100x100/F5EEDE/7D6A4F?text=Img',
            variant: selectedOptionDetails ? `${selectedOptionDetails.weight_grams}g` : null,
            variant_option_id: selectedOptionDetails ? selectedOptionDetails.option_id : null,
            stock: stockAvailable
        };
        cart.push(cartItem);
    }
    saveCart(cart);
    return true;
}

/**
 * Handles adding a product to the cart from the product detail page.
 */
function handleAddToCartFromDetail() {
    if (!currentProductDetail) { // currentProductDetail from product.js
        showGlobalMessage(t('Details_du_produit_non_charges'), "error"); // i18n
        return;
    }
    const quantityInput = document.getElementById('quantity-select');
    if (!quantityInput) {
        console.error("Élément 'quantity-select' non trouvé.");
        return;
    }
    const quantity = parseInt(quantityInput.value);
    const weightOptionsSelect = document.getElementById('weight-options-select');
    let selectedOptionDetails = null;
    const productNameForMessage = currentProductDetail.name; // Already localized

    if (currentProductDetail.weight_options && currentProductDetail.weight_options.length > 0) {
        if (!weightOptionsSelect) {
            console.error("Élément 'weight-options-select' non trouvé.");
            showGlobalMessage(t('Erreur_configuration_page'), "error"); // Add this key
            return;
        }
        const selectedRawOption = weightOptionsSelect.options[weightOptionsSelect.selectedIndex];
        if (!selectedRawOption || selectedRawOption.disabled) {
            showGlobalMessage(t('Veuillez_selectionner_une_option_de_poids_valide_et_en_stock'), "error"); // i18n
            return;
        }
        selectedOptionDetails = {
            option_id: selectedRawOption.value,
            price: selectedRawOption.dataset.price,
            weight_grams: selectedRawOption.dataset.weightGrams,
            stock: parseInt(selectedRawOption.dataset.stock)
        };
        if (selectedOptionDetails.stock < quantity) {
            showGlobalMessage(t('Stock_insuffisant_pour_MAX', { productName: `${productNameForMessage} (${selectedOptionDetails.weight_grams}g)`, stock: selectedOptionDetails.stock }), "error"); // i18n
            return;
        }
    } else {
        if (currentProductDetail.stock_quantity < quantity) {
            showGlobalMessage(t('Stock_insuffisant_pour_MAX', { productName: productNameForMessage, stock: currentProductDetail.stock_quantity }), "error"); // i18n
            return;
        }
    }

    const addedSuccessfully = addToCart(currentProductDetail, quantity, selectedOptionDetails);
    if (addedSuccessfully) {
        openModal('add-to-cart-modal', productNameForMessage); // openModal from ui.js, productName is localized
    }
}

/**
 * Updates the quantity of an item in the cart.
 * @param {string} cartItemId - The unique ID of the cart item.
 * @param {number} newQuantity - The new quantity.
 */
function updateCartItemQuantity(cartItemId, newQuantity) {
    let cart = getCart();
    const itemIndex = cart.findIndex(item => item.cartId === cartItemId);
    if (itemIndex > -1) {
        if (newQuantity <= 0) {
            cart.splice(itemIndex, 1);
        } else if (newQuantity > cart[itemIndex].stock) {
            showGlobalMessage(t('Quantite_maximale_de_ atteinte_pour', {stock: cart[itemIndex].stock, productName: cart[itemIndex].name }), "info"); // i18n
            cart[itemIndex].quantity = cart[itemIndex].stock;
        } else {
            cart[itemIndex].quantity = newQuantity;
        }
        saveCart(cart);
    }
}

/**
 * Removes an item completely from the cart.
 * @param {string} cartItemId - The unique ID of the cart item.
 */
function removeCartItem(cartItemId) {
    let cart = getCart();
    cart = cart.filter(item => item.cartId !== cartItemId);
    saveCart(cart);
}

/**
 * Updates the cart item count display in the header.
 */
function updateCartCountDisplay() {
    const cart = getCart();
    const totalItems = cart.reduce((sum, item) => sum + item.quantity, 0);
    const cartCountDesktop = document.getElementById('cart-item-count');
    const cartCountMobile = document.getElementById('mobile-cart-item-count');

    if(cartCountDesktop) cartCountDesktop.textContent = totalItems;
    if(cartCountMobile) cartCountMobile.textContent = totalItems;
}

/**
 * Displays the cart items on the cart page.
 */
function displayCartItems() {
    const cartItemsContainer = document.getElementById('cart-items-container');
    const cartSummaryContainer = document.getElementById('cart-summary-container');

    if (!cartItemsContainer || !cartSummaryContainer) {
        console.error("Éléments du panier ou du résumé non trouvés.");
        return;
    }

    cartItemsContainer.innerHTML = '';
    const cart = getCart();

    if (cart.length === 0) {
        cartItemsContainer.innerHTML = `<p id="empty-cart-message" class="text-center text-brand-earth-brown py-8">${t('Votre_panier_est_actuellement_vide')} <a href="nos-produits.html" class="text-brand-classic-gold hover:underline" data-translate-key="Continuer_vos_achats">${t('Continuer_vos_achats')}</a></p>`;
        cartSummaryContainer.style.display = 'none';
    } else {
        cartSummaryContainer.style.display = 'block'; // Or 'flex'

        cart.forEach(item => {
            const itemTotal = item.price * item.quantity;
            const cartItemHTML = `
                <div class="cart-item" data-cart-item-id="${item.cartId}">
                    <div class="flex items-center flex-grow">
                        <img src="${item.image}" alt="${item.name}" class="cart-item-image">
                        <div>
                            <h3 class="text-md font-semibold text-brand-near-black">${item.name}</h3>
                            ${item.variant ? `<p class="text-xs text-brand-warm-taupe">${item.variant}</p>` : ''}
                            <p class="text-sm text-brand-classic-gold">${parseFloat(item.price).toFixed(2)} €</p>
                        </div>
                    </div>
                    <div class="flex items-center space-x-2 sm:space-x-3">
                        <div class="quantity-input-controls flex items-center">
                            <button onclick="changeCartItemQuantity('${item.cartId}', -1)" class="px-2 py-0.5 border border-brand-warm-taupe/50 text-brand-near-black hover:bg-brand-warm-taupe/20 text-sm rounded-l">-</button>
                            <input type="number" value="${item.quantity}" min="1" max="${item.stock}" class="quantity-input cart-item-quantity-input w-10 sm:w-12 text-center border-y border-brand-warm-taupe/50 py-1 text-sm appearance-none" readonly data-id="${item.cartId}">
                            <button onclick="changeCartItemQuantity('${item.cartId}', 1)" class="px-2 py-0.5 border border-brand-warm-taupe/50 text-brand-near-black hover:bg-brand-warm-taupe/20 text-sm rounded-r">+</button>
                        </div>
                        <p class="text-md font-semibold text-brand-near-black w-20 text-right">${itemTotal.toFixed(2)} €</p>
                        <button onclick="removeCartItem('${item.cartId}')" title="${t('Supprimer_larticle')}" class="text-brand-truffle-burgundy hover:text-red-700">
                            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-5 h-5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
                        </button>
                    </div>
                </div>
            `; // Add "Supprimer_larticle" to locales
            cartItemsContainer.insertAdjacentHTML('beforeend', cartItemHTML);
        });
        updateCartSummary();
    }
}

/**
 * Changes the quantity of a cart item via input controls.
 * @param {string} cartItemId - The unique ID of the cart item.
 * @param {number} change - The amount to change.
 */
function changeCartItemQuantity(cartItemId, change) {
    const inputElement = document.querySelector(`.cart-item-quantity-input[data-id="${cartItemId}"]`);
    if (inputElement) {
        let currentQuantity = parseInt(inputElement.value);
        updateCartItemQuantity(cartItemId, currentQuantity + change);
    }
}

/**
 * Updates the cart summary (subtotal, shipping, total).
 */
function updateCartSummary() {
    const cart = getCart();
    const subtotal = cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
    const shipping = subtotal > 0 && subtotal < 75 ? 7.50 : 0;
    const total = subtotal + shipping;

    const subtotalEl = document.getElementById('cart-subtotal');
    const shippingEl = document.getElementById('cart-shipping');
    const totalEl = document.getElementById('cart-total');

    if (subtotalEl) subtotalEl.textContent = `${subtotal.toFixed(2)} €`;
    if (shippingEl) {
        if (subtotal > 0) {
            shippingEl.textContent = shipping > 0 ? `${shipping.toFixed(2)} €` : t('Gratuite'); // i18n for "Gratuite"
        } else {
            shippingEl.textContent = 'N/A';
        }
    }
    if (totalEl) totalEl.textContent = `${total.toFixed(2)} €`;
    // Also update summary container display. If cart empty, it's hidden by displayCartItems.
     const cartSummaryContainer = document.getElementById('cart-summary-container');
    if(cartSummaryContainer) cartSummaryContainer.style.display = cart.length > 0 ? 'block' : 'none';

}

website/js/checkout.js
JavaScript

// website/js/checkout.js
// Handles the checkout process and payment page logic.

/**
 * Handles the checkout form submission.
 * @param {Event} event - The form submission event.
 */
async function handleCheckout(event) {
    event.preventDefault();
    const form = event.target;
    clearFormErrors(form); // Assumes clearFormErrors is in ui.js
    const cart = getCart(); // Assumes getCart is in cart.js
    const currentUser = getCurrentUser(); // Assumes getCurrentUser is in auth.js

    if (cart.length === 0) {
        showGlobalMessage(t('Votre_panier_est_vide_Impossible_de_proceder_au_paiement'), "error"); // i18n
        return;
    }

    let isValid = true;
    const requiredFields = [
        { id: 'checkout-email', validator: validateEmail, messageKey: "E-mail_invalide" },
        { id: 'checkout-firstname', messageKey: "Prenom_requis" },
        { id: 'checkout-lastname', messageKey: "Nom_requis" },
        { id: 'checkout-address', messageKey: "Adresse_requise" },
        { id: 'checkout-zipcode', messageKey: "Code_postal_requis" },
        { id: 'checkout-city', messageKey: "Ville_requise" },
        { id: 'checkout-country', messageKey: "Pays_requis" }
    ];

    requiredFields.forEach(fieldInfo => {
        const fieldElement = form.querySelector(`#${fieldInfo.id}`);
        if (fieldElement) {
            const value = fieldElement.value.trim();
            if (!value || (fieldInfo.validator && !fieldInfo.validator(value))) {
                setFieldError(fieldElement, t(fieldInfo.messageKey)); // i18n
                isValid = false;
            }
        }
    });

    const paymentFields = ['card-number', 'card-expiry', 'card-cvc', 'cardholder-name'];
    paymentFields.forEach(id => {
        const field = form.querySelector(`#${id}`);
        if(field && !field.value.trim()){
            setFieldError(field, t('Ce_champ_de_paiement_est_requis')); // i18n
            isValid = false;
        }
    });

    if (!isValid) {
        showGlobalMessage(t('Veuillez_corriger_les_erreurs_dans_le_formulaire_de_paiement'), "error"); // i18n
        return;
    }

    const customerEmail = currentUser ? currentUser.email : form.querySelector('#checkout-email').value;
    const shippingAddress = {
        firstname: form.querySelector('#checkout-firstname').value,
        lastname: form.querySelector('#checkout-lastname').value,
        address: form.querySelector('#checkout-address').value,
        apartment: form.querySelector('#checkout-apartment') ? form.querySelector('#checkout-apartment').value : '',
        zipcode: form.querySelector('#checkout-zipcode').value,
        city: form.querySelector('#checkout-city').value,
        country: form.querySelector('#checkout-country').value,
        phone: form.querySelector('#checkout-phone') ? form.querySelector('#checkout-phone').value : ''
    };

    const orderData = {
        customerEmail: customerEmail,
        shippingAddress: shippingAddress,
        cartItems: cart.map(item => ({
            id: item.id,
            name: item.name, // Name is already localized in the cart
            quantity: item.quantity,
            price: item.price,
            variant: item.variant,
            variant_option_id: item.variant_option_id
        })),
        userId: currentUser ? currentUser.id : null,
        lang: getCurrentLang() // Send language with order for confirmation email, etc.
    };

    showGlobalMessage(t('Traitement_de_la_commande'), "info", 60000); // i18n

    try {
        const result = await makeApiRequest('/orders/checkout', 'POST', orderData, !!currentUser);
        if (result.success) {
            showGlobalMessage(t('Commande_passee_avec_succes_Montant_total', { orderId: result.orderId, totalAmount: parseFloat(result.totalAmount).toFixed(2) }), "success", 10000); // i18n
            saveCart([]);
            sessionStorage.setItem('lastOrderDetails', JSON.stringify(result));
            window.location.href = 'confirmation-commande.html';
        } else {
            showGlobalMessage(result.message || t('Echec_de_la_commande'), "error"); // i18n
        }
    } catch (error) {
        // Error message shown by makeApiRequest
        console.error("Erreur lors du checkout:", error);
    }
}

/**
 * Populates the checkout page.
 */
function initializeCheckoutPage() {
    const checkoutForm = document.getElementById('checkout-form');
    if (checkoutForm) {
        checkoutForm.addEventListener('submit', handleCheckout);
    }

    const currentUser = getCurrentUser();
    const checkoutEmailField = document.getElementById('checkout-email');
    const checkoutFirstname = document.getElementById('checkout-firstname');
    const checkoutLastname = document.getElementById('checkout-lastname');

    if(currentUser && checkoutEmailField) {
        checkoutEmailField.value = currentUser.email;
        checkoutEmailField.readOnly = true;
        checkoutEmailField.classList.add('bg-gray-100', 'cursor-not-allowed');
    }
    if(currentUser && checkoutFirstname && currentUser.prenom) {
        checkoutFirstname.value = currentUser.prenom;
    }
    if(currentUser && checkoutLastname && currentUser.nom) {
        checkoutLastname.value = currentUser.nom;
    }

    const cart = getCart();
    const checkoutCartSummary = document.getElementById('checkout-cart-summary');
    if(checkoutCartSummary && cart.length > 0){
        let summaryHtml = `<h3 class="text-lg font-serif text-brand-near-black mb-4" data-translate-key="Recapitulatif_de_votre_commande">${t('Recapitulatif_de_votre_commande')}</h3><ul class="space-y-2 mb-4">`;
        let subtotal = 0;
        cart.forEach(item => {
            summaryHtml += `<li class="flex justify-between text-sm"><span>${item.name} ${item.variant ? '('+item.variant+')' : ''} x ${item.quantity}</span> <span>${(item.price * item.quantity).toFixed(2)}€</span></li>`;
            subtotal += item.price * item.quantity;
        });
        const shipping = subtotal > 0 && subtotal < 75 ? 7.50 : 0;
        const total = subtotal + shipping;
        summaryHtml += `</ul>
            <div class="border-t border-brand-warm-taupe/30 pt-4 space-y-1">
                <p class="flex justify-between text-sm"><span data-translate-key="Sous-total">${t('Sous-total')}</span> <span>${subtotal.toFixed(2)}€</span></p>
                <p class="flex justify-between text-sm"><span data-translate-key="Livraison">${t('Livraison')}</span> <span>${shipping > 0 ? shipping.toFixed(2)+'€' : t('Gratuite')}</span></p>
                <p class="flex justify-between text-lg font-semibold text-brand-near-black"><span data-translate-key="Total">${t('Total')}</span> <span>${total.toFixed(2)}€</span></p>
            </div>
        `;
        checkoutCartSummary.innerHTML = summaryHtml;
    } else if (checkoutCartSummary) {
        checkoutCartSummary.innerHTML = `<p data-translate-key="Votre_panier_est_actuellement_vide">${t('Votre_panier_est_actuellement_vide')}</p>`;
        const proceedButton = document.querySelector('#checkout-form button[type="submit"]');
        if(proceedButton) proceedButton.disabled = true;
    }
     // Translate static parts of the form if not done by translatePageElements
    if(window.translatePageElements) translatePageElements();
}

/**
 * Initializes the order confirmation page.
 */
function initializeConfirmationPage() {
    const orderDetailsString = sessionStorage.getItem('lastOrderDetails');
    const confirmationOrderIdEl = document.getElementById('confirmation-order-id');
    const confirmationTotalAmountEl = document.getElementById('confirmation-total-amount');
    const confirmationMessageEl = document.getElementById('confirmation-message');

    if (orderDetailsString && confirmationOrderIdEl && confirmationTotalAmountEl) {
        try {
            const orderDetails = JSON.parse(orderDetailsString);
            confirmationOrderIdEl.textContent = orderDetails.orderId;
            confirmationTotalAmountEl.textContent = parseFloat(orderDetails.totalAmount).toFixed(2);
        } catch (e) {
            console.error("Erreur parsing des détails de commande:", e);
            if(confirmationMessageEl) confirmationMessageEl.textContent = t('Erreur_affichage_details_commande'); // Add key
        }
    } else if (confirmationMessageEl) {
        confirmationMessageEl.textContent = t('Details_de_la_commande_non_trouves'); // i18n
        if(confirmationOrderIdEl) confirmationOrderIdEl.textContent = "N/A";
        if(confirmationTotalAmountEl) confirmationTotalAmountEl.textContent = "N/A";
    }
    if(window.translatePageElements) translatePageElements();
}

website/js/auth.js
JavaScript

// website/js/auth.js
// Handles user authentication, session management, and account display.

/**
 * Retrieves the authentication token from session storage.
 * @returns {string|null} The auth token or null if not found.
 */
function getAuthToken() {
    return sessionStorage.getItem('authToken');
}

/**
 * Sets or removes the authentication token in session storage.
 * @param {string|null} token - The token to set, or null to remove.
 */
function setAuthToken(token) {
    if (token) {
        sessionStorage.setItem('authToken', token);
    } else {
        sessionStorage.removeItem('authToken');
    }
}

/**
 * Retrieves the current user data from session storage.
 * @returns {object|null} The user object or null if not found/invalid.
 */
function getCurrentUser() {
    const userString = sessionStorage.getItem('currentUser');
    if (userString) {
        try {
            return JSON.parse(userString);
        } catch (e) {
            console.error(t('Erreur_lors_du_parsing_des_donnees_utilisateur'), e); // i18n
            sessionStorage.removeItem('currentUser');
            sessionStorage.removeItem('authToken');
            return null;
        }
    }
    return null;
}

/**
 * Sets the current user data in session storage and updates login state.
 * @param {object|null} userData - The user data object, or null to clear.
 * @param {string|null} [token=null] - The auth token, if setting a new user.
 */
function setCurrentUser(userData, token = null) {
    if (userData) {
        sessionStorage.setItem('currentUser', JSON.stringify(userData));
        if (token) setAuthToken(token);
    } else {
        sessionStorage.removeItem('currentUser');
        sessionStorage.removeItem('authToken');
    }
    updateLoginState();
    if (typeof updateCartCountDisplay === 'function') updateCartCountDisplay();
}

/**
 * Logs out the current user.
 */
async function logoutUser() {
    setCurrentUser(null);
    showGlobalMessage(t('Deconnecte_message'), "info"); // i18n

    if (document.body.id === 'page-compte' || document.body.id === 'page-paiement') {
        window.location.href = 'compte.html';
    } else {
        updateLoginState();
        if (document.body.id === 'page-compte') displayAccountDashboard();
    }
}

/**
 * Updates the UI elements (account links) based on the current login state.
 */
function updateLoginState() {
    const currentUser = getCurrentUser();
    const accountLinkTextDesktop = document.getElementById('account-link-text-desktop');
    const accountLinkTextMobile = document.getElementById('account-link-text-mobile'); // Assuming you added this ID

    // Fallback to querySelector if specific IDs aren't present (e.g. if header.html wasn't updated)
    const accountLinkDesktopContainer = document.querySelector('header nav a[href="compte.html"]');
    const accountLinkMobileContainer = document.querySelector('#mobile-menu-dropdown a[href="compte.html"]');


    const desktopTextElement = accountLinkTextDesktop || (accountLinkDesktopContainer ? accountLinkDesktopContainer.querySelector('span') : null);
    const mobileTextElement = accountLinkTextMobile || accountLinkMobileContainer;


    if (currentUser) {
        const userName = currentUser.prenom || t('Compte'); // i18n for "Compte"
        if (desktopTextElement) {
            desktopTextElement.textContent = userName;
            // Ensure SVG is present if we are only updating text of a span
            if (accountLinkDesktopContainer && !accountLinkDesktopContainer.querySelector('svg')) {
                 accountLinkDesktopContainer.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-7 h-7 text-brand-classic-gold"><path stroke-linecap="round" stroke-linejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" /></svg> <span class="ml-1 text-xs">${userName}</span>`;
            }
        }
        if (mobileTextElement) mobileTextElement.textContent = `${t('Mon_Compte_Menu')} (${userName})`; // i18n
    } else {
        if (desktopTextElement) {
            desktopTextElement.textContent = t('Mon_Compte_Menu'); // i18n
             if (accountLinkDesktopContainer && !accountLinkDesktopContainer.querySelector('svg')) {
                 accountLinkDesktopContainer.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-7 h-7"><path stroke-linecap="round" stroke-linejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" /></svg> <span class="ml-1 text-xs">${t('Mon_Compte_Menu')}</span>`;
            }
        }
        if (mobileTextElement) mobileTextElement.textContent = t('Mon_Compte_Menu'); // i18n
    }
}


/**
 * Handles the login form submission.
 */
async function handleLogin(event) {
    event.preventDefault();
    const loginForm = event.target;
    clearFormErrors(loginForm);
    const emailField = loginForm.querySelector('#login-email');
    const passwordField = loginForm.querySelector('#login-password');
    const email = emailField.value;
    const password = passwordField.value;
    const loginMessageElement = document.getElementById('login-message');

    let isValid = true;
    if (loginMessageElement) loginMessageElement.textContent = '';

    if (!email || !validateEmail(email)) {
        setFieldError(emailField, t('Veuillez_entrer_une_adresse_e-mail_valide')); // i18n
        isValid = false;
    }
    if (!password) {
        setFieldError(passwordField, t('Veuillez_entrer_votre_mot_de_passe')); // i18n
        isValid = false;
    }
    if (!isValid) {
        showGlobalMessage(t('Veuillez_corriger_les_erreurs_dans_le_formulaire'), "error"); // i18n
        return;
    }

    showGlobalMessage(t('Connexion_en_cours'), "info", 60000); // i18n

    try {
        const result = await makeApiRequest('/auth/login', 'POST', { email, password }); // makeApiRequest sends lang
        if (result.success && result.user && result.token) {
            setCurrentUser(result.user, result.token);
            showGlobalMessage(result.message || t('Connexion_reussie'), "success"); // i18n "Connexion_reussie"
            loginForm.reset();
            displayAccountDashboard();
        } else {
            setCurrentUser(null);
            const generalErrorMessage = result.message || t('Echec_de_la_connexion_Verifiez_vos_identifiants'); // i18n
            showGlobalMessage(generalErrorMessage, "error");
            if (loginMessageElement) loginMessageElement.textContent = generalErrorMessage;
            setFieldError(emailField, " ");
            setFieldError(passwordField, generalErrorMessage);
        }
    } catch (error) {
        setCurrentUser(null);
        if (loginMessageElement) loginMessageElement.textContent = error.message || t('Erreur_de_connexion_au_serveur'); // i18n
    }
}

/**
 * Handles the registration form submission.
 */
async function handleRegistrationForm(event) {
    event.preventDefault();
    const form = event.target;
    clearFormErrors(form);

    const emailField = form.querySelector('#register-email');
    const passwordField = form.querySelector('#register-password');
    const confirmPasswordField = form.querySelector('#register-confirm-password');
    const nomField = form.querySelector('#register-nom');
    const prenomField = form.querySelector('#register-prenom');

    let isValid = true;

    if (!emailField.value || !validateEmail(emailField.value)) {
        setFieldError(emailField, t('E-mail_invalide')); isValid = false; // i18n
    }
    if (!nomField.value.trim()) {
        setFieldError(nomField, t('Nom_requis')); isValid = false; // i18n
    }
    if (!prenomField.value.trim()) {
        setFieldError(prenomField, t('Prenom_requis')); isValid = false; // i18n
    }
    if (passwordField.value.length < 8) {
        setFieldError(passwordField, t('Mot_de_passe_8_caracteres')); isValid = false; // i18n + add key
    }
    if (passwordField.value !== confirmPasswordField.value) {
        setFieldError(confirmPasswordField, t('Mots_de_passe_ne_correspondent_pas')); isValid = false; // i18n + add key
    }

    if (!isValid) {
        showGlobalMessage(t('Veuillez_corriger_les_erreurs_formulaire_inscription'), "error"); // i18n + add key
        return;
    }

    showGlobalMessage(t('Creation_du_compte'), "info"); // i18n + add key
    try {
        const result = await makeApiRequest('/auth/register', 'POST', {
            email: emailField.value, password: passwordField.value,
            nom: nomField.value, prenom: prenomField.value
        });
        if (result.success) {
            showGlobalMessage(result.message || t('Compte_cree_avec_succes_Veuillez_vous_connecter'), "success"); // i18n
            form.reset();
        } else {
            showGlobalMessage(result.message || t('Erreur_lors_de_linscription'), "error"); // i18n
        }
    } catch (error) {
        // Error message shown by makeApiRequest
        console.error("Erreur d'inscription:", error);
    }
}

/**
 * Displays the account dashboard.
 */
function displayAccountDashboard() {
    const loginRegisterSection = document.getElementById('login-register-section');
    const accountDashboardSection = document.getElementById('account-dashboard-section');
    const currentUser = getCurrentUser();

    if (currentUser && loginRegisterSection && accountDashboardSection) {
        loginRegisterSection.style.display = 'none';
        accountDashboardSection.style.display = 'block';

        const dashboardUsername = document.getElementById('dashboard-username');
        const dashboardEmail = document.getElementById('dashboard-email');
        if(dashboardUsername) dashboardUsername.textContent = `${currentUser.prenom || ''} ${currentUser.nom || ''}`;
        if(dashboardEmail) dashboardEmail.textContent = currentUser.email;

        const logoutButton = document.getElementById('logout-button');
        if (logoutButton) {
            logoutButton.removeEventListener('click', logoutUser);
            logoutButton.addEventListener('click', logoutUser);
        }
        loadOrderHistory();
    } else if (loginRegisterSection) {
        loginRegisterSection.style.display = 'block';
        if (accountDashboardSection) accountDashboardSection.style.display = 'none';
    }
    // Translate static parts of the dashboard if not done by translatePageElements on load
    if(window.translatePageElements) translatePageElements();
}

/**
 * Loads and displays the user's order history.
 */
async function loadOrderHistory() {
    const orderHistoryContainer = document.getElementById('order-history-container');
    if (!orderHistoryContainer) return;

    const currentUser = getCurrentUser();
    if (!currentUser) {
        orderHistoryContainer.innerHTML = `<p class="text-sm text-brand-warm-taupe italic">${t('Veuillez_vous_connecter_pour_voir_votre_historique')}</p>`; // i18n
        return;
    }

    orderHistoryContainer.innerHTML = `<p class="text-sm text-brand-warm-taupe italic">${t('Chargement_de_lhistorique_des_commandes')}</p>`; // i18n
    try {
        const ordersData = await makeApiRequest('/orders/history', 'GET', null, true); // makeApiRequest sends lang

        if (ordersData.success && ordersData.orders.length > 0) {
            let html = '<ul class="space-y-4">';
            ordersData.orders.forEach(order => {
                // Assuming order.status is a key that can be translated if needed, or backend sends localized status
                html += `
                    <li class="p-4 border border-brand-warm-taupe/50 rounded-md bg-white">
                        <div class="flex justify-between items-center mb-2">
                            <p class="font-semibold text-brand-near-black">${t('Commande_')} #${order.order_id || order.id}</p>
                            <span class="px-2 py-1 text-xs font-semibold rounded-full ${getOrderStatusClass(order.status)}">${t(order.status) || order.status}</span>
                        </div>
                        <p class="text-sm"><strong>${t('Date')}:</strong> ${new Date(order.order_date).toLocaleDateString(getCurrentLang())}</p>
                        <p class="text-sm"><strong>${t('Total')}:</strong> ${parseFloat(order.total_amount).toFixed(2)} €</p>
                        <button class="text-sm text-brand-classic-gold hover:underline mt-2" onclick="viewOrderDetail('${order.order_id || order.id}')" data-translate-key="Voir_details">${t('Voir_details')}</button>
                    </li>
                `; // Add Commande_, Date, Total, Voir_details to locales
            });
            html += '</ul>';
            orderHistoryContainer.innerHTML = html;
        } else {
            orderHistoryContainer.innerHTML = `<p class="text-sm text-brand-warm-taupe italic">${t('Vous_navez_aucune_commande_pour_le_moment')}</p>`; // i18n
        }
    } catch (error) {
        orderHistoryContainer.innerHTML = `<p class="text-sm text-brand-truffle-burgundy italic">${t('Impossible_de_charger_lhistorique_des_commandes')} ${error.message}</p>`; // i18n
    }
}

/**
 * Placeholder function to view order details.
 * @param {string} orderId - The ID of the order.
 */
function viewOrderDetail(orderId) {
    showGlobalMessage(`${t('Detail_commande_')} #${orderId} (${t('Fonctionnalite_a_implementer')}).`, 'info'); // i18n
    console.log("Voir détails pour commande:", orderId);
}

admin/admin_manage_products.html
HTML

<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Gérer les Produits - Admin Maison Trüvra</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Playfair+Display:ital,wght@0,400;0,700;1,400&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="admin_styles.css">
</head>
<body class="bg-brand-cream text-brand-earth-brown font-inter">
    <div class="admin-layout">
        <aside class="admin-sidebar">
            <div class="p-6"><a href="admin_dashboard.html"><img src="../image_6be700.png" alt="Maison Trüvra Logo" class="h-16 mx-auto mb-6" onerror="this.alt='Logo Maison Trüvra'; this.src='https://placehold.co/150x60/F5EEDE/7D6A4F?text=Maison+Trüvra';"></a></div>
            <nav>
                <ul>
                    <li><a href="admin_dashboard.html" class="admin-nav-link">Tableau de Bord</a></li>
                    <li><a href="admin_manage_products.html" class="admin-nav-link active">Gérer les Produits</a></li>
                    <li><a href="admin_manage_inventory.html" class="admin-nav-link">Gérer les Stocks</a></li>
                    <li><a href="admin_manage_users.html" class="admin-nav-link">Gérer les Utilisateurs</a></li>
                    <li><a href="admin_manage_orders.html" class="admin-nav-link">Gérer les Commandes</a></li>
                </ul>
            </nav>
            <div class="p-6 mt-auto"><button id="admin-logout-button" class="btn-admin-secondary w-full">Déconnexion</button></div>
        </aside>

        <main class="admin-main-content">
            <header class="admin-main-header">
                <h1 class="text-3xl font-serif text-brand-near-black">Gestion des Produits</h1>
                <button id="show-add-product-form-button" class="btn-admin-primary">Ajouter un Nouveau Produit</button>
            </header>

            <section class="p-6">
                <div id="add-edit-product-section" class="admin-card p-6 mb-8" style="display:none;">
                    <h2 id="product-form-title" class="text-2xl font-serif text-brand-near-black mb-6">Ajouter un Nouveau Produit</h2>
                    <form id="product-form" class="space-y-5">
                        <input type="hidden" id="product-edit-id" value="">

                        <div>
                            <label for="product-id" class="form-label-admin">ID Produit (unique, ex: "truffe-noire-20g")</label>
                            <input type="text" id="product-id" name="id" class="form-input-admin" required>
                        </div>

                        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <label for="product-name-fr" class="form-label-admin">Nom du Produit (FR)</label>
                                <input type="text" id="product-name-fr" name="name_fr" class="form-input-admin" required>
                            </div>
                            <div>
                                <label for="product-name-en" class="form-label-admin">Product Name (EN)</label>
                                <input type="text" id="product-name-en" name="name_en" class="form-input-admin" required>
                            </div>
                        </div>

                        <div>
                            <label for="product-category" class="form-label-admin">Catégorie</label>
                            <select id="product-category" name="category" class="form-select-admin" required>
                                <option value="">Sélectionner une catégorie</option>
                                <option value="Fresh Truffles">Truffes Fraîches</option>
                                <option value="Truffle Oils">Huiles Truffées</option>
                                <option value="Truffle Sauces">Sauces Truffées</option>
                                <option value="Gift Sets">Coffrets Cadeaux</option>
                                <option value="Other">Autre</option>
                            </select>
                        </div>

                        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <label for="product-short-description-fr" class="form-label-admin">Description Courte (FR)</label>
                                <textarea id="product-short-description-fr" name="short_description_fr" rows="2" class="form-textarea-admin"></textarea>
                            </div>
                            <div>
                                <label for="product-short-description-en" class="form-label-admin">Short Description (EN)</label>
                                <textarea id="product-short-description-en" name="short_description_en" rows="2" class="form-textarea-admin"></textarea>
                            </div>
                        </div>
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <label for="product-long-description-fr" class="form-label-admin">Description Longue (FR)</label>
                                <textarea id="product-long-description-fr" name="long_description_fr" rows="4" class="form-textarea-admin"></textarea>
                            </div>
                            <div>
                                <label for="product-long-description-en" class="form-label-admin">Long Description (EN)</label>
                                <textarea id="product-long-description-en" name="long_description_en" rows="4" class="form-textarea-admin"></textarea>
                            </div>
                        </div>

                        <div>
                            <label for="product-image-url-main" class="form-label-admin">URL Image Principale</label>
                            <input type="url" id="product-image-url-main" name="image_url_main" class="form-input-admin" placeholder="https://example.com/image.jpg">
                        </div>
                        <div>
                            <label for="product-image-urls-thumb" class="form-label-admin">URLs Images Miniatures (JSON Array, ex: ["url1", "url2"])</label>
                            <input type="text" id="product-image-urls-thumb" name="image_urls_thumb" class="form-input-admin" placeholder='["https://example.com/thumb1.jpg"]'>
                        </div>

                        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div><label for="product-species-fr" class="form-label-admin">Espèce (FR)</label><input type="text" id="product-species-fr" name="species_fr" class="form-input-admin"></div>
                            <div><label for="product-species-en" class="form-label-admin">Species (EN)</label><input type="text" id="product-species-en" name="species_en" class="form-input-admin"></div>
                            <div><label for="product-origin-fr" class="form-label-admin">Origine (FR)</label><input type="text" id="product-origin-fr" name="origin_fr" class="form-input-admin"></div>
                            <div><label for="product-origin-en" class="form-label-admin">Origin (EN)</label><input type="text" id="product-origin-en" name="origin_en" class="form-input-admin"></div>
                            <div><label for="product-seasonality-fr" class="form-label-admin">Saisonnalité (FR)</label><input type="text" id="product-seasonality-fr" name="seasonality_fr" class="form-input-admin"></div>
                            <div><label for="product-seasonality-en" class="form-label-admin">Seasonality (EN)</label><input type="text" id="product-seasonality-en" name="seasonality_en" class="form-input-admin"></div>
                        </div>
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div><label for="product-ideal-uses-fr" class="form-label-admin">Utilisations Idéales (FR)</label><input type="text" id="product-ideal-uses-fr" name="ideal_uses_fr" class="form-input-admin"></div>
                            <div><label for="product-ideal-uses-en" class="form-label-admin">Ideal Uses (EN)</label><input type="text" id="product-ideal-uses-en" name="ideal_uses_en" class="form-input-admin"></div>
                        </div>
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div><label for="product-sensory-description-fr" class="form-label-admin">Description Sensorielle (FR)</label><textarea id="product-sensory-description-fr" name="sensory_description_fr" rows="3" class="form-textarea-admin"></textarea></div>
                            <div><label for="product-sensory-description-en" class="form-label-admin">Sensory Description (EN)</label><textarea id="product-sensory-description-en" name="sensory_description_en" rows="3" class="form-textarea-admin"></textarea></div>
                        </div>
                         <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div><label for="product-pairing-suggestions-fr" class="form-label-admin">Suggestions d'Accords (FR)</label><textarea id="product-pairing-suggestions-fr" name="pairing_suggestions_fr" rows="3" class="form-textarea-admin"></textarea></div>
                            <div><label for="product-pairing-suggestions-en" class="form-label-admin">Pairing Suggestions (EN)</label><textarea id="product-pairing-suggestions-en" name="pairing_suggestions_en" rows="3" class="form-textarea-admin"></textarea></div>
                        </div>

                        <hr class="my-6 border-brand-warm-taupe/30">
                        <h3 class="text-lg font-semibold text-brand-near-black">Prix et Stock</h3>

                        <div>
                            <label for="product-base-price" class="form-label-admin">Prix de Base (si pas de variantes de poids)</label>
                            <input type="number" id="product-base-price" name="base_price" step="0.01" class="form-input-admin" placeholder="Ex: 25.00">
                        </div>
                        <div id="simple-product-stock-section">
                             <label for="product-initial-stock-quantity" class="form-label-admin">Stock Initial (pour produit simple)</label>
                            <input type="number" id="product-initial-stock-quantity" name="initial_stock_quantity" step="1" min="0" class="form-input-admin" placeholder="Ex: 50">
                        </div>

                        <div class="mt-4">
                            <label class="form-label-admin">Options de Poids/Prix (si applicable)</label>
                            <div id="weight-options-container" class="space-y-3">
                                </div>
                            <button type="button" id="add-weight-option-button" class="btn-admin-secondary text-xs mt-2">Ajouter une Option de Poids</button>
                        </div>

                        <hr class="my-6 border-brand-warm-taupe/30">
                         <h3 class="text-lg font-semibold text-brand-near-black">Génération des Actifs (Passeport, QR, Étiquette)</h3>
                        <div>
                            <label for="product-numero-lot-manuel" class="form-label-admin">Numéro de Lot Manuel (pour actifs)</label>
                            <input type="text" id="product-numero-lot-manuel" name="numero_lot_manuel" class="form-input-admin" placeholder="Ex: LOT2024-XYZ">
                        </div>
                         <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <label for="product-date-conditionnement" class="form-label-admin">Date de Conditionnement (pour actifs)</label>
                                <input type="date" id="product-date-conditionnement" name="date_conditionnement" class="form-input-admin">
                            </div>
                            <div>
                                <label for="product-ddm" class="form-label-admin">DDM (Date de Durabilité Minimale - pour actifs)</label>
                                <input type="date" id="product-ddm" name="ddm" class="form-input-admin">
                            </div>
                        </div>
                        <div>
                            <label for="product-specific-weight-for-label" class="form-label-admin">Poids Spécifique pour Étiquette (si différent des options)</label>
                            <input type="text" id="product-specific-weight-for-label" name="specific_weight_for_label" class="form-input-admin" placeholder="Ex: 100g (pour huile, etc.)">
                        </div>
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <label for="product-ingredients-for-label-fr" class="form-label-admin">Ingrédients Étiquette (FR)</label>
                                <textarea id="product-ingredients-for-label-fr" name="ingredients_for_label_fr" rows="2" class="form-textarea-admin" placeholder="Ingrédients..."></textarea>
                            </div>
                            <div>
                                <label for="product-ingredients-for-label-en" class="form-label-admin">Label Ingredients (EN)</label>
                                <textarea id="product-ingredients-for-label-en" name="ingredients_for_label_en" rows="2" class="form-textarea-admin" placeholder="Ingredients..."></textarea>
                            </div>
                        </div>


                        <div class="flex items-center mt-4">
                            <input type="checkbox" id="product-is-published" name="is_published" class="form-checkbox-admin mr-2" checked>
                            <label for="product-is-published" class="text-sm text-brand-near-black">Publier ce produit sur la boutique</label>
                        </div>

                        <div class="flex justify-end space-x-3 pt-4">
                            <button type="button" id="cancel-product-form-button" class="btn-admin-secondary">Annuler</button>
                            <button type="submit" class="btn-admin-primary">Enregistrer Produit</button>
                        </div>
                    </form>
                    <div id="product-assets-preview-section" class="mt-6 p-4 border-t border-brand-warm-taupe/30 rounded-md bg-brand-cream/50" style="display:none;">
                        <h4 class="text-md font-semibold text-brand-near-black mb-3">Aperçu des Actifs Générés :</h4>
                        <div id="product-assets-links" class="space-y-2 text-sm">
                            </div>
                        <p class="text-xs text-brand-warm-taupe mt-3">
                            Note: Les chemins des images QR Code et Étiquette sont relatifs au dossier statique du site. L'URL du Passeport est l'URL publique.
                        </p>
                    </div>
                </div>

                <div class="admin-card overflow-x-auto">
                    <h2 class="text-2xl font-serif text-brand-near-black p-6">Liste des Produits</h2>
                    <table id="products-table" class="admin-table">
                        <thead>
                            <tr>
                                <th scope="col">ID</th>
                                <th scope="col">Nom (FR)</th>
                                <th scope="col">Nom (EN)</th>
                                <th scope="col">Catégorie</th>
                                <th scope="col">Prix Base / Variantes</th>
                                <th scope="col">Stock Total</th>
                                <th scope="col">Publié</th>
                                <th scope="col">Actions</th>
                            </tr>
                        </thead>
                        <tbody id="products-table-body">
                            <tr><td colspan="8" class="text-center py-4">Chargement des produits...</td></tr>
                        </tbody>
                    </table>
                </div>
            </section>
        </main>
    </div>
    <div id="admin-toast-container"><div id="admin-message-toast"><p id="admin-message-text"></p></div></div>
    <script src="js/admin_config.js"></script>
    <script src="js/admin_ui.js"></script>
    <script src="js/admin_api.js"></script>
    <script src="js/admin_auth.js"></script>
    <script src="js/admin_products.js"></script>
    <script src="js/admin_main.js"></script>
</body>
</html>

website/admin/js/admin_products.js
JavaScript

// website/admin/js/admin_products.js
// Logic for managing products in the Admin Panel.

let productsForAdmin = [];
let editingProductId = null;

function initializeProductManagement() {
    const showFormButton = document.getElementById('show-add-product-form-button');
    const productFormSection = document.getElementById('add-edit-product-section');
    const productForm = document.getElementById('product-form');
    const cancelFormButton = document.getElementById('cancel-product-form-button');
    const addWeightOptionButton = document.getElementById('add-weight-option-button');
    const assetsPreviewSection = document.getElementById('product-assets-preview-section');

    if (showFormButton && productFormSection) {
        showFormButton.addEventListener('click', () => {
            editingProductId = null;
            if (productForm) productForm.reset();
            clearFormErrors(productForm);
            const formTitle = document.getElementById('product-form-title');
            if (formTitle) formTitle.textContent = "Ajouter un Nouveau Produit";
            const productIdField = document.getElementById('product-id');
            if (productIdField) productIdField.readOnly = false;
            const weightOptionsContainer = document.getElementById('weight-options-container');
            if (weightOptionsContainer) weightOptionsContainer.innerHTML = '';
            if(assetsPreviewSection) assetsPreviewSection.style.display = 'none';
            productFormSection.style.display = 'block';
            showFormButton.style.display = 'none';
        });
    }

    if (cancelFormButton && productFormSection && showFormButton) {
        cancelFormButton.addEventListener('click', () => {
            productFormSection.style.display = 'none';
            showFormButton.style.display = 'inline-flex';
            if (productForm) productForm.reset();
            clearFormErrors(productForm);
            editingProductId = null;
            if(assetsPreviewSection) assetsPreviewSection.style.display = 'none';
        });
    }

    if (productForm) {
        productForm.addEventListener('submit', handleProductFormSubmit);
    }

    if (addWeightOptionButton) {
        addWeightOptionButton.addEventListener('click', () => addWeightOptionRow());
    }

    loadAdminProductsList();
}

function addWeightOptionRow(option = { option_id: null, weight_grams: '', price: '', initial_stock: '' }) {
    const container = document.getElementById('weight-options-container');
    if (!container) return;
    const optionIndex = container.children.length;
    const optionIdInputHtml = option.option_id ? `<input type="hidden" name="weight_options[${optionIndex}][option_id]" value="${option.option_id}">` : '';
    const rowHtml = `
        <div class="weight-option-row grid grid-cols-1 md:grid-cols-4 gap-3 items-center border p-3 rounded-md mb-2">
            ${optionIdInputHtml}
            <div><label class="text-xs font-medium text-brand-near-black">Poids (g) <span class="text-red-500">*</span></label><input type="number" name="weight_options[${optionIndex}][weight_grams]" class="form-input-admin text-sm p-2 mt-1" value="${option.weight_grams}" placeholder="Ex: 20" required></div>
            <div><label class="text-xs font-medium text-brand-near-black">Prix (€) <span class="text-red-500">*</span></label><input type="number" name="weight_options[${optionIndex}][price]" step="0.01" class="form-input-admin text-sm p-2 mt-1" value="${option.price}" placeholder="Ex: 75.00" required></div>
            <div><label class="text-xs font-medium text-brand-near-black">Stock Initial/Actuel <span class="text-red-500">*</span></label><input type="number" name="weight_options[${optionIndex}][initial_stock]" step="1" min="0" class="form-input-admin text-sm p-2 mt-1" value="${option.initial_stock}" placeholder="Ex: 10" required></div>
            <button type="button" class="btn-admin-danger text-xs py-1 px-2 self-end mt-4 md:mt-0" onclick="this.parentElement.remove()">Retirer</button>
        </div>`;
    container.insertAdjacentHTML('beforeend', rowHtml);
}

async function handleProductFormSubmit(event) {
    event.preventDefault();
    const form = event.target;
    const assetsPreviewSection = document.getElementById('product-assets-preview-section');
    const assetsLinksContainer = document.getElementById('product-assets-links');
    if(assetsPreviewSection) assetsPreviewSection.style.display = 'none';
    if(assetsLinksContainer) assetsLinksContainer.innerHTML = '';

    clearFormErrors(form);
    if (!validateProductForm(form)) return;

    const formData = new FormData(form);
    const productData = {};

     const fieldsToCollect = [
        'id', 'name_fr', 'name_en', 'category',
        'short_description_fr', 'short_description_en',
        'long_description_fr', 'long_description_en',
        'image_url_main', 'image_urls_thumb',
        'species_fr', 'species_en', 'origin_fr', 'origin_en',
        'seasonality_fr', 'seasonality_en', 'ideal_uses_fr', 'ideal_uses_en',
        'sensory_description_fr', 'sensory_description_en',
        'pairing_suggestions_fr', 'pairing_suggestions_en',
        'base_price', 'initial_stock_quantity', // initial_stock_quantity for simple products
        'is_published',
        // Asset generation related fields
        'numero_lot_manuel', 'date_conditionnement', 'ddm',
        'specific_weight_for_label',
        'ingredients_for_label_fr', 'ingredients_for_label_en'
    ];

    for (const fieldName of fieldsToCollect) {
        if (formData.has(fieldName)) {
            if (['base_price', 'initial_stock_quantity'].includes(fieldName)) {
                productData[fieldName] = formData.get(fieldName) ? parseFloat(formData.get(fieldName)) : null;
                if (fieldName === 'initial_stock_quantity' && productData[fieldName] === null) productData[fieldName] = 0;
            } else if (fieldName === 'is_published') {
                productData[fieldName] = form.querySelector(`#product-is-published`).checked;
            } else if (fieldName === 'image_urls_thumb') {
                try {
                    const thumbString = formData.get('image_urls_thumb');
                    productData.image_urls_thumb = thumbString.trim() ? JSON.parse(thumbString) : [];
                    if (!Array.isArray(productData.image_urls_thumb)) productData.image_urls_thumb = [];
                } catch (e) {
                    productData.image_urls_thumb = [];
                    setFieldError(form.querySelector('#product-image-urls-thumb'), "Format JSON invalide pour les miniatures.");
                    return; // Stop submission if JSON is invalid
                }
            } else {
                productData[fieldName] = formData.get(fieldName);
            }
        }
    }


    const weightOptions = [];
    document.querySelectorAll('#weight-options-container .weight-option-row').forEach((row) => {
        const optionIdField = row.querySelector(`input[name*="[option_id]"]`);
        const weightGramsField = row.querySelector(`input[name*="[weight_grams]"]`);
        const priceField = row.querySelector(`input[name*="[price]"]`);
        const initialStockField = row.querySelector(`input[name*="[initial_stock]"]`);
        if (weightGramsField && priceField && initialStockField) {
            const opt = {
                weight_grams: parseInt(weightGramsField.value),
                price: parseFloat(priceField.value),
                initial_stock: parseInt(initialStockField.value)
            };
            if(optionIdField && optionIdField.value) opt.option_id = parseInt(optionIdField.value);
            weightOptions.push(opt);
        }
    });

    if (weightOptions.length > 0) {
        productData.weight_options = weightOptions;
        productData.base_price = null;
        productData.initial_stock_quantity = 0; // Stock managed by variants
    } else {
        if (productData.base_price === null) { /* Validation should catch this */ }
        if(productData.initial_stock_quantity === null) productData.initial_stock_quantity = 0;
    }

    const method = editingProductId ? 'PUT' : 'POST';
    const endpoint = editingProductId ? `/products/${editingProductId}` : '/products';

    try {
        showAdminToast("Enregistrement du produit...", "info");
        const result = await adminApiRequest(endpoint, method, productData);

        if (result.success && result.product) {
            showAdminToast(result.message || "Produit enregistré avec succès!", "success");
            if (result.product.assets && assetsPreviewSection && assetsLinksContainer) {
                let linksHtml = '';
                if (result.product.assets.passport_url) {
                    linksHtml += `<p><strong>Passeport:</strong> <a href="${result.product.assets.passport_url}" target="_blank" class="text-brand-classic-gold hover:underline">${result.product.assets.passport_url}</a></p>`;
                }
                if (result.product.assets.qr_code_file_path) {
                    const qrUrl = `/static_assets/${result.product.assets.qr_code_file_path}`;
                    linksHtml += `<p><strong>QR Code:</strong> <a href="${qrUrl}" target="_blank" class="text-brand-classic-gold hover:underline">Voir QR Code</a> <img src="${qrUrl}" alt="QR Code Preview" class="h-20 w-20 inline-block ml-2 border"></p>`;
                }
                if (result.product.assets.label_file_path) {
                    const labelUrl = `/static_assets/${result.product.assets.label_file_path}`;
                    linksHtml += `<p><strong>Étiquette:</strong> <a href="${labelUrl}" target="_blank" class="text-brand-classic-gold hover:underline">Voir Étiquette</a></p>`;
                }
                if (linksHtml) {
                    assetsLinksContainer.innerHTML = linksHtml;
                    assetsPreviewSection.style.display = 'block';
                } else {
                    assetsLinksContainer.innerHTML = '<p class="text-brand-warm-taupe">Aucun actif spécifique généré.</p>';
                    assetsPreviewSection.style.display = 'block';
                }
            }
            editingProductId = result.product.id;
            document.getElementById('product-form-title').textContent = `Modifier le Produit: ${result.product.name_fr || result.product.name_en}`;
            document.getElementById('product-id').readOnly = true;
            loadAdminProductsList();
        }
    } catch (error) {
        console.error("Erreur soumission formulaire produit:", error);
    }
}

function validateProductForm(form) {
    let isValid = true;
    const requiredFields = [
        { id: 'product-name-fr', message: "Le nom du produit (FR) est requis." },
        { id: 'product-name-en', message: "Product Name (EN) is required." },
        { id: 'product-category', message: "La catégorie est requise." },
        // { id: 'product-short-description-fr', message: "Description courte (FR) requise."}, // Optional now
        // { id: 'product-short-description-en', message: "Short description (EN) required."},
        { id: 'product-image-url-main', message: "L'URL de l'image principale est requise." }
    ];
    if (!editingProductId) {
        requiredFields.unshift({ id: 'product-id', message: "L'ID du produit est requis." });
    }
    requiredFields.forEach(fieldInfo => {
        const field = form.querySelector(`#${fieldInfo.id}`);
        if (field && !field.value.trim()) {
            setFieldError(field, fieldInfo.message);
            isValid = false;
        }
    });

    const basePriceField = form.querySelector('#product-base-price');
    const weightOptionsRows = form.querySelectorAll('#weight-options-container .weight-option-row');
    if (!basePriceField.value.trim() && weightOptionsRows.length === 0) {
        setFieldError(basePriceField, "Un prix de base ou au moins une option de poids est requis.");
        isValid = false;
    }
    if (basePriceField.value.trim() && weightOptionsRows.length > 0) {
        setFieldError(basePriceField, "Ne pas spécifier de prix de base si des options de poids sont définies.");
        isValid = false;
    }
    // ... (rest of validation)
    return isValid;
}

async function loadAdminProductsList() {
    const tableBody = document.getElementById('products-table-body');
    if (!tableBody) return;
    tableBody.innerHTML = '<tr><td colspan="8" class="text-center py-4">Chargement des produits...</td></tr>';
    try {
        productsForAdmin = await adminApiRequest('/products');
        if (productsForAdmin.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="8" class="text-center py-4">Aucun produit trouvé.</td></tr>';
            return;
        }
        let rowsHtml = '';
        productsForAdmin.forEach(product => {
            let priceDisplay = product.base_price !== null ? `${parseFloat(product.base_price).toFixed(2)} €` : 'Variantes';
            let stockDisplay = product.stock_quantity !== undefined ? product.stock_quantity : 'N/A';
            rowsHtml += `
                <tr>
                    <td class="px-6 py-3 text-xs">${product.id}</td>
                    <td class="px-6 py-3 font-medium text-brand-near-black">${product.name_fr || product.name_en}</td>
                    <td class="px-6 py-3 font-medium text-brand-near-black">${product.name_en || product.name_fr}</td>
                    <td class="px-6 py-3">${product.category}</td>
                    <td class="px-6 py-3">${priceDisplay}</td>
                    <td class="px-6 py-3">${stockDisplay}</td>
                    <td class="px-6 py-3">${product.is_published ? '<span class="text-green-600 font-semibold">Oui</span>' : '<span class="text-red-600">Non</span>'}</td>
                    <td class="px-6 py-3 space-x-2 whitespace-nowrap">
                        <button onclick="editProduct('${product.id}')" class="btn-admin-secondary text-xs p-1.5">Éditer</button>
                    </td>
                </tr>`;
        });
        tableBody.innerHTML = rowsHtml;
    } catch (error) {
        tableBody.innerHTML = '<tr><td colspan="8" class="text-center py-4 text-red-600">Erreur de chargement des produits.</td></tr>';
    }
}

async function editProduct(productId) {
    editingProductId = productId;
    let productToEdit;
    const assetsPreviewSection = document.getElementById('product-assets-preview-section');
    const assetsLinksContainer = document.getElementById('product-assets-links');
    if(assetsPreviewSection) assetsPreviewSection.style.display = 'none';
    if(assetsLinksContainer) assetsLinksContainer.innerHTML = '';

    try {
        productToEdit = await adminApiRequest(`/products/${productId}`);
        if (!productToEdit) throw new Error("Produit non trouvé pour l'édition.");
    } catch (e) {
        showAdminToast("Impossible de charger les détails du produit pour l'édition.", "error");
        return;
    }

    const form = document.getElementById('product-form');
    if (!form) return;
    form.reset();
    clearFormErrors(form);

    document.getElementById('product-form-title').textContent = `Modifier le Produit: ${productToEdit.name_fr || productToEdit.name_en}`;
    document.getElementById('product-id').value = productToEdit.id;
    document.getElementById('product-id').readOnly = true;

    const fieldsToPopulate = [
        'name_fr', 'name_en', 'category',
        'short_description_fr', 'short_description_en',
        'long_description_fr', 'long_description_en',
        'image_url_main', 'image_urls_thumb',
        'species_fr', 'species_en', 'origin_fr', 'origin_en',
        'seasonality_fr', 'seasonality_en', 'ideal_uses_fr', 'ideal_uses_en',
        'sensory_description_fr', 'sensory_description_en',
        'pairing_suggestions_fr', 'pairing_suggestions_en',
        'base_price', // stock_quantity is handled by context
        'is_published',
        'numero_lot_manuel', 'date_conditionnement', 'ddm',
        'specific_weight_for_label',
        'ingredients_for_label_fr', 'ingredients_for_label_en'
    ];

    fieldsToPopulate.forEach(fieldName => {
        const elementId = `product-${fieldName.replace(/_/g, '-')}`; // Convert snake_case to kebab-case for IDs
        const element = document.getElementById(elementId);
        if (element) {
            if (fieldName === 'image_urls_thumb') {
                element.value = productToEdit.image_urls_thumb ? JSON.stringify(productToEdit.image_urls_thumb) : '[]';
            } else if (element.type === 'checkbox') {
                 element.checked = productToEdit[fieldName];
            }
            else {
                element.value = productToEdit[fieldName] || '';
            }
        } else {
            console.warn(`Element with ID ${elementId} not found for field ${fieldName}`);
        }
    });


    const weightOptionsContainer = document.getElementById('weight-options-container');
    weightOptionsContainer.innerHTML = '';
    if (productToEdit.weight_options && productToEdit.weight_options.length > 0) {
        productToEdit.weight_options.forEach(opt => addWeightOptionRow({
            option_id: opt.option_id,
            weight_grams: opt.weight_grams,
            price: opt.price,
            initial_stock: opt.stock_quantity
        }));
        document.getElementById('product-base-price').value = '';
        document.getElementById('product-initial-stock-quantity').value = '';
        document.getElementById('simple-product-stock-section').style.display = 'none';
    } else {
        document.getElementById('product-base-price').value = productToEdit.base_price !== null ? productToEdit.base_price : '';
        document.getElementById('product-initial-stock-quantity').value = productToEdit.stock_quantity || 0;
        document.getElementById('simple-product-stock-section').style.display = 'block';
    }

    if (productToEdit.assets && assetsPreviewSection && assetsLinksContainer) {
        let linksHtml = '';
        if (productToEdit.assets.passport_url) { linksHtml += `<p><strong>Passeport:</strong> <a href="${productToEdit.assets.passport_url}" target="_blank" class="text-brand-classic-gold hover:underline">${productToEdit.assets.passport_url}</a></p>`; }
        if (productToEdit.assets.qr_code_file_path) { linksHtml += `<p><strong>QR Code:</strong> <a href="/static_assets/${productToEdit.assets.qr_code_file_path}" target="_blank" class="text-brand-classic-gold hover:underline">Voir QR</a></p>`; }
        if (productToEdit.assets.label_file_path) { linksHtml += `<p><strong>Étiquette:</strong> <a href="/static_assets/${productToEdit.assets.label_file_path}" target="_blank" class="text-brand-classic-gold hover:underline">Voir Étiquette</a></p>`; }
        if (linksHtml) {
            assetsLinksContainer.innerHTML = linksHtml;
            assetsPreviewSection.style.display = 'block';
        }
    }

    document.getElementById('add-edit-product-section').style.display = 'block';
    document.getElementById('show-add-product-form-button').style.display = 'none';
    window.scrollTo(0, 0);
}

// Helper to check if a string is a valid URL (basic check)
function isValidUrl(string) {
    try {
        new URL(string);
        return true;
    } catch (_) {
        return false;
    }
}

This provides the core updates. You'll need to meticulously go through all your HTML files to add data-translate-key attributes to every piece of static text that needs translation and ensure your locale JSON files (fr.json, en.json) contain all these keys. Also, review all JavaScript files for any hardcoded strings that should be replaced with t('YOUR_KEY').Okay, I've updated the requested JavaScript files and the Admin HTML for product management to support bilingual content (French and English) and to integrate with the internationalization (i18n) logic we discussed.

Remember to create these new files in your website/js/ directory as previously outlined:

    website/js/locales/fr.json (Content provided in the previous detailed response)
    website/js/locales/en.json (Content provided in the previous detailed response)
    website/js/i18n.js (Content provided in the previous detailed response)

Ensure these files are correctly placed and that i18n.js is included before main.js in your HTML <script> tags.

Here are the updated files:
Updated JavaScript Files

These files now use the t() function from i18n.js for translatable strings and expect the backend API to return localized product data based on the lang parameter (which makeApiRequest now handles).

website/js/product.js
JavaScript

// website/js/product.js
// Handles fetching and displaying products on listing and detail pages.

let allProducts = []; // Cache for all products
let currentProductDetail = null; // Holds the data for the currently viewed product detail

/**
 * Fetches products from the API and displays them on the product listing page.
 * @param {string} [category='all'] - The category to filter by. 'all' fetches all products.
 */
async function fetchAndDisplayProducts(category = 'all') {
    const productsGrid = document.getElementById('products-grid');
    const loadingMessageElement = document.getElementById('products-loading-message');

    if (!productsGrid || !loadingMessageElement) {
        console.error("Product grid or loading message elements not found.");
        return;
    }

    loadingMessageElement.textContent = t('Chargement_des_produits');
    loadingMessageElement.style.display = 'block';
    productsGrid.innerHTML = '';

    try {
        const products = await makeApiRequest(
            category === 'all' ? '/products' : `/products?category=${encodeURIComponent(category)}`
        ); // makeApiRequest now sends 'lang'

        if (category === 'all' && products.length > 0) {
            allProducts = products;
        }

        const productsToDisplay = products; // API returns localized data

        if (productsToDisplay.length === 0) {
            loadingMessageElement.textContent = t('Aucun_produit_trouve_dans_cette_categorie');
            productsGrid.innerHTML = `<p class="col-span-full text-center text-brand-earth-brown py-8">${t('Aucun_produit_a_afficher')}</p>`;
        } else {
            loadingMessageElement.style.display = 'none';
            productsToDisplay.forEach(product => {
                const stock_quantity = product.stock_quantity !== undefined ? product.stock_quantity : 0;
                const stockMessage = stock_quantity > 5 ? t('En_stock') : (stock_quantity > 0 ? t('Stock_limite') : t('Epuise'));
                const stockClass = stock_quantity > 0 ? 'text-brand-deep-sage-green' : 'text-brand-truffle-burgundy';
                // product.name and product.short_description are now localized from the API
                const productCard = `
                    <div class="product-card">
                        <a href="produit-detail.html?id=${product.id}">
                            <img src="${product.image_url_main || 'https://placehold.co/400x300/F5EEDE/7D6A4F?text=Image+Indisponible'}" alt="${product.name}" class="w-full h-64 object-cover" onerror="this.onerror=null;this.src='https://placehold.co/400x300/F5EEDE/7D6A4F?text=Image+Error';">
                        </a>
                        <div class="product-card-content">
                            <h3 class="text-xl font-serif font-semibold text-brand-near-black mb-2">${product.name}</h3>
                            <p class="text-brand-earth-brown text-sm mb-3 h-16 overflow-hidden">${product.short_description || ''}</p>
                            <p class="text-lg font-semibold text-brand-truffle-burgundy mb-4">
                                ${product.starting_price !== "N/A" && product.starting_price !== null ? `${t('A_partir_de')} ${parseFloat(product.starting_price).toFixed(2)} €` : (product.base_price ? `${parseFloat(product.base_price).toFixed(2)} €` : t('Prix_sur_demande'))}
                            </p>
                             <p class="text-xs ${stockClass} mb-4">${stockMessage}</p>
                        </div>
                        <div class="product-card-footer p-4">
                            <a href="produit-detail.html?id=${product.id}" class="btn-primary block text-center text-sm py-2.5 ${stock_quantity <=0 ? 'opacity-50 cursor-not-allowed' : ''}">${stock_quantity <= 0 ? t('Epuise') : t('Voir_le_produit')}</a>
                        </div>
                    </div>
                `;
                productsGrid.insertAdjacentHTML('beforeend', productCard);
            });
        }
    } catch (error) {
        loadingMessageElement.textContent = t('Impossible_de_charger_les_produits');
        productsGrid.innerHTML = `<p class="col-span-full text-center text-brand-truffle-burgundy py-8">${t('Impossible_de_charger_les_produits')}. ${error.message}</p>`;
    }
}

function setupCategoryFilters() {
    const filterContainer = document.getElementById('product-categories-filter');
    if (filterContainer) {
        const buttons = filterContainer.querySelectorAll('button');
        buttons.forEach(button => {
            button.addEventListener('click', () => {
                buttons.forEach(btn => btn.classList.remove('filter-active', 'bg-brand-earth-brown', 'text-brand-cream'));
                button.classList.add('filter-active', 'bg-brand-earth-brown', 'text-brand-cream');
                const category = button.dataset.category;
                fetchAndDisplayProducts(category);
            });
        });
        if (typeof translatePageElements === 'function') translatePageElements(); // Translate filter buttons
    }
}

async function loadProductDetail() {
    const params = new URLSearchParams(window.location.search);
    const productId = params.get('id');
    const loadingDiv = document.getElementById('product-detail-loading');
    const contentDiv = document.getElementById('product-detail-content');

    if (!productId) {
        if(loadingDiv) loadingDiv.textContent = t('Aucun_produit_specifie');
        if(contentDiv) contentDiv.style.display = 'none';
        return;
    }

    if(loadingDiv) {
        loadingDiv.textContent = t('Chargement_des_details_du_produit');
        loadingDiv.style.display = 'block';
    }
    if(contentDiv) contentDiv.style.display = 'none';

    try {
        const product = await makeApiRequest(`/products/${productId}`); // API sends localized data
        currentProductDetail = product;

        document.getElementById('product-name').textContent = product.name;
        const mainImage = document.getElementById('main-product-image');
        mainImage.src = product.image_url_main || 'https://placehold.co/600x500/F5EEDE/7D6A4F?text=Image';
        mainImage.alt = product.name; // Alt text uses localized name
        mainImage.onerror = () => { mainImage.src = 'https://placehold.co/600x500/F5EEDE/7D6A4F?text=Image+Erreur'; };

        document.getElementById('product-short-description').textContent = product.short_description || '';

        const priceDisplay = document.getElementById('product-price-display');
        const priceUnit = document.getElementById('product-price-unit');
        const weightOptionsContainer = document.getElementById('weight-options-container');
        const weightOptionsSelect = document.getElementById('weight-options-select');
        const addToCartButton = document.getElementById('add-to-cart-button');
        addToCartButton.textContent = t('Ajouter_au_Panier');

        if (product.weight_options && product.weight_options.length > 0) {
            weightOptionsContainer.classList.remove('hidden');
            weightOptionsSelect.innerHTML = '';
            product.weight_options.forEach(opt => {
                const optionElement = document.createElement('option');
                optionElement.value = opt.option_id;
                const stockText = opt.stock_quantity <= 0 ? `(${t('Epuise')})` : `(Stock: ${opt.stock_quantity})`;
                optionElement.textContent = `${opt.weight_grams}g - ${parseFloat(opt.price).toFixed(2)} € ${stockText}`;
                optionElement.dataset.price = opt.price;
                optionElement.dataset.stock = opt.stock_quantity;
                optionElement.dataset.weightGrams = opt.weight_grams;
                if(opt.stock_quantity <= 0) optionElement.disabled = true;
                weightOptionsSelect.appendChild(optionElement);
            });

            let firstEnabledIndex = -1;
            for(let i=0; i<weightOptionsSelect.options.length; i++) {
                if(!weightOptionsSelect.options[i].disabled) { firstEnabledIndex = i; break; }
            }
            if(firstEnabledIndex !== -1) weightOptionsSelect.selectedIndex = firstEnabledIndex;

            updatePriceFromSelection();
            weightOptionsSelect.addEventListener('change', updatePriceFromSelection);
        } else if (product.base_price !== null) {
            priceDisplay.textContent = `${parseFloat(product.base_price).toFixed(2)} €`;
            priceUnit.textContent = '';
            weightOptionsContainer.classList.add('hidden');
             if (product.stock_quantity <= 0) {
                addToCartButton.textContent = t('Epuise');
                addToCartButton.disabled = true;
                addToCartButton.classList.replace('btn-gold','btn-secondary');
                addToCartButton.classList.add('opacity-50', 'cursor-not-allowed');
            }
        } else {
            priceDisplay.textContent = t('Prix_sur_demande');
            priceUnit.textContent = '';
            weightOptionsContainer.classList.add('hidden');
            addToCartButton.textContent = t('Indisponible');
            addToCartButton.disabled = true;
            addToCartButton.classList.add('opacity-50', 'cursor-not-allowed');
        }

        document.getElementById('product-species').textContent = product.species || 'N/A';
        document.getElementById('product-origin').textContent = product.origin || 'N/A';
        document.getElementById('product-seasonality').textContent = product.seasonality || 'N/A';
        document.getElementById('product-uses').textContent = product.ideal_uses || 'N/A';
        document.getElementById('product-sensory-description').innerHTML = product.long_description || product.sensory_description || t('Description_sensorielle_a_venir');
        document.getElementById('product-pairing-suggestions').textContent = product.pairing_suggestions || t('Suggestions_daccords_a_venir');
        document.getElementById('product-reviews').textContent = t('Aucun_avis_pour_le_moment');


        const thumbnailGallery = document.getElementById('product-thumbnail-gallery');
        thumbnailGallery.innerHTML = '';
        if (product.image_urls_thumb && Array.isArray(product.image_urls_thumb) && product.image_urls_thumb.length > 0) {
            product.image_urls_thumb.forEach(thumbUrl => {
                if (typeof thumbUrl === 'string') {
                    const img = document.createElement('img');
                    img.src = thumbUrl;
                    img.alt = `${product.name} miniature`; // Localized alt text
                    img.className = 'w-full h-24 object-cover rounded cursor-pointer hover:opacity-75 transition-opacity';
                    img.onclick = () => { document.getElementById('main-product-image').src = thumbUrl; };
                    img.onerror = () => { img.style.display='none'; };
                    thumbnailGallery.appendChild(img);
                }
            });
        }

        if(loadingDiv) loadingDiv.style.display = 'none';
        if(contentDiv) contentDiv.style.display = 'grid';
        // Translate any static text on this page if not covered by data-translate-key
        if (typeof translatePageElements === 'function') translatePageElements();
    } catch (error) {
        if(loadingDiv) loadingDiv.innerHTML = `<p class="text-brand-truffle-burgundy">${t('Impossible_de_charger_les_details_du_produit')} ${error.message}</p>`;
        if(contentDiv) contentDiv.style.display = 'none';
    }
}

function updatePriceFromSelection() {
    const weightOptionsSelect = document.getElementById('weight-options-select');
    const priceDisplay = document.getElementById('product-price-display');
    const priceUnit = document.getElementById('product-price-unit');
    const addToCartButton = document.getElementById('add-to-cart-button');

    if (!weightOptionsSelect || !priceDisplay || !priceUnit || !addToCartButton) return;

    const selectedOption = weightOptionsSelect.options[weightOptionsSelect.selectedIndex];

    if (selectedOption && selectedOption.value) {
        priceDisplay.textContent = `${parseFloat(selectedOption.dataset.price).toFixed(2)} €`;
        priceUnit.textContent = `/ ${selectedOption.dataset.weightGrams}g`;
        if (parseInt(selectedOption.dataset.stock) <= 0 || selectedOption.disabled) {
            addToCartButton.textContent = t('Epuise');
            addToCartButton.disabled = true;
            addToCartButton.classList.replace('btn-gold','btn-secondary');
            addToCartButton.classList.add('opacity-50', 'cursor-not-allowed');
        } else {
            addToCartButton.textContent = t('Ajouter_au_Panier');
            addToCartButton.disabled = false;
            addToCartButton.classList.replace('btn-secondary','btn-gold');
            addToCartButton.classList.remove('opacity-50', 'cursor-not-allowed');
        }
    } else if (currentProductDetail && currentProductDetail.base_price === null && (!currentProductDetail.weight_options || currentProductDetail.weight_options.length === 0)) {
        addToCartButton.textContent = t('Indisponible');
        addToCartButton.disabled = true;
    } else if (currentProductDetail && currentProductDetail.base_price !== null) {
        if (currentProductDetail.stock_quantity <= 0) {
            addToCartButton.textContent = t('Epuise');
            addToCartButton.disabled = true;
        } else {
            addToCartButton.textContent = t('Ajouter_au_Panier');
            addToCartButton.disabled = false;
        }
    }
}

function updateDetailQuantity(change) {
    const quantityInput = document.getElementById('quantity-select');
    if (!quantityInput) return;
    let currentValue = parseInt(quantityInput.value);
    currentValue += change;
    if (currentValue < 1) currentValue = 1;
    if (currentValue > 10) currentValue = 10;
    quantityInput.value = currentValue;
}

website/js/cart.js
JavaScript

// website/js/cart.js

function getCart() {
    const cartString = localStorage.getItem('maisonTruvraCart');
    try {
        return cartString ? JSON.parse(cartString) : [];
    } catch (e) {
        console.error(t('Erreur_parsing_panier_localStorage'), e); // Add key
        localStorage.removeItem('maisonTruvraCart');
        return [];
    }
}

function saveCart(cart) {
    localStorage.setItem('maisonTruvraCart', JSON.stringify(cart));
    updateCartCountDisplay();
    if (document.body.id === 'page-panier') {
        displayCartItems();
    }
}

function addToCart(product, quantity, selectedOptionDetails = null) {
    let cart = getCart();
    const productId = product.id;
    const cartItemId = selectedOptionDetails ? `${productId}_${selectedOptionDetails.option_id}` : productId.toString();
    const existingItemIndex = cart.findIndex(item => item.cartId === cartItemId);
    const stockAvailable = selectedOptionDetails ? parseInt(selectedOptionDetails.stock) : parseInt(product.stock_quantity);
    const itemNameForMessage = product.name + (selectedOptionDetails ? ` (${selectedOptionDetails.weight_grams}g)` : ''); // product.name is localized

    if (existingItemIndex > -1) {
        const newQuantity = cart[existingItemIndex].quantity + quantity;
        if (newQuantity > stockAvailable) {
            showGlobalMessage(t('Stock_insuffisant_MAX_pour', { productName: itemNameForMessage, stock: stockAvailable }), "error");
            return false;
        }
        cart[existingItemIndex].quantity = newQuantity;
    } else {
        if (quantity > stockAvailable) {
            showGlobalMessage(t('Stock_insuffisant_pour_MAX', { productName: itemNameForMessage, stock: stockAvailable }), "error");
            return false;
        }
        const cartItem = {
            cartId: cartItemId,
            id: productId,
            name: product.name, // Localized name
            price: selectedOptionDetails ? parseFloat(selectedOptionDetails.price) : parseFloat(product.base_price),
            quantity: quantity,
            image: product.image_url_main || 'https://placehold.co/100x100/F5EEDE/7D6A4F?text=Img',
            variant: selectedOptionDetails ? `${selectedOptionDetails.weight_grams}g` : null,
            variant_option_id: selectedOptionDetails ? selectedOptionDetails.option_id : null,
            stock: stockAvailable
        };
        cart.push(cartItem);
    }
    saveCart(cart);
    return true;
}

function handleAddToCartFromDetail() {
    if (!currentProductDetail) {
        showGlobalMessage(t('Details_du_produit_non_charges'), "error");
        return;
    }
    const quantityInput = document.getElementById('quantity-select');
    if (!quantityInput) {
        console.error("Element 'quantity-select' not found.");
        return;
    }
    const quantity = parseInt(quantityInput.value);
    const weightOptionsSelect = document.getElementById('weight-options-select');
    let selectedOptionDetails = null;
    const productNameForMessage = currentProductDetail.name; // Localized name

    if (currentProductDetail.weight_options && currentProductDetail.weight_options.length > 0) {
        // ... (rest of the logic, ensure messages use t())
        if (!weightOptionsSelect) {
            console.error("Element 'weight-options-select' not found.");
            showGlobalMessage(t('Erreur_configuration_page'), "error"); // Add to locales
            return;
        }
        const selectedRawOption = weightOptionsSelect.options[weightOptionsSelect.selectedIndex];
        if (!selectedRawOption || selectedRawOption.disabled) {
            showGlobalMessage(t('Veuillez_selectionner_une_option_de_poids_valide_et_en_stock'), "error");
            return;
        }
        selectedOptionDetails = { /* ... */ };
         if (selectedOptionDetails.stock < quantity) {
            showGlobalMessage(t('Stock_insuffisant_pour_MAX', { productName: `${productNameForMessage} (${selectedOptionDetails.weight_grams}g)`, stock: selectedOptionDetails.stock }), "error");
            return;
        }
    } else {
        if (currentProductDetail.stock_quantity < quantity) {
             showGlobalMessage(t('Stock_insuffisant_pour_MAX', { productName: productNameForMessage, stock: currentProductDetail.stock_quantity }), "error");
            return;
        }
    }

    const addedSuccessfully = addToCart(currentProductDetail, quantity, selectedOptionDetails);
    if (addedSuccessfully) {
        openModal('add-to-cart-modal', productNameForMessage);
    }
}

function updateCartItemQuantity(cartItemId, newQuantity) {
    let cart = getCart();
    const itemIndex = cart.findIndex(item => item.cartId === cartItemId);
    if (itemIndex > -1) {
        if (newQuantity <= 0) {
            cart.splice(itemIndex, 1);
        } else if (newQuantity > cart[itemIndex].stock) {
            showGlobalMessage(t('Quantite_maximale_de_ atteinte_pour', {stock: cart[itemIndex].stock, productName: cart[itemIndex].name }), "info");
            cart[itemIndex].quantity = cart[itemIndex].stock;
        } else {
            cart[itemIndex].quantity = newQuantity;
        }
        saveCart(cart);
    }
}

function removeCartItem(cartItemId) {
    let cart = getCart();
    cart = cart.filter(item => item.cartId !== cartItemId);
    saveCart(cart);
}

function updateCartCountDisplay() {
    const cart = getCart();
    const totalItems = cart.reduce((sum, item) => sum + item.quantity, 0);
    const cartCountDesktop = document.getElementById('cart-item-count');
    const cartCountMobile = document.getElementById('mobile-cart-item-count');
    if(cartCountDesktop) cartCountDesktop.textContent = totalItems;
    if(cartCountMobile) cartCountMobile.textContent = totalItems;
}

function displayCartItems() {
    const cartItemsContainer = document.getElementById('cart-items-container');
    const cartSummaryContainer = document.getElementById('cart-summary-container');
    if (!cartItemsContainer || !cartSummaryContainer) return;

    cartItemsContainer.innerHTML = '';
    const cart = getCart();

    if (cart.length === 0) {
        cartItemsContainer.innerHTML = `<p id="empty-cart-message" class="text-center text-brand-earth-brown py-8">${t('Votre_panier_est_actuellement_vide')} <a href="nos-produits.html" class="text-brand-classic-gold hover:underline" data-translate-key="Continuer_mes_achats">${t('Continuer_mes_achats')}</a></p>`;
        cartSummaryContainer.style.display = 'none';
    } else {
        cartSummaryContainer.style.display = 'block';
        cart.forEach(item => {
            const itemTotal = item.price * item.quantity;
            const cartItemHTML = `
                <div class="cart-item" data-cart-item-id="${item.cartId}">
                    <div class="flex items-center flex-grow">
                        <img src="${item.image}" alt="${item.name}" class="cart-item-image">
                        <div>
                            <h3 class="text-md font-semibold text-brand-near-black">${item.name}</h3>
                            ${item.variant ? `<p class="text-xs text-brand-warm-taupe">${item.variant}</p>` : ''}
                            <p class="text-sm text-brand-classic-gold">${parseFloat(item.price).toFixed(2)} €</p>
                        </div>
                    </div>
                    <div class="flex items-center space-x-2 sm:space-x-3">
                        <div class="quantity-input-controls flex items-center">
                            <button onclick="changeCartItemQuantity('${item.cartId}', -1)" class="px-2 py-0.5 border border-brand-warm-taupe/50 text-brand-near-black hover:bg-brand-warm-taupe/20 text-sm rounded-l">-</button>
                            <input type="number" value="${item.quantity}" min="1" max="${item.stock}" class="quantity-input cart-item-quantity-input w-10 sm:w-12 text-center border-y border-brand-warm-taupe/50 py-1 text-sm appearance-none" readonly data-id="${item.cartId}">
                            <button onclick="changeCartItemQuantity('${item.cartId}', 1)" class="px-2 py-0.5 border border-brand-warm-taupe/50 text-brand-near-black hover:bg-brand-warm-taupe/20 text-sm rounded-r">+</button>
                        </div>
                        <p class="text-md font-semibold text-brand-near-black w-20 text-right">${itemTotal.toFixed(2)} €</p>
                        <button onclick="removeCartItem('${item.cartId}')" title="${t('Supprimer_larticle')}" class="text-brand-truffle-burgundy hover:text-red-700">
                            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-5 h-5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
                        </button>
                    </div>
                </div>`;
            cartItemsContainer.insertAdjacentHTML('beforeend', cartItemHTML);
        });
        updateCartSummary();
    }
}

function changeCartItemQuantity(cartItemId, change) {
    const inputElement = document.querySelector(`.cart-item-quantity-input[data-id="${cartItemId}"]`);
    if (inputElement) {
        let currentQuantity = parseInt(inputElement.value);
        updateCartItemQuantity(cartItemId, currentQuantity + change);
    }
}

function updateCartSummary() {
    const cart = getCart();
    const subtotal = cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
    const shipping = subtotal > 0 && subtotal < 75 ? 7.50 : 0;
    const total = subtotal + shipping;

    const subtotalEl = document.getElementById('cart-subtotal');
    const shippingEl = document.getElementById('cart-shipping');
    const totalEl = document.getElementById('cart-total');

    if (subtotalEl) subtotalEl.textContent = `${subtotal.toFixed(2)} €`;
    if (shippingEl) {
        if (subtotal > 0) shippingEl.textContent = shipping > 0 ? `${shipping.toFixed(2)} €` : t('Gratuite');
        else shippingEl.textContent = 'N/A';
    }
    if (totalEl) totalEl.textContent = `${total.toFixed(2)} €`;

    const cartSummaryContainer = document.getElementById('cart-summary-container');
    if(cartSummaryContainer) cartSummaryContainer.style.display = cart.length > 0 ? 'block' : 'none';
}

website/js/auth.js
JavaScript

// website/js/auth.js

function getAuthToken() {
    return sessionStorage.getItem('authToken');
}

function setAuthToken(token) {
    if (token) sessionStorage.setItem('authToken', token);
    else sessionStorage.removeItem('authToken');
}

function getCurrentUser() {
    const userString = sessionStorage.getItem('currentUser');
    if (userString) {
        try {
            return JSON.parse(userString);
        } catch (e) {
            console.error(t('Erreur_lors_du_parsing_des_donnees_utilisateur'), e);
            sessionStorage.removeItem('currentUser');
            sessionStorage.removeItem('authToken');
            return null;
        }
    }
    return null;
}

function setCurrentUser(userData, token = null) {
    if (userData) {
        sessionStorage.setItem('currentUser', JSON.stringify(userData));
        if (token) setAuthToken(token);
    } else {
        sessionStorage.removeItem('currentUser');
        sessionStorage.removeItem('authToken');
    }
    updateLoginState();
    if (typeof updateCartCountDisplay === 'function') updateCartCountDisplay();
}

async function logoutUser() {
    setCurrentUser(null);
    showGlobalMessage(t('Deconnecte_message'), "info");
    if (document.body.id === 'page-compte' || document.body.id === 'page-paiement') {
        window.location.href = 'compte.html';
    } else {
        updateLoginState();
        if (document.body.id === 'page-compte') displayAccountDashboard();
    }
}

function updateLoginState() {
    const currentUser = getCurrentUser();
    const accountLinkTextDesktop = document.getElementById('account-link-text-desktop');
    const accountLinkTextMobile = document.getElementById('account-link-text-mobile'); // Make sure this ID exists in header.html's mobile menu
    const accountLinkDesktopContainer = document.querySelector('header nav a[href="compte.html"]'); // Fallback
    const accountLinkMobileContainer = document.querySelector('#mobile-menu-dropdown a[href="compte.html"]'); // Fallback


    const desktopTextElement = accountLinkTextDesktop || (accountLinkDesktopContainer ? accountLinkDesktopContainer.querySelector('span') : null);
    const mobileTextElement = accountLinkTextMobile || accountLinkMobileContainer;


    if (currentUser) {
        const userName = currentUser.prenom || t('Mon_Compte');
        if (desktopTextElement) {
             desktopTextElement.textContent = userName;
             // Ensure SVG is part of the structure if relying on just updating span
            if (accountLinkDesktopContainer && !accountLinkDesktopContainer.innerHTML.includes('<svg')) {
                 accountLinkDesktopContainer.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-7 h-7 text-brand-classic-gold"><path stroke-linecap="round" stroke-linejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" /></svg> <span id="account-link-text-desktop" class="ml-1 text-xs">${userName}</span>`;
            }
        }
        if (mobileTextElement) mobileTextElement.textContent = `${t('Mon_Compte_Menu')} (${userName})`;
    } else {
        if (desktopTextElement) {
            desktopTextElement.textContent = t('Mon_Compte_Menu');
             if (accountLinkDesktopContainer && !accountLinkDesktopContainer.innerHTML.includes('<svg')) {
                 accountLinkDesktopContainer.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-7 h-7"><path stroke-linecap="round" stroke-linejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" /></svg> <span id="account-link-text-desktop" class="ml-1 text-xs">${t('Mon_Compte_Menu')}</span>`;
            }
        }
        if (mobileTextElement) mobileTextElement.textContent = t('Mon_Compte_Menu');
    }
}


async function handleLogin(event) {
    event.preventDefault();
    const loginForm = event.target;
    clearFormErrors(loginForm);
    const emailField = loginForm.querySelector('#login-email');
    const passwordField = loginForm.querySelector('#login-password');
    const email = emailField.value;
    const password = passwordField.value;
    const loginMessageElement = document.getElementById('login-message');

    let isValid = true;
    if (loginMessageElement) loginMessageElement.textContent = '';

    if (!email || !validateEmail(email)) {
        setFieldError(emailField, t('Veuillez_entrer_une_adresse_e-mail_valide')); isValid = false;
    }
    if (!password) {
        setFieldError(passwordField, t('Veuillez_entrer_votre_mot_de_passe')); isValid = false;
    }
    if (!isValid) {
        showGlobalMessage(t('Veuillez_corriger_les_erreurs_dans_le_formulaire'), "error"); return;
    }

    showGlobalMessage(t('Connexion_en_cours'), "info", 60000);

    try {
        const result = await makeApiRequest('/auth/login', 'POST', { email, password });
        if (result.success && result.user && result.token) {
            setCurrentUser(result.user, result.token);
            showGlobalMessage(result.message || t('Connexion_reussie'), "success"); // Add key
            loginForm.reset();
            displayAccountDashboard();
        } else {
            setCurrentUser(null);
            const generalErrorMessage = result.message || t('Echec_de_la_connexion_Verifiez_vos_identifiants');
            showGlobalMessage(generalErrorMessage, "error");
            if (loginMessageElement) loginMessageElement.textContent = generalErrorMessage;
            setFieldError(emailField, " ");
            setFieldError(passwordField, generalErrorMessage);
        }
    } catch (error) {
        setCurrentUser(null);
        if (loginMessageElement) loginMessageElement.textContent = error.message || t('Erreur_de_connexion_au_serveur');
    }
}

async function handleRegistrationForm(event) {
    event.preventDefault();
    const form = event.target;
    clearFormErrors(form);
    const emailField = form.querySelector('#register-email'); // Assuming these IDs exist
    const passwordField = form.querySelector('#register-password');
    const confirmPasswordField = form.querySelector('#register-confirm-password');
    const nomField = form.querySelector('#register-nom');
    const prenomField = form.querySelector('#register-prenom');

    let isValid = true;
    if (!emailField.value || !validateEmail(emailField.value)) { setFieldError(emailField, t('E-mail_invalide')); isValid = false; }
    if (!nomField.value.trim()) { setFieldError(nomField, t('Nom_requis')); isValid = false; }
    if (!prenomField.value.trim()) { setFieldError(prenomField, t('Prenom_requis')); isValid = false; }
    if (passwordField.value.length < 8) { setFieldError(passwordField, t('Mot_de_passe_8_caracteres')); isValid = false; } // Add key
    if (passwordField.value !== confirmPasswordField.value) { setFieldError(confirmPasswordField, t('Mots_de_passe_ne_correspondent_pas')); isValid = false; } // Add key

    if (!isValid) { showGlobalMessage(t('Veuillez_corriger_les_erreurs_formulaire_inscription'), "error"); return; } // Add key

    showGlobalMessage(t('Creation_du_compte'), "info"); // Add key
    try {
        const result = await makeApiRequest('/auth/register', 'POST', {
            email: emailField.value, password: passwordField.value,
            nom: nomField.value, prenom: prenomField.value
        });
        if (result.success) {
            showGlobalMessage(result.message || t('Compte_cree_avec_succes_Veuillez_vous_connecter'), "success");
            form.reset();
        } else {
            showGlobalMessage(result.message || t('Erreur_lors_de_linscription'), "error");
        }
    } catch (error) { console.error("Erreur d'inscription:", error); }
}

function displayAccountDashboard() {
    const loginRegisterSection = document.getElementById('login-register-section');
    const accountDashboardSection = document.getElementById('account-dashboard-section');
    const currentUser = getCurrentUser();

    if (currentUser && loginRegisterSection && accountDashboardSection) {
        loginRegisterSection.style.display = 'none';
        accountDashboardSection.style.display = 'block';
        const dashboardUsername = document.getElementById('dashboard-username');
        const dashboardEmail = document.getElementById('dashboard-email');
        if(dashboardUsername) dashboardUsername.textContent = `${currentUser.prenom || ''} ${currentUser.nom || ''}`;
        if(dashboardEmail) dashboardEmail.textContent = currentUser.email;
        const logoutButton = document.getElementById('logout-button');
        if (logoutButton) {
            logoutButton.removeEventListener('click', logoutUser);
            logoutButton.addEventListener('click', logoutUser);
        }
        loadOrderHistory();
    } else if (loginRegisterSection) {
        loginRegisterSection.style.display = 'block';
        if (accountDashboardSection) accountDashboardSection.style.display = 'none';
    }
    if(window.translatePageElements) translatePageElements(); // Translate dashboard static text
}

async function loadOrderHistory() {
    const orderHistoryContainer = document.getElementById('order-history-container');
    if (!orderHistoryContainer) return;
    const currentUser = getCurrentUser();
    if (!currentUser) {
        orderHistoryContainer.innerHTML = `<p class="text-sm text-brand-warm-taupe italic">${t('Veuillez_vous_connecter_pour_voir_votre_historique')}</p>`;
        return;
    }
    orderHistoryContainer.innerHTML = `<p class="text-sm text-brand-warm-taupe italic">${t('Chargement_de_lhistorique_des_commandes')}</p>`;
    try {
        const ordersData = await makeApiRequest('/orders/history', 'GET', null, true);
        if (ordersData.success && ordersData.orders.length > 0) {
            let html = '<ul class="space-y-4">';
            ordersData.orders.forEach(order => {
                html += `
                    <li class="p-4 border border-brand-warm-taupe/50 rounded-md bg-white">
                        <div class="flex justify-between items-center mb-2">
                            <p class="font-semibold text-brand-near-black">${t('Commande_')} #${order.order_id || order.id}</p>
                            <span class="px-2 py-1 text-xs font-semibold rounded-full ${getOrderStatusClass(order.status)}">${t(order.status) || order.status}</span>
                        </div>
                        <p class="text-sm"><strong>${t('Date')}:</strong> ${new Date(order.order_date).toLocaleDateString(getCurrentLang() || 'fr-FR')}</p>
                        <p class="text-sm"><strong>${t('Total')}:</strong> ${parseFloat(order.total_amount).toFixed(2)} €</p>
                        <button class="text-sm text-brand-classic-gold hover:underline mt-2" onclick="viewOrderDetail('${order.order_id || order.id}')" data-translate-key="Voir_details">${t('Voir_details')}</button>
                    </li>`;
            });
            html += '</ul>';
            orderHistoryContainer.innerHTML = html;
        } else {
            orderHistoryContainer.innerHTML = `<p class="text-sm text-brand-warm-taupe italic">${t('Vous_navez_aucune_commande_pour_le_moment')}</p>`;
        }
    } catch (error) {
        orderHistoryContainer.innerHTML = `<p class="text-sm text-brand-truffle-burgundy italic">${t('Impossible_de_charger_lhistorique_des_commandes')} ${error.message}</p>`;
    }
}

function viewOrderDetail(orderId) {
    showGlobalMessage(`${t('Detail_commande_')} #${orderId} (${t('Fonctionnalite_a_implementer')}).`, 'info'); // Add keys
    console.log("Voir détails pour commande:", orderId);
}

admin/admin_manage_products.html (Key changes shown for one set of localized fields, apply pattern to others)
HTML

<!DOCTYPE html>
<html lang="fr"> <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Gérer les Produits - Admin Maison Trüvra</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Playfair+Display:ital,wght@0,400;0,700;1,400&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="admin_styles.css">
</head>
<body class="bg-brand-cream text-brand-earth-brown font-inter">
    <div class="admin-layout">
        <aside class="admin-sidebar">
            <div class="p-6"><a href="admin_dashboard.html"><img src="../image_6be700.png" alt="Maison Trüvra Logo" class="h-16 mx-auto mb-6" onerror="this.alt='Logo Maison Trüvra'; this.src='https://placehold.co/150x60/F5EEDE/7D6A4F?text=Maison+Trüvra';"></a></div>
            <nav>
                <ul>
                    <li><a href="admin_dashboard.html" class="admin-nav-link">Tableau de Bord</a></li>
                    <li><a href="admin_manage_products.html" class="admin-nav-link active">Gérer les Produits</a></li>
                    <li><a href="admin_manage_inventory.html" class="admin-nav-link">Gérer les Stocks</a></li>
                    <li><a href="admin_manage_users.html" class="admin-nav-link">Gérer les Utilisateurs</a></li>
                    <li><a href="admin_manage_orders.html" class="admin-nav-link">Gérer les Commandes</a></li>
                </ul>
            </nav>
            <div class="p-6 mt-auto"><button id="admin-logout-button" class="btn-admin-secondary w-full">Déconnexion</button></div>
        </aside>

        <main class="admin-main-content">
            <header class="admin-main-header">
                <h1 class="text-3xl font-serif text-brand-near-black">Gestion des Produits</h1>
                <button id="show-add-product-form-button" class="btn-admin-primary">Ajouter un Nouveau Produit</button>
            </header>

            <section class="p-6">
                <div id="add-edit-product-section" class="admin-card p-6 mb-8" style="display:none;">
                    <h2 id="product-form-title" class="text-2xl font-serif text-brand-near-black mb-6">Ajouter un Nouveau Produit</h2>
                    <form id="product-form" class="space-y-5">
                        <input type="hidden" id="product-edit-id" value="">

                        <div>
                            <label for="product-id" class="form-label-admin">ID Produit (unique, ex: "truffe-noire-20g")</label>
                            <input type="text" id="product-id" name="id" class="form-input-admin" required>
                        </div>

                        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <label for="product-name-fr" class="form-label-admin">Nom du Produit (FR)</label>
                                <input type="text" id="product-name-fr" name="name_fr" class="form-input-admin" required>
                            </div>
                            <div>
                                <label for="product-name-en" class="form-label-admin">Product Name (EN)</label>
                                <input type="text" id="product-name-en" name="name_en" class="form-input-admin" required>
                            </div>
                        </div>

                        <div>
                            <label for="product-category" class="form-label-admin">Catégorie</label>
                            <select id="product-category" name="category" class="form-select-admin" required>
                                <option value="">Sélectionner une catégorie</option>
                                <option value="Fresh Truffles">Truffes Fraîches</option>
                                <option value="Truffle Oils">Huiles Truffées</option>
                                <option value="Truffle Sauces">Sauces Truffées</option>
                                <option value="Gift Sets">Coffrets Cadeaux</option>
                                <option value="Other">Autre</option>
                            </select>
                        </div>

                        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <label for="product-short-description-fr" class="form-label-admin">Description Courte (FR)</label>
                                <textarea id="product-short-description-fr" name="short_description_fr" rows="2" class="form-textarea-admin"></textarea>
                            </div>
                            <div>
                                <label for="product-short-description-en" class="form-label-admin">Short Description (EN)</label>
                                <textarea id="product-short-description-en" name="short_description_en" rows="2" class="form-textarea-admin"></textarea>
                            </div>
                        </div>
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <label for="product-long-description-fr" class="form-label-admin">Description Longue (FR)</label>
                                <textarea id="product-long-description-fr" name="long_description_fr" rows="4" class="form-textarea-admin"></textarea>
                            </div>
                            <div>
                                <label for="product-long-description-en" class="form-label-admin">Long Description (EN)</label>
                                <textarea id="product-long-description-en" name="long_description_en" rows="4" class="form-textarea-admin"></textarea>
                            </div>
                        </div>

                        <div>
                            <label for="product-image-url-main" class="form-label-admin">URL Image Principale</label>
                            <input type="url" id="product-image-url-main" name="image_url_main" class="form-input-admin" placeholder="https://example.com/image.jpg">
                        </div>
                        <div>
                            <label for="product-image-urls-thumb" class="form-label-admin">URLs Images Miniatures (JSON Array, ex: ["url1", "url2"])</label>
                            <input type="text" id="product-image-urls-thumb" name="image_urls_thumb" class="form-input-admin" placeholder='["https://example.com/thumb1.jpg"]'>
                        </div>

                        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div><label for="product-species-fr" class="form-label-admin">Espèce (FR)</label><input type="text" id="product-species-fr" name="species_fr" class="form-input-admin"></div>
                            <div><label for="product-species-en" class="form-label-admin">Species (EN)</label><input type="text" id="product-species-en" name="species_en" class="form-input-admin"></div>
                        </div>
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div><label for="product-origin-fr" class="form-label-admin">Origine (FR)</label><input type="text" id="product-origin-fr" name="origin_fr" class="form-input-admin"></div>
                            <div><label for="product-origin-en" class="form-label-admin">Origin (EN)</label><input type="text" id="product-origin-en" name="origin_en" class="form-input-admin"></div>
                        </div>
                         <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div><label for="product-seasonality-fr" class="form-label-admin">Saisonnalité (FR)</label><input type="text" id="product-seasonality-fr" name="seasonality_fr" class="form-input-admin"></div>
                            <div><label for="product-seasonality-en" class="form-label-admin">Seasonality (EN)</label><input type="text" id="product-seasonality-en" name="seasonality_en" class="form-input-admin"></div>
                        </div>
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div><label for="product-ideal-uses-fr" class="form-label-admin">Utilisations Idéales (FR)</label><input type="text" id="product-ideal-uses-fr" name="ideal_uses_fr" class="form-input-admin"></div>
                            <div><label for="product-ideal-uses-en" class="form-label-admin">Ideal Uses (EN)</label><input type="text" id="product-ideal-uses-en" name="ideal_uses_en" class="form-input-admin"></div>
                        </div>
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div><label for="product-sensory-description-fr" class="form-label-admin">Description Sensorielle (FR)</label><textarea id="product-sensory-description-fr" name="sensory_description_fr" rows="3" class="form-textarea-admin"></textarea></div>
                            <div><label for="product-sensory-description-en" class="form-label-admin">Sensory Description (EN)</label><textarea id="product-sensory-description-en" name="sensory_description_en" rows="3" class="form-textarea-admin"></textarea></div>
                        </div>
                         <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div><label for="product-pairing-suggestions-fr" class="form-label-admin">Suggestions d'Accords (FR)</label><textarea id="product-pairing-suggestions-fr" name="pairing_suggestions_fr" rows="3" class="form-textarea-admin"></textarea></div>
                            <div><label for="product-pairing-suggestions-en" class="form-label-admin">Pairing Suggestions (EN)</label><textarea id="product-pairing-suggestions-en" name="pairing_suggestions_en" rows="3" class="form-textarea-admin"></textarea></div>
                        </div>


                        <hr class="my-6 border-brand-warm-taupe/30">
                        <h3 class="text-lg font-semibold text-brand-near-black">Prix et Stock</h3>

                        <div>
                            <label for="product-base-price" class="form-label-admin">Prix de Base (si pas de variantes de poids)</label>
                            <input type="number" id="product-base-price" name="base_price" step="0.01" class="form-input-admin" placeholder="Ex: 25.00">
                        </div>
                        <div id="simple-product-stock-section">
                             <label for="product-initial-stock-quantity" class="form-label-admin">Stock Initial (pour produit simple)</label>
                            <input type="number" id="product-initial-stock-quantity" name="initial_stock_quantity" step="1" min="0" class="form-input-admin" placeholder="Ex: 50">
                        </div>

                        <div class="mt-4">
                            <label class="form-label-admin">Options de Poids/Prix (si applicable)</label>
                            <div id="weight-options-container" class="space-y-3">
                                </div>
                            <button type="button" id="add-weight-option-button" class="btn-admin-secondary text-xs mt-2">Ajouter une Option de Poids</button>
                        </div>

                        <hr class="my-6 border-brand-warm-taupe/30">
                         <h3 class="text-lg font-semibold text-brand-near-black">Génération des Actifs (Passeport, QR, Étiquette)</h3>
                        <div>
                            <label for="product-numero-lot-manuel" class="form-label-admin">Numéro de Lot Manuel (pour actifs)</label>
                            <input type="text" id="product-numero-lot-manuel" name="numero_lot_manuel" class="form-input-admin" placeholder="Ex: LOT2024-XYZ">
                        </div>
                         <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <label for="product-date-conditionnement" class="form-label-admin">Date de Conditionnement (pour actifs)</label>
                                <input type="date" id="product-date-conditionnement" name="date_conditionnement" class="form-input-admin">
                            </div>
                            <div>
                                <label for="product-ddm" class="form-label-admin">DDM (Date de Durabilité Minimale - pour actifs)</label>
                                <input type="date" id="product-ddm" name="ddm" class="form-input-admin">
                            </div>
                        </div>
                        <div>
                            <label for="product-specific-weight-for-label" class="form-label-admin">Poids Spécifique pour Étiquette (si différent des options)</label>
                            <input type="text" id="product-specific-weight-for-label" name="specific_weight_for_label" class="form-input-admin" placeholder="Ex: 100g (pour huile, etc.)">
                        </div>
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <label for="product-ingredients-for-label-fr" class="form-label-admin">Ingrédients Étiquette (FR)</label>
                                <textarea id="product-ingredients-for-label-fr" name="ingredients_for_label_fr" rows="2" class="form-textarea-admin" placeholder="Ingrédients..."></textarea>
                            </div>
                            <div>
                                <label for="product-ingredients-for-label-en" class="form-label-admin">Label Ingredients (EN)</label>
                                <textarea id="product-ingredients-for-label-en" name="ingredients_for_label_en" rows="2" class="form-textarea-admin" placeholder="Ingredients..."></textarea>
                            </div>
                        </div>

                        <div class="flex items-center mt-4">
                            <input type="checkbox" id="product-is-published" name="is_published" class="form-checkbox-admin mr-2" checked>
                            <label for="product-is-published" class="text-sm text-brand-near-black">Publier ce produit sur la boutique</label>
                        </div>

                        <div class="flex justify-end space-x-3 pt-4">
                            <button type="button" id="cancel-product-form-button" class="btn-admin-secondary">Annuler</button>
                            <button type="submit" class="btn-admin-primary">Enregistrer Produit</button>
                        </div>
                    </form>
                    <div id="product-assets-preview-section" class="mt-6 p-4 border-t border-brand-warm-taupe/30 rounded-md bg-brand-cream/50" style="display:none;">
                        <h4 class="text-md font-semibold text-brand-near-black mb-3">Aperçu des Actifs Générés :</h4>
                        <div id="product-assets-links" class="space-y-2 text-sm"></div>
                        <p class="text-xs text-brand-warm-taupe mt-3">Note: Les chemins QR/Étiquette sont relatifs au dossier statique.</p>
                    </div>
                </div>

                <div class="admin-card overflow-x-auto">
                    <h2 class="text-2xl font-serif text-brand-near-black p-6">Liste des Produits</h2>
                    <table id="products-table" class="admin-table">
                        <thead>
                            <tr>
                                <th scope="col">ID</th>
                                <th scope="col">Nom (FR)</th>
                                <th scope="col">Catégorie</th>
                                <th scope="col">Prix Base / Variantes</th>
                                <th scope="col">Stock Total</th>
                                <th scope="col">Publié</th>
                                <th scope="col">Actions</th>
                            </tr>
                        </thead>
                        <tbody id="products-table-body">
                            <tr><td colspan="7" class="text-center py-4">Chargement des produits...</td></tr> </tbody>
                    </table>
                </div>
            </section>
        </main>
    </div>
    <div id="admin-toast-container"><div id="admin-message-toast"><p id="admin-message-text"></p></div></div>
    <script src="js/admin_config.js"></script>
    <script src="js/admin_ui.js"></script>
    <script src="js/admin_api.js"></script>
    <script src="js/admin_auth.js"></script>
    <script src="js/admin_products.js"></script>
    <script src="js/admin_main.js"></script>
</body>
</html>

website/admin/js/admin_products.js (Displaying only French name in list, but handling both FR/EN in forms)
JavaScript

// website/admin/js/admin_products.js
let productsForAdmin = [];
let editingProductId = null;

function initializeProductManagement() {
    // ... (same as previous, no changes needed here for i18n specifically)
    const showFormButton = document.getElementById('show-add-product-form-button');
    const productFormSection = document.getElementById('add-edit-product-section');
    const productForm = document.getElementById('product-form');
    const cancelFormButton = document.getElementById('cancel-product-form-button');
    const addWeightOptionButton = document.getElementById('add-weight-option-button');
    const assetsPreviewSection = document.getElementById('product-assets-preview-section');

    if (showFormButton && productFormSection) {
        showFormButton.addEventListener('click', () => {
            editingProductId = null;
            if (productForm) productForm.reset();
            clearFormErrors(productForm);
            const formTitle = document.getElementById('product-form-title');
            if (formTitle) formTitle.textContent = "Ajouter un Nouveau Produit";
            const productIdField = document.getElementById('product-id');
            if (productIdField) productIdField.readOnly = false;
            const weightOptionsContainer = document.getElementById('weight-options-container');
            if (weightOptionsContainer) weightOptionsContainer.innerHTML = '';
            if(assetsPreviewSection) assetsPreviewSection.style.display = 'none';
            productFormSection.style.display = 'block';
            showFormButton.style.display = 'none';
        });
    }

    if (cancelFormButton && productFormSection && showFormButton) {
        cancelFormButton.addEventListener('click', () => {
            productFormSection.style.display = 'none';
            showFormButton.style.display = 'inline-flex';
            if (productForm) productForm.reset();
            clearFormErrors(productForm);
            editingProductId = null;
            if(assetsPreviewSection) assetsPreviewSection.style.display = 'none';
        });
    }

    if (productForm) {
        productForm.addEventListener('submit', handleProductFormSubmit);
    }

    if (addWeightOptionButton) {
        addWeightOptionButton.addEventListener('click', () => addWeightOptionRow());
    }

    loadAdminProductsList();
}

function addWeightOptionRow(option = { option_id: null, weight_grams: '', price: '', initial_stock: '' }) {
    // ... (same as previous)
    const container = document.getElementById('weight-options-container');
    if (!container) return;
    const optionIndex = container.children.length;
    const optionIdInputHtml = option.option_id ? `<input type="hidden" name="weight_options[${optionIndex}][option_id]" value="${option.option_id}">` : '';
    const rowHtml = `
        <div class="weight-option-row grid grid-cols-1 md:grid-cols-4 gap-3 items-center border p-3 rounded-md mb-2">
            ${optionIdInputHtml}
            <div><label class="text-xs font-medium text-brand-near-black">Poids (g) <span class="text-red-500">*</span></label><input type="number" name="weight_options[${optionIndex}][weight_grams]" class="form-input-admin text-sm p-2 mt-1" value="${option.weight_grams}" placeholder="Ex: 20" required></div>
            <div><label class="text-xs font-medium text-brand-near-black">Prix (€) <span class="text-red-500">*</span></label><input type="number" name="weight_options[${optionIndex}][price]" step="0.01" class="form-input-admin text-sm p-2 mt-1" value="${option.price}" placeholder="Ex: 75.00" required></div>
            <div><label class="text-xs font-medium text-brand-near-black">Stock Initial/Actuel <span class="text-red-500">*</span></label><input type="number" name="weight_options[${optionIndex}][initial_stock]" step="1" min="0" class="form-input-admin text-sm p-2 mt-1" value="${option.initial_stock}" placeholder="Ex: 10" required></div>
            <button type="button" class="btn-admin-danger text-xs py-1 px-2 self-end mt-4 md:mt-0" onclick="this.parentElement.remove()">Retirer</button>
        </div>`;
    container.insertAdjacentHTML('beforeend', rowHtml);
}

async function handleProductFormSubmit(event) {
    event.preventDefault();
    const form = event.target;
    const assetsPreviewSection = document.getElementById('product-assets-preview-section');
    const assetsLinksContainer = document.getElementById('product-assets-links');
    if(assetsPreviewSection) assetsPreviewSection.style.display = 'none';
    if(assetsLinksContainer) assetsLinksContainer.innerHTML = '';

    clearFormErrors(form);
    if (!validateProductForm(form)) return;

    const formData = new FormData(form);
    const productData = {};

    const fieldsToCollect = [
        'id', 'name_fr', 'name_en', 'category',
        'short_description_fr', 'short_description_en',
        'long_description_fr', 'long_description_en',
        'image_url_main', 'image_urls_thumb',
        'species_fr', 'species_en', 'origin_fr', 'origin_en',
        'seasonality_fr', 'seasonality_en', 'ideal_uses_fr', 'ideal_uses_en',
        'sensory_description_fr', 'sensory_description_en',
        'pairing_suggestions_fr', 'pairing_suggestions_en',
        'base_price', 'initial_stock_quantity',
        'is_published',
        'numero_lot_manuel', 'date_conditionnement', 'ddm',
        'specific_weight_for_label',
        'ingredients_for_label_fr', 'ingredients_for_label_en'
    ];

    for (const fieldName of fieldsToCollect) {
        if (formData.has(fieldName)) {
            if (['base_price', 'initial_stock_quantity'].includes(fieldName)) {
                productData[fieldName] = formData.get(fieldName) ? parseFloat(formData.get(fieldName)) : null;
                if (fieldName === 'initial_stock_quantity' && productData[fieldName] === null) productData[fieldName] = 0;
            } else if (fieldName === 'is_published') {
                productData[fieldName] = form.querySelector(`#product-is-published`).checked;
            } else if (fieldName === 'image_urls_thumb') {
                try {
                    const thumbString = formData.get('image_urls_thumb');
                    productData.image_urls_thumb = thumbString.trim() ? JSON.parse(thumbString) : [];
                    if (!Array.isArray(productData.image_urls_thumb)) productData.image_urls_thumb = [];
                } catch (e) {
                    productData.image_urls_thumb = [];
                    setFieldError(form.querySelector('#product-image-urls-thumb'), "Format JSON invalide.");
                    return;
                }
            } else {
                productData[fieldName] = formData.get(fieldName);
            }
        }
    }

    const weightOptions = [];
    document.querySelectorAll('#weight-options-container .weight-option-row').forEach((row) => {
        const optionIdField = row.querySelector(`input[name*="[option_id]"]`);
        const weightGramsField = row.querySelector(`input[name*="[weight_grams]"]`);
        const priceField = row.querySelector(`input[name*="[price]"]`);
        const initialStockField = row.querySelector(`input[name*="[initial_stock]"]`);
        if (weightGramsField && priceField && initialStockField && weightGramsField.value && priceField.value && initialStockField.value) {
            const opt = {
                weight_grams: parseInt(weightGramsField.value),
                price: parseFloat(priceField.value),
                initial_stock: parseInt(initialStockField.value)
            };
            if(optionIdField && optionIdField.value) opt.option_id = parseInt(optionIdField.value);
            weightOptions.push(opt);
        }
    });

    if (weightOptions.length > 0) {
        productData.weight_options = weightOptions;
        productData.base_price = null;
        productData.initial_stock_quantity = 0;
    } else {
        if (productData.base_price === null || productData.base_price === '') {
             // If no variants, base_price is required (validateProductForm should handle this)
        }
        if(productData.initial_stock_quantity === null || productData.initial_stock_quantity === '') productData.initial_stock_quantity = 0;
    }

    const method = editingProductId ? 'PUT' : 'POST';
    const endpoint = editingProductId ? `/products/${editingProductId}` : '/products';

    try {
        showAdminToast("Enregistrement du produit...", "info");
        const result = await adminApiRequest(endpoint, method, productData);

        if (result.success && result.product) {
            showAdminToast(result.message || "Produit enregistré avec succès!", "success");
            if (result.product.assets && assetsPreviewSection && assetsLinksContainer) {
                let linksHtml = '';
                if (result.product.assets.passport_url) linksHtml += `<p><strong>Passeport:</strong> <a href="${result.product.assets.passport_url}" target="_blank" class="text-brand-classic-gold hover:underline">${result.product.assets.passport_url}</a></p>`;
                if (result.product.assets.qr_code_file_path) linksHtml += `<p><strong>QR Code:</strong> <a href="/static_assets/${result.product.assets.qr_code_file_path}" target="_blank" class="text-brand-classic-gold hover:underline">Voir QR</a></p>`;
                if (result.product.assets.label_file_path) linksHtml += `<p><strong>Étiquette:</strong> <a href="/static_assets/${result.product.assets.label_file_path}" target="_blank" class="text-brand-classic-gold hover:underline">Voir Étiquette</a></p>`;

                if (linksHtml) {
                    assetsLinksContainer.innerHTML = linksHtml;
                    assetsPreviewSection.style.display = 'block';
                } else {
                    assetsLinksContainer.innerHTML = '<p class="text-brand-warm-taupe">Aucun actif spécifique généré.</p>';
                    assetsPreviewSection.style.display = 'block';
                }
            }
            editingProductId = result.product.id;
            document.getElementById('product-form-title').textContent = `Modifier le Produit: ${result.product.name_fr || result.product.name_en}`;
            document.getElementById('product-id').readOnly = true;
            loadAdminProductsList();
        }
    } catch (error) {
        console.error("Erreur soumission formulaire produit:", error);
    }
}

function validateProductForm(form) {
    let isValid = true;
    const requiredFields = [
        { id: 'product-name-fr', message: "Le nom du produit (FR) est requis." },
        // { id: 'product-name-en', message: "Product Name (EN) is required." }, // At least one name is good
        { id: 'product-category', message: "La catégorie est requise." },
        { id: 'product-image-url-main', message: "L'URL de l'image principale est requise." }
    ];
    if (!editingProductId) {
        requiredFields.unshift({ id: 'product-id', message: "L'ID du produit est requis." });
    }

    // Check at least one name is filled
    const nameFr = form.querySelector('#product-name-fr').value.trim();
    const nameEn = form.querySelector('#product-name-en').value.trim();
    if (!nameFr && !nameEn) {
        setFieldError(form.querySelector('#product-name-fr'), "Au moins un nom de produit (FR ou EN) est requis.");
        setFieldError(form.querySelector('#product-name-en'), "Au moins un nom de produit (FR ou EN) est requis.");
        isValid = false;
    }


    requiredFields.forEach(fieldInfo => {
        const field = form.querySelector(`#${fieldInfo.id}`);
        if (field && !field.value.trim()) {
            // Skip name validation if one of them is filled
            if ((fieldInfo.id === 'product-name-fr' && nameEn) || (fieldInfo.id === 'product-name-en' && nameFr)) {
                // one of the names is filled, so this specific one is not strictly required
            } else {
                setFieldError(field, fieldInfo.message);
                isValid = false;
            }
        }
    });
    // ... (rest of the validation, URL checks, JSON parsing for thumbs)
    const basePriceField = form.querySelector('#product-base-price');
    const weightOptionsRows = form.querySelectorAll('#weight-options-container .weight-option-row');
    if ((!basePriceField.value || basePriceField.value.trim() === '') && weightOptionsRows.length === 0) {
        setFieldError(basePriceField, "Un prix de base ou au moins une option de poids est requis.");
        isValid = false;
    }
    if (basePriceField.value && basePriceField.value.trim() !== '' && weightOptionsRows.length > 0) {
        setFieldError(basePriceField, "Ne pas spécifier de prix de base si des options de poids sont définies.");
        isValid = false;
    }

    if (!isValid) showAdminToast("Veuillez corriger les erreurs dans le formulaire.", "error");
    return isValid;
}

async function loadAdminProductsList() {
    const tableBody = document.getElementById('products-table-body');
    if (!tableBody) return;
    tableBody.innerHTML = '<tr><td colspan="7" class="text-center py-4">Chargement des produits...</td></tr>'; // Adjusted colspan
    try {
        productsForAdmin = await adminApiRequest('/products');
        if (productsForAdmin.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="7" class="text-center py-4">Aucun produit trouvé.</td></tr>'; // Adjusted colspan
            return;
        }
        let rowsHtml = '';
        productsForAdmin.forEach(product => {
            let priceDisplay = product.base_price !== null ? `${parseFloat(product.base_price).toFixed(2)} €` : 'Variantes';
            let stockDisplay = product.stock_quantity !== undefined ? product.stock_quantity : 'N/A';
            // Display French name by default in the list, or English if French is missing
            let displayName = product.name_fr || product.name_en || product.id;
            rowsHtml += `
                <tr>
                    <td class="px-6 py-3 text-xs">${product.id}</td>
                    <td class="px-6 py-3 font-medium text-brand-near-black">${displayName}</td>
                    <td class="px-6 py-3">${product.category}</td>
                    <td class="px-6 py-3">${priceDisplay}</td>
                    <td class="px-6 py-3">${stockDisplay}</td>
                    <td class="px-6 py-3">${product.is_published ? '<span class="text-green-600 font-semibold">Oui</span>' : '<span class="text-red-600">Non</span>'}</td>
                    <td class="px-6 py-3 space-x-2 whitespace-nowrap">
                        <button onclick="editProduct('${product.id}')" class="btn-admin-secondary text-xs p-1.5">Éditer</button>
                    </td>
                </tr>`;
        });
        tableBody.innerHTML = rowsHtml;
    } catch (error) {
        tableBody.innerHTML = '<tr><td colspan="7" class="text-center py-4 text-red-600">Erreur de chargement.</td></tr>'; // Adjusted colspan
    }
}

async function editProduct(productId) {
    editingProductId = productId;
    let productToEdit;
    const assetsPreviewSection = document.getElementById('product-assets-preview-section');
    const assetsLinksContainer = document.getElementById('product-assets-links');
    if(assetsPreviewSection) assetsPreviewSection.style.display = 'none';
    if(assetsLinksContainer) assetsLinksContainer.innerHTML = '';

    try {
        productToEdit = await adminApiRequest(`/products/${productId}`); // This endpoint now returns all localized fields
        if (!productToEdit) throw new Error("Produit non trouvé.");
    } catch (e) {
        showAdminToast("Impossible de charger les détails du produit.", "error");
        return;
    }

    const form = document.getElementById('product-form');
    if (!form) return;
    form.reset();
    clearFormErrors(form);

    document.getElementById('product-form-title').textContent = `Modifier: ${productToEdit.name_fr || productToEdit.name_en}`;
    document.getElementById('product-id').value = productToEdit.id;
    document.getElementById('product-id').readOnly = true;

    const fieldsToPopulate = [
        'name_fr', 'name_en', 'category',
        'short_description_fr', 'short_description_en',
        'long_description_fr', 'long_description_en',
        'image_url_main', 'image_urls_thumb',
        'species_fr', 'species_en', 'origin_fr', 'origin_en',
        'seasonality_fr', 'seasonality_en', 'ideal_uses_fr', 'ideal_uses_en',
        'sensory_description_fr', 'sensory_description_en',
        'pairing_suggestions_fr', 'pairing_suggestions_en',
        'base_price', 'is_published',
        'numero_lot_manuel', 'date_conditionnement', 'ddm',
        'specific_weight_for_label',
        'ingredients_for_label_fr', 'ingredients_for_label_en'
    ];

    fieldsToPopulate.forEach(fieldName => {
        const elementId = `product-${fieldName.replace(/_/g, '-')}`;
        const element = document.getElementById(elementId);
        if (element) {
            if (fieldName === 'image_urls_thumb') {
                element.value = productToEdit.image_urls_thumb ? JSON.stringify(productToEdit.image_urls_thumb) : '[]';
            } else if (element.type === 'checkbox') {
                 element.checked = productToEdit[fieldName];
            } else if (element.type === 'date' && productToEdit[fieldName]) {
                // Dates from DB might be full ISO strings, HTML date input needs YYYY-MM-DD
                try {
                    element.value = new Date(productToEdit[fieldName]).toISOString().split('T')[0];
                } catch (e) {
                    element.value = ''; // Fallback if date parsing fails
                }
            }
            else {
                element.value = productToEdit[fieldName] || '';
            }
        } else {
            console.warn(`Element with ID ${elementId} not found for field ${fieldName} during edit.`);
        }
    });

    // ... (rest of weight options and asset display logic from previous version)
    const weightOptionsContainer = document.getElementById('weight-options-container');
    weightOptionsContainer.innerHTML = '';
    if (productToEdit.weight_options && productToEdit.weight_options.length > 0) {
        productToEdit.weight_options.forEach(opt => addWeightOptionRow({
            option_id: opt.option_id, weight_grams: opt.weight_grams,
            price: opt.price, initial_stock: opt.stock_quantity // `initial_stock` here represents current stock for editing
        }));
        document.getElementById('product-base-price').value = '';
        document.getElementById('product-initial-stock-quantity').value = '';
        document.getElementById('simple-product-stock-section').style.display = 'none';
    } else {
        document.getElementById('product-base-price').value = productToEdit.base_price !== null ? productToEdit.base_price : '';
        document.getElementById('product-initial-stock-quantity').value = productToEdit.stock_quantity || 0;
        document.getElementById('simple-product-stock-section').style.display = 'block';
    }
     if (productToEdit.assets && assetsPreviewSection && assetsLinksContainer) {
        let linksHtml = '';
        if (productToEdit.assets.passport_url) { linksHtml += `<p><strong>Passeport:</strong> <a href="${productToEdit.assets.passport_url}" target="_blank" class="text-brand-classic-gold hover:underline">${productToEdit.assets.passport_url}</a></p>`; }
        if (productToEdit.assets.qr_code_file_path) { linksHtml += `<p><strong>QR Code:</strong> <a href="/static_assets/${productToEdit.assets.qr_code_file_path}" target="_blank" class="text-brand-classic-gold hover:underline">Voir QR</a></p>`; }
        if (productToEdit.assets.label_file_path) { linksHtml += `<p><strong>Étiquette:</strong> <a href="/static_assets/${productToEdit.assets.label_file_path}" target="_blank" class="text-brand-classic-gold hover:underline">Voir Étiquette</a></p>`; }
        if (linksHtml) {
            assetsLinksContainer.innerHTML = linksHtml;
            assetsPreviewSection.style.display = 'block';
        }
    }


    document.getElementById('add-edit-product-section').style.display = 'block';
    document.getElementById('show-add-product-form-button').style.display = 'none';
    window.scrollTo(0, 0);
}

function isValidUrl(string) { try { new URL(string); return true; } catch (_) { return false; } }

Please apply these changes and remember to translate all static text using the data-translate-key attribute in your HTML and the t('KEY') function in your JavaScript. This is a large refactoring, so test thoroughly!

Is the code correct now?

Yes, the code provided in the previous steps implements the core strategy for making your website bilingual and generating bilingual QR code passports.

Here's a summary of why it's on the right track and what makes it "correct" in terms of the approach:

    Centralized Translation Logic:
        The new website/js/i18n.js file provides a central place for loading translation files (fr.json, en.json) and includes the t('KEY') function for translating text. This is a standard and correct approach for frontend internationalization.
        The loadTranslations and setLanguage functions correctly handle switching languages and updating the page content.

    Frontend Text Localization:
        JavaScript Files (product.js, cart.js, checkout.js, auth.js): The updates correctly show how to use the t('KEY') function for user-facing messages (e.g., in showGlobalMessage, button texts, error messages). They also correctly assume that dynamic data like product names and descriptions will be fetched in the currently selected language from the backend.
        HTML (admin/admin_manage_products.html and general HTML structure): The instruction to use data-translate-key="KEY_NAME" on static HTML elements is the correct way to allow i18n.js to translate them. The provided admin/admin_manage_products.html now includes paired input fields for French and English, which is necessary for managing bilingual content.

    Backend Data Handling (Assumed from Previous Changes):
        The changes previously made to backend files (like backend/database.py for schema, backend/products/routes.py to serve localized data, and backend/admin_api/routes.py to save/update localized data) are essential for this system to work. The frontend code now correctly requests and expects this localized data.

    Bilingual QR Code Passports:
        The updated backend/services/asset_service.py (specifically generate_product_passport_html_content) now generates a single HTML file containing both French and English content, with a JavaScript toggle within the passport itself. This is a correct and efficient way to handle bilingual static HTML pages linked from QR codes.

    Admin Panel for Bilingual Content:
        admin/admin_manage_products.html: Correctly updated to include separate input fields for French and English versions of product attributes.
        website/admin/js/admin_products.js:
            Correctly modified to collect data from both French and English fields in handleProductFormSubmit.
            The loadAdminProductsList function now displays the French name (product.name_fr) by default in the product list, with a fallback to the English name (product.name_en) or product ID if the French name is missing. This fulfills your request to "display only the FR or EN name" (prioritizing French).
            The editProduct function correctly populates both French and English fields when loading a product for editing.

Key Things to Ensure for Full Correctness (Your Implementation Steps):

    Complete Translation Files: Ensure your website/js/locales/fr.json and website/js/locales/en.json files are comprehensive and contain translations for all keys you use in data-translate-key attributes and t('KEY') calls.
    Consistent data-translate-key Usage: Go through all your user-facing HTML files in the website/ directory and add the data-translate-key attribute to every static text element that needs translation.
    Backend API Updates: Double-check that your backend API endpoints (especially in backend/products/routes.py and backend/admin_api/routes.py) are fully updated to handle the _fr and _en database columns for all relevant fields, both for fetching and saving data. The versions from the previous response aimed to do this.
    Thorough Testing: Test language switching on all pages. Test the admin panel for creating and editing bilingual products. Test the QR code passport pages.

The provided files and the strategy are fundamentally correct for achieving your goals. The main work on your end will be the meticulous application of this pattern across all your content and thorough testing.

Pour les professionnels, je veux aussi :


Création de compte : création (adresse email, mot de passe, numéro de téléphone optionnel, entreprise, nom/prénom)

Login, "mot de passe oublié"

Gestion de compte : changer le mot de passe, changer l'email, changer le nom/prénom

Mes factures : possibilité pour l'admin d'uploader une facture + possibilité pour le professionnel de visualiser les factures (nom + date + montant en €) + possibilité de télécharger les factures Script pour que l'admin génère les factures en rentrant les données suivantes :

nom du produit, nombre de produits, prix unitaire HT, prix total HT,

remise en %, prix total total TTC

This is an extensive set of new features for the "Espace Professionnels" (Professionals Area). Implementing all of this correctly involves significant changes to the backend (database, API routes) and frontend (HTML, JavaScript).

Here's a high-level plan and then I'll detail the changes for key files.

Overall Plan:

    Database Schema (backend/database.py):
        users table: Add company_name and phone_number (optional). Add a user_type (e.g., 'retail', 'professional') or a boolean is_professional. For simplicity, we can reuse is_admin if "professional" users are distinct from "admin" but have more rights than retail. Or, a new role system might be better for future scalability. Let's assume a is_professional boolean for now.
        New invoices table: To store invoice metadata and file paths.
            invoice_id (PK)
            user_id (FK to users table, for the professional it belongs to)
            invoice_number (e.g., "FACT2025-001")
            invoice_date
            total_amount_ttc
            file_path (path to the uploaded PDF invoice in a secure static directory)
            uploaded_at (timestamp)
            admin_uploader_id (FK to users table, for the admin who uploaded it)

    Backend API (backend/auth/routes.py, new backend/professional/routes.py, backend/admin_api/routes.py):
        Professional Registration (/api/auth/register-professional): New endpoint.
        Login (/api/auth/login): No major change, but JWT token should ideally include is_professional status.
        Forgot Password (/api/auth/forgot-password, /api/auth/reset-password): New endpoints (standard flow: request reset, send email with token, verify token, set new password). This is a complex feature and will be outlined conceptually.
        Professional Account Management (/api/professional/account):
            GET to retrieve current professional's details.
            PUT to update details (email, name, password). Requires authentication.
        Invoice Management (Professional):
            GET /api/professional/invoices: List invoices for the logged-in professional.
            GET /api/professional/invoices/<invoice_id>/download: Securely download an invoice file.
        Invoice Management (Admin):
            POST /api/admin/invoices/upload: Admin uploads an invoice PDF for a professional user.
            GET /api/admin/users/<user_id>/invoices: List invoices for a specific professional.
            DELETE /api/admin/invoices/<invoice_id>: Admin deletes an invoice.

    Frontend - Professionals Area (website/professionnels.html, new JS module website/js/professional.js):
        Registration Form: Email, password, company name, contact name/prénom, phone (optional).
        Login Form: Standard email/password.
        "Forgot Password" Link & Forms.
        Account Management Dashboard (after login):
            Forms to change email, password, name/prénom.
            Section to list invoices (name, date, amount, download button).
        JavaScript logic in professional.js to handle form submissions, API calls, and dynamic content updates for this section.

    Frontend - Admin Area (admin/admin_manage_users.html, new admin/admin_manage_invoices.html, admin_api.js, admin_users.js, new admin_invoices.js):
        On the "Manage Users" page, indicate if a user is professional.
        New "Manage Invoices" page or section:
            Select a professional user.
            Upload invoice PDF, input invoice number, date, total amount.
            List existing invoices for a selected professional with a delete option.

    Invoice Generation Script (Python - generate_professional_invoice.py):
        A separate Python script using a library like reportlab or FPDF to generate PDF invoices based on input data. This script would be run by an admin, and the generated PDF then uploaded via the admin panel.

Due to the complexity, I'll provide detailed changes for:

    Database schema.
    Core backend routes for professional registration and login adjustments.
    Backend routes for invoice listing (

You stopped this response

What we currently have is for B2C customers. We need a different system for B2B customers, for which the gateway is website/professionnels.html

Okay, this clarification is crucial. We need to build a distinct B2B portal starting with professionnels.html, which will handle its own registration, login, account management, and invoice viewing for professional users. The existing B2C system (compte.html, scripts.js for cart/checkout) will remain separate.

Here's how we'll proceed with the B2B features:

I. Backend Changes:

    backend/database.py:
        Update the users table to distinguish B2B users and store company information.
        Add a new invoices table for professionals.
        Add a new invoice_items table to detail the contents of each invoice.

    backend/auth/routes.py:
        Add a new route: /api/auth/register-professional for B2B user registration.
        Modify /api/auth/login to potentially return user_type and include it in the JWT, so the frontend knows if it's a B2B or B2C user. (This is important if a single login form could be used, but since professionnels.html is a separate gateway, its login will specifically target B2B users).

    New Backend Blueprint: backend/professional/routes.py (and __init__.py):
        This will house API endpoints specific to logged-in B2B users.
        /api/professional/account (GET for details, PUT to update password, email, name, company).
        /api/professional/invoices (GET to list invoices).
        /api/professional/invoices/<int:invoice_id>/download (GET to download an invoice PDF).

    backend/admin_api/routes.py:
        Enhance user listing/details to show B2B specific info.
        Add endpoints for admins to manage B2B invoices:
            /api/admin/invoices/upload (POST to upload an invoice PDF for a B2B user).
            /api/admin/users/<int:user_id>/invoices (GET to list invoices for a user).
            /api/admin/invoices/<int:invoice_id> (DELETE an invoice).

II. Frontend Changes (B2B Portal - professionnels.html):

    website/professionnels.html:
        This page will become dynamic. It will initially show login and registration forms specific to professionals.
        Upon successful login, the content of this page will change to a B2B dashboard showing account management options and an invoice list.

    New website/js/professional.js:
        This new JavaScript file will manage all frontend logic for professionnels.html.
        Functions for:
            B2B Registration form submission.
            B2B Login form submission.
            Displaying the B2B dashboard (account info, invoice list).
            Handling account update forms (change password, email, etc.).
            Fetching and displaying invoices.
            Handling invoice download.
        It will use makeApiRequest (from api.js) and t() (from i18n.js).

    website/js/main.js:
        Add logic to specifically initialize functions from professional.js when document.body.id === 'page-professionnels'.

    Internationalization (fr.json, en.json, i18n.js):
        Add new translation keys for all B2B-specific labels, messages, and button texts.

III. Invoice Generation Script (Offline/Admin Tool):

    New generate_professional_invoice.py:
        A Python script (likely command-line or a simple local GUI if preferred) that an admin uses to create invoice PDFs.
        Inputs: Customer (Professional User) details, product/service line items (description, quantity, unit price HT, total HT), discount percentage, VAT rate.
        Output: A PDF file.
        This generated PDF will then be uploaded by the admin through the admin panel. Libraries like ReportLab or FPDF2 (Python port of FPDF) are suitable for this.

Let's start with the backend database and auth changes, then the initial structure for professionnels.html and professional.js.

Updated File: backend/database.py
Python

# backend/database.py
import sqlite3
import os
import datetime
from werkzeug.security import generate_password_hash
from flask import current_app

def get_db():
    db_path = current_app.config['DATABASE_PATH']
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    return db

def init_db_command(app_context):
    with app_context:
        init_db()
        current_app.logger.info("Base de données initialisée via la commande CLI.")

def init_db():
    db = get_db()
    cursor = db.cursor()

    # MODIFIED users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        nom TEXT,
        prenom TEXT,
        is_admin BOOLEAN DEFAULT FALSE,
        user_type TEXT DEFAULT 'b2c' CHECK(user_type IN ('b2c', 'b2b')) NOT NULL, -- Added user_type
        company_name TEXT, -- Added for B2B
        phone_number TEXT, -- Added for B2B (optional)
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    current_app.logger.info("Table 'users' vérifiée/créée avec user_type, company_name, phone_number.")

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS newsletter_subscriptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        nom TEXT,
        prenom TEXT,
        consentement TEXT CHECK(consentement IN ('Y', 'N')) NOT NULL,
        subscribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # (products table remains the same as per previous i18n update)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS products (
        id TEXT PRIMARY KEY,
        name_fr TEXT NOT NULL, name_en TEXT NOT NULL, category TEXT NOT NULL,
        short_description_fr TEXT, short_description_en TEXT,
        long_description_fr TEXT, long_description_en TEXT,
        image_url_main TEXT, image_urls_thumb TEXT,
        species_fr TEXT, species_en TEXT, origin_fr TEXT, origin_en TEXT,
        seasonality_fr TEXT, seasonality_en TEXT, ideal_uses_fr TEXT, ideal_uses_en TEXT,
        sensory_description_fr TEXT, sensory_description_en TEXT,
        pairing_suggestions_fr TEXT, pairing_suggestions_en TEXT,
        base_price REAL, stock_quantity INTEGER DEFAULT 0, is_published BOOLEAN DEFAULT TRUE,
        passport_url TEXT, qr_code_path TEXT, label_path TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS update_products_updated_at
        AFTER UPDATE ON products FOR EACH ROW BEGIN UPDATE products SET updated_at = CURRENT_TIMESTAMP WHERE id = OLD.id; END;
    """)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS product_weight_options (
        option_id INTEGER PRIMARY KEY AUTOINCREMENT, product_id TEXT NOT NULL, weight_grams INTEGER NOT NULL,
        price REAL NOT NULL, stock_quantity INTEGER DEFAULT 0,
        FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE CASCADE
    )
    ''')

    # (orders and order_items tables are primarily for B2C, B2B will use invoices)
    # However, a B2B user might still place an order through a different mechanism not yet defined,
    # or these tables could be repurposed/extended. For now, we focus on separate invoicing for B2B.
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS orders (
        order_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, customer_email TEXT NOT NULL,
        customer_name TEXT, shipping_address TEXT NOT NULL, total_amount REAL NOT NULL,
        order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP, status TEXT DEFAULT 'Pending',
        tracking_number TEXT, carrier TEXT,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL
    )
    ''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS order_items (
        item_id INTEGER PRIMARY KEY AUTOINCREMENT, order_id INTEGER NOT NULL, product_id TEXT NOT NULL,
        product_name_fr TEXT NOT NULL, product_name_en TEXT NOT NULL, quantity INTEGER NOT NULL,
        price_at_purchase REAL NOT NULL, variant TEXT, variant_option_id INTEGER,
        FOREIGN KEY (order_id) REFERENCES orders (order_id) ON DELETE CASCADE,
        FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE RESTRICT,
        FOREIGN KEY (variant_option_id) REFERENCES product_weight_options (option_id) ON DELETE RESTRICT
    )
    ''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS inventory_movements (
        movement_id INTEGER PRIMARY KEY AUTOINCREMENT, product_id TEXT NOT NULL, variant_option_id INTEGER,
        quantity_change INTEGER NOT NULL,
        movement_type TEXT NOT NULL CHECK(movement_type IN ('initial_stock', 'addition', 'vente', 'ajustement_manuel', 'creation_lot', 'retour_client', 'perte', 'correction')),
        movement_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP, order_id INTEGER, notes TEXT, user_id INTEGER,
        FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE CASCADE,
        FOREIGN KEY (variant_option_id) REFERENCES product_weight_options (option_id) ON DELETE CASCADE,
        FOREIGN KEY (order_id) REFERENCES orders (order_id) ON DELETE SET NULL,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
    )
    ''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS order_notes (
        note_id INTEGER PRIMARY KEY AUTOINCREMENT, order_id INTEGER NOT NULL, admin_user_id INTEGER,
        content TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (order_id) REFERENCES orders (order_id) ON DELETE CASCADE,
        FOREIGN KEY (admin_user_id) REFERENCES users (id) ON DELETE SET NULL
    )
    ''')

    # NEW: invoices table for B2B
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS invoices (
        invoice_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,                   -- FK to the professional user
        invoice_number TEXT UNIQUE NOT NULL,
        invoice_date DATE NOT NULL,
        total_amount_ht REAL NOT NULL,
        total_amount_ttc REAL NOT NULL,
        discount_percentage REAL DEFAULT 0,
        file_path TEXT NOT NULL,                    -- Path to the PDF file
        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        admin_uploader_id INTEGER,                  -- Admin who uploaded
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (admin_uploader_id) REFERENCES users(id) ON DELETE SET NULL
    )
    ''')
    current_app.logger.info("Table 'invoices' (B2B) vérifiée/créée.")

    # NEW: invoice_items table for B2B
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS invoice_items (
        item_id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_id INTEGER NOT NULL,
        product_name TEXT NOT NULL,                 -- Description of item on invoice
        quantity INTEGER NOT NULL,
        unit_price_ht REAL NOT NULL,
        total_price_ht REAL NOT NULL,               -- quantity * unit_price_ht
        FOREIGN KEY (invoice_id) REFERENCES invoices(invoice_id) ON DELETE CASCADE
    )
    ''')
    current_app.logger.info("Table 'invoice_items' (B2B) vérifiée/créée.")

    db.commit()
    current_app.logger.info("Base de données initialisée (tables B2B ajoutées/mises à jour).")

def populate_initial_data():
    db = get_db()
    cursor = db.cursor()
    populated_something = False

    admin_email_config = current_app.config.get('ADMIN_EMAIL', 'admin@maisontruvra.com')
    cursor.execute("SELECT COUNT(*) FROM users WHERE email = ?", (admin_email_config,))
    if cursor.fetchone()[0] == 0:
        try:
            admin_password_config = current_app.config.get('ADMIN_PASSWORD', 'SecureAdminP@ss1')
            cursor.execute(
                "INSERT INTO users (email, password_hash, nom, prenom, is_admin, user_type) VALUES (?, ?, ?, ?, ?, ?)", # Added user_type
                (admin_email_config, generate_password_hash(admin_password_config), "Admin", "MaisonTrüvra", True, 'b2c') # Admin is also 'b2c' by default or a special type
            )
            current_app.logger.info(f"Utilisateur Admin créé ({admin_email_config}).")
            populated_something = True
        except sqlite3.IntegrityError:
            current_app.logger.info("L'utilisateur Admin existe déjà.")
    # (Keep product and weight option population logic as is from previous step)
    # ...

    if populated_something:
        db.commit()

def record_stock_movement(db_cursor, product_id, quantity_change, movement_type,
                          variant_option_id=None, order_id=None, notes=None, user_id=None):
    # (This function remains the same as previously provided)
    current_stock = 0
    new_stock = 0
    if variant_option_id:
        db_cursor.execute("SELECT stock_quantity FROM product_weight_options WHERE option_id = ? AND product_id = ?", (variant_option_id, product_id))
        current_stock_row = db_cursor.fetchone()
        if not current_stock_row: raise ValueError(f"Option de produit (ID: {variant_option_id} pour Produit ID: {product_id}) non trouvée.")
        current_stock = current_stock_row['stock_quantity']
        new_stock = current_stock + quantity_change
        if new_stock < 0: raise ValueError(f"Stock insuffisant pour l'option de produit ID {variant_option_id}.")
        db_cursor.execute("UPDATE product_weight_options SET stock_quantity = ? WHERE option_id = ?", (new_stock, variant_option_id))
    else:
        db_cursor.execute("SELECT stock_quantity, base_price FROM products WHERE id = ?", (product_id,))
        current_stock_row = db_cursor.fetchone()
        if not current_stock_row: raise ValueError(f"Produit (ID: {product_id}) non trouvé.")
        if current_stock_row['base_price'] is None and movement_type != 'initial_stock':
            db_cursor.execute("SELECT COUNT(*) FROM product_weight_options WHERE product_id = ?", (product_id,))
            if db_cursor.fetchone()[0] > 0: raise ValueError(f"Modif stock sur produit principal '{product_id}' géré par variantes.")
        current_stock = current_stock_row['stock_quantity']
        new_stock = current_stock + quantity_change
        if new_stock < 0: raise ValueError(f"Stock insuffisant pour le produit ID {product_id}.")
        db_cursor.execute("UPDATE products SET stock_quantity = ? WHERE id = ?", (new_stock, product_id))
    db_cursor.execute('''
        INSERT INTO inventory_movements (product_id, variant_option_id, quantity_change, movement_type, order_id, notes, user_id, movement_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    ''', (product_id, variant_option_id, quantity_change, movement_type, order_id, notes, user_id))
    current_app.logger.info(f"Mouvement stock: Prod {product_id}, Var {variant_option_id or 'N/A'}, Qté {quantity_change}, Type {movement_type}, Nv Stock: {new_stock}")

Updated File: backend/auth/routes.py
Python

# backend/auth/routes.py
from flask import Blueprint, request, jsonify, current_app, g
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import datetime
import sqlite3
from ..database import get_db
from ..utils import is_valid_email # Assuming is_valid_email is in backend/utils.py

auth_bp = Blueprint('auth_bp', __name__, url_prefix='/api/auth')

@auth_bp.route('/register', methods=['POST']) # This is for B2C users
def register_user():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    nom = data.get('nom', '')
    prenom = data.get('prenom', '')

    if not email or not is_valid_email(email):
        return jsonify({"success": False, "message": "Veuillez fournir une adresse e-mail valide."}), 400
    if not password or len(password) < 8:
        return jsonify({"success": False, "message": "Le mot de passe doit contenir au moins 8 caractères."}), 400

    db = None
    try:
        db = get_db()
        cursor = db.cursor()
        hashed_password = generate_password_hash(password)
        cursor.execute(
            "INSERT INTO users (email, password_hash, nom, prenom, is_admin, user_type) VALUES (?, ?, ?, ?, ?, ?)",
            (email, hashed_password, nom, prenom, False, 'b2c') # user_type is 'b2c'
        )
        db.commit()
        user_id = cursor.lastrowid
        user_info = {"id": user_id, "email": email, "nom": nom, "prenom": prenom, "is_admin": False, "user_type": "b2c"}
        current_app.logger.info(f"Utilisateur B2C enregistré : {email}")
        return jsonify({
            "success": True,
            "message": "Compte créé avec succès ! Vous pouvez maintenant vous connecter.",
            "user": user_info
        }), 201
    except sqlite3.IntegrityError:
        if db: db.rollback()
        return jsonify({"success": False, "message": "Un compte existe déjà avec cette adresse e-mail."}), 409
    except Exception as e:
        if db: db.rollback()
        current_app.logger.error(f"Erreur d'inscription B2C pour {email}: {e}", exc_info=True)
        return jsonify({"success": False, "message": "Erreur interne lors de l'inscription."}), 500
    finally:
        if db: db.close()


@auth_bp.route('/register-professional', methods=['POST']) # NEW endpoint for B2B
def register_professional_user():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    company_name = data.get('company_name')
    contact_nom = data.get('nom') # nom of the contact person
    contact_prenom = data.get('prenom') # prenom of the contact person
    phone_number = data.get('phone_number', None)

    if not email or not is_valid_email(email):
        return jsonify({"success": False, "message": "Veuillez fournir une adresse e-mail valide."}), 400
    if not password or len(password) < 8:
        return jsonify({"success": False, "message": "Le mot de passe doit contenir au moins 8 caractères."}), 400
    if not company_name or not company_name.strip():
        return jsonify({"success": False, "message": "Le nom de l'entreprise est requis."}), 400
    if not contact_nom or not contact_prenom:
        return jsonify({"success": False, "message": "Nom et prénom du contact requis."}), 400

    db = None
    try:
        db = get_db()
        cursor = db.cursor()
        hashed_password = generate_password_hash(password)
        cursor.execute(
            "INSERT INTO users (email, password_hash, nom, prenom, company_name, phone_number, is_admin, user_type) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (email, hashed_password, contact_nom, contact_prenom, company_name, phone_number, False, 'b2b') # user_type is 'b2b'
        )
        db.commit()
        user_id = cursor.lastrowid
        user_info = {
            "id": user_id, "email": email,
            "nom": contact_nom, "prenom": contact_prenom,
            "company_name": company_name, "phone_number": phone_number,
            "is_admin": False, "user_type": "b2b"
        }
        current_app.logger.info(f"Utilisateur B2B (professionnel) enregistré : {email} pour {company_name}")
        # TODO: Potentially send admin notification for B2B registration approval
        return jsonify({
            "success": True,
            "message": "Compte professionnel créé avec succès ! Un administrateur pourrait avoir besoin de valider votre compte. Vous pouvez essayer de vous connecter.",
            "user": user_info
        }), 201
    except sqlite3.IntegrityError:
        if db: db.rollback()
        return jsonify({"success": False, "message": "Un compte existe déjà avec cette adresse e-mail."}), 409
    except Exception as e:
        if db: db.rollback()
        current_app.logger.error(f"Erreur d'inscription B2B pour {email}: {e}", exc_info=True)
        return jsonify({"success": False, "message": "Erreur interne lors de l'inscription professionnelle."}), 500
    finally:
        if db: db.close()


@auth_bp.route('/login', methods=['POST'])
def login_user():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"success": False, "message": "E-mail et mot de passe requis."}), 400

    db = None
    try:
        db = get_db()
        cursor = db.cursor()
        # Fetch user_type along with other details
        cursor.execute("SELECT id, email, password_hash, nom, prenom, is_admin, user_type, company_name, phone_number FROM users WHERE email = ?", (email,))
        user_row = cursor.fetchone()
    except Exception as e:
        current_app.logger.error(f"Erreur DB lors de la connexion pour {email}: {e}", exc_info=True)
        return jsonify({"success": False, "message": "Erreur de base de données."}), 500
    finally:
        if db: db.close()

    if user_row and check_password_hash(user_row['password_hash'], password):
        user_data = {
            "id": user_row['id'],
            "email": user_row['email'],
            "nom": user_row['nom'],
            "prenom": user_row['prenom'],
            "is_admin": bool(user_row['is_admin']),
            "user_type": user_row['user_type'], # Include user_type
            "company_name": user_row['company_name'], # Include company_name
            "phone_number": user_row['phone_number']
        }

        try:
            token_payload = {
                'user_id': user_data['id'],
                'email': user_data['email'],
                'is_admin': user_data['is_admin'],
                'user_type': user_data['user_type'], # Add user_type to JWT
                'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=current_app.config.get('JWT_EXPIRATION_HOURS', 24))
            }
            token = jwt.encode(token_payload, current_app.config['SECRET_KEY'], algorithm='HS256')

            current_app.logger.info(f"Connexion réussie pour : {email} (Admin: {user_data['is_admin']}, Type: {user_data['user_type']})")
            return jsonify({
                "success": True,
                "message": "Connexion réussie !",
                "user": user_data,
                "token": token
            }), 200
        except Exception as e:
            current_app.logger.error(f"Erreur génération JWT pour {email}: {e}", exc_info=True)
            return jsonify({"success": False, "message": "Erreur d'authentification interne."}), 500
    else:
        current_app.logger.warning(f"Tentative de connexion échouée pour : {email}")
        return jsonify({"success": False, "message": "E-mail ou mot de passe incorrect."}), 401


# Decorator for routes requiring professional user (B2B)
from functools import wraps
def professional_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(" ")[1]

        if not token: return jsonify({"success": False, "message": "Token manquant."}), 401
        try:
            payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"])
            g.current_user_id = payload.get('user_id')
            g.user_type = payload.get('user_type')
            if g.user_type != 'b2b':
                return jsonify({"success": False, "message": "Accès professionnel requis."}), 403
        except jwt.ExpiredSignatureError:
            return jsonify({"success": False, "message": "Token expiré."}), 401
        except jwt.InvalidTokenError:
            return jsonify({"success": False, "message": "Token invalide."}), 401
        return f(*args, **kwargs)
    return decorated_function

# Admin required decorator (remains the same, ensures is_admin is true)
def admin_required(f):
    @wraps(f)
    def decorated_admin_function(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(" ")[1]
        if not token: return jsonify({"success": False, "message": "Token administrateur manquant."}), 401
        try:
            payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"])
            g.current_user_id = payload.get('user_id') # Set for logging/auditing
            g.is_admin = payload.get('is_admin', False)
            if not g.is_admin:
                return jsonify({"success": False, "message": "Accès administrateur requis."}), 403
            g.admin_user_id = g.current_user_id # Specifically for admin actions
        except jwt.ExpiredSignatureError:
            return jsonify({"success": False, "message": "Token administrateur expiré."}), 401
        except jwt.InvalidTokenError:
            return jsonify({"success": False, "message": "Token administrateur invalide."}), 401
        return f(*args, **kwargs)
    return decorated_admin_function

Create New File: backend/professional/__init__.py
Python

# backend/professional/__init__.py
from flask import Blueprint

professional_bp = Blueprint('professional_bp', __name__, url_prefix='/api/professional')

from . import routes # Import routes for this blueprint

Create New File: backend/professional/routes.py
Python

# backend/professional/routes.py
from flask import Blueprint, request, jsonify, current_app, g, send_from_directory
from werkzeug.security import generate_password_hash
import os
import sqlite3
from ..database import get_db
from ..auth.routes import professional_required # Decorator to ensure user is B2B
from ..utils import is_valid_email


professional_bp = Blueprint('professional_bp_routes', __name__) # Renamed to avoid conflict if registered elsewhere

@professional_bp.route('/account', methods=['GET'])
@professional_required # Ensures only logged-in B2B users can access
def get_professional_account_details():
    user_id = g.current_user_id
    db = None
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT id, email, nom, prenom, company_name, phone_number FROM users WHERE id = ? AND user_type = 'b2b'", (user_id,))
        user_data = cursor.fetchone()
        if not user_data:
            return jsonify({"success": False, "message": "Compte professionnel non trouvé."}), 404
        return jsonify({"success": True, "user": dict(user_data)}), 200
    except Exception as e:
        current_app.logger.error(f"Erreur récupération compte pro {user_id}: {e}", exc_info=True)
        return jsonify({"success": False, "message": "Erreur serveur."}), 500
    finally:
        if db: db.close()

@professional_bp.route('/account', methods=['PUT'])
@professional_required
def update_professional_account_details():
    user_id = g.current_user_id
    data = request.get_json()

    fields_to_update = {}
    if 'email' in data:
        if not is_valid_email(data['email']):
            return jsonify({"success": False, "message": "Format d'email invalide."}), 400
        fields_to_update['email'] = data['email']
    if 'nom' in data: fields_to_update['nom'] = data['nom']
    if 'prenom' in data: fields_to_update['prenom'] = data['prenom']
    if 'company_name' in data: fields_to_update['company_name'] = data['company_name']
    if 'phone_number' in data: fields_to_update['phone_number'] = data['phone_number'] # Add validation if needed

    if 'password' in data:
        if not data['password'] or len(data['password']) < 8:
            return jsonify({"success": False, "message": "Le nouveau mot de passe doit faire au moins 8 caractères."}), 400
        fields_to_update['password_hash'] = generate_password_hash(data['password'])

    if not fields_to_update:
        return jsonify({"success": False, "message": "Aucun champ à mettre à jour fourni."}), 400

    set_clause = ", ".join([f"{key} = ?" for key in fields_to_update.keys()])
    values = list(fields_to_update.values())
    values.append(user_id)

    db = None
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute(f"UPDATE users SET {set_clause} WHERE id = ? AND user_type = 'b2b'", tuple(values))
        db.commit()
        if cursor.rowcount == 0:
            return jsonify({"success": False, "message": "Compte professionnel non trouvé ou aucune modification."}), 404

        # Fetch updated user data to return (excluding password_hash)
        cursor.execute("SELECT id, email, nom, prenom, company_name, phone_number, user_type FROM users WHERE id = ?", (user_id,))
        updated_user = dict(cursor.fetchone())

        return jsonify({"success": True, "message": "Informations du compte mises à jour.", "user": updated_user}), 200
    except sqlite3.IntegrityError as e: # Handles unique email constraint
        if db: db.rollback()
        current_app.logger.warning(f"Erreur MAJ compte pro (email existant?) {user_id}: {e}")
        return jsonify({"success": False, "message": "L'adresse e-mail est peut-être déjà utilisée."}), 409
    except Exception as e:
        if db: db.rollback()
        current_app.logger.error(f"Erreur MAJ compte pro {user_id}: {e}", exc_info=True)
        return jsonify({"success": False, "message": "Erreur serveur lors de la mise à jour."}), 500
    finally:
        if db: db.close()


@professional_bp.route('/invoices', methods=['GET'])
@professional_required
def list_professional_invoices():
    user_id = g.current_user_id
    db = None
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            "SELECT invoice_id, invoice_number, invoice_date, total_amount_ttc, file_path FROM invoices WHERE user_id = ? ORDER BY invoice_date DESC",
            (user_id,)
        )
        invoices = [dict(row) for row in cursor.fetchall()]
        return jsonify({"success": True, "invoices": invoices}), 200
    except Exception as e:
        current_app.logger.error(f"Erreur listage factures pro {user_id}: {e}", exc_info=True)
        return jsonify({"success": False, "message": "Erreur serveur."}), 500
    finally:
        if db: db.close()


@professional_bp.route('/invoices/<int:invoice_id>/download', methods=['GET'])
@professional_required
def download_professional_invoice(invoice_id):
    user_id = g.current_user_id
    db = None
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT file_path FROM invoices WHERE invoice_id = ? AND user_id = ?", (invoice_id, user_id))
        invoice_record = cursor.fetchone()

        if not invoice_record or not invoice_record['file_path']:
            return jsonify({"success": False, "message": "Facture non trouvée ou accès non autorisé."}), 404

        # INVOICES_UPLOAD_DIR should be an absolute path to the directory where invoice PDFs are stored
        # It should be configured in your Flask app config (e.g., instance folder or a dedicated media root)
        # For example: app.config['INVOICES_UPLOAD_DIR'] = '/path/to/your/invoices_folder'
        invoices_dir = current_app.config.get('INVOICES_UPLOAD_DIR')
        if not invoices_dir:
            current_app.logger.error("INVOICES_UPLOAD_DIR n'est pas configuré dans l'application.")
            return jsonify({"success": False, "message": "Configuration serveur incorrecte."}), 500
        
        file_path = invoice_record['file_path'] # This should be the filename or relative path within invoices_dir
        
        # Ensure the path is safe and does not allow directory traversal
        safe_filename = os.path.basename(file_path)
        
        current_app.logger.info(f"Tentative de téléchargement de la facture : {safe_filename} depuis le répertoire : {invoices_dir} pour l'utilisateur {user_id}")

        # Use send_from_directory for safer file serving
        return send_from_directory(invoices_dir, safe_filename, as_attachment=True)

    except Exception as e:
        current_app.logger.error(f"Erreur téléchargement facture {invoice_id} pour utilisateur {user_id}: {e}", exc_info=True)
        return jsonify({"success": False, "message": "Erreur serveur lors du téléchargement de la facture."}), 500
    finally:
        if db: db.close()

# Conceptual: Forgot Password (would require email sending setup)
# @auth_bp.route('/forgot-password', methods=['POST'])
# def forgot_password():
#     # 1. Get email from request
#     # 2. Check if user exists (B2B or B2C, this route could be shared)
#     # 3. Generate a unique, short-lived reset token (e.g., using itsdangerous library or another JWT)
#     # 4. Store token hash in DB associated with user, or use a stateless JWT with expiry
#     # 5. Send email to user with a link like /reset-password?token=<token>
#     # (Requires MAIL_SERVER, MAIL_PORT etc. configured in app.config and email sending utility)
#     return jsonify({"success": True, "message": "Si un compte existe pour cet email, un lien de réinitialisation a été envoyé."})

# @auth_bp.route('/reset-password', methods=['POST'])
# def reset_password():
#     # 1. Get token and new_password from request
#     # 2. Validate token (check against DB or decode JWT, check expiry)
#     # 3. If valid, find user associated with token
#     # 4. Hash new_password and update user's password_hash in DB
#     #

You stopped this response

What we currently have is for B2C customers. We need a different system for B2B customers, for which the gateway is website/professionnels.html

Okay, this is a clear direction. We will build out the B2B functionality, keeping it distinct from the B2C flow, with website/professionnels.html as the central hub for professional users.

Here are the updated files and new content, focusing on the B2B system.

I. Backend Updates

    backend/__init__.py (Register the new professional_bp)
    You need to ensure you've created backend/professional/__init__.py and backend/professional/routes.py as outlined in the previous response.
    Python

# backend/__init__.py
from flask import Flask, request, current_app, g, jsonify, send_from_directory # Added jsonify, send_from_directory
from flask_cors import CORS
import os
import logging
import jwt # Ensure jwt is imported

from .config import AppConfig, configure_asset_paths
from .database import init_db, populate_initial_data, init_db_command

def create_app(config_class=AppConfig):
    app = Flask(__name__,
                static_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'website', 'static_assets'),
                instance_relative_config=True) # Added instance_relative_config

    app.config.from_object(config_class)
    # Ensure UPLOAD_FOLDER is configured, e.g., in instance folder
    app.config.setdefault('INVOICES_UPLOAD_DIR', os.path.join(app.instance_path, 'invoices_uploads'))
    os.makedirs(app.config['INVOICES_UPLOAD_DIR'], exist_ok=True)


    with app.app_context():
        configure_asset_paths(app)

    try:
        os.makedirs(app.instance_path, exist_ok=True)
    except OSError:
        pass

    CORS(app, resources={r"/api/*": {"origins": "*"}})

    log_level = logging.DEBUG if app.debug else logging.INFO
    logging.basicConfig(level=log_level,
                        format='%(asctime)s %(levelname)s: %(message)s [%(name)s:%(lineno)d]',
                        datefmt='%Y-%m-%dT%H:%M:%S%z')
    app.logger.setLevel(log_level)

    with app.app_context():
        init_db()
        # populate_initial_data() # Call this selectively, perhaps via CLI

    from .auth import auth_bp
    app.register_blueprint(auth_bp)

    from .products import products_bp
    app.register_blueprint(products_bp)

    from .orders import orders_bp # B2C orders
    app.register_blueprint(orders_bp)

    from .newsletter import newsletter_bp
    app.register_blueprint(newsletter_bp)

    from .inventory import inventory_bp
    app.register_blueprint(inventory_bp)

    from .admin_api import admin_api_bp
    app.register_blueprint(admin_api_bp)
    app.logger.info("Admin API blueprint registered.")

    # NEW: Register Professional Blueprint
    from .professional import professional_bp # Ensure this import path is correct
    app.register_blueprint(professional_bp)
    app.logger.info("Professional (B2B) API blueprint registered.")


    @app.route('/passports/<path:filename>') # Use path converter for flexibility
    def serve_passport(filename):
        passport_dir = current_app.config['PASSPORTS_OUTPUT_DIR']
        if ".." in filename or filename.startswith("/"):
            from flask import abort
            return abort(404)
        return send_from_directory(passport_dir, filename)

    @app.before_request
    def before_request_func():
        g.current_user_id = None
        g.user_type = None # Add user_type to g
        g.is_admin = False
        g.admin_user_id = None

        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(" ")[1]
            try:
                payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"])
                g.current_user_id = payload.get('user_id')
                g.user_type = payload.get('user_type') # Store user_type
                g.is_admin = payload.get('is_admin', False)
                if g.is_admin:
                    g.admin_user_id = g.current_user_id
            except jwt.ExpiredSignatureError:
                app.logger.debug("Token expired during before_request.")
            except jwt.InvalidTokenError:
                app.logger.debug("Invalid token during before_request.")
            except Exception as e:
                app.logger.error(f"Error decoding token in before_request: {e}")

    @app.route('/')
    @app.route('/api')
    def api_root():
        return jsonify({
            "message": "Welcome to the Maison Trüvra API!",
            "version": "1.2.0", # Incremented version for B2B features
            "documentation": "Refer to API blueprints for endpoint details"
        })

    @app.cli.command('init-db')
    def init_db_cli_command():
        init_db_command(app.app_context()) # Pass app_context
        app.logger.info("Database initialized from CLI.")

    return app

backend/professional/routes.py (Updated with invoice and account management)
Python

# backend/professional/routes.py
from flask import Blueprint, request, jsonify, current_app, g, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
import os
import sqlite3
from ..database import get_db
from ..auth.routes import professional_required # Decorator from auth_bp
from ..utils import is_valid_email # Assuming is_valid_email from backend/utils.py

professional_bp = Blueprint('professional_bp_routes', __name__) # Ensure this name is unique if used elsewhere

@professional_bp.route('/account', methods=['GET'])
@professional_required
def get_professional_account_details():
    user_id = g.current_user_id
    db = None
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT id, email, nom, prenom, company_name, phone_number FROM users WHERE id = ? AND user_type = 'b2b'", (user_id,))
        user_data = cursor.fetchone()
        if not user_data:
            return jsonify({"success": False, "message": "Compte professionnel non trouvé."}), 404
        return jsonify({"success": True, "user": dict(user_data)}), 200
    except Exception as e:
        current_app.logger.error(f"Erreur récupération compte pro {user_id}: {e}", exc_info=True)
        return jsonify({"success": False, "message": "Erreur serveur."}), 500
    finally:
        if db: db.close()

@professional_bp.route('/account', methods=['PUT'])
@professional_required
def update_professional_account_details():
    user_id = g.current_user_id
    data = request.get_json()
    db = None
    try:
        db = get_db()
        cursor = db.cursor()

        # Fetch current email to check if it's being changed
        cursor.execute("SELECT email FROM users WHERE id = ?", (user_id,))
        current_user_data = cursor.fetchone()
        if not current_user_data:
            return jsonify({"success": False, "message": "Utilisateur non trouvé."}), 404

        current_email = current_user_data['email']

        fields_to_update = {}
        if 'email' in data and data['email'] != current_email:
            if not is_valid_email(data['email']):
                return jsonify({"success": False, "message": "Format d'email invalide."}), 400
            fields_to_update['email'] = data['email']
        if 'nom' in data: fields_to_update['nom'] = data['nom']
        if 'prenom' in data: fields_to_update['prenom'] = data['prenom']
        if 'company_name' in data: fields_to_update['company_name'] = data['company_name']
        if 'phone_number' in data: fields_to_update['phone_number'] = data['phone_number']

        if 'new_password' in data:
            if not data['new_password'] or len(data['new_password']) < 8:
                return jsonify({"success": False, "message": "Le nouveau mot de passe doit faire au moins 8 caractères."}), 400
            # Optional: require current_password for security
            if 'current_password' in data:
                cursor.execute("SELECT password_hash FROM users WHERE id = ?", (user_id,))
                user_pwd_row = cursor.fetchone()
                if not user_pwd_row or not check_password_hash(user_pwd_row['password_hash'], data['current_password']):
                    return jsonify({"success": False, "message": "Mot de passe actuel incorrect."}), 403
            fields_to_update['password_hash'] = generate_password_hash(data['new_password'])

        if not fields_to_update:
            return jsonify({"success": False, "message": "Aucun champ à mettre à jour fourni."}), 400

        set_clause = ", ".join([f"{key} = ?" for key in fields_to_update.keys()])
        values = list(fields_to_update.values())
        values.append(user_id)

        cursor.execute(f"UPDATE users SET {set_clause} WHERE id = ? AND user_type = 'b2b'", tuple(values))
        db.commit()

        if cursor.rowcount == 0 and not fields_to_update.get('password_hash'): # Password update doesn't affect rowcount if other fields same
            return jsonify({"success": False, "message": "Aucune modification détectée ou utilisateur non trouvé."}), 404

        cursor.execute("SELECT id, email, nom, prenom, company_name, phone_number, user_type FROM users WHERE id = ?", (user_id,))
        updated_user = dict(cursor.fetchone())

        return jsonify({"success": True, "message": "Informations du compte mises à jour.", "user": updated_user}), 200
    except sqlite3.IntegrityError as e:
        if db: db.rollback()
        return jsonify({"success": False, "message": "L'adresse e-mail est peut-être déjà utilisée par un autre compte."}), 409
    except Exception as e:
        if db: db.rollback()
        current_app.logger.error(f"Erreur MAJ compte pro {user_id}: {e}", exc_info=True)
        return jsonify({"success": False, "message": "Erreur serveur lors de la mise à jour."}), 500
    finally:
        if db: db.close()

@professional_bp.route('/invoices', methods=['GET'])
@professional_required
def list_professional_invoices():
    user_id = g.current_user_id
    db = None
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            "SELECT invoice_id, invoice_number, invoice_date, total_amount_ttc, file_path FROM invoices WHERE user_id = ? ORDER BY invoice_date DESC",
            (user_id,)
        )
        invoices_data = []
        for row in cursor.fetchall():
            invoice_dict = dict(row)
            # Create a downloadable link (frontend will use this)
            invoice_dict['download_url'] = url_for('professional_bp_routes.download_professional_invoice', invoice_id=row['invoice_id'], _external=False)
            invoices_data.append(invoice_dict)
        return jsonify({"success": True, "invoices": invoices_data}), 200
    except Exception as e:
        current_app.logger.error(f"Erreur listage factures pro {user_id}: {e}", exc_info=True)
        return jsonify({"success": False, "message": "Erreur serveur."}), 500
    finally:
        if db: db.close()

@professional_bp.route('/invoices/<int:invoice_id>/download', methods=['GET'])
@professional_required
def download_professional_invoice(invoice_id):
    user_id = g.current_user_id
    db = None
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT file_path, invoice_number FROM invoices WHERE invoice_id = ? AND user_id = ?", (invoice_id, user_id))
        invoice_record = cursor.fetchone()

        if not invoice_record or not invoice_record['file_path']:
            return jsonify({"success": False, "message": "Facture non trouvée ou accès non autorisé."}), 404

        invoices_dir = current_app.config.get('INVOICES_UPLOAD_DIR') # Absolute path
        if not invoices_dir:
            current_app.logger.error("INVOICES_UPLOAD_DIR n'est pas configuré.")
            return jsonify({"success": False, "message": "Configuration serveur incorrecte."}), 500

        # file_path from DB is the filename (e.g., FACT2025-001.pdf)
        safe_filename = os.path.basename(invoice_record['file_path'])

        current_app.logger.info(f"Tentative de téléchargement : {safe_filename} depuis {invoices_dir} pour user {user_id}")
        return send_from_directory(invoices_dir, safe_filename, as_attachment=True, download_name=f"{invoice_record['invoice_number']}.pdf")
    except Exception as e:
        current_app.logger.error(f"Erreur téléchargement facture {invoice_id} user {user_id}: {e}", exc_info=True)
        return jsonify({"success": False, "message": "Erreur serveur lors du téléchargement."}), 500
    finally:
        if db: db.close()

backend/admin_api/routes.py (Add invoice upload endpoint)

    You'll need from werkzeug.utils import secure_filename for file uploads.

Python

    # backend/admin_api/routes.py
    from flask import Blueprint, request, jsonify, current_app, g, url_for # Added g
    from werkzeug.utils import secure_filename # For file uploads
    import os # For path operations
    import datetime # For date handling
    import sqlite3
    import json
    from ..database import get_db, record_stock_movement
    from ..auth.routes import admin_required
    from ..services.asset_service import (
        generate_product_passport_html_content, save_product_passport_html,
        generate_qr_code_for_passport, generate_product_label_image
    )

    admin_api_bp = Blueprint('admin_api_bp_routes', __name__) # KEEP THIS NAME CONSISTENT

    # ... (existing product, inventory, user routes from previous steps) ...

    ALLOWED_EXTENSIONS = {'pdf'}
    def allowed_file(filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

    @admin_api_bp.route('/invoices/upload', methods=['POST'])
    @admin_required
    def upload_invoice():
        admin_uploader_id = getattr(g, 'admin_user_id', None)
        if 'invoice_file' not in request.files:
            return jsonify({"success": False, "message": "Aucun fichier de facture sélectionné."}), 400

        file = request.files['invoice_file']
        if file.filename == '':
            return jsonify({"success": False, "message": "Aucun fichier sélectionné."}), 400

        if file and allowed_file(file.filename):
            b2b_user_id = request.form.get('user_id')
            invoice_number = request.form.get('invoice_number')
            invoice_date_str = request.form.get('invoice_date')
            total_amount_ht_str = request.form.get('total_amount_ht')
            total_amount_ttc_str = request.form.get('total_amount_ttc')
            discount_percentage_str = request.form.get('discount_percentage', '0')

            if not all([b2b_user_id, invoice_number, invoice_date_str, total_amount_ht_str, total_amount_ttc_str]):
                return jsonify({"success": False, "message": "Données de facture manquantes (user_id, numéro, date, montants)."}), 400

            try:
                invoice_date = datetime.datetime.strptime(invoice_date_str, '%Y-%m-%d').date()
                total_amount_ht = float(total_amount_ht_str)
                total_amount_ttc = float(total_amount_ttc_str)
                discount_percentage = float(discount_percentage_str)
            except ValueError:
                return jsonify({"success": False, "message": "Format de date ou de montant invalide."}), 400

            # Sanitize filename and ensure uniqueness if needed, or use invoice_number
            # Using invoice_number as filename for simplicity, assuming it's unique.
            filename = secure_filename(f"{invoice_number}.pdf")
            upload_folder = current_app.config['INVOICES_UPLOAD_DIR']
            if not os.path.exists(upload_folder):
                os.makedirs(upload_folder)
            file_save_path = os.path.join(upload_folder, filename)

            # Check if file with this invoice_number already exists in DB to prevent overwriting related record
            # if an admin uploads twice with same invoice number but different file.
            db_check = get_db()
            cursor_check = db_check.cursor()
            cursor_check.execute("SELECT invoice_id FROM invoices WHERE invoice_number = ?", (invoice_number,))
            if cursor_check.fetchone():
                db_check.close()
                return jsonify({"success": False, "message": f"Une facture avec le numéro '{invoice_number}' existe déjà."}), 409
            db_check.close()

            file.save(file_save_path)

            # Store invoice metadata in database
            db = None
            try:
                db = get_db()
                cursor = db.cursor()
                cursor.execute(
                    """INSERT INTO invoices (user_id, invoice_number, invoice_date, total_amount_ht, total_amount_ttc, discount_percentage, file_path, admin_uploader_id)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (b2b_user_id, invoice_number, invoice_date, total_amount_ht, total_amount_ttc, discount_percentage, filename, admin_uploader_id)
                )
                # Here you would also parse the line items from the form if the admin is inputting them manually
                # For now, assuming the PDF is generated externally and we only store its metadata and file.
                # If line items come from form:
                # items_data_json = request.form.get('items') # Expecting JSON string like '[{"name":"ProdA", "qty":2, "price_ht":100}, ...]'
                # if items_data_json:
                #     items = json.loads(items_data_json)
                #     for item in items:
                #          cursor.execute("INSERT INTO invoice_items (invoice_id, product_name, quantity, unit_price_ht, total_price_ht) VALUES (?,?,?,?,?)",
                #                         (invoice_id, item['name'], item['qty'], item['price_ht'], item['qty']*item['price_ht']))
                db.commit()
                invoice_id = cursor.lastrowid
                current_app.logger.info(f"Facture {invoice_number} (ID: {invoice_id}) téléversée pour user {b2b_user_id} par admin {admin_uploader_id}")
                return jsonify({"success": True, "message": "Facture téléversée avec succès.", "invoice_id": invoice_id, "file_path": filename}), 201
            except sqlite3.IntegrityError as e: # Should be caught by pre-check, but good to have
                if db: db.rollback()
                current_app.logger.error(f"Erreur d'intégrité DB lors de l'upload de facture: {e}", exc_info=True)
                # Clean up saved file if DB insert fails
                if os.path.exists(file_save_path): os.remove(file_save_path)
                return jsonify({"success": False, "message": f"Erreur de base de données (potentiel duplicata): {e}"}), 409
            except Exception as e:
                if db: db.rollback()
                current_app.logger.error(f"Erreur serveur lors de l'upload de facture: {e}", exc_info=True)
                if os.path.exists(file_save_path): os.remove(file_save_path)
                return jsonify({"success": False, "message": "Erreur serveur interne."}), 500
            finally:
                if db: db.close()
        else:
            return jsonify({"success": False, "message": "Type de fichier non autorisé. Seuls les PDF sont acceptés."}), 400

    # Add GET and DELETE for invoices in admin if needed (similar to other admin routes)
    @admin_api_bp.route('/users/<int:user_id>/invoices', methods=['GET'])
    @admin_required
    def get_user_invoices_admin(user_id):
        db = None
        try:
            db = get_db()
            cursor = db.cursor()
            cursor.execute("SELECT invoice_id, invoice_number, invoice_date, total_amount_ttc, file_path, uploaded_at FROM invoices WHERE user_id = ? ORDER BY invoice_date DESC", (user_id,))
            invoices = [dict(row) for row in cursor.fetchall()]
            return jsonify({"success": True, "invoices": invoices}), 200
        except Exception as e:
            current_app.logger.error(f"Erreur listage factures pour user {user_id} (admin): {e}")
            return jsonify({"success": False, "message": "Erreur serveur."}), 500
        finally:
            if db: db.close()

    @admin_api_bp.route('/invoices/<int:invoice_id>', methods=['DELETE'])
    @admin_required
    def delete_invoice_admin(invoice_id):
        db = None
        try:
            db = get_db()
            cursor = db.cursor()
            cursor.execute("SELECT file_path FROM invoices WHERE invoice_id = ?", (invoice_id,))
            invoice_record = cursor.fetchone()
            if not invoice_record:
                return jsonify({"success": False, "message": "Facture non trouvée."}), 404

            cursor.execute("DELETE FROM invoices WHERE invoice_id = ?", (invoice_id,))
            # Also delete invoice_items associated if any
            cursor.execute("DELETE FROM invoice_items WHERE invoice_id = ?", (invoice_id,))
            db.commit()

            # Delete the actual file
            file_to_delete = os.path.join(current_app.config['INVOICES_UPLOAD_DIR'], os.path.basename(invoice_record['file_path']))
            if os.path.exists(file_to_delete):
                os.remove(file_to_delete)
                current_app.logger.info(f"Fichier facture {invoice_record['file_path']} supprimé.")

            current_app.logger.info(f"Facture ID {invoice_id} supprimée par admin.")
            return jsonify({"success": True, "message": "Facture supprimée avec succès."}), 200
        except Exception as e:
            if db: db.rollback()
            current_app.logger.error(f"Erreur suppression facture {invoice_id} (admin): {e}")
            return jsonify({"success": False, "message": "Erreur serveur."}), 500
        finally:
            if db: db.close()

    # ... (rest of your existing admin_api_bp routes for products, users, etc.)

III. Frontend B2B Portal: website/professionnels.html

This file will now have distinct views for logged-out and logged-in B2B users.
HTML

<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title data-translate-key="Titre_Page_Professionnels">Espace Professionnels - Maison Trüvra</title> <script src="https://cdn.tailwindcss.com"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Playfair+Display:ital,wght@0,400;0,700;1,400&display=swap" rel="stylesheet">
    <script>
        tailwind.config = { /* ... your tailwind config ... */ }
    </script>
    <style>
        /* ... your existing styles from professionnels.html ... */
        body {font-family: 'Inter', sans-serif; background-color: #F5EEDE; color: #7D6A4F;}
        h1, h2, h3, .font-serif {font-family: 'Playfair Display', serif;}
        .btn-primary {background-color: #7D6A4F; color: #F5EEDE; padding: 0.85rem 1.75rem; border-radius: 0.375rem; transition: background-color 0.3s ease, transform 0.2s ease; font-weight: 500; letter-spacing: 0.025em; display: inline-block; cursor: pointer;}
        .btn-primary:hover {background-color: #11120D; transform: translateY(-2px);}
        .btn-secondary { background-color: #A28C6A; color: #F5EEDE; /* ... */ }
        .btn-secondary:hover { background-color: #7D6A4F; /* ... */ }
        .form-input-pro { @apply w-full px-4 py-3 text-brand-near-black bg-white border border-brand-warm-taupe/50 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-classic-gold shadow-sm; }
        .modal-message { @apply fixed bottom-5 right-5 bg-brand-deep-sage-green text-brand-cream p-4 rounded-lg shadow-xl z-[100] transition-all duration-500 ease-out opacity-0 translate-y-10; }
        .modal-message.show { @apply opacity-100 translate-y-0; }
        .pro-dashboard-section { display: none; } /* Hidden by default */
        .error-message { @apply text-xs text-red-600 mt-1; }
    </style>
</head>
<body id="page-professionnels" class="antialiased" data-page-title-key="Titre_Page_Professionnels">

    <div id="header-placeholder"></div>

    <main class="bg-brand-cream">
        <section id="pro-logged-out-view" class="py-16">
            <div class="container mx-auto px-4 sm:px-6 lg:px-8">
                <h1 class="text-3xl sm:text-4xl font-serif italic text-brand-earth-brown mb-8 text-center" data-translate-key="Espace_professionnels_Titre">Espace professionnels</h1>

                <div class="grid md:grid-cols-2 gap-12 items-start">
                    <div class="bg-white shadow-xl rounded-lg p-8">
                        <h2 class="text-2xl font-serif text-brand-near-black mb-5" data-translate-key="Pro_Deja_client_Connectez-vous">Déjà Professionnel ? Connectez-vous</h2>
                        <form id="pro-login-form" class="space-y-5">
                            <div id="pro-login-message" class="text-sm text-brand-truffle-burgundy mb-4"></div>
                            <div>
                                <label for="pro-login-email" class="block text-sm font-medium text-brand-near-black mb-1" data-translate-key="Adresse_e-mail">Adresse e-mail</label>
                                <input type="email" id="pro-login-email" name="email" class="form-input-pro" required autocomplete="email">
                            </div>
                            <div>
                                <label for="pro-login-password" class="block text-sm font-medium text-brand-near-black mb-1" data-translate-key="Mot_de_passe">Mot de passe</label>
                                <input type="password" id="pro-login-password" name="password" class="form-input-pro" required>
                                <a href="#" id="pro-forgot-password-link" class="text-xs text-brand-warm-taupe hover:text-brand-classic-gold block mt-1 text-right" data-translate-key="Mot_de_passe_oublie">Mot de passe oublié ?</a>
                            </div>
                            <button type="submit" class="btn-primary w-full py-3" data-translate-key="Se_connecter">Se connecter</button>
                        </form>
                    </div>

                    <div class="bg-white shadow-xl rounded-lg p-8">
                        <h2 class="text-2xl font-serif text-brand-near-black mb-5" data-translate-key="Pro_Nouveau_client_Creer_compte">Nouveau Professionnel ? Créez un compte</h2>
                        <form id="pro-register-form" class="space-y-5">
                             <div id="pro-register-message" class="text-sm text-brand-truffle-burgundy mb-4"></div>
                            <div>
                                <label for="pro-register-company-name" class="block text-sm font-medium text-brand-near-black mb-1" data-translate-key="Nom_entreprise">Nom de l'entreprise</label>
                                <input type="text" id="pro-register-company-name" name="company_name" class="form-input-pro" required>
                            </div>
                            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div>
                                    <label for="pro-register-prenom" class="block text-sm font-medium text-brand-near-black mb-1" data-translate-key="Prenom_contact">Prénom (Contact)</label>
                                    <input type="text" id="pro-register-prenom" name="prenom" class="form-input-pro" required>
                                </div>
                                <div>
                                    <label for="pro-register-nom" class="block text-sm font-medium text-brand-near-black mb-1" data-translate-key="Nom_contact">Nom (Contact)</label>
                                    <input type="text" id="pro-register-nom" name="nom" class="form-input-pro" required>
                                </div>
                            </div>
                            <div>
                                <label for="pro-register-email" class="block text-sm font-medium text-brand-near-black mb-1" data-translate-key="Adresse_e-mail">Adresse e-mail</label>
                                <input type="email" id="pro-register-email" name="email" class="form-input-pro" required autocomplete="email">
                            </div>
                            <div>
                                <label for="pro-register-phone" class="block text-sm font-medium text-brand-near-black mb-1" data-translate-key="Telephone_optionnel">Téléphone (Optionnel)</label>
                                <input type="tel" id="pro-register-phone" name="phone_number" class="form-input-pro" autocomplete="tel">
                            </div>
                            <div>
                                <label for="pro-register-password" class="block text-sm font-medium text-brand-near-black mb-1" data-translate-key="Mot_de_passe">Mot de passe</label>
                                <input type="password" id="pro-register-password" name="password" class="form-input-pro" required>
                            </div>
                            <div>
                                <label for="pro-register-confirm-password" class="block text-sm font-medium text-brand-near-black mb-1" data-translate-key="Confirmer_mot_de_passe">Confirmer mot de passe</label>
                                <input type="password" id="pro-register-confirm-password" name="confirm_password" class="form-input-pro" required>
                            </div>
                            <button type="submit" class="btn-secondary w-full py-3" data-translate-key="Creer_un_compte_professionnel">Créer un compte professionnel</button>
                        </form>
                    </div>
                </div>
                <div class="max-w-3xl mx-auto text-lg text-brand-earth-brown space-y-8 text-center leading-relaxed mt-12">
                    <p data-translate-key="Pro_Texte_Intro1">Fruit de notre artisanat méticuleux et de notre environnement contrôlé, nos truffes sont récoltées au moment précis où elles atteignent leur pic de maturité aromatique.</p>
                    <p data-translate-key="Pro_Texte_Intro2">Nous proposons aux professionnels de la gastronomie des truffes melanosporum fraîches d'une qualité exceptionnelle, idéales pour sublimer vos créations culinaires.</p>
                    <div class="mt-12 pt-2">
                        <p class="mb-6" data-translate-key="Pro_Texte_Contact_Demande">Pour toute demande de tarifs, informations sur les disponibilités ou partenariats, veuillez nous contacter directement :</p>
                        <a href="mailto:professionnels@maisontruvra.com" class="text-2xl text-brand-classic-gold hover:text-brand-earth-brown font-semibold block mt-4 transition-colors duration-300">professionnels@maisontruvra.com</a>
                    </div>
                </div>
            </div>
        </section>

        <section id="pro-dashboard-view" class="pro-dashboard-section py-16">
            <div class="container mx-auto px-4 sm:px-6 lg:px-8">
                <div class="flex justify-between items-center mb-8">
                    <h1 class="text-3xl sm:text-4xl font-serif text-brand-near-black" data-translate-key="Pro_Mon_Espace_Titre">Mon Espace Professionnel</h1>
                    <button id="pro-logout-button" class="btn-secondary text-sm" data-translate-key="Se_deconnecter">Se déconnecter</button>
                </div>

                <div class="grid md:grid-cols-3 gap-8">
                    <div class="md:col-span-1 bg-white shadow-xl rounded-lg p-6">
                        <h2 class="text-xl font-serif text-brand-near-black mb-5" data-translate-key="Pro_Gestion_Compte">Gestion de Compte</h2>
                        <div id="pro-account-info" class="mb-6 text-sm space-y-1">
                            <p><strong><span data-translate-key="Nom_entreprise">Entreprise</span>:</strong> <span id="pro-dashboard-company-name"></span></p>
                            <p><strong><span data-translate-key="Contact">Contact</span>:</strong> <span id="pro-dashboard-contact-name"></span></p>
                            <p><strong><span data-translate-key="Email">Email</span>:</strong> <span id="pro-dashboard-email"></span></p>
                            <p><strong><span data-translate-key="Telephone">Téléphone</span>:</strong> <span id="pro-dashboard-phone"></span></p>
                        </div>
                        <button id="pro-show-update-form-button" class="btn-primary w-full text-sm mb-3" data-translate-key="Pro_Modifier_Infos">Modifier mes informations</button>

                        <form id="pro-update-account-form" class="space-y-4 mt-4" style="display:none;">
                            <h3 class="text-md font-semibold" data-translate-key="Pro_Modifier_Details_Titre">Modifier les détails :</h3>
                             <div id="pro-update-message" class="text-sm text-brand-truffle-burgundy my-2"></div>
                            <div><label for="pro-update-company-name" class="block text-xs font-medium" data-translate-key="Nom_entreprise">Nom Entreprise</label><input type="text" id="pro-update-company-name" class="form-input-pro text-sm"></div>
                            <div><label for="pro-update-prenom" class="block text-xs font-medium" data-translate-key="Prenom_contact">Prénom Contact</label><input type="text" id="pro-update-prenom" class="form-input-pro text-sm"></div>
                            <div><label for="pro-update-nom" class="block text-xs font-medium" data-translate-key="Nom_contact">Nom Contact</label><input type="text" id="pro-update-nom" class="form-input-pro text-sm"></div>
                            <div><label for="pro-update-email" class="block text-xs font-medium" data-translate-key="Email">Email</label><input type="email" id="pro-update-email" class="form-input-pro text-sm"></div>
                            <div><label for="pro-update-phone" class="block text-xs font-medium" data-translate-key="Telephone">Téléphone</label><input type="tel" id="pro-update-phone" class="form-input-pro text-sm"></div>
                            <hr>
                            <h3 class="text-md font-semibold pt-2" data-translate-key="Pro_Changer_Mot_De_Passe">Changer de mot de passe :</h3>
                            <div><label for="pro-update-current-password" class="block text-xs font-medium" data-translate-key="Pro_Mot_de_passe_actuel">Mot de passe actuel (requis pour changer MDP)</label><input type="password" id="pro-update-current-password" class="form-input-pro text-sm"></div>
                            <div><label for="pro-update-new-password" class="block text-xs font-medium" data-translate-key="Pro_Nouveau_mot_de_passe">Nouveau mot de passe</label><input type="password" id="pro-update-new-password" class="form-input-pro text-sm"></div>
                            <div><label for="pro-update-confirm-password" class="block text-xs font-medium" data-translate-key="Pro_Confirmer_nouveau_mot_de_passe">Confirmer nouveau mot de passe</label><input type="password" id="pro-update-confirm-password" class="form-input-pro text-sm"></div>
                            <div class="flex space-x-2">
                                <button type="submit" class="btn-primary text-sm" data-translate-key="Pro_Enregistrer_Modifs">Enregistrer Modifications</button>
                                <button type="button" id="pro-cancel-update-form-button" class="btn-secondary text-sm" data-translate-key="Annuler">Annuler</button>
                            </div>
                        </form>
                    </div>

                    <div class="md:col-span-2 bg-white shadow-xl rounded-lg p-6">
                        <h2 class="text-xl font-serif text-brand-near-black mb-5" data-translate-key="Pro_Mes_Factures">Mes Factures</h2>
                        <div id="pro-invoices-list-container" class="max-h-96 overflow-y-auto">
                            <p class="text-brand-warm-taupe italic" data-translate-key="Pro_Chargement_Factures">Chargement des factures...</p>
                            </div>
                    </div>
                </div>
            </div>
        </section>
    </main>

    <div id="footer-placeholder"></div>

    <div id="global-message-toast" style="display:none;" class="modal-message">
        <p id="global-message-text"></p>
    </div>

    <script src="js/config.js"></script>
    <script src="js/i18n.js"></script>
    <script src="js/ui.js"></script> <script src="js/api.js"></script> <script src="js/auth.js"></script> <script src="js/professional.js"></script>

    <script src="js/main.js"></script>
</body>
</html>

Create New File: website/js/professional.js
JavaScript

// website/js/professional.js

document.addEventListener('DOMContentLoaded', () => {
    // This check ensures professional.js logic only runs if specifically on 'page-professionnels'
    // and main.js will call initializeProfessionalPage()
});

async function initializeProfessionalPage() {
    const proLoginForm = document.getElementById('pro-login-form');
    const proRegisterForm = document.getElementById('pro-register-form');
    const proLogoutButton = document.getElementById('pro-logout-button');
    const proShowUpdateFormButton = document.getElementById('pro-show-update-form-button');
    const proUpdateAccountForm = document.getElementById('pro-update-account-form');
    const proCancelUpdateFormButton = document.getElementById('pro-cancel-update-form-button');
    const proForgotPasswordLink = document.getElementById('pro-forgot-password-link');


    if (proLoginForm) proLoginForm.addEventListener('submit', handleProLogin);
    if (proRegisterForm) proRegisterForm.addEventListener('submit', handleProRegister);
    if (proLogoutButton) proLogoutButton.addEventListener('click', handleProLogout);

    if (proShowUpdateFormButton) {
        proShowUpdateFormButton.addEventListener('click', () => {
            proUpdateAccountForm.style.display = 'block';
            proShowUpdateFormButton.style.display = 'none';
            populateProUpdateForm(); // Populate with current details
        });
    }
    if (proCancelUpdateFormButton) {
        proCancelUpdateFormButton.addEventListener('click', () => {
            proUpdateAccountForm.style.display = 'none';
            clearFormErrors(proUpdateAccountForm);
            proShowUpdateFormButton.style.display = 'block';
        });
    }
    if (proUpdateAccountForm) proUpdateAccountForm.addEventListener('submit', handleProUpdateAccount);

    if (proForgotPasswordLink) {
        proForgotPasswordLink.addEventListener('click', (e) => {
            e.preventDefault();
            // Implement "Forgot Password" modal or redirect
            showGlobalMessage(t('Fonctionnalite_Mot_de_passe_oublie_B2B_TODO'), 'info'); // Add to locales
        });
    }


    checkProLoginState();
    // Translate static elements on this page if not already done by main.js
    if(typeof translatePageElements === 'function') translatePageElements();
}

function checkProLoginState() {
    const currentUser = getCurrentUser(); // from auth.js
    const loggedOutView = document.getElementById('pro-logged-out-view');
    const dashboardView = document.getElementById('pro-dashboard-view');

    if (currentUser && currentUser.user_type === 'b2b') {
        if (loggedOutView) loggedOutView.style.display = 'none';
        if (dashboardView) dashboardView.style.display = 'block';
        displayProDashboard(currentUser);
    } else {
        if (loggedOutView) loggedOutView.style.display = 'block'; // Or 'grid' based on your layout
        if (dashboardView) dashboardView.style.display = 'none';
        // If a B2C user lands here, or non-logged-in, they see login/register
        // If a B2C user is logged in and lands here, they should still see login/register for B2B.
        // Or redirect them to B2C account or homepage. For now, just show B2B login.
    }
}

async function handleProLogin(event) {
    event.preventDefault();
    const form = event.target;
    clearFormErrors(form);
    const email = form.querySelector('#pro-login-email').value;
    const password = form.querySelector('#pro-login-password').value;
    const messageElement = document.getElementById('pro-login-message');
    messageElement.textContent = '';

    if (!email || !password) {
        messageElement.textContent = t('Email_et_mot_de_passe_requis'); // Add to locales
        return;
    }
    showGlobalMessage(t('Connexion_en_cours'), 'info');
    try {
        const result = await makeApiRequest('/auth/login', 'POST', { email, password });
        if (result.success && result.user && result.user.user_type === 'b2b') {
            setCurrentUser(result.user, result.token); // from auth.js
            showGlobalMessage(t('Connexion_reussie'), 'success');
            checkProLoginState(); // Refresh view to show dashboard
        } else if (result.success && result.user && result.user.user_type !== 'b2b') {
            messageElement.textContent = t('Pro_Compte_non_professionnel'); // Add to locales
            showGlobalMessage(t('Pro_Compte_non_professionnel_long'), 'error'); // Add to locales
            setCurrentUser(null); // Log out if B2C user tried to log in here
        }
        else {
            messageElement.textContent = result.message || t('Echec_de_la_connexion_Verifiez_vos_identifiants');
            showGlobalMessage(result.message || t('Echec_de_la_connexion_Verifiez_vos_identifiants'), 'error');
        }
    } catch (error) {
        messageElement.textContent = error.message || t('Erreur_de_connexion_au_serveur');
        showGlobalMessage(error.message || t('Erreur_de_connexion_au_serveur'), 'error');
    }
}

async function handleProRegister(event) {
    event.preventDefault();
    const form = event.target;
    clearFormErrors(form);
    const messageElement = document.getElementById('pro-register-message');
    messageElement.textContent = '';

    const company_name = form.querySelector('#pro-register-company-name').value;
    const prenom = form.querySelector('#pro-register-prenom').value;
    const nom = form.querySelector('#pro-register-nom').value;
    const email = form.querySelector('#pro-register-email').value;
    const phone_number = form.querySelector('#pro-register-phone').value;
    const password = form.querySelector('#pro-register-password').value;
    const confirm_password = form.querySelector('#pro-register-confirm-password').value;

    let isValid = true;
    if (!company_name) { setFieldError(form.querySelector('#pro-register-company-name'), t('Nom_entreprise_requis')); isValid = false; } // Add
    if (!prenom) { setFieldError(form.querySelector('#pro-register-prenom'), t('Prenom_contact_requis')); isValid = false; } // Add
    if (!nom) { setFieldError(form.querySelector('#pro-register-nom'), t('Nom_contact_requis')); isValid = false; } // Add
    if (!email || !validateEmail(email)) { setFieldError(form.querySelector('#pro-register-email'), t('E-mail_invalide')); isValid = false; }
    if (password.length < 8) { setFieldError(form.querySelector('#pro-register-password'), t('Mot_de_passe_8_caracteres')); isValid = false; }
    if (password !== confirm_password) { setFieldError(form.querySelector('#pro-register-confirm-password'), t('Mots_de_passe_ne_correspondent_pas')); isValid = false; }

    if (!isValid) {
        showGlobalMessage(t('Veuillez_corriger_les_erreurs_dans_le_formulaire'), "error");
        return;
    }

    showGlobalMessage(t('Creation_compte_pro_en_cours'), 'info'); // Add
    try {
        const result = await makeApiRequest('/auth/register-professional', 'POST', {
            email, password, company_name, nom, prenom, phone_number
        });
        if (result.success) {
            showGlobalMessage(result.message || t('Compte_professionnel_cree_succes'), 'success'); // Add
            form.reset();
            // Optionally auto-login or prompt to login
        } else {
            messageElement.textContent = result.message || t('Erreur_creation_compte_pro'); // Add
            showGlobalMessage(result.message || t('Erreur_creation_compte_pro'), 'error');
        }
    } catch (error) {
        messageElement.textContent = error.message || t('Erreur_serveur');
        showGlobalMessage(error.message || t('Erreur_serveur'), 'error');
    }
}

function handleProLogout() {
    setCurrentUser(null); // from auth.js
    showGlobalMessage(t('Deconnecte_message'), 'info');
    checkProLoginState(); // Refresh view to show login/register
}

function displayProDashboard(userData) {
    document.getElementById('pro-dashboard-company-name').textContent = userData.company_name || 'N/A';
    document.getElementById('pro-dashboard-contact-name').textContent = `${userData.prenom || ''} ${userData.nom || ''}`.trim() || 'N/A';
    document.getElementById('pro-dashboard-email').textContent = userData.email || 'N/A';
    document.getElementById('pro-dashboard-phone').textContent = userData.phone_number || 'N/A';
    fetchProInvoices();
}

function populateProUpdateForm() {
    const currentUser = getCurrentUser();
    if (!currentUser || currentUser.user_type !== 'b2b') return;

    document.getElementById('pro-update-company-name').value = currentUser.company_name || '';
    document.getElementById('pro-update-prenom').value = currentUser.prenom || '';
    document.getElementById('pro-update-nom').value = currentUser.nom || '';
    document.getElementById('pro-update-email').value = currentUser.email || '';
    document.getElementById('pro-update-phone').value = currentUser.phone_number || '';
    document.getElementById('pro-update-current-password').value = '';
    document.getElementById('pro-update-new-password').value = '';
    document.getElementById('pro-update-confirm-password').value = '';
}


async function handleProUpdateAccount(event) {
    event.preventDefault();
    const form = event.target;
    clearFormErrors(form);
    const messageElement = document.getElementById('pro-update-message');
    messageElement.textContent = '';

    const updateData = {
        company_name: form.querySelector('#pro-update-company-name').value,
        prenom: form.querySelector('#pro-update-prenom').value,
        nom: form.querySelector('#pro-update-nom').value,
        email: form.querySelector('#pro-update-email').value,
        phone_number: form.querySelector('#pro-update-phone').value,
    };

    const currentPassword = form.querySelector('#pro-update-current-password').value;
    const newPassword = form.querySelector('#pro-update-new-password').value;
    const confirmPassword = form.querySelector('#pro-update-confirm-password').value;

    if (newPassword) {
        if (newPassword.length < 8) {
            setFieldError(form.querySelector('#pro-update-new-password'), t('Mot_de_passe_8_caracteres')); return;
        }
        if (newPassword !== confirmPassword) {
            setFieldError(form.querySelector('#pro-update-confirm-password'), t('Mots_de_passe_ne_correspondent_pas')); return;
        }
        if (!currentPassword) { // Require current password only if changing password
            setFieldError(form.querySelector('#pro-update-current-password'), t('Pro_Mot_de_passe_actuel_requis_pour_changement')); return; // Add
        }
        updateData.current_password = currentPassword;
        updateData.new_password = newPassword;
    }
    // Filter out empty fields so they don't overwrite existing data with empty strings if not intended
    const finalUpdateData = {};
    for (const key in updateData) {
        if (updateData[key] || key === 'phone_number') { // Allow empty phone_number to clear it
             if (typeof updateData[key] === 'string' && updateData[key].trim() === '' && key !== 'phone_number') continue;
            finalUpdateData[key] = updateData[key];
        }
    }
    if (Object.keys(finalUpdateData).length === 0 && !newPassword) {
        messageElement.textContent = t('Pro_Aucun_changement_detecte'); // Add
        return;
    }


    showGlobalMessage(t('Pro_Mise_a_jour_en_cours'), 'info'); // Add
    try {
        const result = await makeApiRequest('/professional/account', 'PUT', finalUpdateData, true);
        if (result.success) {
            showGlobalMessage(t('Pro_Compte_mis_a_jour_succes'), 'success'); // Add
            setCurrentUser(result.user, getAuthToken()); // Update session storage
            displayProDashboard(result.user); // Refresh displayed info
            form.style.display = 'none';
            clearFormErrors(form);
            document.getElementById('pro-show-update-form-button').style.display = 'block';
            form.querySelector('#pro-update-current-password').value = '';
            form.querySelector('#pro-update-new-password').value = '';
            form.querySelector('#pro-update-confirm-password').value = '';

        } else {
            messageElement.textContent = result.message || t('Pro_Erreur_mise_a_jour_compte'); // Add
            showGlobalMessage(result.message || t('Pro_Erreur_mise_a_jour_compte'), 'error');
        }
    } catch (error) {
        messageElement.textContent = error.message || t('Erreur_serveur');
        showGlobalMessage(error.message || t('Erreur_serveur'), 'error');
    }
}


async function fetchProInvoices() {
    const container = document.getElementById('pro-invoices-list-container');
    container.innerHTML = `<p class="text-brand-warm-taupe italic">${t('Pro_Chargement_Factures')}</p>`;
    try {
        const result = await makeApiRequest('/professional/invoices', 'GET', null, true);
        if (result.success && result.invoices) {
            if (result.invoices.length === 0) {
                container.innerHTML = `<p class="text-brand-warm-taupe italic" data-translate-key="Pro_Aucune_facture">${t('Pro_Aucune_facture')}</p>`; // Add
                return;
            }
            let html = '<ul class="space-y-3">';
            result.invoices.forEach(invoice => {
                const invoiceDate = new Date(invoice.invoice_date).toLocaleDateString(getCurrentLang() || 'fr-FR');
                html += `
                    <li class="p-3 border border-brand-warm-taupe/30 rounded-md flex justify-between items-center">
                        <div>
                            <span class="font-semibold text-brand-near-black">${invoice.invoice_number}</span>
                            <span class="text-xs text-brand-warm-taupe ml-2">(${invoiceDate})</span>
                        </div>
                        <div class="flex items-center">
                            <span class="text-brand-earth-brown mr-4">${parseFloat(invoice.total_amount_ttc).toFixed(2)} €</span>
                            <a href="${API_BASE_URL}/professional/invoices/${invoice.invoice_id}/download?token=${getAuthToken()}" 
                               target="_blank" download="${invoice.invoice_number}.pdf"
                               class="btn-secondary text-xs py-1 px-2" data-translate-key="Telecharger">
                                ${t('Telecharger')}
                            </a>
                        </div>
                    </li>
                `;
            });
            html += '</ul>';
            container.innerHTML = html;
        } else {
            container.innerHTML = `<p class="text-red-500 italic">${result.message || t('Pro_Erreur_chargement_factures')}</p>`; // Add
        }
    } catch (error) {
        container.innerHTML = `<p class="text-red-500 italic">${t('Pro_Erreur_chargement_factures')}: ${error.message}</p>`;
    }
}

// Expose the initializer to be called from main.js
window.initializeProfessionalPage = initializeProfessionalPage;

Update website/js/main.js (to initialize B2B page)
JavaScript

// website/js/main.js
// ... (keep existing DOMContentLoaded structure)

document.addEventListener('DOMContentLoaded', async () => {
    // --- Global Initializations ---
    await loadTranslations(localStorage.getItem('maisonTruvraLang') || 'fr');
    initializeMobileMenu();
    initializeNewsletterForm();
    setActiveNavLink();
    updateLoginState(); // This will now also update based on B2B user if they are on B2C pages by mistake
    updateCartCountDisplay();

    const currentLangInitial = getCurrentLang();
    const langDisplay = document.getElementById('current-lang-display');
    const langDisplayMobile = document.getElementById('current-lang-display-mobile');
    if (langDisplay) langDisplay.textContent = currentLangInitial.toUpperCase();
    if (langDisplayMobile) langDisplayMobile.textContent = currentLangInitial.toUpperCase();

    const currentYearEl = document.getElementById('currentYear');
    if (currentYearEl) currentYearEl.textContent = new Date().getFullYear();

    const bodyId = document.body.id;

    if (bodyId === 'page-nos-produits') { /* ... */ }
    else if (bodyId === 'page-produit-detail') { /* ... */ }
    else if (bodyId === 'page-panier') { /* ... */ }
    else if (bodyId === 'page-compte') { /* This is B2C account page */
        if (typeof displayAccountDashboard === 'function') displayAccountDashboard(); // B2C dashboard
        const loginForm = document.getElementById('login-form'); // B2C login
        if (loginForm && typeof handleLogin === 'function') {
            loginForm.addEventListener('submit', handleLogin); // B2C login handler
        }
        // ... B2C create account button ...
    }
    else if (bodyId === 'page-professionnels') { // NEW: Initialize B2B page logic
        if (typeof initializeProfessionalPage === 'function') {
            initializeProfessionalPage();
        } else {
            console.error("professional.js not loaded or initializeProfessionalPage not found");
        }
    }
    else if (bodyId === 'page-paiement') { /* ... */ }
    else if (bodyId === 'page-confirmation-commande') { /* ... */ }

    // ... (modal listeners) ...
    await Promise.all([loadHeader(), loadFooter()]);
    if(window.translatePageElements) window.translatePageElements();
});

// ... (loadHeader, loadFooter functions remain the same)

IV. Admin Invoice Management (Conceptual)

    admin/admin_manage_invoices.html (New File - Structure Idea):
    HTML

<h1 data-translate-key="Admin_Gestion_Factures_B2B">Gestion des Factures (B2B)</h1>
<div>
    <label for="select-b2b-user" data-translate-key="Selectionner_Professionnel">Sélectionner un Professionnel:</label>
    <select id="select-b2b-user" class="form-select-admin"></select>
</div>
<div id="upload-invoice-form-section" style="display:none;">
    <h3 data-translate-key="Televerser_Nouvelle_Facture">Téléverser une Nouvelle Facture</h3>
    <form id="admin-upload-invoice-form">
        <input type="hidden" id="invoice-user-id" name="user_id">
        <div><label data-translate-key="Numero_Facture">Numéro de Facture:</label><input type="text" name="invoice_number" required></div>
        <div><label data-translate-key="Date_Facture">Date de Facture:</label><input type="date" name="invoice_date" required></div>
        <div><label data-translate-key="Montant_HT">Montant HT (€):</label><input type="number" step="0.01" name="total_amount_ht" required></div>
        <div><label data-translate-key="Montant_TTC">Montant TTC (€):</label><input type="number" step="0.01" name="total_amount_ttc" required></div>
        <div><label data-translate-key="Remise_Pourcentage">Remise (%):</label><input type="number" step="0.01" name="discount_percentage" value="0"></div>
        <div><label data-translate-key="Fichier_PDF_Facture">Fichier PDF Facture:</label><input type="file" name="invoice_file" accept=".pdf" required></div>
        <button type="submit" data-translate-key="Televerser_Facture">Téléverser Facture</button>
    </form>
</div>
<div id="user-invoices-list">
    <h3 data-translate-key="Factures_Pour_Utilisateur_Selectionne">Factures pour l'utilisateur sélectionné:</h3>
    <table class="admin-table">
        <thead><tr><th data-translate-key="Numero">Numéro</th><th data-translate-key="Date">Date</th><th data-translate-key="Montant_TTC">Montant TTC</th><th data-translate-key="Actions">Actions</th></tr></thead>
        <tbody id="admin-invoices-table-body"></tbody>
    </table>
</div>

website/admin/js/admin_invoices.js (New File - Conceptual Functions):
JavaScript

    // Conceptual functions for admin_invoices.js
    function initializeAdminInvoiceManagement() {
        // Populate B2B user dropdown
        // Add event listener to dropdown to load invoices for selected user
        // Add event listener to upload form
    }
    async function loadB2BUsersForDropdown() { /* Fetch users where user_type='b2b' */ }
    async function loadInvoicesForUser(userId) { /* Fetch from /api/admin/users/<userId>/invoices */ }
    async function handleInvoiceUpload(event) {
        // event.preventDefault();
        // const formData = new FormData(event.target);
        // await adminApiRequest('/invoices/upload', 'POST', formData, true); // Note: adminApiRequest needs to handle FormData
    }
    async function deleteInvoice(invoiceId) { /* Call DELETE /api/admin/invoices/<invoiceId> */ }

    Note: adminApiRequest would need modification to handle FormData for file uploads instead of JSON.stringify(body).

V. Invoice Generation Script (generate_professional_invoice.py - Conceptual)
Python

# generate_professional_invoice.py (Standalone script)
# from reportlab.pdfgen import canvas
# from reportlab.lib.pagesizes import A4
# from reportlab.lib.units import cm

def generate_invoice_pdf(output_filename, client_data, invoice_data, items_data, company_info):
    # client_data = {"company_name": "Pro Client Inc.", "contact_person": "John Doe", "address": "..."}
    # invoice_data = {"number": "FACT2025-001", "date": "2025-05-27", "due_date": "2025-06-26", "total_ht": 500.00, "total_ttc": 600.00, "discount_percent": 5}
    # items_data = [{"name": "Truffe Noire Extra 50g", "quantity": 2, "unit_price_ht": 100.00, "total_ht": 200.00}, ...]
    # company_info = {"name": "Maison Trüvra", "address": "...", "siret": "...", "vat_number": "..."}

    # c = canvas.Canvas(output_filename, pagesize=A4)
    # width, height = A4

    # --- Header (Your company logo, address) ---
    # c.setFont("Helvetica-Bold", 16)
    # c.drawString(3*cm, height - 3*cm, company_info["name"])
    # ...

    # --- Client Info ---
    # c.setFont("Helvetica", 12)
    # c.drawString(3*cm, height - 5*cm, client_data["company_name"])
    # ...

    # --- Invoice Meta (Number, Date, Due Date) ---
    # ...

    # --- Line Items Table ---
    # y_position = height - 10*cm
    # for item in items_data:
    #     c.drawString(3*cm, y_position, item["name"])
    #     c.drawString(10*cm, y_position, str(item["quantity"]))
    #     # ... and so on for unit price, total price
    #     y_position -= 0.7*cm

    # --- Totals (HT, Discount, VAT, TTC) ---
    # ...

    # --- Footer (Payment terms, bank details) ---
    # ...

    # c.save()
    print(f"Invoice {output_filename} would be generated here.")

if __name__ == '__main__':
    # This is where an admin would typically input data or load from a CSV/DB
    mock_client = {"company_name": "Restaurant Le Gourmet", "contact_person": "Chef Cuisine", "address": "1 Rue de la Paix, Paris"}
    mock_invoice = {"number": "FACT2025-B2B-001", "date": "2025-05-27", "total_ht": 250.00, "total_ttc": 300.00, "discount_percent": 0}
    mock_items = [
        {"name": "Truffe Noire Melanosporum - Qualité Extra (100g)", "quantity": 1, "unit_price_ht": 200.00, "total_ht": 200.00},
        {"name": "Huile d'olive à la truffe noire 250ml", "quantity": 2, "unit_price_ht": 25.00, "total_ht": 50.00}
    ]
    mock_company = {"name": "Maison Trüvra SARL", "address": "Quelque Part, France", "siret": "12345678900012", "vat_number": "FR00123456789"}

    # Admin would run:
    # generate_invoice_pdf(f"{mock_invoice['number']}.pdf", mock_client, mock_invoice, mock_items, mock_company)
    print(f"Conceptual generation for invoice {mock_invoice['number']}.pdf")
    print("Install a PDF library like 'reportlab' or 'fpdf2' and implement the drawing logic.")

VI. New i18n Keys (Examples to add to fr.json and en.json):
You'll need to add keys for all new labels and messages in professionnels.html and professional.js.

    fr.json:
    JSON

    {
      "Titre_Page_Professionnels": "Espace Professionnels - Maison Trüvra",
      "Pro_Deja_client_Connectez-vous": "Déjà Professionnel ? Connectez-vous",
      "Mot_de_passe": "Mot de passe",
      "Pro_Nouveau_client_Creer_compte": "Nouveau Professionnel ? Créez un compte",
      "Nom_entreprise": "Nom de l'entreprise",
      "Prenom_contact": "Prénom (Contact)",
      "Nom_contact": "Nom (Contact)",
      "Telephone_optionnel": "Téléphone (Optionnel)",
      "Confirmer_mot_de_passe": "Confirmer mot de passe",
      "Creer_un_compte_professionnel": "Créer un compte professionnel",
      "Pro_Texte_Intro1": "Fruit de notre artisanat méticuleux...",
      "Pro_Texte_Intro2": "Nous proposons aux professionnels...",
      "Pro_Texte_Contact_Demande": "Pour toute demande de tarifs...",
      "Pro_Mon_Espace_Titre": "Mon Espace Professionnel",
      "Pro_Gestion_Compte": "Gestion de Compte",
      "Contact": "Contact",
      "Telephone": "Téléphone",
      "Pro_Modifier_Infos": "Modifier mes informations",
      "Pro_Modifier_Details_Titre": "Modifier les détails :",
      "Pro_Changer_Mot_De_Passe": "Changer de mot de passe :",
      "Pro_Mot_de_passe_actuel": "Mot de passe actuel",
      "Pro_Nouveau_mot_de_passe": "Nouveau mot de passe",
      "Pro_Confirmer_nouveau_mot_de_passe": "Confirmer nouveau mot de passe",
      "Pro_Enregistrer_Modifs": "Enregistrer Modifications",
      "Annuler": "Annuler",
      "Pro_Mes_Factures": "Mes Factures",
      "Pro_Chargement_Factures": "Chargement des factures...",
      "Pro_Aucune_facture": "Vous n'avez aucune facture pour le moment.",
      "Telecharger": "Télécharger",
      "Pro_Erreur_chargement_factures": "Erreur lors du chargement des factures",
      "Email_et_mot_de_passe_requis": "E-mail et mot de passe requis.",
      "Pro_Compte_non_professionnel": "Ce compte n'est pas un compte professionnel.",
      "Pro_Compte_non_professionnel_long": "Accès refusé. Veuillez utiliser un compte professionnel ou contacter le support.",
      "Nom_entreprise_requis": "Le nom de l'entreprise est requis.",
      "Prenom_contact_requis": "Le prénom du contact est requis.",
      "Nom_contact_requis": "Le nom du contact est requis.",
      "Creation_compte_pro_en_cours": "Création du compte professionnel en cours...",
      "Compte_professionnel_cree_succes": "Compte professionnel créé avec succès ! Il se peut qu'une validation administrative soit nécessaire.",
      "Erreur_creation_compte_pro": "Erreur lors de la création du compte professionnel.",
      "Pro_Mot_de_passe_actuel_requis_pour_changement": "Mot de passe actuel requis pour changer le mot de passe.",
      "Pro_Aucun_changement_detecte": "Aucune modification détectée.",
      "Pro_Mise_a_jour_en_cours": "Mise à jour du compte en cours...",
      "Pro_Compte_mis_a_jour_succes": "Compte mis à jour avec succès.",
      "Pro_Erreur_mise_a_jour_compte": "Erreur lors de la mise à jour du compte.",
      "Fonctionnalite_Mot_de_passe_oublie_B2B_TODO": "Fonctionnalité 'Mot de passe oublié' pour B2B à implémenter.",
      "Admin_Gestion_Factures_B2B": "Gestion des Factures (B2B)",
      "Selectionner_Professionnel": "Sélectionner un Professionnel:",
      "Televerser_Nouvelle_Facture": "Téléverser une Nouvelle Facture",
      "Numero_Facture": "Numéro de Facture:",
      "Date_Facture": "Date de Facture:",
      "Montant_HT": "Montant HT (€):",
      "Montant_TTC": "Montant TTC (€):",
      "Remise_Pourcentage": "Remise (%):",
      "Fichier_PDF_Facture": "Fichier PDF Facture:",
      "Televerser_Facture": "Téléverser Facture",
      "Factures_Pour_Utilisateur_Selectionne": "Factures pour l'utilisateur sélectionné:",
      "Numero": "Numéro",
      "Date": "Date",
      "Actions": "Actions"
    }

    en.json: Create corresponding English translations.

Next Steps & Important Considerations:

    Implement "Forgot Password": This involves secure token generation, email sending (configure Flask-Mail or similar in backend/config.py and backend/utils.py), and views/routes for reset token validation and password update.
    Invoice Generation Script: Develop generate_professional_invoice.py using a PDF library. This is a separate task.
    Admin Invoice Management Frontend: Implement admin/admin_manage_invoices.html and its JavaScript (website/admin/js/admin_invoices.js) for uploading and managing the generated PDFs. The adminApiRequest in admin_api.js will need to be adapted to handle FormData for file uploads.
    Security:
        Ensure proper validation and sanitization of all inputs, especially file uploads (check file types, size, scan for malware if possible).
        Store uploaded invoices in a directory that is not directly web-accessible if possible, and serve them via a secure backend endpoint that checks authentication/authorization (as done with download_professional_invoice). The current setup assumes INVOICES_UPLOAD_DIR is handled carefully.
        Protect against CSRF if forms are not purely JS/API driven.
    Error Handling & User Feedback: Provide clear messages for all operations.
    Testing: Thoroughly test the B2B registration, login, account updates, and invoice processes for both professionals and admins.

This is a large set of changes. Implement and test them piece by piece. Start with the backend database and API changes, then build the frontend for professionnels.html, and finally the admin invoice management.

website/js/main.js : send me the full file

en.json: write it

Okay, I'll provide the full, updated website/js/main.js and the content for website/js/locales/en.json.

These files are crucial for the internationalization (i18n) and the correct initialization of both B2C and the new B2B functionalities.

Important:

    Make sure you have created the website/js/i18n.js file as provided in earlier responses. It contains the core translation functions (t(), loadTranslations(), setLanguage(), getCurrentLang(), translatePageElements()).
    Ensure website/js/locales/fr.json is also created and populated.
    In all your HTML files, include the scripts in the correct order, especially i18n.js before main.js:
    HTML

    <script src="js/config.js"></script>
    <script src="js/i18n.js"></script>   <script src="js/ui.js"></script>    <script src="js/api.js"></script>   <script src="js/auth.js"></script>  <script src="js/cart.js"></script>
    <script src="js/product.js"></script>
    <script src="js/checkout.js"></script>
    <script src="js/newsletter.js"></script>
    <script src="js/professional.js"></script> <script src="js/main.js"></script>  ```

Here are the files:
website/js/main.js (Updated for B2B & i18n)
27 May, 10:41
website/js/locales/en.json (Updated)
27 May, 10:41

I've updated website/js/main.js to correctly initialize the B2B page (page-professionnels) by calling initializeProfessionalPage() (which you'll define in website/js/professional.js). I've also ensured that loadHeader and loadFooter are robust and attempt to translate their content after loading.

The en.json file now includes the keys we discussed for the B2B professional area, as well as many common keys from the B2C side. You should review this and fr.json to ensure all necessary translations are present and accurate for your entire site.

Remember to:

    Create website/js/i18n.js with the content provided previously.
    Create website/js/locales/fr.json with the French translations.
    Go through all your HTML files (like index.html, nos-produits.html, etc.) and add data-translate-key="YOUR_KEY" to all elements with static text.
    Review all your other JavaScript files (ui.js, api.js, auth.js, cart.js, product.js, checkout.js, newsletter.js) and replace any hardcoded user-facing strings with t('YOUR_KEY').

This should set you up with a solid foundation for your bilingual website and the new B2B portal.

Implement "Forgot Password": This involves secure token generation, email sending (configure Flask-Mail or similar in backend/config.py and backend/utils.py), and views/routes for reset token validation and password update.

Invoice Generation Script: Develop generate_professional_invoice.py using a PDF library. This is a separate task.

Okay, I'll outline the "Forgot Password" functionality and provide the invoice generation script.

I. Forgot Password Functionality (Conceptual Implementation)

This feature requires backend API endpoints, frontend UI elements, and new JavaScript logic.

1. Backend Updates (backend/auth/routes.py)

You'll need to add two new routes to your auth_bp. For this conceptual implementation, we'll mock the token generation and email sending. In a real application, you'd use a secure token generation library (like itsdangerous in Flask) and an email sending service (like Flask-Mail).
Python

# backend/auth/routes.py
# ... (existing imports)
import uuid # For mock token generation
from werkzeug.security import generate_password_hash # Ensure this is imported

# ... (existing routes: /register, /register-professional, /login) ...

@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    data = request.get_json()
    email = data.get('email')

    if not email or not is_valid_email(email):
        return jsonify({"success": False, "message": "Veuillez fournir une adresse e-mail valide."}), 400

    db = None
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT id, user_type FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()

        if user:
            user_id = user['id']
            user_type = user['user_type'] # To tailor the reset link if needed (e.g. b2c vs b2b reset page)
            
            # In a real app:
            # 1. Generate a secure, time-limited token (e.g., using itsdangerous.URLSafeTimedSerializer)
            # 2. Store the token (or its hash) in a `password_reset_tokens` table with user_id and expiry.
            # 3. Construct the reset_url (e.g., https://yourdomain.com/reset-password.html?token=THE_TOKEN)
            # 4. Send an email to the user with this reset_url.
            
            mock_token = str(uuid.uuid4()) # Simple mock token
            reset_url = f"{current_app.config.get('SITE_BASE_URL', 'http://127.0.0.1:5500/website')}/reset-password.html?token={mock_token}&email={email}"
            
            current_app.logger.info(f"Demande de réinitialisation de mot de passe pour {email} (User ID: {user_id}, Type: {user_type}).")
            current_app.logger.info(f"MOCK EMAIL: Lien de réinitialisation (normalement envoyé par email): {reset_url}")
            # Here, you would call your email sending function:
            # send_password_reset_email(email, reset_url)

            # For now, we just log it and return success.
            # The frontend will need to inform the user to check their email (even though we are not sending one here).
            return jsonify({"success": True, "message": "Si un compte existe pour cet email, un lien de réinitialisation (théoriquement) envoyé."}), 200
        else:
            # Do not reveal if an email exists or not for security reasons in forgot password flow
            current_app.logger.info(f"Tentative de réinitialisation de mot de passe pour un email non trouvé: {email}")
            return jsonify({"success": True, "message": "Si un compte existe pour cet email, un lien de réinitialisation (théoriquement) envoyé."}), 200

    except Exception as e:
        current_app.logger.error(f"Erreur lors de la demande de mot de passe oublié pour {email}: {e}", exc_info=True)
        return jsonify({"success": False, "message": "Erreur serveur."}), 500
    finally:
        if db: db.close()

@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    data = request.get_json()
    token = data.get('token')
    email = data.get('email') # Good to have for an extra check, though token should be primary
    new_password = data.get('new_password')

    if not token or not new_password or not email:
        return jsonify({"success": False, "message": "Token, email et nouveau mot de passe sont requis."}), 400
    if len(new_password) < 8:
        return jsonify({"success": False, "message": "Le nouveau mot de passe doit faire au moins 8 caractères."}), 400

    db = None
    try:
        # In a real app:
        # 1. Validate the token:
        #    - Query your `password_reset_tokens` table for the token (or its hash).
        #    - Check if it's associated with the provided email/user.
        #    - Check if it hasn't expired.
        #    - Check if it hasn't been used.
        #    - If using itsdangerous, serializer.loads(token, max_age=...) handles expiry and signature.
        # For this mock: We'll assume the token is valid if it exists (it's just a UUID here).
        # We'll find the user by email since we don't store the mock token.
        
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()

        if not user:
            # This case should ideally be caught by token validation in a real app
            return jsonify({"success": False, "message": "Utilisateur non trouvé ou token invalide."}), 404

        user_id = user['id']
        hashed_password = generate_password_hash(new_password)
        cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hashed_password, user_id))
        
        # In a real app, mark the token as used or delete it from `password_reset_tokens` table.
        
        db.commit()
        current_app.logger.info(f"Mot de passe réinitialisé pour l'utilisateur ID {user_id} (Email: {email}).")
        return jsonify({"success": True, "message": "Mot de passe réinitialisé avec succès. Vous pouvez maintenant vous connecter."}), 200

    except Exception as e:
        if db: db.rollback()
        current_app.logger.error(f"Erreur lors de la réinitialisation du mot de passe pour {email}: {e}", exc_info=True)
        return jsonify({"success": False, "message": "Erreur serveur lors de la réinitialisation du mot de passe."}), 500
    finally:
        if db: db.close()

@auth_bp.route('/register', methods=['POST'])
def register_user():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    nom = data.get('nom', '')
    prenom = data.get('prenom', '')

    if not email or not is_valid_email(email):
        return jsonify({"success": False, "message": "Veuillez fournir une adresse e-mail valide."}), 400
    if not password or len(password) < 8:
        return jsonify({"success": False, "message": "Le mot de passe doit contenir au moins 8 caractères."}), 400
    
    db = None
    try:
        db = get_db()
        cursor = db.cursor()
        hashed_password = generate_password_hash(password)
        # New users are not admin by default
        cursor.execute(
            "INSERT INTO users (email, password_hash, nom, prenom, is_admin) VALUES (?, ?, ?, ?, ?)",
            (email, hashed_password, nom, prenom, False) # is_admin defaults to False
        )
        db.commit()
        user_id = cursor.lastrowid
        user_info = {"id": user_id, "email": email, "nom": nom, "prenom": prenom, "is_admin": False}
        current_app.logger.info(f"Utilisateur enregistré : {email}")
        return jsonify({
            "success": True, 
            "message": "Compte créé avec succès ! Vous pouvez maintenant vous connecter.",
            "user": user_info 
        }), 201
    except sqlite3.IntegrityError:
        if db: db.rollback()
        current_app.logger.warning(f"Tentative d'enregistrement avec un email existant : {email}")
        return jsonify({"success": False, "message": "Un compte existe déjà avec cette adresse e-mail."}), 409
    except Exception as e:
        if db: db.rollback()
        current_app.logger.error(f"Erreur d'inscription pour {email}: {e}", exc_info=True)
        return jsonify({"success": False, "message": "Une erreur interne s'est produite lors de l'inscription."}), 500
    finally:
        if db: db.close()

@auth_bp.route('/login', methods=['POST'])
def login_user():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"success": False, "message": "E-mail et mot de passe requis."}), 400

    db = None
    try:
        db = get_db()
        cursor = db.cursor()
        # Fetch is_admin along with other user details
        cursor.execute("SELECT id, email, password_hash, nom, prenom, is_admin FROM users WHERE email = ?", (email,))
        user_row = cursor.fetchone()
    except Exception as e:
        current_app.logger.error(f"Erreur DB lors de la connexion pour {email}: {e}", exc_info=True)
        return jsonify({"success": False, "message": "Erreur de base de données."}), 500
    finally:
        if db: db.close()

    if user_row and check_password_hash(user_row['password_hash'], password):
        user_data = {
            "id": user_row['id'],
            "email": user_row['email'],
            "nom": user_row['nom'],
            "prenom": user_row['prenom'],
            "is_admin": bool(user_row['is_admin']) # Ensure boolean
        }
        
        try:
            token_payload = {
                'user_id': user_data['id'],
                'email': user_data['email'],
                'is_admin': user_data['is_admin'], # Include admin status in JWT
                'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=current_app.config.get('JWT_EXPIRATION_HOURS', 24))
            }
            token = jwt.encode(token_payload, current_app.config['SECRET_KEY'], algorithm='HS256')
            
            current_app.logger.info(f"Connexion réussie pour : {email} (Admin: {user_data['is_admin']})")
            return jsonify({
                "success": True,
                "message": "Connexion réussie !",
                "user": user_data,
                "token": token
            }), 200
        except Exception as e:
            current_app.logger.error(f"Erreur génération JWT pour {email}: {e}", exc_info=True)
            return jsonify({"success": False, "message": "Erreur d'authentification interne."}), 500
    else:
        current_app.logger.warning(f"Tentative de connexion échouée pour : {email}")
        return jsonify({"success": False, "message": "E-mail ou mot de passe incorrect."}), 401

# Helper decorator for admin routes (to be created and used in admin_api/routes.py)
from functools import wraps

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]
            except IndexError:
                return jsonify({"success": False, "message": "Token mal formaté."}), 401

        if not token:
            return jsonify({"success": False, "message": "Token manquant."}), 401

        try:
            data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"])
            if not data.get('is_admin'):
                return jsonify({"success": False, "message": "Accès administrateur requis."}), 403
            # Pass current admin user_id to the route if needed
            # g.current_admin_id = data.get('user_id') 
        except jwt.ExpiredSignatureError:
            return jsonify({"success": False, "message": "Token expiré."}), 401
        except jwt.InvalidTokenError:
            return jsonify({"success": False, "message": "Token invalide."}), 401
        
        # Store admin user_id in flask.g for access in the route if needed
        # from flask import g
        # g.admin_user_id = data.get('user_id')

        return f(*args, **kwargs)
    return decorated_function

