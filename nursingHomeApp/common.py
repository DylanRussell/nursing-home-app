from __future__ import absolute_import
from nursingHomeApp import mysql
from functools import wraps
from flask_login import current_user
from flask import flash, redirect, url_for, request, jsonify


SELECT_FLOOR_CNT = """SELECT num_floors FROM facility WHERE id IN
(SELECT facility_id FROM user_to_facility WHERE user_id=%s)"""
SELECT_FACILITY_ID = "SELECT facility_id FROM user_to_facility WHERE user_id=%s"


def login_required(fn):
    def wrapper(f):
        @wraps(f)
        def decorated_view(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('You must be logged in to view this page.', 'warning')
                if request.is_xhr:
                    return jsonify({'url': url_for('registration.login')})
                return redirect(url_for('registration.login'))
            role = current_user.role
            cursor = mysql.connection.cursor()
            if not cursor.execute("""SELECT * FROM user_role WHERE
                    (select role_value FROM user_role WHERE role=%s) &
                    (select bit from permission where name=%s)""", (role, fn)):
                flash('You are not authorized to view this page.', 'danger')
                if request.is_xhr:
                    return jsonify({'url': url_for('registration.login')})
                return redirect(url_for('registration.login'))
            return f(*args, **kwargs)
        return decorated_view
    return wrapper


def get_num_floors():
    # a user may not be associated with a facility
    # in which case None is returned
    cursor = mysql.connection.cursor()
    if cursor.execute(SELECT_FLOOR_CNT, (current_user.id, )):
        return cursor.fetchall()[0][0]


def get_user_facility_id():
    cursor = mysql.connection.cursor()
    cursor.execute(SELECT_FACILITY_ID, (current_user.id,))
    return cursor.fetchall()[0][0]
