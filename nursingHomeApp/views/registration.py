from __future__ import absolute_import
from nursingHomeApp import app, mysql, lm, mail, bcrypt
from flask import render_template, request, url_for, flash, redirect
from nursingHomeApp.forms.registration_forms import LoginForm, AddUserForm, PasswordForm
from nursingHomeApp.views.common import login_required
from nursingHomeApp.config_safe import role2role
from urlparse import urlparse, urljoin
from flask_login import logout_user, login_user, current_user
from itsdangerous import URLSafeTimedSerializer, BadSignature
from flask_mail import Message


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.before_request
def before_request():
    app.jinja_env.cache = {}


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
            if next and is_safe_url(next):  # need to test an invalid url...
                return redirect(next)

            return redirect(url_for('add_user'))
        else:
            flash('The account associated with this email has been deactivated.', 'danger')
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
        msg.html = render_template('invitation.html', url=invitation_url)
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
    if form.validate_on_submit():
        authenticate_user(email, form.pw1.data)
        user = User(email=email)
        if user.active:
            login_user(user)
            flash('Sign up complete! View your patients here.', 'success')
            return redirect(url_for('add_user'))
        else:
            flash('The account associated with this email has been deactivated.', 'danger')
            return redirect(url_for('login'))
    return render_template('add_password.html', form=form)


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
    cursor.execute("""UPDATE user SET password=%s, confirmed_on=NOW(),
                    email_confirmed=1 WHERE email=%s""",
                   (bcrypt.generate_password_hash(password), email))
    mysql.connection.commit()


def create_user(form):
    cursor = mysql.connection.cursor()
    args = (form.role.data, form.first.data.title(), form.last.data.title(),
            current_user.facility_id, form.email.data, form.phone.data,
            form.floor.data, current_user.id, current_user.id)
    cursor.execute("""INSERT INTO user (role, first, last, facility_id, email,
                        phone, floor, create_user, update_user) VALUES
                        (%s, %s, %s, %s, %s, %s, %s, %s, %s)""", args)
    mysql.connection.commit()
    return cursor.lastrowid


def create_notification(form, userId):
    if form.role.data in {'Nurse Practicioner', 'Medical Doctor'}:
        cursor = mysql.connection.cursor()
        args = (form.email.data, form.phone.data, userId, current_user.id,
                current_user.id)
        cursor.execute("""INSERT INTO notification (email, phone, user_id,
                            create_user, update_user) VALUES
                            (%s, %s, %s, %s, %s)""", args)
        mysql.connection.commit()


def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and \
        ref_url.netloc == test_url.netloc


class User():
    def __init__(self, email=None, id=None):
        cursor = mysql.connection.cursor()
        cursor.execute("""SELECT id, role, first, last, facility_id, email,
                floor, email_confirmed, active FROM USER
                WHERE (id=%s or email=%s)""", (id, email))
        self.id, self.role, self.first, self.last, self.facility_id,\
            self.email, self.floor, self.confirmed,\
            self.active = cursor.fetchall()[0]

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
