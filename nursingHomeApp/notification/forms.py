from flask_wtf import FlaskForm
from wtforms import SubmitField, IntegerField, BooleanField
from wtforms.fields.html5 import EmailField, TelField
from nursingHomeApp.common_validators import STR_2_NONE, is_valid_phone, is_gt_zero


class NotificationForm(FlaskForm):
    """Form fields correspond to columns in the notification table"""
    # primaryEmail is the e-mail the send_notifiations script will send
    # notification emails to, can be empty in which case it is set to null in DB
    primaryEmail = EmailField('Primary Email', filters=[STR_2_NONE])
    # boolean value: True means send e-mails to the primary e-mail, False
    # means don't send
    notifyPrimary = BooleanField('Send Notifications To Primary Email')
    # below 2 fields function exactly as above 2 fields
    secondaryEmail = EmailField('Secondary Email', filters=[STR_2_NONE])
    notifySecondary = BooleanField('Send Notifications To Secondary Email')
    # an integer representing how often an e-mail notification should be sent
    # must be >0, field will not validate if empty (required)
    numDays = IntegerField('Send Email Every N Days', validators=[is_gt_zero])
    # cellphone number, set to null in DB if empty
    phone = TelField('Phone number', validators=[is_valid_phone],
                     filters=[STR_2_NONE])
    # Boolean value: True means send text notifications, False means don't send
    notifyPhone = BooleanField('Text Notifications To Phone')
    # an integer representing how many days before or after the day a visit becomes
    # overdue a text message should be sent out. negative number is OK, means the
    # text should be sent before the visit has become overdue. field will not
    # validate if empty (required)
    daysBefore = IntegerField('Send Text N Days Prior to Overdue Visit')
    submit = SubmitField('Update')
