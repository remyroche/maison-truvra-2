# backend/__init__.py
from flask import Flask, request, current_app # Added request, current_app
from flask_cors import CORS
import os
import logging
from flask import g 

from .config import AppConfig, configure_asset_paths # Import new helper
from .database import init_db, populate_initial_data, init_db_command

def create_app(config_class=AppConfig):
    app = Flask(__name__, static_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'website', 'static_assets'))
    # Configure static_folder to point to a directory at the project root, e.g., 'project_root/static_assets'
    # Or, if you prefer 'backend/static': static_folder='static' (relative to backend package)
    # Or, if 'website' serves its own static files and admin assets are separate:
    # static_url_path='/admin_assets', static_folder='admin_assets' (inside backend or project root)
    # For simplicity, let's assume a shared static folder at project root for now.
    # This means create a folder named 'static_assets' in your project root.
    # And inside 'static_assets', create 'passports', 'qrcodes', 'labels', 'images', 'fonts'.

    app.config.from_object(config_class)

    # Call configure_asset_paths after app config is loaded
    with app.app_context(): # Ensure app context for current_app.config
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
        populate_initial_data() 

    from .auth import auth_bp
    app.register_blueprint(auth_bp)

    from .products import products_bp
    app.register_blueprint(products_bp)

    from .orders import orders_bp
    app.register_blueprint(orders_bp)

    from .newsletter import newsletter_bp
    app.register_blueprint(newsletter_bp)

    from .inventory import inventory_bp 
    app.register_blueprint(inventory_bp)

    from .admin_api import admin_api_bp 
    app.register_blueprint(admin_api_bp)
    app.logger.info("Admin API blueprint registered.")

    # Add a route to serve passports if they are in static folder
    # This is a simple way; for many files, a dedicated serving mechanism or Nginx is better.
    @app.route('/passports/<filename>')
    def serve_passport(filename):
        passport_dir = current_app.config['PASSPORTS_OUTPUT_DIR']
        # Ensure filename is safe
        if ".." in filename or filename.startswith("/"):
            from flask import abort
            return abort(404)
        return send_from_directory(passport_dir, filename)


    @app.before_request
    def before_request_func():
        g.admin_user_id = None 
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(" ")[1]
            try:
                import jwt 
                payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"])
                g.current_user_id = payload.get('user_id')
                g.is_admin = payload.get('is_admin', False)
                if g.is_admin:
                    g.admin_user_id = g.current_user_id 
            except jwt.ExpiredSignatureError:
                g.current_user_id = None
                g.is_admin = False
                app.logger.debug("Token expired during before_request.")
            except jwt.InvalidTokenError:
                g.current_user_id = None
                g.is_admin = False
                app.logger.debug("Invalid token during before_request.")
            except Exception as e:
                g.current_user_id = None
                g.is_admin = False
                app.logger.error(f"Error decoding token in before_request: {e}")


    @app.route('/')
    @app.route('/api')
    def api_root():
        return jsonify({
            "message": "Welcome to the Maison Trüvra API!",
            "version": "1.1.0", # Incremented version for asset automation
            "documentation": "/api/docs" 
        })

    @app.cli.command('init-db')
    def init_db_cli_command():
        init_db_command(app.app_context())
        app.logger.info("Database initialized from CLI.")

    # Import send_from_directory for serving passports
    from flask import send_from_directory
    return app
