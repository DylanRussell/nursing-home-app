from __future__ import absolute_import
from nursingHomeApp import app, mysql
from flask import render_template, flash, request, jsonify
from nursingHomeApp.views.common import login_required
from flask_login import current_user
import datetime


SELECT_FLOOR_CNT = "SELECT num_floors FROM facility WHERE id=1"
SELECT_CLINICIANS = """SELECT CONCAT_WS(' ', first, last) FROM user WHERE role
IN ('Physician', 'Nurse Practitioner') ORDER BY first, last"""
SELECT_PATIENTS = """SELECT p.id, CONCAT_WS(' ', p.first, p.last), p.status,
p.room_number,CONCAT_WS(' ', n.first, n.last), CONCAT_WS(' ', d.first, d.last),
p.admittance_date FROM patient p LEFT JOIN user n ON n.id=p.np_id
JOIN user d ON d.id=p.md_id WHERE p.status != 3"""
SELECT_LAST_VISIT = """SELECT visit_date, visit_done_by_doctor FROM visit
WHERE patient_id=%s ORDER BY visit_date desc LIMIT 1"""
SELECT_SECOND_TO_LAST_VISIT = SELECT_LAST_VISIT + ", 1"
INSERT_VISIT = """INSERT INTO VISIT (patient_id, visit_done_by_doctor,
visit_date, create_user) VALUES (%s, %s, %s, %s)"""
SELECT_VISIT_CNT = "SELECT * FROM VISIT WHERE patient_id=%s"
PATIENT_MOVED_2_LONG_TERM_CARE = "UPDATE patient SET status=1 WHERE id=%s"


@app.route("/upcoming/clinician", methods=['GET'])
@login_required('upcoming_for_clinician')
def upcoming_for_clinician():
    rows = format_patient_info(get_patient_info(current_user.id), True)
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    return render_template('upcoming_for_clinician.html', patients=rows,
                           today=today)


@app.route("/upcoming", methods=['GET'])
@login_required('upcoming_for_clerk')
def upcoming_for_clerk():
    rows = format_patient_info(get_patient_info())
    numFloors = get_num_floors()
    clinicians = get_clinicians()
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    return render_template('upcoming_for_clerk.html', numFloors=numFloors,
                           clinicians=clinicians, patients=rows, today=today)


def get_num_floors():
    cursor = mysql.connection.cursor()
    cursor.execute(SELECT_FLOOR_CNT)
    return cursor.fetchall()[0][0]


def get_clinicians():
    cursor = mysql.connection.cursor()
    cursor.execute(SELECT_CLINICIANS)
    return [x[0] for x in cursor.fetchall()]


def get_patient_info(clinicianId=None):
    """Gets patients id, name, status, room no, nurse's name, doctor's name,
    admitdate, last visit date, last visit by, second to last visit date,
    second to last visit by for all active patients"""
    patients = []
    q = SELECT_PATIENTS
    if clinicianId:
        q += " AND (p.NP_ID=%s OR p.MD_ID=%s)" % (clinicianId, clinicianId)
    cursor = mysql.connection.cursor()
    cursor.execute(q)
    for p in cursor.fetchall():
        pId = p[0]
        for visit in [SELECT_LAST_VISIT, SELECT_SECOND_TO_LAST_VISIT]:
            if cursor.execute(visit, (pId,)):
                p += cursor.fetchone()
            else:
                p += (None, None)
        patients.append(p)
    return patients


def format_patient_info(patients, forClinician=False):
    rows = []
    for pId, pName, status, rm, np, md, admit, lv, lvBy, pv, pvBy in patients:
        if not lv:
            lvDesc = 'None'
        elif lvBy:
            lvDesc = lv.strftime('%b %d, Physician')
        else:
            lvDesc = lv.strftime('%b %d, APRN')
        nv, nvBy = get_next_visit_date(status, lv, lvBy, pv, pvBy, admit)
        nvDesc = nv.strftime('%A, %b %d ') + nvBy
        days = (nv - datetime.datetime.today().date()).days
        if forClinician:  # clinician sees stripped down view
            rows.append([pName, rm, lvDesc, nvDesc, days])
        else:
            rows.append([pId, pName, status, rm, np, md, lvDesc, nvDesc, days])
    return sorted(rows, key=lambda x: x[-1])


def get_next_visit_date(pStatus, lv, lvBy, pv, pvBy, admit):
    """Returns: (The date a patient must be seen by,
    who must administer the vist)"""
    if pStatus == 1:  # long term care
        nv = lv + datetime.timedelta(days=60)
        nvBy = 'APRN/Physician' if lvBy else 'Physician'
    else:
        lv = lv or admit
        nv = lv + datetime.timedelta(days=30)
        nvBy = 'APRN/Physician' if (lvBy or pvBy) else 'Physician'
    return nv, nvBy


@app.route("/submit/upcoming", methods=['POST'])
def upcoming_for_clerk_submit():
    errors, visits = {}, []
    for key in request.form:
        if key.endswith('_visited'):
            pId = key.split('_')[0]
            visitBy = bool(request.form.get('%s_visited_by_md' % pId))
            visitDate = request.form.get("%s_visited_on" % pId)
            pStatus = request.form.get("%s_status" % pId)
            visits.append([pId, pStatus, visitDate, visitBy])
            if not visitDate:
                errors[visitDate] = 'This field is required'
    if errors or not visits:
        return jsonify(errors)
    # add visits
    curUser = current_user.id
    cursor = mysql.connection.cursor()
    for pId, pStatus, visitDate, visitBy in visits:
        cursor.execute(INSERT_VISIT, (pId, visitBy, visitDate, curUser))
        if pStatus == '4' and cursor.execute(SELECT_VISIT_CNT, (pId,)) > 2:
            cursor.execute(PATIENT_MOVED_2_LONG_TERM_CARE, (pId,))
    mysql.connection.commit()
    flash('Successfully added %s patient visits!' % len(visits), 'success')
    return jsonify({})
