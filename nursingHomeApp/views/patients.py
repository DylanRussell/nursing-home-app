from __future__ import absolute_import
from nursingHomeApp import app, mysql
from flask import render_template, flash, redirect, url_for, request, make_response
from nursingHomeApp.views.common import login_required
from flask_login import current_user
from nursingHomeApp.forms.patient_forms import AddPatientForm, UpdatePatientForm, LoadPatientsForm
import StringIO, csv


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
    if form.validate_on_submit():
        update_patient_data(form, id)
        flash('Your Changes Have Been saved', 'success')
    set_patient_defaults(form, id)
    return render_template('update_patient.html', form=form)


def set_patient_defaults(form, patientId):
    cursor = mysql.connection.cursor()
    cursor.execute("""SELECT p.first, p.last, p.room_number, p.status, p.md_id,
        p.np_id FROM patient p WHERE id=%s""", (patientId,))
    (form.first.default, form.last.default, form.room.default,
        form.status.default, form.md.default,
        form.np.default) = cursor.fetchone()
    form.process()


def update_patient_data(form, patientId):
    args = (form.first.data.title(), form.last.data.title(), form.room.data,
            form.status.data, form.md.data,
            form.np.data, current_user.id, patientId)
    cursor = mysql.connection.cursor()
    cursor.execute("""UPDATE patient SET first=%s, last=%s, room_number=%s,
        status=%s, md_id=%s, np_id=%s, update_user=%s WHERE id=%s""", args)
    mysql.connection.commit()


@app.route('/view/patient', defaults={'floor': None}, methods=['GET', 'POST'])
@app.route('/view/patient/<int:floor>', methods=['GET', 'POST'])
@login_required('view_patients')
def view_patients(floor):
    if request.method == 'POST':
        si = StringIO.StringIO()
        cw = csv.writer(si)
        cw.writerows(get_patients_for_csv(floor))
        out = make_response(si.getvalue())
        out.headers["Content-Disposition"] = "attachment; filename=patients.csv"
        out.headers["Content-type"] = "text/csv"
        return out
    return render_template('view_patients.html', patients=get_patients(floor), floor=floor, numFloors=get_num_floors())


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
    if form.lastMDVisit.data:
        cursor.execute("""INSERT INTO visit (facility_id, patient_id, user_id,
            visit_date, patient_status, create_user, update_user) VALUES
            (%s, %s, %s, %s, %s, %s, %s)""", (current_user.facility_id,
                                              patientId, form.md.data,
                                              form.lastMDVisit.data, form.status.data,
                                              current_user.id, current_user.id))
    if form.lastNPVisit.data:
        cursor.execute("""INSERT INTO visit (facility_id, patient_id, user_id,
            visit_date, patient_status, create_user, update_user) VALUES
            (%s, %s, %s, %s, %s, %s, %s)""", (current_user.facility_id,
                                              patientId, form.np.data,
                                              form.lastNPVisit.data, form.status.data,
                                              current_user.id, current_user.id))
    mysql.connection.commit()


def create_patient(form):
    cursor = mysql.connection.cursor()
    cursor.execute("""INSERT INTO patient (facility_id, first, last,
        room_number, status, last_visit_by_md, last_visit_by_np, np_id, md_id,
        create_user, update_user) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s,
        %s, %s)""", (current_user.facility_id, form.first.data, form.last.data,
                     form.room.data, form.status.data, form.lastMDVisit.data,
                     form.lastNPVisit.data, form.np.data, form.md.data,
                     current_user.id, current_user.id))
    mysql.connection.commit()
    return cursor.lastrowid


def get_patients(floor):
    q = """SELECT p.first, p.last, p.room_number, s.status, p.last_visit_by_md,
    p.last_visit_by_np, CONCAT_WS(' ', m.first, m.last),
    CONCAT_WS(' ', n.first, n.last), p.id FROM patient p LEFT JOIN
    user m ON m.id=p.md_id LEFT JOIN user n ON n.id=p.np_id
    JOIN patient_status s ON s.id=p.status WHERE 1=1"""
    if current_user.role == 'Nurse Practitioner':
        q += ' AND n.id=%s' % current_user.id
    elif current_user.role == 'Medical Doctor':
        q += ' AND m.id=%s' % current_user.id
    if floor:
        q += " AND room_number like '{}%'".format(floor)
    cursor = mysql.connection.cursor()
    cursor.execute(q)
    return cursor.fetchall()


def get_num_floors():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT num_floors FROM facility WHERE id=%s", (current_user.facility_id,))
    return cursor.fetchall()[0][0]


def get_patients_for_csv(floor):
    return (('First Name', 'Last Name', 'Room', 'Status', 'Last Visit by MD',
             'Last Visit by NP', 'MD Name', 'NP Name'),) + get_patients(floor)


def load_patient_data(form):
    cursor = mysql.connection.cursor()
    reader = csv.reader(form.upload.data, skipinitialspace=True)
    next(reader)
    for row in reader:
        first, last, room, status, md, mdV, np, npV, admittance = row
        first, last, md, np, status = [' '.join(x for x in val.split(' ') if x).title() or None
                                        for val in (first, last, md, np, status)]
        mdV, npV, admittance = [x.strip() or None for x in (mdV, npV, admittance)]
        status = get_status_int(status)
        md, np = [get_user_id(x) for x in (md, np)]
        fields = (first, last, room, status, md, mdV, np, npV, admittance, current_user.id, current_user.id, current_user.facility_id)
        cursor.execute("""INSERT INTO patient (first, last, room_number,
            status, md_id, last_visit_by_md, np_id, last_visit_by_np,
            admittance_date, create_user, update_user, facility_id) VALUES
            (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""", fields)
    mysql.connection.commit()


def get_status_int(status):
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT id FROM patient_status WHERE status=%s", (status,))
    return cursor.fetchall()[0][0]


def get_user_id(userName):
    if userName:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT id FROM USER WHERE CONCAT_WS(' ', first, last)=%s", (userName,))
        return cursor.fetchall()[0][0]
