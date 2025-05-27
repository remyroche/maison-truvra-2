# backend/newsletter/routes.py
from flask import Blueprint, request, jsonify, current_app
import sqlite3 
from ..database import get_db 
from ..utils import is_valid_email

# Keep the blueprint name consistent if other parts of the app refer to 'newsletter_bp'
# but change the URL prefix for the entire blueprint if desired, or just the route below.
# For this specific request, we only change the route for the subscribe function.
newsletter_bp = Blueprint('newsletter_bp', __name__, url_prefix='/api') # Adjusted prefix to /api

@newsletter_bp.route('/subscribe-newsletter', methods=['POST']) # Route changed to /api/subscribe-newsletter
def subscribe_to_newsletter():
    data = request.get_json()
    email = data.get('email')
    nom = data.get('nom', '')
    prenom = data.get('prenom', '')
    consentement = data.get('consentement', 'N')

    if not email or not is_valid_email(email):
        return jsonify({"success": False, "message": "Veuillez fournir une adresse e-mail valide."}), 400
    
    if consentement != 'Y':
        return jsonify({"success": False, "message": "Le consentement est requis pour l'inscription à la newsletter."}), 400

    db = None
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            "INSERT INTO newsletter_subscriptions (email, nom, prenom, consentement) VALUES (?, ?, ?, ?)",
            (email, nom, prenom, consentement)
        )
        db.commit()
        current_app.logger.info(f"Nouvel abonné à la newsletter : {email}")
        return jsonify({"success": True, "message": "Merci ! Votre adresse a été enregistrée à notre newsletter."}), 201
    except sqlite3.IntegrityError: 
        if db:
            db.rollback()
        current_app.logger.warning(f"Tentative d'abonnement à la newsletter avec un email existant : {email}")
        # Return a more specific message if the email already exists
        existing_subscriber_message = "Cette adresse e-mail est déjà inscrite à notre newsletter."
        # Check if consent was previously 'N' and is now 'Y'
        # This would require fetching the existing record first, which adds complexity.
        # For now, we'll keep it simple.
        return jsonify({"success": False, "message": existing_subscriber_message}), 409
    except Exception as e:
        if db:
            db.rollback()
        current_app.logger.error(f"Erreur d'abonnement à la newsletter pour {email}: {e}", exc_info=True)
        return jsonify({"success": False, "message": "Une erreur interne s'est produite. Veuillez réessayer."}), 500
    finally:
        if db:
            db.close()
