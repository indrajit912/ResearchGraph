from flask import Blueprint
api_bp = Blueprint('api', __name__, url_prefix='/api')
from . import routes
from .admin_routes import admin_api_bp
