from __future__ import absolute_import
from nursingHomeApp import mysql, lm, mail, bcrypt
from flask import render_template, request, url_for, flash, redirect, current_app
from nursingHomeApp.registration.forms import LoginForm, AddUserForm,\
    PasswordForm, NewPasswordForm, EmailForm
from nursingHomeApp.registration import bp
from nursingHomeApp.common import login_required
from nursingHomeApp.config_prod import canAdd, canRemove, canView
from urlparse import urlparse, urljoin
from flask_login import logout_user, login_user, current_user
from itsdangerous import URLSafeTimedSerializer, BadSignature
from flask_mail import Message
import flask, datetime


AUTHENTICATE_A_USER = """UPDATE user SET password=%s, confirmed_on=NOW(),
email_confirmed=1, update_user=%s WHERE id=%s"""
INSERT_USER = """INSERT INTO user (role, first, last, email, phone,
create_user, active) VALUES (%s, %s, %s, %s, %s, %s, 1)"""
INSERT_NOTIFICATION = """INSERT INTO notification (email, phone, user_id,
create_user) VALUES (%s, %s, %s, %s)"""
SELECT_USER = """SELECT id, role, first, last, email, floor, active,
email_confirmed FROM USER WHERE (id=%s or email=%s)"""
SELECT_USERS_FACILITY = """SELECT facility_id FROM user_to_facility WHERE
user_id=%s"""
INSERT_USER_TO_FACILITY_MAPPING = """INSERT INTO user_to_facility (user_id,
facility_id, create_user, update_user) VALUES (%s, %s, %s, %s)"""
TOGGLE_USER_STATE = """UPDATE user SET active=not active,
update_user=%s, update_date=NOW() WHERE id=%s"""
SELECT_ROLE = "SELECT role FROM user WHERE id=%s"
SELECT_NEW_USER = """SELECT email, first, last, role FROM user WHERE id=%s
AND password IS NULL AND active=1 AND
DATE(invitation_last_sent) != CURDATE()"""
CANT_RESEND_CONFIRMATION = """Invitation E-mail has already been sent out
in the last 24 hours"""
UPDATE_INVITATION_SENT = """UPDATE user SET invitation_last_sent=NOW(),
update_user=%s, update_date=NOW() WHERE id=%s"""
SELECT_USERS_FACILITIES = """SELECT u.user_id, f.name FROM user_to_facility u
JOIN facility f ON f.id=u.facility_id"""


@bp.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('registration.login'))


@bp.errorhandler(500)
def page_not_found(e):
    return render_template('registration/500.html'), 500


@lm.user_loader
def load_user(id):
    return User(id=id)


@bp.route('/reset/<token>', methods=["GET", "POST"])
def reset_password(token):
    email = confirm_token(token)
    if not email:
        flash('The reset password link is invalid or has expired.', 'danger')
        return redirect(url_for('registration.forgot_pword'))
    form = NewPasswordForm()
    user = User(email=email)
    if form.validate_on_submit():
        authenticate_user(email, form.pw1.data, user.id)
        if user.active:
            login_user(user)
            flash('Your password has been reset!', 'success')
            if current_user.role in {'Nurse Practitioner', 'Physician'}:
                return redirect(url_for('visit.upcoming_for_clinician'))
            return redirect(url_for('visit.upcoming_for_clerk'))
        flash('The account associated with this email has been deactivated.', 'danger')
        return redirect(url_for('registration.login'))
    return render_template('registration/new_password.html', form=form)


@bp.route('/forgot', methods=['GET', 'POST'])
def forgot_pword():
    form = EmailForm()
    if form.validate_on_submit():
        msg = Message("Reset Your Password", recipients=[form.email.data])
        token = generate_confirmation_token(form.email.data)
        reset_url = url_for('registration.reset_password', token=token, _external=True)
        msg.html = render_template('registration/reset_pw_email.html', url=reset_url)
        mail.send(msg)
        flash('An e-mail has been sent with a link for you to reset your password.', 'success')
    return render_template('registration/reset_password.html', form=form)


@bp.route('/', methods=['GET', 'POST'])
def login():
    # password validation done in LoginForm
    form = LoginForm()
    if form.validate_on_submit():
        user = User(email=form.email.data)
        if user.active:
            login_user(user)
            flash('You Have Been Logged In!', 'success')
            next = request.args.get('next')
            if next and is_safe_url(next):
                return redirect(next)
            if current_user.role in {'Nurse Practitioner', 'Physician'}:
                return redirect(url_for('visit.upcoming_for_clinician'))
            elif current_user.role == 'Site Admin':
                return redirect(url_for('facility.view_facilities'))
            else:
                return redirect(url_for('visit.upcoming_for_clerk'))
        flash('The account linked to this email has been deactivated.', 'danger')
    return render_template('registration/login.html', form=form)


@bp.route('/add/user', methods=['GET', 'POST'])
@login_required('add_user')
def add_user():
    form = AddUserForm()
    form.role.choices = [(x, x) for x in canAdd[current_user.role]]
    if form.validate_on_submit():
        userId = create_user(form)
        msg = Message("Sign Up For visitMinder", recipients=[form.email.data])
        token = generate_confirmation_token(form.email.data)
        invitation_url = url_for('registration.confirm_email', token=token, _external=True)
        opt_out_url = url_for('notification.opt_out_page', userId=userId, _external=True)
        msg.html = render_template('registration/invitation.html', url=invitation_url,
                                   first=form.first.data, last=form.last.data,
                                   role=form.role.data,
                                   opt_out_url=opt_out_url)
        mail.send(msg)
        flash('User successfully added!', 'success')
        return redirect(url_for('registration.add_user'))
    return render_template('registration/add_user.html', form=form)


@bp.route('/confirm/<token>', methods=["GET", "POST"])
def confirm_email(token):
    email = confirm_token(token)
    if not email:
        flash('The confirmation link is invalid or has expired.', 'danger')
        return redirect(url_for('registration.login'))
    form = PasswordForm()
    user = User(email=email)
    if user.role == 'Physician':
        name = 'Doctor ' + user.last
    else:
        name = user.first + ' ' + user.last
    if form.validate_on_submit():
        authenticate_user(email, form.pw1.data, user.id)
        if user.active:
            login_user(user)
            flash('Sign up complete!', 'success')
            if current_user.role in {'Nurse Practitioner', 'Physician'}:
                return redirect(url_for('visit.upcoming_for_clinician'))
            return redirect(url_for('visit.upcoming_for_clerk'))
        flash('The account associated with this email has been deactivated.', 'danger')
        return redirect(url_for('registration.login'))
    return render_template('registration/add_password.html', form=form, name=name)


def generate_confirmation_token(email):
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return serializer.dumps(email, salt='invitation')


def confirm_token(token, expiration=604800):
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        return serializer.loads(
            token,
            salt='invitation',
            max_age=expiration
        )
    except BadSignature:
        return False


def authenticate_user(email, password, userId):
    cursor = mysql.connection.cursor()
    cursor.execute(AUTHENTICATE_A_USER,
                   (bcrypt.generate_password_hash(password), userId, userId))
    mysql.connection.commit()


def create_user(form):
    cursor = mysql.connection.cursor()
    args = (form.role.data, form.first.data.title(), form.last.data.title(),
            form.email.data, form.phone.data, current_user.id)
    cursor.execute(INSERT_USER, args)
    userId = cursor.lastrowid
    #if the user being added is a Site Admin, they do not belong to facility
    #otherwise the new user belongs to the facility that the user adding them
    #belongs to. if the user adding them is a Site Admin, the Site Admin is
    #asked in the add user form to select a facility for the new user
    if form.role.data != 'Site Admin':
        if current_user.role != 'Site Admin':
            cursor.execute(SELECT_USERS_FACILITY, (current_user.id,))
            facilityId = cursor.fetchall()[0][0]
        else:
            facilityId = form.facility.data
        args = (userId, facilityId, current_user.id, current_user.id)
        cursor.execute(INSERT_USER_TO_FACILITY_MAPPING, args)
        #a user receives notifications only if they are a physician / NP
        if form.role.data in {'Nurse Practitioner', 'Physician'}:
            args = (form.email.data, form.phone.data, userId, current_user.id)
            cursor.execute(INSERT_NOTIFICATION, args)
    mysql.connection.commit()
    return userId


@bp.before_app_request
def before_request():
    flask.session.permanent = True
    current_app.permanent_session_lifetime = datetime.timedelta(minutes=20)
    flask.session.modified = True
    flask.g.user = current_user


@bp.route('/send/invitation/<userId>', methods=['GET'])
@login_required('send_invitation')
def send_invitation(userId):
    cursor = mysql.connection.cursor()
    if cursor.execute(SELECT_NEW_USER, (userId,)):
        email, first, last, role = cursor.fetchall()[0]
        msg = Message("Sign Up For visitMinder", recipients=[email])
        token = generate_confirmation_token(email)
        invitation_url = url_for('registration.confirm_email', token=token, _external=True)
        opt_out_url = url_for('notification.opt_out_page', userId=userId, _external=True)
        msg.html = render_template('registration/invitation.html', url=invitation_url,
                                   first=first, last=last, role=role,
                                   opt_out_url=opt_out_url)
        mail.send(msg)
        flash('Invitation e-mail has been resent!', 'success')
        cursor.execute(UPDATE_INVITATION_SENT, (current_user.id, userId))
        mysql.connection.commit()
    else:
        flash(CANT_RESEND_CONFIRMATION, 'danger')
    return redirect(url_for('registration.view_users'))


@bp.route("/view/users")
@login_required('view_users')
def view_users():
    return render_template('registration/view_users.html', users=get_users(), canRemove=canRemove, facilities=get_user_facilities())


def get_user_facilities():
    # map of user id to comma separated string of facility names
    facilities = {}
    cursor = mysql.connection.cursor()
    cursor.execute(SELECT_USERS_FACILITIES)
    for userId, facility in cursor.fetchall():
        if userId in facilities:
            facilities[userId] += ', %s' % facility
        else:
            facilities[userId] = facility
    return facilities


def get_users():
    q = """SELECT first, last, email, phone, role, active, id,
    password IS NOT NULL, invitation_last_sent
    FROM user WHERE role in ('%s')""" % "','".join(canView[current_user.role])
    if current_user.role != 'Site Admin':
        q += """ AND id IN (SELECT user_id FROM user_to_facility
            WHERE facility_id IN (SELECT facility_id FROM user_to_facility
            WHERE user_id=%s))""" % current_user.id
    cursor = mysql.connection.cursor()
    cursor.execute(q)
    return cursor.fetchall()


@bp.route("/toggle/<id>")
@login_required('toggle_user')
def toggle_user(id):
    cur = current_user.role
    userRole = get_user_role(id)
    if str(current_user.id) == str(id):
        flash('Cannot add or remove yourself.', 'danger')
    elif userRole in canRemove[cur]:
        toggle_active_state(id)
        flash('Users status has been updated.', 'success')
    else:
        flash('You are not allowed to add or remove this type of user.', 'danger')
    return redirect(url_for('registration.view_users'))


def toggle_active_state(userId):
    cursor = mysql.connection.cursor()
    cursor.execute(TOGGLE_USER_STATE, (current_user.id, userId))
    mysql.connection.commit()


def get_user_role(id):
    cursor = mysql.connection.cursor()
    cursor.execute(SELECT_ROLE, (id,))
    return cursor.fetchone()[0]


def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and \
        ref_url.netloc == test_url.netloc


class User():
    def __init__(self, email=None, id=None):
        cursor = mysql.connection.cursor()
        cursor.execute(SELECT_USER, (id, email))
        self.id, self.role, self.first, self.last, self.email, self.floor,\
            self.active, self.confirmed = cursor.fetchall()[0]

    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return self.active

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return unicode(self.id)

    def __repr__(self):
        return '<User %r>' % (self.email)
