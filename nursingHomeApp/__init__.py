from __future__ import absolute_import
from flask import Flask
from nursingHomeApp.flask_mysql import MySQL
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_bootstrap import Bootstrap
from flask_mail import Mail
from flask_sslify import SSLify


application = Flask(__name__)
app = application
app.config.from_object('nursingHomeApp.config_safe')
Bootstrap(app)
lm = LoginManager(app)
lm.login_view = 'login'
mysql = MySQL(app)
bcrypt = Bcrypt(app)
mail = Mail(app)

if not app.debug:
    SSLify(app)
    from nursingHomeApp.flask_mail_handler import register_mail_error_handler
    register_mail_error_handler(app, mail)

import nursingHomeApp.views.registration, nursingHomeApp.views.users, nursingHomeApp.views.patients, nursingHomeApp.views.visits
