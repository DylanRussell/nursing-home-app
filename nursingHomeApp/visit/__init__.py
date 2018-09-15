from flask import Blueprint

bp = Blueprint('visit', __name__)

from nursingHomeApp.visit import routes
