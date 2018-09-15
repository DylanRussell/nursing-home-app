from flask_wtf import FlaskForm
from wtforms import SubmitField, IntegerField, BooleanField
from wtforms.fields.html5 import EmailField, TelField
from nursingHomeApp.common_validators import STR_2_NONE, is_valid_phone


class NotificationForm(FlaskForm):
    primaryEmail = EmailField('Primary Email', filters=[STR_2_NONE])
    notifyPrimary = BooleanField('Send Notifications To Primary Email')
    secondaryEmail = EmailField('Secondary Email', filters=[STR_2_NONE])
    notifySecondary = BooleanField('Send Notifications To Secondary Email')
    numDays = IntegerField('Send Email Every N Days', filters=[STR_2_NONE])
    phone = TelField('Phone number', validators=[is_valid_phone], filters=[STR_2_NONE])
    notifyPhone = BooleanField('Text Notifications To Phone')
    daysBefore = IntegerField('Send Text N Days Prior to Overdue Visit', filters=[STR_2_NONE])
    submit = SubmitField('Update')
