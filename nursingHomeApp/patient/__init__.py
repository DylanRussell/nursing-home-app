from flask import Blueprint

bp = Blueprint('patient', __name__)

from nursingHomeApp.patient import routes
