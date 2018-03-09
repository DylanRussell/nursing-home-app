from nursingHomeApp import mysql, bcrypt
from wtforms.validators import ValidationError, StopValidation


IS_EMAIL_VALID = "SELECT * FROM user WHERE email=%s AND password IS NOT NULL"
SELECT_PW = "SELECT password FROM user WHERE email=%s"
DOES_EMAIL_EXIST = "SELECT * FROM user WHERE email=%s"


def is_valid_phone(form, field):
    if form.phone.data:
        try:
            int(form.phone.data)
        except ValueError:
            raise ValidationError('Please only include digits in this field')
        if len(form.phone.data) not in {10, 11}:
            raise ValidationError('Phone number must be 10 or 11 digits long')


def is_valid_email(form, field):
    cursor = mysql.connection.cursor()
    if not cursor.execute(IS_EMAIL_VALID, (form.email.data,)):
        raise StopValidation('This email is not associated with an account')


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
