from __future__ import absolute_import
from flask import Flask
from nursingHomeApp.flask_mysql import MySQL
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_bootstrap import Bootstrap
from flask_mail import Mail


app = Flask(__name__)
app.config.from_object('nursingHomeApp.config_safe')
Bootstrap(app)
lm = LoginManager(app)
lm.login_view = 'login'
mysql = MySQL(app)
bcrypt = Bcrypt(app)
mail = Mail(app)
import nursingHomeApp.views.registration, nursingHomeApp.views.users, nursingHomeApp.views.patients, nursingHomeApp.views.visits