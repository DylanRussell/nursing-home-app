from __future__ import absolute_import
from flask import render_template, url_for, flash, redirect
from flask_login import current_user
from twilio.twiml.messaging_response import MessagingResponse
from nursingHomeApp import mysql
from nursingHomeApp.notification import bp
from nursingHomeApp.notification.forms import NotificationForm
from nursingHomeApp.registration.routes import login_required


OPT_OUT = """UPDATE notification SET email_notification_on=0, notify_designee=0,
phone_notification_on=0, update_date=NOW() WHERE user_id=%s"""
SELECT_NOTIFICATION = """SELECT email, designee_email, email_notification_on,
notify_designee, email_every_n_days, phone, phone_notification_on,
sms_n_days_advance FROM notification WHERE user_id=%s"""
UPDATE_NOTIFICATION = """UPDATE notification SET email=%s, designee_email=%s,
email_notification_on=%s, notify_designee=%s, email_every_n_days=%s, phone=%s,
phone_notification_on=%s, sms_n_days_advance=%s, update_user=%s
WHERE user_id=%s"""


@bp.route("/sms", methods=['GET', 'POST'])
def sms_reply():
    """Respond to incoming calls/texts with a simple text message.
    
    twilio is used to send out text messages (see the send_notifications.py
    script). Twilio's api is also used here to send a text message response whenever
    a user texts or emails the twilio number that texted them.
    """
    # Start our TwiML response
    resp = MessagingResponse()

    # Add a message
    resp.message("Please visit www.visitMinder.com for more info.")

    return str(resp)


@bp.route("/opt/out/<int:userId>")
def opt_out_page(userId):
    """This link is included in the invitation and notification e-mails
    sent to Physician and Nurse Practitioner users (these are the only users
    that receive notifications) to allow them to opt out of receiving 
    notifications. By default they are opted-in to receiving text & e-mail
    notifications.

    Doesn't require the user to be logged in, which is bad as anyone (not just
    the owner of the account) could make a request to this endpoint with a 
    user's ID, and that user's notifications would be turned off.

    However because a user is opted in by default before they create a password, 
    they should be allowed to opt out without first creating a password as well,
    and this was the simplest way of allowing them to do that.

    The URL to this route doesn't appear anywhere except in e-mails to the
    user, so no requests should be made except by the user unless someone is 
    trying to deliberately mess with the app.

    Users can also login and visit the /notificatios route (see below) to 
    adjust their notification preferences.
    """
    cursor = mysql.connection.cursor()
    cursor.execute(OPT_OUT, (userId,))
    mysql.connection.commit()
    flash('You have been opted out of all notifications.', 'success')
    return redirect(url_for('registration.login'))



@bp.route("/notifications", methods=['GET', 'POST'])
@login_required('notifications')
def notifications():
    """Allows the logged in user to update their notification preferences.
    Only Nurse Practitioner / Physician user's receive notifications, and
    thus only those user role's have permission to this route (and the URL
    to this route only appear's in those user's navbars).

    This route works the same as the update_patient route in the way it sets
    a form's fields by default, and executes an UPDATE statement regardless of if
    the user actually changed anything (as long as the form validates and a POST
    request is made). See that route's docstring for more details.

    See the NotificationForm for which fields can be updated and what they are
    used for. Also see the send_notifications.py script, as this script
    is what makes use of the notification table to send out text and e-mail
    notifications.
    """
    form = NotificationForm()
    if form.validate_on_submit():
        update_notifications(form)
        flash('Your Changes Have Been saved', 'success')
    set_notification_defaults(form)
    return render_template('notification/notifications.html', form=form)


def set_notification_defaults(form):
    """Sets the fields in the NotificationForm equal to their values in the 
    notification table.
    """
    cursor = mysql.connection.cursor()
    cursor.execute(SELECT_NOTIFICATION, (current_user.id,))
    (form.primaryEmail.default, form.secondaryEmail.default,
     form.notifyPrimary.default, form.notifySecondary.default,
     form.numDays.default, form.phone.default, form.notifyPhone.default,
     form.daysBefore.default) = cursor.fetchone()
    form.process()


def update_notifications(form):
    """Updates a row in the notification table to be equal to the values of the
    user submitted & validated NotificationForm.
    """
    args = (form.primaryEmail.data, form.secondaryEmail.data,
            form.notifyPrimary.data, form.notifySecondary.data,
            form.numDays.data, form.phone.data, form.notifyPhone.data,
            form.daysBefore.data, current_user.id, current_user.id)
    cursor = mysql.connection.cursor()
    cursor.execute(UPDATE_NOTIFICATION, args)
    mysql.connection.commit()
