from flask import Blueprint

bp = Blueprint('notification', __name__)

from nursingHomeApp.notification import routes
