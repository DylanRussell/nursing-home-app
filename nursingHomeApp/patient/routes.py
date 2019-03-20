from __future__ import absolute_import
import csv
import StringIO
from flask import render_template, flash, redirect, url_for, request,\
    make_response
from flask_login import current_user
from nursingHomeApp import mysql
from nursingHomeApp.common_queries import get_num_floors, get_user_facility_id
from nursingHomeApp.patient import bp
from nursingHomeApp.patient.forms import AddPatientForm, UpdatePatientForm
from nursingHomeApp.registration.routes import login_required



PATIENT_INSERT = """INSERT INTO patient (first, last, room_number, status,
md_id, np_id, admittance_date, create_user, has_medicaid,
consecutive_skilled_visits, facility_id)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
VISIT_INSERT = """INSERT INTO VISIT (patient_id, visit_date,
visit_done_by_doctor, create_user, note_received, orders_signed)
VALUES (%s, %s, %s, %s, %s, %s)"""
SELECT_PATIENT = """SELECT first, last, room_number, status, md_id, np_id,
has_medicaid, consecutive_skilled_visits FROM patient p WHERE id=%s"""
UPDATE_PATIENT = """UPDATE patient SET first=%s, last=%s, room_number=%s,
status=%s, md_id=%s, np_id=%s, update_user=%s, has_medicaid=%s,
consecutive_skilled_visits=%s WHERE id=%s"""
SELECT_USER_ID = "SELECT id FROM USER WHERE CONCAT_WS(' ', first, last)=%s"
SELECT_PATIENT_STATUS = "SELECT id FROM patient_status WHERE status=%s"


@bp.route('/update/patient/<id>', methods=['GET', 'POST'])
@login_required('update_patient')
def update_patient(id):
    """This route is only available to Clerk or Clerk Manager or Facility Admin
    or Site Admin users. From the view the user can update an existing patient's 
    data.

    The UpdatePatientForm fields are populated with a patient's data by default. 

    The patient chosen has the id that is passed into the route as an argument.

    The user can then update any field(s), and any field not updated will
    still be passed back to the route for use in an UPDATE statement.

    The route doesn't track which field (if any) was updated, it will execute 
    the UPDATE statement on all fields, using the form's fields as arguments,
    regardless of if they were changed by the user.

    If nothing changed the field will UPDATE to itself, no harm done.

    See the UpdatePatientForm in forms.py and the update_patient_data function
    below for more details.
    """
    form = UpdatePatientForm()
    form.patientId.data = id
    if form.validate_on_submit():
        update_patient_data(form)
        flash('Your Changes Have Been saved', 'success')
    set_patient_defaults(form)
    return render_template('patient/update_patient.html', form=form)


def set_patient_defaults(form):
    """Sets the fields in the UpdatePatient form equal to their values in the 
    patient table.
    """
    cursor = mysql.connection.cursor()
    cursor.execute(SELECT_PATIENT, (form.patientId.data,))
    (form.first.default, form.last.default, form.room.default,
     form.status.default, form.md.default, form.np.default,
     form.medicaid.default, form.skilledVisits.default) = cursor.fetchone()
    form.process()


def update_patient_data(form):
    """Updates a row in the patient table to be equal to the values of the user
    submitted & validated UpdatePatient form.
    """
    skilledVisits = 0 if form.status.data != 2 else form.skilledVisits.data
    args = (form.first.data.title(), form.last.data.title(), form.room.data,
            form.status.data, form.md.data, form.np.data, current_user.id,
            form.medicaid.data, skilledVisits, form.patientId.data)
    cursor = mysql.connection.cursor()
    cursor.execute(UPDATE_PATIENT, args)
    mysql.connection.commit()


@bp.route('/view/patient', methods=['GET', 'POST'])
@login_required('view_patients')
def view_patients():
    """Displays a table of patients to the user, which the user may download
    by clicking a download button which sends a POST request to this route

    Every user role has access to this route after logging in. However, which 
    patients are displayed in the table will vary by role -- see the
    get_patients function below for details.
    """
    patients = get_patients()
    if request.method == 'POST':
        header = [('First Name', 'Last Name', 'Room', 'Status', 'MD Name',
                   'NP Name', 'Has Medicaid', 'Facility Name')]
        # remove last field from patient row which is the patient_id field
        rows = header + [patient[:-1] for patient in patients]
        # in memory file object
        output = StringIO.StringIO()
        writer = csv.writer(output)
        writer.writerows(rows)
        response = make_response(output.getvalue())
        response.headers["Content-Disposition"] = "attachment;filename=patients.csv"
        response.headers["Content-type"] = "text/csv"
        return response
    return render_template('patient/view_patients.html', patients=patients,
                           numFloors=get_num_floors())


@bp.route('/add/patient', methods=['GET', 'POST'])
@login_required('add_patient')
def add_patient():
    """This view is only accessible to user's with the role Facility Admin,
    Clerk, or Clerk Manager. From this view the logged in user can add a patient
    by filling out a form. 

    Sometimes a patient being added has already been at the facility for some
    time and has already been visited by a doctor or nurse. Because future visits 
    are determined in part by when the last doctor visit occured and when the 
    last visit (regardless of who administered it) occured, the user is asked to
    fill in those dates if applicable.

    Every patient in the facility must have at some point been a new
    admission, and therefore had the status of New Admission / Skilled Care.
    This status requires 3 visits within 30 days of eachother (the first of
    which must be done by a doctor). Also at any point the facility may decide a 
    patient needs more frequent visits (and more doctor visits) and give a 
    patient this status, restarting the visit requirement this status has.

    If a patient is being added with the status Long Term Care, they must have
    been in New Admission at some point in the past and therefore visited by a doctor at 
    some point in the past, so the visit fields described above become required.

    This is important to do because the next visit calculation for patients
    in Long Term Care assumes that a doctor visit has occured in the past (see
    the get_next_visit_dates function in the visit module for more info).

    See the AddPatientForm class defined forms.py & associated form validators
    found in validators.py, to see which fields the user is asked to fill in,
    and what validations are done.

    See the create_patient function below to see a patient inserted into the
    database after form validation. Visits are also inserted if applicable.
    """
    form = AddPatientForm()
    if form.validate_on_submit():
        create_patient(form)
        flash('Successfully Added Patient', 'success')
        return redirect(url_for('patient.add_patient'))
    return render_template('patient/add_patient.html', form=form)


def create_patient(form):
    """INSERTS a row into the patient table, and 0, 1, or 2 visits into the 
    visit table, depending on if the user filled out the past/prior visit date 
    fields in the form
    Args:
        form: filled in & validated AddPatient wtform object
    """
    # the skilledVisits field is used to populate the consecutive_skilled_visits
    # column in the patient table, but it should be 0 if the patient doesn't
    # have the New Admission / Skilled Visit status (AKA 2).
    skilledVisits = 0 if form.status.data != 2 else form.skilledVisits.data
    cursor = mysql.connection.cursor()
    # insert a row into the patient table. patient belongs to logged in users facility
    args = (form.first.data, form.last.data, form.room.data, form.status.data,
            form.md.data, form.np.data, form.admittance.data, current_user.id,
            form.medicaid.data, skilledVisits, get_user_facility_id())
    cursor.execute(PATIENT_INSERT, args)
    patient_id = cursor.lastrowid
    # if the patient has been visited before, insert a record into the visit table
    if form.lastVisit.data:
        # was the visit administered by a doctor
        doctor_visit = int(form.lastVisit.data == form.priorVisit.data)
        args = (patient_id, form.lastVisit.data, doctor_visit, current_user.id, 1, 1)
        cursor.execute(VISIT_INSERT, args)
    # if the last doctor visit (AKA form.priorVisit) is different from the 
    # last overall visit (AKA form.lastVisit) which was just inserted, 
    # then insert an additional record into the visit table
    if form.priorVisit.data and form.priorVisit.data != form.lastVisit.data:
        args = (patient_id, form.priorVisit.data, 1, current_user.id, 1, 1)
        cursor.execute(VISIT_INSERT, args)
    mysql.connection.commit()


def get_patients():
    """Returns a list of tuples containing patient information for use in the
    view_patients route/view. If the logged in user is a Nurse or Doctor,
    just patients belonging to them are returned.

    If the logged in user is a Clerk or Clerk Manager or Facility Admin, only
    patients belonging to the facility the logged in user belongs to are
    returned.

    If the logged in user is a Site Admin, all patients are returned.
    
    In all cases patients with a status of 3 (discharged) are not returned.
    """
    query = """SELECT p.first, p.last, p.room_number, s.status,
    CONCAT_WS(' ', m.first, m.last), CONCAT_WS(' ', n.first, n.last),
    if(p.has_medicaid, 'yes', 'no'), f.name, p.id FROM patient p
    LEFT JOIN user m ON m.id=p.md_id
    LEFT JOIN user n ON n.id=p.np_id
    JOIN facility f ON p.facility_id=f.id
    JOIN patient_status s ON s.id=p.status WHERE p.status != 3"""
    if current_user.role == 'Nurse Practitioner':
        query += ' AND n.id=%s' % current_user.id
    elif current_user.role == 'Physician':
        query += ' AND m.id=%s' % current_user.id
    elif current_user.role != 'Site Admin':
        query += """ AND p.facility_id IN (SELECT facility_id FROM 
                 user_to_facility WHERE user_id=%s)""" % current_user.id
    cursor = mysql.connection.cursor()
    cursor.execute(query)
    return cursor.fetchall()


# the below code is currently depreciated. the idea was to give user a way to
# load in a bunch of patients at once via file upload (instead of 1 at a time, 
# which is the only way it can be done now)

# it was too complicated for the users to figure out how to use, and also was
# complicated to validate that the file contained all the information needed

# from nursingHomeApp.patient.forms import LoadPatientsForm

# @bp.route('/load/patient/format')
# @login_required('load_patient_format')
# def load_patient_format():
#     return render_template('patient/load_patient_format.html')


# @bp.route('/load/patient', methods=['GET', 'POST'])
# @login_required('load_patient')
# def load_patient():
#     form = LoadPatientsForm()
#     if form.validate_on_submit():
#         load_patient_data(form)
#         flash('Patient data successfully loaded in.', 'success')
#     return render_template('patient/load_patient.html', form=form)


# def load_patient_data(form):
#     cursor = mysql.connection.cursor()
#     reader = csv.reader(form.upload.data, skipinitialspace=True)
#     next(reader)
#     for row in reader:
#         if not any(row):
#             continue
#         first, last, room, state, md, np, lv, lvByDr, admit, medicaid = row
#         medicaid = int(medicaid.lower().strip() == 'yes')
#         first, last, md, np, state = [clean_text(x) for x in (first, last, md, np, state)]
#         lv, lvByDr, admit = [x or None for x in (lv, lvByDr, admit)]
#         state, md, np = get_status_int(state), get_user_id(md), get_user_id(np)
#         cursor.execute(PATIENT_INSERT, (first, last, room, state, md, np,
#                                         admit, current_user.id, medicaid))
#         pId = cursor.lastrowid
#         if lvByDr:
#             cursor.execute(VISIT_INSERT, (pId, lvByDr, 1, current_user.id, 1, 1))
#         if lv and lvByDr != lv:
#             cursor.execute(VISIT_INSERT, (pId, lv, 0, current_user.id, 1, 1))
#     mysql.connection.commit()


# def clean_text(val):
#     return " ".join(val.split()).title() or None


# def get_status_int(status):
#     cursor = mysql.connection.cursor()
#     cursor.execute(SELECT_PATIENT_STATUS, (status,))
#     return cursor.fetchall()[0][0]


# def get_user_id(un):
#     if un:
#         cursor = mysql.connection.cursor()
#         cursor.execute(SELECT_USER_ID, (un,))
#         return cursor.fetchall()[0][0]
