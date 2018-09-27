DEBUG = True
MYSQL_HOST = 'YOUR_MYSQL_HOSTNAME'
MYSQL_USER = 'YOUR_USERNAME'
MYSQL_PASSWORD = 'MYSQL_PW_HERE'
MYSQL_DB = 'YOUR__DEV_DB_NAME'
SECRET_KEY = 'YOUR_SECRET_KEY'
MAIL_SERVER = 'YOUR_MAIL_SERVER'
MAIL_PORT = 587
MAIL_USE_TLS = True
MAIL_USERNAME = 'YOUR_MAIL_USERNAME'
MAIL_PASSWORD = 'YOUR_MAIL_PW'
MAIL_DEFAULT_SENDER = 'YOUR_MAIL_USERNAME'
MAIL_UTILS_ERROR_SEND_TO = ADMINS = ['YOUR_ERR_EMAIL']
# map of user role, to list of user roles that role is allowed to add when adding a user
canAdd = {'Clerk': ['Physician', 'Nurse Practitioner'],
             'Facility Admin': ['Facility Admin', 'Clerk Manager', 'Clerk', 'Physician', 'Nurse Practitioner'],
             'Clerk Manager': ['Clerk', 'Physician', 'Nurse Practitioner'],
             'Site Admin': ['Facility Admin', 'Clerk Manager', 'Clerk', 'Physician', 'Nurse Practitioner', 'Site Admin']}
# map of user role, to list of user roles that role is allowed to delete (set inactive) when removing a user
canRemove = {'Clerk': [],
             'Facility Admin': ['Facility Admin', 'Clerk Manager', 'Clerk', 'Physician', 'Nurse Practitioner'],
             'Clerk Manager': ['Clerk'],
             'Site Admin': ['Facility Admin', 'Clerk Manager', 'Clerk', 'Physician', 'Nurse Practitioner', 'Site Admin']}
# map of user role, to list of user roles that role is allowed to view on the 'view_users' page
canView = {'Clerk': ['Nurse Practitioner', 'Physician'],
           'Facility Admin': ['Facility Admin', 'Clerk Manager', 'Clerk', 'Physician', 'Nurse Practitioner'],
           'Clerk Manager': ['Clerk', 'Physician', 'Nurse Practitioner'],
           'Site Admin': ['Facility Admin', 'Clerk Manager', 'Clerk', 'Physician', 'Nurse Practitioner', 'Site Admin']}
