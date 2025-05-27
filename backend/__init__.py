# backend/__init__.py
import os
import logging
import jwt
import json # For json.loads in admin_api/routes.py, good to have it here if used elsewhere too

from flask import Flask, request, current_app, send_from_directory, g, jsonify, abort
from flask_cors import CORS
from werkzeug.utils import safe_join
from sqlalchemy import func # For dashboard stats

from .config import Config
from .database import db, init_db, populate_initial_data, User, Order, Product, init_db_command # Added Order, Product

# Import blueprints
from .admin_api import admin_api_bp_for_app
from .auth import auth_bp
from .products import products_bp
from .orders import orders_bp
from .newsletter import newsletter_bp
from .professional import professional_bp
# from .inventory import inventory_bp # Uncomment if you have an inventory blueprint

def create_app(config_class=Config):
    app = Flask(__name__, static_folder='../static_assets', static_url_path='/static_assets')
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    CORS(app, resources={r"/api/*": {"origins": "*"}}) # Configure CORS early

    # Configure logging
    log_level = logging.DEBUG if app.debug else logging.INFO
    logging.basicConfig(level=log_level,
                        format='%(asctime)s %(levelname)s: %(message)s [%(name)s:%(lineno)d]',
                        datefmt='%Y-%m-%dT%H:%M:%S%z')
    app.logger.setLevel(log_level)

    # Initialize database and optionally populate initial data
    with app.app_context():
        init_db() # Creates tables if they don't exist

        admin_username = app.config.get("ADMIN_USERNAME", "admin")
        admin_user = User.query.filter_by(username=admin_username).first()
        if not admin_user:
            app.logger.info(f"Admin user '{admin_username}' not found. Populating initial data.")
            populate_initial_data()
        else:
            app.logger.info(f"Admin user '{admin_username}' already exists. Skipping initial data population.")

    # Register blueprints
    app.register_blueprint(admin_api_bp_for_app, url_prefix='/api/admin')
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(products_bp, url_prefix='/api/products')
    app.register_blueprint(orders_bp, url_prefix='/api/orders')
    app.register_blueprint(newsletter_bp, url_prefix='/api/newsletter')
    app.register_blueprint(professional_bp, url_prefix='/api/professional')
    # if inventory_bp:
    #     app.register_blueprint(inventory_bp, url_prefix='/api/inventory')
    
    app.logger.info("All blueprints registered.")

    @app.route('/passports/<path:filename>')
    def serve_passport_route(filename):
        passports_config_dir = current_app.config.get('PASSPORTS_OUTPUT_DIR')
        if not passports_config_dir:
            current_app.logger.error("PASSPORTS_OUTPUT_DIR is not configured.")
            return abort(500)

        passports_abs_dir = os.path.abspath(os.path.join(app.root_path, passports_config_dir))
        
        try:
            safe_file_path = safe_join(passports_abs_dir, filename)
            if safe_file_path is None or \
               not os.path.normpath(safe_file_path).startswith(os.path.normpath(passports_abs_dir) + os.sep) and \
               os.path.normpath(safe_file_path) != os.path.normpath(passports_abs_dir): # check for exact match for dir itself
                current_app.logger.warning(f"Potential path traversal attempt for passport: {filename} from directory {passports_abs_dir}")
                return abort(404)
        except Exception as e:
            current_app.logger.error(f"Error during safe_join for passport {filename}: {e}", exc_info=True)
            return abort(404)

        if not os.path.isfile(safe_file_path):
            current_app.logger.info(f"Passport file not found: {safe_file_path}")
            return abort(404)

        try:
            return send_from_directory(passports_abs_dir, filename, as_attachment=False)
        except FileNotFoundError:
            current_app.logger.warning(f"Passport not found by send_from_directory: {filename} in {passports_abs_dir}")
            return abort(404)
        except Exception as e:
            current_app.logger.error(f"Error serving passport {filename}: {e}", exc_info=True)
            return "Error serving file", 500

    @app.before_request
    def before_request_func():
        g.current_user_id = None
        g.user_type = None
        g.is_admin = False

        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(" ")[1]
            try:
                payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"])
                g.current_user_id = payload.get('user_id')
                g.user_type = payload.get('user_type')
                g.is_admin = payload.get('is_admin', False)
            except jwt.ExpiredSignatureError:
                app.logger.debug("Token expired during before_request.")
            except jwt.InvalidTokenError:
                app.logger.debug("Invalid token during before_request.")
            except Exception as e:
                app.logger.error(f"Error decoding token in before_request: {e}", exc_info=True)

    @app.route('/')
    @app.route('/api')
    def api_root():
        return jsonify({
            "message": "Welcome to the Maison Trüvra API!",
            "version": "1.2.1", # Incremented version
            "documentation": "Refer to API blueprints for endpoint details"
        })

    @app.cli.command('init-db')
    def init_db_cli_command():
        init_db_command() 
        app.logger.info("Database initialized from CLI.")

    return app
