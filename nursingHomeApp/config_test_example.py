DEBUG = True
TESTING = True
WTF_CSRF_ENABLED = False
MYSQL_HOST = 'YOUR_MYSQL_HOSTNAME'
MYSQL_USER = 'YOUR_USERNAME'
MYSQL_PASSWORD = 'MYSQL_PW_HERE'
MYSQL_DB = 'YOUR_TEST_DB_NAME'
SECRET_KEY = 'YOUR_SECRET_KEY'
MAIL_SERVER = 'YOUR_MAIL_SERVER'
MAIL_PORT = 587
MAIL_USE_TLS = True
MAIL_USERNAME = 'YOUR_MAIL_USERNAME'
MAIL_PASSWORD = 'YOUR_MAIL_PW'
MAIL_DEFAULT_SENDER = 'YOUR_MAIL_USERNAME'
MAIL_UTILS_ERROR_SEND_TO = ADMINS = ['YOUR_ERR_EMAIL']
# https://flask-login.readthedocs.io/en/latest/#cookie-settings
REMEMBER_COOKIE_DURATION = 60 * 20
REMEMBER_COOKIE_REFRESH_EACH_REQUEST = True
TWILIO_ACCOUNT_SID = "YOUR_TWILIO_ACCOUNT_SID"
TWILIO_AUTH_TOKEN = "YOUR_TWILIO_AUTH_TOKEN"
TWILIO_PHONE = "YOUR_TWILIO_PHONE"
