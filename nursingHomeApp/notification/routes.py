from __future__ import absolute_import
from nursingHomeApp import app, mysql
from flask import render_template, flash, redirect, url_for
from nursingHomeApp.views.common import login_required
from flask_login import current_user
from nursingHomeApp.forms.notification_forms import NotificationForm
import flask, datetime


SELECT_NOTIFICATION = """SELECT email, designee_email, email_notification_on,
notify_designee, email_every_n_days, phone, phone_notification_on,
sms_n_days_advance FROM notification WHERE user_id=%s"""
UPDATE_NOTIFICATION = """UPDATE notification SET email=%s, designee_email=%s,
email_notification_on=%s, notify_designee=%s, email_every_n_days=%s, phone=%s,
phone_notification_on=%s, sms_n_days_advance=%s WHERE user_id=%s"""
TOGGLE_USER_STATE = "UPDATE user SET active=not active WHERE id=%s"
SELECT_ROLE = "SELECT role FROM user WHERE id=%s"


@app.before_request
def before_request():
    flask.session.permanent = True
    app.permanent_session_lifetime = datetime.timedelta(minutes=20)
    flask.session.modified = True
    flask.g.user = current_user


@app.route("/view/users")
@login_required('view_users')
def view_users():
    return render_template('view_users.html', users=get_users())


def get_users():
    q = "SELECT first, last, email, phone, role, active, id FROM user"
    if current_user.role == 'Clerk':
        q += " WHERE role IN ('Nurse Practitioner', 'Physician') AND active=1"
    elif current_user.role == 'Clerk Manager':
        q += " WHERE ROLE IN ('Nurse Practitioner', 'Physician', 'Clerk', 'Clerk Manager')"
    cursor = mysql.connection.cursor()
    cursor.execute(q)
    return cursor.fetchall()


@app.route("/notifications", methods=['GET', 'POST'])
@login_required('notifications')
def notifications():
    form = NotificationForm()
    if form.validate_on_submit():
        flash('Your Changes Have Been saved', 'success')
        update_notifications(form)
    set_notification_defaults(form)
    return render_template('notifications.html', form=form)


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
            form.daysBefore.data, current_user.id)
    cursor = mysql.connection.cursor()
    cursor.execute(UPDATE_NOTIFICATION, args)
    mysql.connection.commit()


@app.route("/toggle/<id>")
@login_required('toggle_user')
def toggle_user(id):
    cur = current_user.role
    userRole = get_user_role(id)
    if str(current_user.id) == str(id):
        flash('Cannot change your own status.', 'danger')
    elif (cur == 'Clerk Manager' and userRole == 'Clerk') or cur == 'Admin':
        toggle_active_state(id)
        flash('Users status has been updated.', 'success')
    else:
        flash('You do not have access to this operation.', 'danger')
    return redirect(url_for('view_users'))


def toggle_active_state(userId):
    cursor = mysql.connection.cursor()
    cursor.execute(TOGGLE_USER_STATE, (userId,))
    mysql.connection.commit()


def get_user_role(id):
    cursor = mysql.connection.cursor()
    cursor.execute(SELECT_ROLE, (id,))
    return cursor.fetchone()[0]