from __future__ import absolute_import
from nursingHomeApp import mysql
from nursingHomeApp.notification import bp
from flask import render_template, url_for, flash, redirect
from nursingHomeApp.notification.forms import NotificationForm
from nursingHomeApp.common import login_required
from flask_login import current_user
from twilio.twiml.messaging_response import MessagingResponse


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
    """Respond to incoming calls with a simple text message."""
    # Start our TwiML response
    resp = MessagingResponse()

    # Add a message
    resp.message("Please visit www.visitMinder.com for more info.")

    return str(resp)


@bp.route("/opt/out/<int:userId>")
def opt_out_page(userId):
    opt_out_user(userId)
    flash('You have been opted out of all notifications.', 'success')
    return redirect(url_for('registration.login'))


def opt_out_user(userId):
    cursor = mysql.connection.cursor()
    cursor.execute(OPT_OUT, (userId,))
    mysql.connection.commit()


@bp.route("/notifications", methods=['GET', 'POST'])
@login_required('notifications')
def notifications():
    form = NotificationForm()
    if form.validate_on_submit():
        flash('Your Changes Have Been saved', 'success')
        update_notifications(form)
    set_notification_defaults(form)
    return render_template('notification/notifications.html', form=form)


def set_notification_defaults(form):
    cursor = mysql.connection.cursor()
    cursor.execute(SELECT_NOTIFICATION, (current_user.id,))
    (form.primaryEmail.default, form.secondaryEmail.default,
        form.notifyPrimary.default, form.notifySecondary.default,
        form.numDays.default, form.phone.default, form.notifyPhone.default,
        form.daysBefore.default) = cursor.fetchone()
    form.process()


def update_notifications(form):
    args = (form.primaryEmail.data, form.secondaryEmail.data,
            form.notifyPrimary.data, form.notifySecondary.data,
            form.numDays.data, form.phone.data, form.notifyPhone.data,
            form.daysBefore.data, current_user.id, current_user.id)
    cursor = mysql.connection.cursor()
    cursor.execute(UPDATE_NOTIFICATION, args)
    mysql.connection.commit()
