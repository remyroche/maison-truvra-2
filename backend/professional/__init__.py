# backend/professional/__init__.py
from flask import Blueprint

professional_bp = Blueprint('professional_bp', __name__, url_prefix='/api/professional')

from . import routes # Import routes for this blueprint
