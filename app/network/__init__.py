from flask import Blueprint
network_bp = Blueprint('network', __name__, url_prefix='/network')
from . import routes
