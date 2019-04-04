from __future__ import absolute_import
import logging
from logging.handlers import SMTPHandler, RotatingFileHandler
import os
from flask import Flask
from flask_bcrypt import Bcrypt
from flask_bootstrap import Bootstrap
from flask_login import LoginManager
from flask_mail import Mail
from flask_mysqldb import MySQL
from flask_sslify import SSLify


lm = LoginManager()
lm.login_view = 'login'
mysql = MySQL()
bcrypt = Bcrypt()
mail = Mail()


def create_app(config_file='nursingHomeApp.config_dev'):
    """App factory function"""
    app = Flask(__name__)
    app.config.from_object(config_file)
    Bootstrap(app)
    lm.init_app(app)
    mysql.init_app(app)
    bcrypt.init_app(app)
    mail.init_app(app)
    from nursingHomeApp.facility import bp as facility_bp
    from nursingHomeApp.notification import bp as notification_bp
    from nursingHomeApp.patient import bp as patient_bp
    from nursingHomeApp.registration import bp as registration_bp
    from nursingHomeApp.visit import bp as visit_bp
    for bp in [facility_bp, notification_bp, patient_bp, registration_bp, visit_bp]:
        app.register_blueprint(bp)

    if not app.debug and not app.testing:
        SSLify(app)
        auth = (app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
        mail_handler = SMTPHandler(
            mailhost=(app.config['MAIL_SERVER'], app.config['MAIL_PORT']),
            fromaddr=app.config['MAIL_SERVER'],
            toaddrs=app.config['ADMINS'], subject='VisitMinder Failure',
            credentials=auth, secure=())
        mail_handler.setLevel(logging.ERROR)
        app.logger.addHandler(mail_handler)
        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = RotatingFileHandler('logs/nursingHomeApp.log', maxBytes=10240,
                                           backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)

        app.logger.setLevel(logging.INFO)
        app.logger.info('nursingHomeApp start up')

    return app
