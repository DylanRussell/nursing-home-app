from __future__ import absolute_import
from flask import render_template, flash, redirect, url_for
from flask_login import current_user
from nursingHomeApp import mysql
from nursingHomeApp.common import login_required, get_user_facility_id
from nursingHomeApp.facility import bp
from nursingHomeApp.facility.forms import AddFacilityForm, AddCliniciansForm


INSERT_FACILITY = """INSERT INTO facility (name, address, city, state, zipcode,
active, num_floors, create_user) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
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
    """Update an existing facility. Only Site Admin user's can access this view.

    This route is similar to the 'update_patient' and 'notifications' routes. 

    Form field defaults are set to what their corresponding values are in the
    facility database table. The id of the facility (primary key in the facility 
    table), is passed into the route as an argument.

    When the user submits a form the corresponding row in the facility table
    is updated. Doesn't track which fields if any were actually updated, will
    execute the UPDATE statement upon form submission, simply setting the fields
    to their existing values if nothing has changed.

    This route is accessible to the Site Admin user from the view_facilities
    page. That route displays a list of facilities in a table view. One of 
    the columns in the table is populated with links (one link per facility/row) 
    pointing to this route.

    See AddFacilityForm in forms.py to see which fields the user can update.
    """
    # re-use add facility form as all fields are the same as in the add facility form.
    form = AddFacilityForm()
    # change form submission button label name
    form.submit.label.text = 'Update'
    # include primary key of the existing facility in the form, for use in the UPDATE statement
    form.facilityId.data = id
    if form.validate_on_submit():
        update_facility_data(form)
        flash('Your Changes Have Been saved', 'success')
    set_facility_defaults(form)
    return render_template('facility/update_facility.html', form=form)


def set_facility_defaults(form):
    """Sets the fields in the AddFacility form equal to their values in the 
    facility table.
    """
    cursor = mysql.connection.cursor()
    cursor.execute(SELECT_FACILITY, (form.facilityId.data,))
    (form.name.default, form.address.default, form.city.default,
     form.state.default, form.zipcode.default,
     form.active.default, form.floors.default) = cursor.fetchone()
    form.process()


def update_facility_data(form):
    """UPDATEs a row in the facility table to be equal to the values of the
    user submitted & validated AddFacilityForm.
    """
    args = (form.name.data, form.address.data, form.city.data, form.state.data,
            form.zipcode.data, form.active.data, form.floors.data,
            current_user.id, form.facilityId.data)
    cursor = mysql.connection.cursor()
    cursor.execute(UPDATE_FACILITY, args)
    mysql.connection.commit()


@bp.route('/view/facility', methods=['GET'])
@login_required('view_facilities')
def view_facilities():
    """This route is only accessible to user's with the role of Site Admin.
    Displays a table of existing facilities to the user. From this route the
    user can reach the update_facility route, which allows them to update
    a single facilities data.
    """
    cursor = mysql.connection.cursor()
    cursor.execute(SELECT_FACILITIES)
    facilities = cursor.fetchall()
    return render_template('facility/view_facilities.html', facilities=facilities)


@bp.route('/add/facility', methods=['GET', 'POST'])
@login_required('add_facility')
def add_facility():
    """This route is only accessible to user's with the role of Site Admin.

    This route contains a simple form the Site Admin user can fill out to
    add (INSERT) a facility.

    Site Admin user's do not belong to a facility, but every other type of user
    does, so at least one facility must exist before other user types are added.
    """
    form = AddFacilityForm()
    if form.validate_on_submit():
        create_facility(form)
        flash('Successfully Added Facility', 'success')
        return redirect(url_for('facility.add_facility'))
    return render_template('facility/add_facility.html', form=form)


def create_facility(form):
    """INSERTs a row into the facility table. Values are supplied by the user
    submitted and validated AddFacilityForm.
    """
    args = (form.name.data, form.address.data, form.city.data, form.state.data,
            form.zipcode.data, form.active.data, form.floors.data,
            current_user.id)
    cursor = mysql.connection.cursor()
    cursor.execute(INSERT_FACILITY, args)
    mysql.connection.commit()


@bp.route('/add/clinicians', methods=['GET', 'POST'])
@login_required('add_clinicians')
def add_clinicians():
    """This route only accessible to user's with the role of Clerk, Clerk Manager,
    or Facility Admin.

    This route allows the logged in user to add existing Physician or Nurse Practitioner
    users to the facility they belong to.

    The form on this page has only 2 fields: a multiselect box with a list of
    existing Physician users who don't already belong to the logged in user's
    facility, and a second multiselect box that is the same but for Nurse users.

    There is a user_to_facility mapping table which maps user_id to facility_id.
    For each physician or nurse selected by the user, a record is INSERTed into
    the table (see the add_clinicians_to_facility function).

    Once a Physician/Nurse belongs to a facility, they appear in the dropdown
    list the clerk sees when adding a patient's Physician/Nurse.

    Physicians/Nurses frequently go between facilities and administer visits,
    so it makes sense for them to belong to many facilities.
    """
    form = AddCliniciansForm()
    if form.validate_on_submit():
        add_clinicians_to_facility(form)
        args = (len(form.doctors.data), len(form.nurses.data))
        flash('Added %s doctors and %s nurses to your facility!' % args, 'success')
        return redirect(url_for('facility.add_clinicians'))
    return render_template('facility/add_clinicians.html', form=form)


def add_clinicians_to_facility(form):
    """For each Nurse/Physician user selected by the logged in user, a row is
    INSERTed into the user_to_facility table which maps users to facility.
    """
    facility_id = get_user_facility_id()
    cursor = mysql.connection.cursor()
    for user_id in form.doctors.data + form.nurses.data:
        args = (user_id, facility_id, current_user.id, current_user.id)
        cursor.execute(INSERT_USER_TO_FACILITY_MAPPING, args)
    mysql.connection.commit()
