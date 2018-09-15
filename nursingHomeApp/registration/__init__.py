from flask import Blueprint

bp = Blueprint('registration', __name__)

from nursingHomeApp.registration import routes
