from flask import Blueprint

bp = Blueprint('facility', __name__)

from nursingHomeApp.facility import routes
