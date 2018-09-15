from __future__ import absolute_import
from nursingHomeApp import mysql
from flask import render_template, flash, redirect, url_for
from nursingHomeApp.common import login_required, get_user_facility_id
from nursingHomeApp.facility import bp
from flask_login import current_user
from nursingHomeApp.facility.forms import AddFacilityForm, AddCliniciansForm


INSERT_FACILITY = """INSERT INTO facility (name, address, city, state, zipcode,
active, num_floors, create_user) VALUES
(%s, %s, %s, %s, %s, %s, %s, %s)"""
UPDATE_FACILITY = """UPDATE facility SET name=%s, address=%s, city=%s,
state=%s, zipcode=%s, active=%s, num_floors=%s, update_user=%s WHERE id=%s"""
SELECT_FACILITY = """SELECT name, address, city, state, zipcode, active,
num_floors FROM facility WHERE id=%s"""
SELECT_FACILITIES = """SELECT id, name, address, city, state, zipcode, active,
num_floors FROM facility"""
INSERT_USER_TO_FACILITY_MAPPING = """INSERT INTO user_to_facility (user_id,
facility_id, create_user, update_user) VALUES (%s, %s, %s, %s)"""


@bp.route('/update/facility/<id>', methods=['GET', 'POST'])
@login_required('update_facility')
def update_facility(id):
    form = AddFacilityForm()
    form.submit.label.text = 'Update'
    form.facilityId.data = id
    if form.validate_on_submit():
        update_facility_data(form)
        flash('Your Changes Have Been saved', 'success')
    set_facility_defaults(form)
    return render_template('facility/update_facility.html', form=form)


def set_facility_defaults(form):
    cursor = mysql.connection.cursor()
    cursor.execute(SELECT_FACILITY, (form.facilityId.data,))
    (form.name.default, form.address.default, form.city.default,
        form.state.default, form.zipcode.default,
        form.active.default, form.floors.default) = cursor.fetchone()
    form.process()


def update_facility_data(form):
    args = (form.name.data, form.address.data, form.city.data, form.state.data,
            form.zipcode.data, form.active.data, form.floors.data,
            current_user.id, form.facilityId.data)
    cursor = mysql.connection.cursor()
    cursor.execute(UPDATE_FACILITY, args)
    mysql.connection.commit()


@bp.route('/view/facility', methods=['GET'])
@login_required('view_facilities')
def view_facilities():
    return render_template('facility/view_facilities.html', facilities=get_facilities())


def get_facilities():
    cursor = mysql.connection.cursor()
    cursor.execute(SELECT_FACILITIES)
    return cursor.fetchall()


@bp.route('/add/facility', methods=['GET', 'POST'])
@login_required('add_facility')
def add_facility():
    form = AddFacilityForm()
    if form.validate_on_submit():
        create_facility(form)
        flash('Successfully Added Facility', 'success')
        return redirect(url_for('facility.add_facility'))
    return render_template('facility/add_facility.html', form=form)


def create_facility(form):
    args = (form.name.data, form.address.data, form.city.data, form.state.data,
            form.zipcode.data, form.active.data, form.floors.data,
            current_user.id)
    cursor = mysql.connection.cursor()
    cursor.execute(INSERT_FACILITY, args)
    mysql.connection.commit()


@bp.route('/add/clinicians', methods=['GET', 'POST'])
@login_required('add_clinicians')
def add_clinicians():
    form = AddCliniciansForm()
    if form.validate_on_submit():
        add_clinicians_to_facility(form)
        args = (len(form.doctors.data), len(form.nurses.data))
        flash('Added %s doctors and %s nurses to your facility!' % args, 'success')
        return redirect(url_for('facility.add_clinicians'))
    return render_template('facility/add_clinicians.html', form=form)


def add_clinicians_to_facility(form):
    facility = get_user_facility_id()
    cursor = mysql.connection.cursor()
    for userId in form.doctors.data + form.nurses.data:
        args = (userId, facility, current_user.id, current_user.id)
        cursor.execute(INSERT_USER_TO_FACILITY_MAPPING, args)
    mysql.connection.commit()
