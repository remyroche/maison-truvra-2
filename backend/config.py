# backend/config.py
import os
from dotenv import load_dotenv

load_dotenv() # Load environment variables from .env file

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-very-secret-and-hard-to-guess-key'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(__file__)), 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False# backend/config.py
import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'votre_cle_secrete_par_defaut_tres_difficile_a_deviner'
    DATABASE_PATH = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', 'maison_truvra_database.db')
    
    # JWT Configuration
    JWT_EXPIRATION_HOURS = 24 # Token validity period
    PASSWORD_RESET_TOKEN_EXPIRY_MINUTES = 30 # For password reset links

    # Directory for storing generated/uploaded invoices
    # Ensure this directory exists and the application has write permissions.
    # It's often better to place this outside the application's code directory.
    INVOICES_UPLOAD_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', 'uploaded_invoices_b2b')
    # Make sure this path is correct and the directory is writable by the Flask app user.
    # For production, consider using a dedicated, persistent storage solution (e.g., S3, Google Cloud Storage).

    # Email for Admin Notifications (e.g., new B2B registration)
    ADMIN_EMAIL_NOTIFICATIONS = os.environ.get('ADMIN_EMAIL_NOTIFICATIONS') or 'admin@maisontruvra.com' # Replace with actual admin email

    # --- Email Server Configuration (Placeholder - Configure for your provider) ---
    # These should ideally be set via environment variables for security.
    MAIL_SERVER = os.environ.get('MAIL_SERVER') # e.g., 'smtp.sendgrid.net' or 'smtp.gmail.com'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587) # 587 for TLS, 465 for SSL
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', '1', 't']
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'false').lower() in ['true', '1', 't']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME') # Your email account username
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD') # Your email account password or app-specific password
    MAIL_SENDER_ADDRESS = os.environ.get('MAIL_SENDER_ADDRESS') or 'noreply@maisontruvra.com' # Default sender

    # --- Default Invoice Template Data ---
    # These can be overridden by settings stored in the database (app_settings table)
    # Paths for logos should be relative to the `generate_professional_invoice.py` script if used directly by it,
    # or an absolute path, or handled by Flask's static files if served through the app.
    # For generate_professional_invoice.py, it expects paths relative to its own location.
    INVOICE_COMPANY_NAME = "Maison Trüvra SARL"
    INVOICE_COMPANY_ADDRESS_LINES = [
        "123 Rue de la Truffe",
        "75001 Paris, France"
    ]
    INVOICE_COMPANY_SIRET = "SIRET: 123 456 789 00012"
    INVOICE_COMPANY_VAT_NUMBER = "TVA Intracom.: FR 00 123456789"
    INVOICE_COMPANY_CONTACT_INFO = "contact@maisontruvra.com | +33 1 23 45 67 89"
    # The logo path in generate_professional_invoice.py is currently "../website/image_6be700.png"
    # This needs to be consistent or made configurable.
    # For now, let generate_professional_invoice.py use its hardcoded relative path or make it an absolute path here.
    INVOICE_COMPANY_LOGO_PATH = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', 'website', 'image_6be700.png') # Example absolute path
    
    INVOICE_FOOTER_TEXT = "Merci de votre confiance. Conditions de paiement : 30 jours net."
    INVOICE_BANK_DETAILS = "Banque: XYZ | IBAN: FR76 XXXX XXXX XXXX XXXX XXXX XXX | BIC: XYZAFRPP"


class DevelopmentConfig(Config):
    DEBUG = True
    # SQLALCHEMY_ECHO = True # If using SQLAlchemy

class ProductionConfig(Config):
    DEBUG = False
    # Add production specific settings, e.g., different database URI, logging levels

# Choose the configuration based on an environment variable, e.g., FLASK_ENV
config_by_name = dict(
    development=DevelopmentConfig,
    production=ProductionConfig,
    default=DevelopmentConfig
)

def get_config():
    env = os.getenv('FLASK_ENV', 'default')
    return config_by_name.get(env, DevelopmentConfig)

# When initializing your Flask app:
# from .config import get_config
# app.config.from_object(get_config())
