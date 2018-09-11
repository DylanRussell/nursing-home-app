from __future__ import absolute_import
from nursingHomeApp import app, mysql
from flask import render_template, flash, redirect, url_for, request,\
    make_response
from nursingHomeApp.views.common import login_required
from flask_login import current_user
from nursingHomeApp.forms.patient_forms import AddPatientForm,\
    UpdatePatientForm, LoadPatientsForm
import StringIO, csv


PATIENT_INSERT = """INSERT INTO patient (first, last, room_number, status,
md_id, np_id, admittance_date, create_user, has_medicaid) VALUES
(%s, %s, %s, %s, %s, %s, %s, %s, %s)"""
VISIT_INSERT = """INSERT INTO VISIT (patient_id, visit_date,
visit_done_by_doctor, create_user) VALUES (%s, %s, %s, %s)"""
SELECT_PATIENT = """SELECT first, last, room_number, status, md_id, np_id,
has_medicaid FROM patient p WHERE id=%s"""
UPDATE_PATIENT = """UPDATE patient SET first=%s, last=%s, room_number=%s,
status=%s, md_id=%s, np_id=%s, update_user=%s, has_medicaid=%s WHERE id=%s"""
SELECT_USER_ID = "SELECT id FROM USER WHERE CONCAT_WS(' ', first, last)=%s"
SELECT_PATIENT_STATUS = "SELECT id FROM patient_status WHERE status=%s"
SELECT_FLOOR_CNT = "SELECT num_floors FROM facility WHERE id=1"


@app.route('/load/patient/format')
@login_required('load_patient_format')
def load_patient_format():
    return render_template('load_patient_format.html')


@app.route('/load/patient', methods=['GET', 'POST'])
@login_required('load_patient')
def load_patient():
    form = LoadPatientsForm()
    if form.validate_on_submit():
        load_patient_data(form)
        flash('Patient data successfully loaded in.', 'success')
    return render_template('load_patient.html', form=form)


@app.route('/update/patient/<id>', methods=['GET', 'POST'])
@login_required('update_patient')
def update_patient(id):
    form = UpdatePatientForm()
    form.patientId.data = id
    if form.validate_on_submit():
        update_patient_data(form)
        flash('Your Changes Have Been saved', 'success')
    set_patient_defaults(form)
    return render_template('update_patient.html', form=form)


def set_patient_defaults(form):
    cursor = mysql.connection.cursor()
    cursor.execute(SELECT_PATIENT, (form.patientId.data,))
    (form.first.default, form.last.default, form.room.default,
        form.status.default, form.md.default,
        form.np.default, form.medicaid.default) = cursor.fetchone()
    form.process()


def update_patient_data(form):
    args = (form.first.data.title(), form.last.data.title(), form.room.data,
            form.status.data, form.md.data, form.np.data, current_user.id,
            form.medicaid.data, form.patientId.data)
    cursor = mysql.connection.cursor()
    cursor.execute(UPDATE_PATIENT, args)
    mysql.connection.commit()


@app.route('/view/patient', methods=['GET', 'POST'])
@login_required('view_patients')
def view_patients():
    if request.method == 'POST':
        si = StringIO.StringIO()
        cw = csv.writer(si)
        cw.writerows(get_patients_for_csv())
        out = make_response(si.getvalue())
        out.headers["Content-Disposition"] = "attachment;filename=patients.csv"
        out.headers["Content-type"] = "text/csv"
        return out
    return render_template('view_patients.html', patients=get_patients(),
                           numFloors=get_num_floors())


@app.route('/add/patient', methods=['GET', 'POST'])
@login_required('add_patient')
def add_patient():
    form = AddPatientForm()
    if form.validate_on_submit():
        patientId = create_patient(form)
        create_prior_visits(form, patientId)
        flash('Successfully Added Patient', 'success')
        return redirect(url_for('add_patient'))
    return render_template('add_patient.html', form=form)


def create_prior_visits(form, patientId):
    cursor = mysql.connection.cursor()
    if form.priorVisit.data and form.priorVisit.data != form.lastVisit.data:
        args = (patientId, form.priorVisit.data, 1, current_user.id)
        cursor.execute(VISIT_INSERT, args)
    if form.lastVisit.data:
        lvBy = int(form.lastVisit.data == form.priorVisit.data)
        args = (patientId, form.lastVisit.data, lvBy, current_user.id)
        cursor.execute(VISIT_INSERT, args)
        # cannot have a prior visit without a last visit so safe to commit here
        mysql.connection.commit()


def create_patient(form):
    cursor = mysql.connection.cursor()
    args = (form.first.data, form.last.data, form.room.data, form.status.data,
            form.md.data, form.np.data, form.admittance.data, current_user.id,
            form.medicaid.data)
    cursor.execute(PATIENT_INSERT, args)
    mysql.connection.commit()
    return cursor.lastrowid


def get_patients():
    q = """SELECT p.first, p.last, p.room_number, s.status,
    CONCAT_WS(' ', m.first, m.last), CONCAT_WS(' ', n.first, n.last),
    p.has_medicaid, p.id FROM patient p LEFT JOIN user m ON m.id=p.md_id
    LEFT JOIN user n ON n.id=p.np_id
    JOIN patient_status s ON s.id=p.status WHERE 1=1"""
    if current_user.role == 'Nurse Practitioner':
        q += ' AND n.id=%s' % current_user.id
    elif current_user.role == 'Physician':
        q += ' AND m.id=%s' % current_user.id
    cursor = mysql.connection.cursor()
    cursor.execute(q)
    return cursor.fetchall()


def get_num_floors():
    cursor = mysql.connection.cursor()
    cursor.execute(SELECT_FLOOR_CNT)
    return cursor.fetchall()[0][0]


def get_patients_for_csv():
    h = [('First Name', 'Last Name', 'Room', 'Status', 'MD Name', 'NP Name', 'Has Medicaid')]
    return h + [x[:-1] for x in get_patients()]


def load_patient_data(form):
    cursor = mysql.connection.cursor()
    reader = csv.reader(form.upload.data, skipinitialspace=True)
    next(reader)
    for row in reader:
        if not any(row):
            continue
        first, last, room, state, md, np, lv, lvByDr, admit, medicaid = row
        medicaid = int(medicaid.lower().strip() == 'yes')
        first, last, md, np, state = [clean_text(x) for x in (first, last, md, np, state)]
        lv, lvByDr, admit = [x or None for x in (lv, lvByDr, admit)]
        state, md, np = get_status_int(state), get_user_id(md), get_user_id(np)
        cursor.execute(PATIENT_INSERT, (first, last, room, state, md, np,
                                        admit, current_user.id, medicaid))
        pId = cursor.lastrowid
        if lvByDr:
            cursor.execute(VISIT_INSERT, (pId, lvByDr, 1, current_user.id))
        if lv and lvByDr != lv:
            cursor.execute(VISIT_INSERT, (pId, lv, 0, current_user.id))
    mysql.connection.commit()


def clean_text(val):
    return " ".join(val.split()).title() or None


def get_status_int(status):
    cursor = mysql.connection.cursor()
    cursor.execute(SELECT_PATIENT_STATUS, (status,))
    return cursor.fetchall()[0][0]


def get_user_id(un):
    if un:
        cursor = mysql.connection.cursor()
        cursor.execute(SELECT_USER_ID, (un,))
        return cursor.fetchall()[0][0]