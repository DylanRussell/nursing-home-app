from flask_wtf import FlaskForm
from wtforms import SubmitField, IntegerField, BooleanField
from wtforms.fields.html5 import EmailField, TelField
from nursingHomeApp.forms.registration_forms import is_valid_phone


class NotificationForm(FlaskForm):
    primaryEmail = EmailField('Primary Email', filters=[lambda x: x or None])
    notifyPrimary = BooleanField('Send Notifications To Primary Email')
    secondaryEmail = EmailField('Secondary Email',  filters=[lambda x: x or None])
    notifySecondary = BooleanField('Send Notifications To Secondary Email')
    numDays = IntegerField('Send Email Every N Days', filters=[lambda x: x or None])
    phone = TelField('Phone number', validators=[is_valid_phone], filters=[lambda x: x or None])
    notifyPhone = BooleanField('Text Notifications To Phone')
    daysBefore = IntegerField('Send Text N Days Prior to Overdue Visit', filters=[lambda x: x or None])
    submit = SubmitField('Update')
