from flask_wtf import FlaskForm
from wtforms import PasswordField, SubmitField, TextField, IntegerField, SelectField
from wtforms.fields.html5 import EmailField, TelField
from wtforms.validators import DataRequired, ValidationError, StopValidation, Optional
from nursingHomeApp import mysql, bcrypt


def is_valid_phone(form, field):
    if form.phone.data:
        try:
            int(form.phone.data)
        except ValueError:
            raise ValidationError('Please only include digits in this field')
        if len(form.phone.data) < 10 or len(form.phone.data) > 11:
            raise ValidationError('Phone number must be 10 or 11 digits long')


def is_valid_email(form, field):
    cursor = mysql.connection.cursor()
    if not cursor.execute("""SELECT * FROM user WHERE email=%s
            AND password IS NOT NULL""", (form.email.data,)):
        raise ValidationError('This email is not associated with an aaccount')


def is_valid_pw(form, field):
    cursor = mysql.connection.cursor()
    if cursor.execute("""SELECT password FROM user WHERE email=%s
            AND password IS NOT NULL""", (form.email.data,)):
        pw = cursor.fetchall()[0][0]
        if not bcrypt.check_password_hash(pw, form.pw.data):
            raise ValidationError('Incorrect Password')


def is_same_pw(form, field):
    if form.pw1.data != form.pw2.data:
        raise ValidationError('Does not match above password.')


def is_email_unique(form, field):
    cursor = mysql.connection.cursor()
    if cursor.execute("SELECT * FROM user WHERE email=%s", (form.email.data,)):
        raise ValidationError('This email is already in use!')


class LoginForm(FlaskForm):
    email = EmailField('email', validators=[DataRequired(), is_valid_email])
    pw = PasswordField('password', validators=[DataRequired(), is_valid_pw])
    submit = SubmitField('Login')


class AddUserForm(FlaskForm):
    first = TextField('First Name', validators=[DataRequired()])
    last = TextField('Last Name', validators=[DataRequired()])
    email = EmailField('Email', validators=[DataRequired(), is_email_unique])
    phone = TelField('Phone number', validators=[is_valid_phone])
    role = SelectField('Role', validators=[DataRequired()])
    submit = SubmitField('Add')

class PasswordForm(FlaskForm):
    pw1 = PasswordField('password', validators=[DataRequired()])
    pw2 = PasswordField('confirm password', validators=[DataRequired(), is_same_pw])
    submit = SubmitField('Create Password')