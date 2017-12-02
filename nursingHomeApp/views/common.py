from __future__ import absolute_import
from nursingHomeApp import mysql
from functools import wraps
from flask_login import current_user
from flask import flash, redirect, url_for


def login_required(fn):
    def wrapper(f):
        @wraps(f)
        def decorated_view(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('You must be logged in to view this page.', 'warning')
                return redirect(url_for('login'))
            role = current_user.role
            cursor = mysql.connection.cursor()
            if not cursor.execute("""SELECT * FROM user_role WHERE
                    (select role_value FROM user_role WHERE role=%s) &
                    (select bit from permission where name=%s)""", (role, fn)):
                flash('You are not authorized to view this page.', 'danger')
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_view
    return wrapper
