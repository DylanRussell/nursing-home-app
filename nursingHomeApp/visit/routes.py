from __future__ import absolute_import
from nursingHomeApp import app, mysql
from flask import render_template, flash, request, jsonify
from nursingHomeApp.views.common import login_required
from flask_login import current_user
import datetime


SELECT_FLOOR_CNT = "SELECT num_floors FROM facility WHERE id=1"
SELECT_CLINICIANS = """SELECT CONCAT_WS(' ', first, last) FROM user WHERE role
IN ('Physician', 'Nurse Practitioner') ORDER BY first, last"""
SELECT_PATIENTS = """SELECT p.id, CONCAT_WS(' ', p.first, p.last), s.status,
p.room_number,CONCAT_WS(' ', n.first, n.last), CONCAT_WS(' ', d.first, d.last),
p.admittance_date, p.has_medicaid FROM patient p
JOIN patient_status s ON s.id=p.status
LEFT JOIN user n ON n.id=p.np_id
JOIN user d ON d.id=p.md_id WHERE p.status != 3"""
SELECT_LAST_VISIT = """SELECT visit_date FROM visit
WHERE patient_id=%s ORDER BY visit_date desc LIMIT 1"""
SELECT_LAST_DR_VISIT = """SELECT visit_date FROM visit WHERE patient_id=%s
AND visit_done_by_doctor=1 ORDER BY visit_date desc LIMIT 1"""
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
    admit date, last visit date, last visit by doctor date for all active
    patients"""
    patients = []
    q = SELECT_PATIENTS
    if clinicianId:
        q += " AND (p.NP_ID=%s OR p.MD_ID=%s)" % (clinicianId, clinicianId)
    cursor = mysql.connection.cursor()
    cursor.execute(q)
    for p in cursor.fetchall():
        pId = p[0]
        for visit in [SELECT_LAST_VISIT, SELECT_LAST_DR_VISIT]:
            if cursor.execute(visit, (pId,)):
                p += cursor.fetchone()
            else:
                p += (None,)
        patients.append(p)
    return patients


def format_patient_info(patients, forClinician=False):
    rows = []
    for pId, name, status, rm, np, md, admit, mcaid, lv, lvByDr in patients:
        if not lv:
            lvDesc = 'None'
        elif lvByDr == lv:
            lvDesc = lv.strftime('%m/%d/%Y, Physician')
        else:
            lvDesc = lv.strftime('%m/%d/%Y, APRN')
        nv, nvByDr = get_next_visit_dates(status, lv, lvByDr, admit, mcaid)
        nvDesc, nvByDrDesc = (dt.strftime('%m/%d/%Y') for dt in (nv, nvByDr))
        # number of days until due date
        nvDays = (nv - datetime.datetime.today().date()).days
        nvByDrDays = (nvByDr - datetime.datetime.today().date()).days
        if forClinician:  # clinician sees stripped down view
            rows.append([name, rm, lvDesc, nvDesc, nvDays, nvByDrDesc, nvByDrDays])
        else:
            rows.append([pId, name, status, rm, np, md, lvDesc, nvDesc, nvDays, nvByDrDesc, nvByDrDays])
    return sorted(rows, key=lambda x: x[-3])


def get_next_visit_dates(status, lv, lvByDr, admit, mcaid):
    """Returns: Next patient visit, next patient visit that must be
    administered by a doctor"""
    lv = lv or admit
    if status == 'Long Term Care':
        nv = lv + datetime.timedelta(days=60)
        nvByDr = lvByDr + datetime.timedelta(days=120 if not mcaid else 365)
    else:
        nv = lv + datetime.timedelta(days=30)
        if not lvByDr or lv > lvByDr:
            nvByDr = lv + datetime.timedelta(days=30)
        else:
            nvByDr = lv + datetime.timedelta(days=60)
    return nv, nvByDr


@app.route("/submit/upcoming", methods=['POST'])
@login_required('upcoming_for_clerk_submit')
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
