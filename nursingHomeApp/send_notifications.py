from datetime import datetime, timedelta
from flask import url_for, current_app, render_template
from flask_mail import Message
import pytz
from tabulate import tabulate
from twilio.rest import Client
from nursingHomeApp import mysql, mail
from nursingHomeApp.visit.routes import get_patient_info, prepare_patient_info

HEADERS = [['Name', 'Room', 'Days Until Next Visit', 'Days Until Next Dr. Visit', 
            'Next Required Visit (Doctor or Nurse)', 'Next Required Doctor Visit']]
INTRO = "Hello %s %s,\n\n Below are your patient's upcoming visit dates.\n\n"
MORE_INFO = ("\n\nFor more information regarding upcoming visits, login to your"
             " account here: %s\n\n")
OUTRO = "\n\nFollow this link if you would like all notifications turned off: %s"
TEXT_ALERT = ("You have %s patient(s) due for a visit by %s or earlier at the"
              " Havenwood Nursing Facility. The following patient(s) are due for"
              " a visit: %s. For a complete list please login on visitminder.com.")
# for now only doctors receive notifications
SELECT_NOTIFICATIONS = """SELECT u.first, u.last, n.email,
n.designee_email, n.email_notification_on, n.notify_designee,
n.email_every_n_days, n.phone, n.phone_notification_on, n.sms_n_days_advance,
n.user_id, n.email_last_sent, n.text_last_sent FROM notification n
JOIN user u ON u.id=n.user_id WHERE u.role='Physician'"""
EMAIL_SENT = "UPDATE notification SET email_last_sent=NOW() WHERE user_id=%s"
TEXT_SENT = "UPDATE notification SET text_last_sent=NOW() WHERE user_id=%s"


def send_notifications():
    """See if text or email notifications need to be sent out"""
    homepage = url_for('registration.login', _external=True)
    cursor = mysql.connection.cursor()
    # right now the app is running in a nursing home located on the east coast
    # only matters for sending out texts - only should send texts during daytime.
    current_tz = pytz.timezone('US/Eastern')
    current_hour = datetime.now(current_tz).hour
    today = datetime.now(current_tz).date()
    client = Client(current_app.config['TWILIO_ACCOUNT_SID'],
                    current_app.config['TWILIO_AUTH_TOKEN'])
    cursor.execute(SELECT_NOTIFICATIONS)
    # SELECT each physician user's notification preferences
    for (first, last, email1, email2, email1_permission, email2_permission, 
         days_between_email_notification, phone, notify_by_phone, days_before_overdue_text, 
         physician_user_id, last_email, last_text) in cursor.fetchall():
        # fetch list of patient's assiged to the physician (will be empty if none)
        patients = prepare_patient_info(get_patient_info(physician_user_id), True)
        # anonomize patient names
        for patient in patients:
            patient[0] = ' '.join('%s****%s' % (x[0], x[-1]) for x in patient[0].split())
        # send an email every N days, where N is specified by user and stored in
        # the Notification table
        email_by = (last_email + timedelta(days=days_between_email_notification)).date()
        emails = [(email1, email1_permission), (email2, email2_permission)]
        email_to = [dest for dest, permission in emails if permission and dest]
        # only send email if there is a recipient, at least 1 patient, and if
        # the last e-mail wasn't sent too recently
        if email_by <= today and patients and email_to:
            # generate the body of the email (html & plaintext)
            
            opt_out_url = url_for('notification.opt_out_page',
                                  userId=physician_user_id, _external=True)
            html = render_template('notification/notification_template.html',
                                   first=first, last=last, patients=patients,
                                   opt_out_url=opt_out_url, homepage=homepage)
            plain = tabulate([x[:-2] for x in patients], headers=HEADERS)
            plain = INTRO % (first, last) + plain + MORE_INFO % homepage + OUTRO % opt_out_url
            msg = Message("Your Upcoming Patient Visits", recipients=email_to,
                          html=html, body=plain)
            mail.send(msg)
            # update last e-mail sent timestamp
            cursor.execute(EMAIL_SENT, (physician_user_id,))
        # days_before_overdue_text is another notification preference set by the user
        # it is always a negative integer
        notify_by = (today + timedelta(days=-days_before_overdue_text)).strftime("%m/%d/%Y")
        # send a text at most once every week, between the hours of 9-6 east coast time
        # only send if the user has text notifications turned on
        dont_notify_before = (last_text + timedelta(days=7)).date()
        if phone and notify_by_phone and dont_notify_before <= today and 9 < current_hour <= 18:
            overdue_patients = []
            for name, _, _, days_until_next_dr_visit, _, _, _, _ in patients:
                if -days_before_overdue_text >= days_until_next_dr_visit:
                    overdue_patients.append(name)
            if overdue_patients:
                if not phone.startswith('1'):
                    phone = '1' + phone
                phone = '+' + phone
                args = (len(overdue_patients), notify_by, ", ".join(overdue_patients))
                msg = TEXT_ALERT % args
                client.messages.create(phone, body=msg, from_=current_app.config['TWILIO_PHONE'])
                # update last text sent timestamp
                cursor.execute(TEXT_SENT, (physician_user_id,))
    mysql.connection.commit()
