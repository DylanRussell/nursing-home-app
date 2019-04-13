from functools import wraps
from urllib.parse import urlparse, urljoin
from flask import render_template, request, url_for, flash, redirect, current_app, jsonify
from flask_login import logout_user, login_user, current_user
from flask_mail import Message
from itsdangerous import URLSafeTimedSerializer, BadSignature
from nursingHomeApp import mysql, lm, mail, bcrypt
from nursingHomeApp.registration import bp
from nursingHomeApp.registration.forms import LoginForm, AddUserForm,\
    PasswordForm, EmailForm

# map of user role, to list of user roles that role is allowed to add
# when adding a user
CAN_ADD = {
    'Clerk': 
        ['Physician', 'Nurse Practitioner'],
    'Facility Admin': 
        ['Facility Admin', 'Clerk Manager', 'Clerk', 'Physician',
         'Nurse Practitioner'],
    'Clerk Manager': 
        ['Clerk', 'Physician', 'Nurse Practitioner'],
    'Site Admin': 
        ['Facility Admin', 'Clerk Manager', 'Clerk', 'Physician',
         'Nurse Practitioner', 'Site Admin']
    }
# map of user role, to list of user roles that role is allowed to set inactive
CAN_REMOVE = {
    'Clerk': 
        [],
    'Facility Admin': 
        ['Facility Admin', 'Clerk Manager', 'Clerk', 'Physician',
         'Nurse Practitioner'],
    'Clerk Manager': 
        ['Clerk'],
    'Site Admin': 
        ['Facility Admin', 'Clerk Manager', 'Clerk', 'Physician',
         'Nurse Practitioner', 'Site Admin']
    }
# map of user role, to list of user roles that role is allowed to view
# on the 'view_users' page
CAN_VIEW = {
    'Clerk': 
        ['Nurse Practitioner', 'Physician'],
    'Facility Admin': 
        ['Facility Admin', 'Clerk Manager', 'Clerk', 'Physician',
         'Nurse Practitioner'],
    'Clerk Manager': 
        ['Clerk', 'Physician', 'Nurse Practitioner'],
    'Site Admin': 
        ['Facility Admin', 'Clerk Manager', 'Clerk', 'Physician',
         'Nurse Practitioner', 'Site Admin']
    }

UPDATE_USERS_PW = """UPDATE user SET password=%s, confirmed_on=NOW(),
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


def login_required(view_name):
    """View decorator for views requiring login"""
    def wrapper(view):
        """wraps view functions"""
        @wraps(view)
        def decorated_view(*args, **kwargs):
            """First check if user has logged in using flask_login's current_user.is_authenticated.
            Then check if the user's role has permission to view the requested page. 

            If the user passes these checks they are allowed to view the page, otherwise
            they are redirected to the login screen and flashed a message.

            Each view name requiring login is assigned a unique bit in the permission table. 

            Each user role is assigned a bit mask in the user_role table.

            If the bit associated with a view name is set in the bit mask, then
            that user role is allowed access to the view.
            """
            if not current_user.is_authenticated:
                flash('You must be logged in to view this page.', 'warning')
                if request.is_xhr:
                    return jsonify({'url': url_for('registration.login')})
                return redirect(url_for('registration.login'))
            role = current_user.role
            cursor = mysql.connection.cursor()
            if not cursor.execute("""SELECT * FROM user_role WHERE
                    (select role_value FROM user_role WHERE role=%s) &
                    (select bit from permission where name=%s)""", (role, view_name)):
                flash('You are not authorized to view this page.', 'danger')
                if request.is_xhr:
                    return jsonify({'url': url_for('registration.login')})
                return redirect(url_for('registration.login'))
            return view(*args, **kwargs)
        return decorated_view
    return wrapper


@bp.route("/logout")
def logout():
    """Logout a user"""
    logout_user()
    return redirect(url_for('registration.login'))


@bp.app_errorhandler(500)
def page_not_found(e):
    """Page shown to user on error code 500 (internal server error).
    Used for all requests, not just those specific to this Blueprint."""
    return render_template('registration/500.html'), 500


@lm.user_loader
def load_user(id):
    """Used by flask-login to log a user in"""
    return User(id=id)


@bp.route('/forgot', methods=['GET', 'POST'])
def forgot_pword():
    """Any user can get a reset password link sent to them from this page. 
    User supplies their e-mail, and the link is sent if the e-mail is valid.

    The link sent out is the same as the activation link sent to new users
    asking them to 'sign up', which just requires them to select a password.
    """
    form = EmailForm()
    if form.validate_on_submit():
        msg = Message("Reset Your Password", recipients=[form.email.data])
        token = generate_confirmation_token(form.email.data)
        reset_url = url_for('registration.confirm_email', token=token, 
                            _external=True)
        msg.html = render_template('registration/reset_pw_email.html',
                                   url=reset_url)
        mail.send(msg)
        flash('An e-mail has been sent with a link to reset your password.',
              'success')
    return render_template('registration/reset_password.html', form=form)


def login_and_redirect(user):
    """checks if the user has the active flag set. If so logs in the user, and 
    redirects them to where they intended to go, or to the most relevant page 
    given their user role. Otherwise flashes an account inactive message and
    redirects the user to the login page.
    """
    if user.active:
        login_user(user, remember=True)
        flash('You Have Been Logged In!', 'success')
        nex = request.args.get('next')
        if nex and is_safe_url(nex):
            return redirect(nex)
        if user.role in {'Nurse Practitioner', 'Physician'}:
            return redirect(url_for('visit.upcoming_for_clinician'))
        if user.role == 'Site Admin':
            return redirect(url_for('facility.view_facilities'))
        return redirect(url_for('visit.upcoming_for_clerk'))
    flash('The account linked to this email has been deactivated.', 'danger')
    return redirect(url_for('registration.login'))


@bp.route('/', methods=['GET', 'POST'])
def login():
    """Login page. If the user submits a valid email/pw pair, and has the active
    flag set to 1, they are logged in and redirected. Session management is 
    handled by flask_login's login_user method which is called with the user 
    object (defined below in this module).
    """
    form = LoginForm()
    if form.validate_on_submit(): # validates password
        return login_and_redirect(User(email=form.email.data))
    return render_template('registration/login.html', form=form)


@bp.route('/add/user', methods=['GET', 'POST'])
@login_required('add_user')
def add_user():
    """This view has a short form which a user can fill out to add a user.

    Have Permission to Access this view: Clerk Users (Clerk / Clerk Manager), 
    Admin Users (Site Admin / Facility Admin)

    Don't Have Permission: Nurse Parctitioner, Physician

    Each user role can is only allowed to add users with the roles defined
    in the CAN_ADD dictionary. Ex: in the CAN_ADD dictionary 'Clerk' is mapped
    to ['Physician', 'Nurse Practitioner'], meaning they may only add users
    with those roles.

    If the form validates, the user is created in the database (see the 
    create_user function).

    Also, an activation link is sent to the new users e-mail asking them to sign 
    up. 

    If the new user is a Physician or Nurse Practitioner User, they are
    automatically opted into text/e-mail notifications but are given the option
    to opt out by clicking a link included in the invitation email.

    """
    form = AddUserForm()
    form.role.choices = [(x, x) for x in CAN_ADD[current_user.role]]
    # Site Admin must select a facility for the new user they are adding,
    # Otherwise the new user is assumed to belong to the facility of the user who added them
    if current_user.role != 'Site Admin':
        del form.facility
    if form.validate_on_submit():
        userid = create_user(form)
        msg = Message("Sign Up For visitMinder", recipients=[form.email.data])
        token = generate_confirmation_token(form.email.data)
        invitation_url = url_for('registration.confirm_email', token=token, 
                                 _external=True)
        opt_out_url = url_for('notification.opt_out_page', userId=userid,
                              _external=True)
        msg.html = render_template('registration/invitation.html',
                                   url=invitation_url, first=form.first.data, 
                                   last=form.last.data, role=form.role.data,
                                   opt_out_url=opt_out_url)
        mail.send(msg)
        flash('User successfully added!', 'success')
        return redirect(url_for('registration.add_user'))
    return render_template('registration/add_user.html', form=form)


@bp.route('/confirm/<token>', methods=["GET", "POST"])
def confirm_email(token):
    """This route is the endpoint for the activation link emailed to users
    asking them to sign up. This route is public (doesn't require a login).

    Users email is deserialized from token using the app's secret key (see
    confirm_token function below). If token is invalid, user is prevented
    from selecting a password and told their activation link is invalid.

    Otherwise the user is asked to select a password. After selecting a password
    the user is logged in.

    One edge case considered here is if the user has been set inactive by 
    another user. In this case they are allowed to select a password as their
    account may be reactivated later on, but prevented from logging in.
    """
    email = confirm_token(token)
    if not email:
        flash('The activation link is invalid or has expired.', 'danger')
        return redirect(url_for('registration.login'))
    form = PasswordForm()
    user = User(email=email)
    if user.role == 'Physician':
        name = 'Doctor' + ' ' + user.last
    else:
        name = user.first + ' ' + user.last
    if form.validate_on_submit():
        store_users_password(form.pw1.data, user.id)
        flash('Sign up complete!', 'success')
        return login_and_redirect(user)
    return render_template('registration/add_password.html', form=form,
                           name=name)


def generate_confirmation_token(email):
    """Serialize and sign users email using app's secret key.

    Args:
        email: An existing users email address

    Returns:
        token: A token for use in token based authentication"""
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return serializer.dumps(email, salt='invitation')


def confirm_token(token, expiration=604800):
    """Validates token using app's secret key. Token is invalidated after 7 
    days. If token validates, the users deserialized email is returned.
    """
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        return serializer.loads(
            token,
            salt='invitation',
            max_age=expiration
        )
    except BadSignature:
        return False


def store_users_password(password, userid):
    """Stores a user's hashed password, and the datetime of when the password
    was set
    """
    cursor = mysql.connection.cursor()
    args = (bcrypt.generate_password_hash(password), userid, userid)
    cursor.execute(UPDATE_USERS_PW, args)
    mysql.connection.commit()


def create_user(form):
    """Inserts row into user table, and a corresponding row in the notifcations
    table and the user_to_facility mapping table if applicable.

    Args:
        form: The Add User form after having been filled in by a user and 
            validated in the add_user view.

    Returns:
        userid: The new user's ID"""
    cursor = mysql.connection.cursor()
    args = (form.role.data, form.first.data.title(), form.last.data.title(),
            form.email.data, form.phone.data, current_user.id)
    cursor.execute(INSERT_USER, args)
    userid = cursor.lastrowid
    #if the user being added is a Site Admin, they do not belong to facility
    #otherwise the new user belongs to the facility that the user adding them
    #belongs to. if the user adding them is a Site Admin, the Site Admin is
    #asked in the add user form to select a facility for the new user
    if form.role.data != 'Site Admin':
        if current_user.role != 'Site Admin':
            cursor.execute(SELECT_USERS_FACILITY, (current_user.id,))
            facility_id = cursor.fetchall()[0][0]
        else:
            facility_id = form.facility.data
        args = (userid, facility_id, current_user.id, current_user.id)
        cursor.execute(INSERT_USER_TO_FACILITY_MAPPING, args)
        #a user receives notifications only if they are a physician / NP
        if form.role.data in {'Nurse Practitioner', 'Physician'}:
            args = (form.email.data, form.phone.data, userid, current_user.id)
            cursor.execute(INSERT_NOTIFICATION, args)
    mysql.connection.commit()
    return userid


@bp.route('/send/invitation/<userId>', methods=['GET'])
@login_required('send_invitation')
def send_invitation(userId):
    """Resends the invitation e-mail to a user, if an e-mail wasn't sent out 
    during the last day, if the user hasn't signed up (clicked the activation
    link and selected a password) already, and if the user has not been set 
    inactive.

    This route is only accessible from the view_users page. 
    On the view_users page, for each user listed who has not selected a password
    there is a link the logged in user can click which calls this route.

    This route will ultimately redirect the user back to the view_users page.
    """
    cursor = mysql.connection.cursor()
    if cursor.execute(SELECT_NEW_USER, (userId,)):
        email, first, last, role = cursor.fetchall()[0]
        msg = Message("Sign Up For visitMinder", recipients=[email])
        token = generate_confirmation_token(email)
        invitation_url = url_for('registration.confirm_email', token=token, 
                                 _external=True)
        opt_out_url = url_for('notification.opt_out_page', userId=userId,
                              _external=True)
        msg.html = render_template('registration/invitation.html',
                                   url=invitation_url, first=first, last=last,
                                   role=role, opt_out_url=opt_out_url)
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
    """This view display's a table of users. From this view a user can toggle 
    the active state of other users, and resend the activation invitation 
    e-mail.

    Which users appear in the table, and the ability to toggle or trigger the
    activation email varies depending on the logged in user's role.

    Have Permission to Access this view: Clerk Users (Clerk / Clerk Manager), 
    Admin Users (Site Admin / Facility Admin)

    Don't Have Permission: Nurse Parctitioner, Physician
    
    Users with the role Clerk / Clerk Manager / Facility Admin belong to a
    single Facility, and will only see Users belonging to the same facility, 
    so the facility name column is left out of the table for these users.

    The Site Admin on the other hand doesn't belong to any one facility and
    can view all user roles. This user type will see the Facility Name column
    which displays a list of facilities that each User belongs to.

    This mapping of user to facility is generated by the get_user_facilities 
    function below.

    Which users appear in the table is determined by the get_users function 
    below.

    """
    return render_template('registration/view_users.html', users=get_users(),
                           canRemove=CAN_REMOVE,
                           facilities=get_user_facilities())


def get_user_facilities():
    """Returns a map of user id to comma separated string of facility names
    to populate the facility name column on the view_users page.
    """
    facilities = {}
    cursor = mysql.connection.cursor()
    cursor.execute(SELECT_USERS_FACILITIES)
    for userid, facility in cursor.fetchall():
        if userid in facilities:
            facilities[userid] += ', %s' % facility
        else:
            facilities[userid] = facility
    return facilities


def get_users():
    """Fetches a list of users to populate the table in the view_users view.

    Users are constrained in what users they can view based on their role.
    The CAN_VIEW dictionary maps a user role to a list of user roles the
    corresponding key has permission to view.

    Clerk users for example can only view users with the role of Physician or
    Nurse Practitioner. The same mechanism is used to determine which user 
    roles a user is allowed to toggle the active state of -
    see toggle_user view below.

    Returns:
        List of tuples with user information (first name, last name, email, 
        phone, user role, active state, user id, boolean representing whether
        password has been set, last time activation invitation email was sent)
    """
    query = """SELECT first, last, email, phone, role, active, id,
    password IS NOT NULL, invitation_last_sent FROM user WHERE role in
    ('%s')""" % "','".join(CAN_VIEW[current_user.role])
    # only site admin allowed to see users from other facilities
    if current_user.role != 'Site Admin':
        query += """ AND id IN (SELECT user_id FROM user_to_facility
            WHERE facility_id IN (SELECT facility_id FROM user_to_facility
            WHERE user_id=%s))""" % current_user.id
    cursor = mysql.connection.cursor()
    cursor.execute(query)
    return cursor.fetchall()


@bp.route("/toggle/<id>")
@login_required('toggle_user')
def toggle_user(id):
    """Toggles a user's active state. If a user's active state is 0, they cannot 
    login.

    This route is only accessible from the view_users page. On the view_users 
    page, for each user listed, there is a toggle user button which the user 
    can click which calls this route.

    This route will ultimately redirect the user back to the view_users page.
    
    The button to toggle a user's active state is only displayed to the logged 
    in user if they have permission to toggle that user's active state.

    How is permission determined? By looking at the CAN_REMOVE dictionary. 
    The keys are user roles (strings), the values are lists of user roles the 
    corresponding key has permission to toggle the active state of.

    Args:
        id: the id of the user whose active state is to be toggled
    """
    user_role = get_user_role(id)
    if str(current_user.id) == str(id):
        flash('Cannot add or remove yourself.', 'danger')
    elif user_role in CAN_REMOVE[current_user.role]:
        toggle_active_state(id)
        flash('Users status has been updated.', 'success')
    else:
        flash('You are not allowed to add or remove this type of user.',
              'danger')
    return redirect(url_for('registration.view_users'))


def toggle_active_state(userid):
    """Toggles the active state of the given userid"""
    cursor = mysql.connection.cursor()
    cursor.execute(TOGGLE_USER_STATE, (current_user.id, userid))
    mysql.connection.commit()


def get_user_role(userid):
    """Returns the role of the given userid"""
    cursor = mysql.connection.cursor()
    cursor.execute(SELECT_ROLE, (userid,))
    return cursor.fetchone()[0]


def is_safe_url(target):
    """Prevents open redirect"""
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return (test_url.scheme in ('http', 'https') and 
            ref_url.netloc == test_url.netloc)


class User(object):
    """User Class that implements methods/properties per the flask-login
    specification: https://flask-login.readthedocs.io/en/latest/"""
    def __init__(self, email=None, id=None):
        cursor = mysql.connection.cursor()
        cursor.execute(SELECT_USER, (id, email))
        (self.id, self.role, self.first, self.last, self.email, self.floor,
         self.active, self.confirmed) = cursor.fetchall()[0]

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
        return str(self.id)

    def __repr__(self):
        return '<User %r>' % (self.email)
