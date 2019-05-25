from flask_wtf import FlaskForm
from wtforms import PasswordField, SubmitField, TextField
from wtforms.fields.html5 import EmailField, TelField
from wtforms.validators import DataRequired
from wtforms_components import SelectField
from nursingHomeApp.registration.validators import is_email_unique,\
    is_same_pw, is_valid_pw, is_valid_email, email_exists, has_selected_pw
from nursingHomeApp.common_queries import get_facilities
from nursingHomeApp.common_validators import is_valid_phone


class AddUserForm(FlaskForm):
    first = TextField('First Name', validators=[DataRequired()])
    last = TextField('Last Name', validators=[DataRequired()])
    email = EmailField('Email', validators=[DataRequired(), is_email_unique])
    phone = TelField('Phone number', validators=[is_valid_phone])
    role = SelectField('Role', validators=[DataRequired()])
    facility = SelectField('Facility', choices=get_facilities, coerce=int)
    submit = SubmitField('Add')


class PasswordForm(FlaskForm):
    pw1 = PasswordField('password', validators=[DataRequired()])
    pw2 = PasswordField('confirm password', validators=[DataRequired(), is_same_pw])
    submit = SubmitField('Create Password')


class LoginForm(FlaskForm):
    email = EmailField('email', validators=[DataRequired(), is_valid_email])
    pw = PasswordField('password', validators=[DataRequired(), has_selected_pw, is_valid_pw])
    submit = SubmitField('Login')


class EmailForm(FlaskForm):
    email = EmailField('email', validators=[DataRequired(), email_exists])
    submit = SubmitField('Reset Password')
