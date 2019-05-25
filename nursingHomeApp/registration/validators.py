from wtforms.validators import ValidationError, StopValidation
from nursingHomeApp import mysql, bcrypt


IS_EMAIL_VALID = "SELECT * FROM user WHERE email=%s"
USER_HAS_PW = "SELECT password FROM user WHERE email=%s"
SELECT_PW = "SELECT password FROM user WHERE email=%s"
DOES_EMAIL_EXIST = "SELECT * FROM user WHERE email=%s"


def is_valid_email(form, field):
    cursor = mysql.connection.cursor()
    if not cursor.execute(IS_EMAIL_VALID, (form.email.data,)):
        raise StopValidation('This e-mail is not associated with an account')


def has_selected_pw(form, field):
    cursor = mysql.connection.cursor()
    if cursor.execute(USER_HAS_PW, (form.email.data,)):
        if cursor.fetchall()[0][0] is None:
            raise StopValidation(('Please select a password before trying to login. ' 
                                  'Check your e-mail for a signup link from visitminder.'))


def is_valid_pw(form, field):
    cursor = mysql.connection.cursor()
    if cursor.execute(SELECT_PW, (form.email.data,)):
        pw = cursor.fetchall()[0][0]
        if not bcrypt.check_password_hash(pw, form.pw.data):
            raise ValidationError('Incorrect Password')


def is_same_pw(form, field):
    if form.pw1.data != form.pw2.data:
        raise ValidationError('Does not match above password.')


def is_email_unique(form, field):
    cursor = mysql.connection.cursor()
    if cursor.execute(DOES_EMAIL_EXIST, (form.email.data,)):
        raise ValidationError('This email is already in use!')


def email_exists(form, field):
    cursor = mysql.connection.cursor()
    if not cursor.execute(DOES_EMAIL_EXIST, (form.email.data,)):
        raise ValidationError('This e-mail is not associated with an account.')
