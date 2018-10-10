DEBUG = False
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
canAdd = {'Clerk': ['Physician', 'Nurse Practitioner'],
             'Facility Admin': ['Facility Admin', 'Clerk Manager', 'Clerk', 'Physician', 'Nurse Practitioner'],
             'Clerk Manager': ['Clerk', 'Physician', 'Nurse Practitioner'],
             'Site Admin': ['Facility Admin', 'Clerk Manager', 'Clerk', 'Physician', 'Nurse Practitioner', 'Site Admin']}
canRemove = {'Clerk': [],
             'Facility Admin': ['Facility Admin', 'Clerk Manager', 'Clerk', 'Physician', 'Nurse Practitioner'],
             'Clerk Manager': ['Clerk'],
             'Site Admin': ['Facility Admin', 'Clerk Manager', 'Clerk', 'Physician', 'Nurse Practitioner', 'Site Admin']}
canView = {'Clerk': ['Nurse Practitioner', 'Physician'],
           'Facility Admin': ['Facility Admin', 'Clerk Manager', 'Clerk', 'Physician', 'Nurse Practitioner'],
           'Clerk Manager': ['Clerk', 'Physician', 'Nurse Practitioner'],
           'Site Admin': ['Facility Admin', 'Clerk Manager', 'Clerk', 'Physician', 'Nurse Practitioner', 'Site Admin']}
