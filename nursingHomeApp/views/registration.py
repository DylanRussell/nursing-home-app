from __future__ import absolute_import
from nursingHomeApp import app, mysql, lm, mail, bcrypt
from flask import render_template, request, url_for, flash, redirect
from nursingHomeApp.forms.registration_forms import LoginForm, AddUserForm,\
    PasswordForm
from nursingHomeApp.views.common import login_required
from nursingHomeApp.config_safe import role2role
from urlparse import urlparse, urljoin
from flask_login import logout_user, login_user, current_user
from itsdangerous import URLSafeTimedSerializer, BadSignature
from flask_mail import Message
from twilio.twiml.messaging_response import MessagingResponse


OPT_OUT = """UPDATE notification SET email_notification_on=0, notify_designee=0,
phone_notification_on=0 WHERE user_id=%s"""
AUTHENTICATE_A_USER = """UPDATE user SET password=%s, confirmed_on=NOW(),
email_confirmed=1 WHERE email=%s"""
INSERT_USER = """INSERT INTO user (role, first, last, email, phone, create_user)
VALUES (%s, %s, %s, %s, %s, %s)"""
INSERT_NOTIFICATION = """INSERT INTO notification (email, phone, user_id,
create_user) VALUES (%s, %s, %s, %s)"""
SELECT_USER = """SELECT id, role, first, last, email, floor, active,
email_confirmed FROM USER WHERE (id=%s or email=%s)"""


@app.route("/sms", methods=['GET', 'POST'])
def sms_reply():
    """Respond to incoming calls with a simple text message."""
    # Start our TwiML response
    resp = MessagingResponse()

    # Add a message
    resp.message("Please visit www.visitMinder.com for more info.")

    return str(resp)


@app.route("/opt/out/<int:userId>")
def opt_out_page(userId):
    opt_out_user(userId)
    flash('You have been opted out of all notifications.', 'success')
    return redirect(url_for('login'))


def opt_out_user(userId):
    cursor = mysql.connection.cursor()
    cursor.execute(OPT_OUT, (userId,))
    mysql.connection.commit()


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.errorhandler(500)
def page_not_found(e):
    return render_template('500.html'), 500


@lm.user_loader
def load_user(id):
    return User(id=id)


@app.route('/', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User(email=form.email.data)
        if user.active:
            login_user(user)
            flash('Logged in successfully!', 'success')
            next = request.args.get('next')
            if next and is_safe_url(next):
                return redirect(next)
            if current_user.role in {'Nurse Practitioner', 'Physician'}:
                return redirect(url_for('upcoming_for_clinician'))
            else:
                return redirect(url_for('upcoming_for_clerk'))
        flash('The account linked to this email has been deactivated.', 'danger')
    return render_template('login.html', form=form)


@app.route('/add/user', methods=['GET', 'POST'])
@login_required('add_user')
def add_user():
    form = AddUserForm()
    form.role.choices = [(x, x) for x in role2role[current_user.role]]
    if form.validate_on_submit():
        userId = create_user(form)
        create_notification(form, userId)
        msg = Message("Sign Up For visitMinder", recipients=[form.email.data])
        token = generate_confirmation_token(form.email.data)
        invitation_url = url_for('confirm_email', token=token, _external=True)
        opt_out_url = url_for('opt_out_page', userId=userId, _external=True)
        msg.html = render_template('invitation.html', url=invitation_url,
                                   first=form.first.data, last=form.last.data,
                                   role=form.role.data,
                                   opt_out_url=opt_out_url)
        mail.send(msg)
        flash('User successfully added!', 'success')
        return redirect(url_for('add_user'))
    return render_template('add_user.html', form=form)


@app.route('/confirm/<token>', methods=["GET", "POST"])
def confirm_email(token):
    email = confirm_token(token)
    if not email:
        flash('The confirmation link is invalid or has expired.', 'danger')
        return redirect(url_for('login'))
    form = PasswordForm()
    user = User(email=email)
    if user.role == 'Physician':
        name = 'Doctor ' + user.last
    else:
        name = user.first + ' ' + user.last
    if form.validate_on_submit():
        authenticate_user(email, form.pw1.data)
        if user.active:
            login_user(user)
            flash('Sign up complete!', 'success')
            if current_user.role in {'Nurse Practitioner', 'Physician'}:
                return redirect(url_for('upcoming_for_clinician'))
            return redirect(url_for('upcoming_for_clerk'))
        flash('The account associated with this email has been deactivated.', 'danger')
        return redirect(url_for('login'))
    return render_template('add_password.html', form=form, name=name)


def generate_confirmation_token(email):
    serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    return serializer.dumps(email, salt='invitation')


def confirm_token(token, expiration=3600):
    serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    try:
        return serializer.loads(
            token,
            salt='invitation',
            max_age=expiration
        )
    except BadSignature:
        return False


def authenticate_user(email, password):
    cursor = mysql.connection.cursor()
    cursor.execute(AUTHENTICATE_A_USER,
                   (bcrypt.generate_password_hash(password), email))
    mysql.connection.commit()


def create_user(form):
    cursor = mysql.connection.cursor()
    args = (form.role.data, form.first.data.title(), form.last.data.title(),
            form.email.data, form.phone.data, current_user.id)
    cursor.execute(INSERT_USER, args)
    mysql.connection.commit()
    return cursor.lastrowid


def create_notification(form, userId):
    if form.role.data in {'Nurse Practitioner', 'Physician'}:
        cursor = mysql.connection.cursor()
        cursor.execute(INSERT_NOTIFICATION, (form.email.data, form.phone.data,
                       userId, current_user.id))
        mysql.connection.commit()


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
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return unicode(self.id)

    def __repr__(self):
        return '<User %r>' % (self.email)
