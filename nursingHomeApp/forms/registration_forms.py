from flask_wtf import FlaskForm
from wtforms import PasswordField, SubmitField, TextField, SelectField
from wtforms.fields.html5 import EmailField, TelField
from wtforms.validators import DataRequired
from nursingHomeApp.forms.registration_validators import is_email_unique,\
    is_same_pw, is_valid_pw, is_valid_email, is_valid_phone


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


class LoginForm(FlaskForm):
    email = EmailField('email', validators=[DataRequired(), is_valid_email])
    pw = PasswordField('password', validators=[DataRequired(), is_valid_pw])
    submit = SubmitField('Login')
