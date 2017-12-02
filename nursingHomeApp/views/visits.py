from __future__ import absolute_import
from nursingHomeApp import app, mysql
from flask import render_template, flash, request, jsonify
from nursingHomeApp.views.common import login_required
from flask_login import current_user
import datetime


@app.route("/upcoming/clinician", methods=['GET'])
@login_required('upcoming_for_clinician')
def upcoming_for_clinician():
    patients = get_patient_info(current_user.id)
    rows = format_patient_info(patients, True)
    return render_template('upcoming_for_clinician.html', patients=rows,
                           today=datetime.datetime.now().strftime('%Y-%m-%d'))


@app.route("/upcoming", methods=['GET'])
@login_required('upcoming_for_clerk')
def upcoming_for_clerk():
    patients = get_patient_info()
    rows = format_patient_info(patients)
    return render_template('upcoming_for_clerk.html', numFloors=get_num_floors(), clinicians=get_clinicians(), patients=rows,
                           today=datetime.datetime.now().strftime('%Y-%m-%d'))


def get_num_floors():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT num_floors FROM facility WHERE id=1")
    return cursor.fetchall()[0][0]


def get_clinicians():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT CONCAT_WS(' ', first, last) FROM user WHERE role IN ('Medical Doctor', 'Nurse Practitioner') ORDER BY first, last")
    return [x[0] for x in cursor.fetchall()]


def get_patient_info(clinicianId=None):
    """Gets patients id, name, status, room no, nurse's name, doctor's name,
    admitdate, last visit date, last visit by, second to last visit date,
    second to last visit by for all active patients"""
    patients = []
    q = """SELECT p.id, CONCAT_WS(' ', p.first, p.last), p.status, p.room_number,
    CONCAT_WS(' ', n.first, n.last), CONCAT_WS(' ', d.first, d.last),
    p.admittance_date FROM patient p LEFT JOIN user n ON n.id=p.np_id
    JOIN user d ON d.id=p.md_id WHERE p.status != 3"""
    if clinicianId:
        q += " AND (p.NP_ID=%s OR p.MD_ID=%s)" % (clinicianId, clinicianId)
    lv = "SELECT max(visit_date), visit_done_by_doctor FROM visit WHERE patient_id={0}"
    pv = """SELECT max(visit_date), visit_done_by_doctor FROM visit
    WHERE patient_id={0} AND visit_date != (SELECT max(visit_date) FROM visit
    WHERE patient_id={0})"""
    cursor = mysql.connection.cursor()
    cursor.execute(q)
    for p in cursor.fetchall():
        for visit in [lv, pv]:
            if cursor.execute(visit.format(p[0])):
                p += cursor.fetchone()
            else:
                p += (None, None)
        patients.append(p)
    return patients


def format_patient_info(patients, forClinician=False):
    rows = []
    for pId, pName, pStatus, rm, np, md, admit, lv, lvBy, pv, pvBy in patients:
        if not lv:
            lvDesc = 'None'
        elif lvBy:
            lvDesc = lv.strftime('%A, %b %d Doctor')
        else:
            lvDesc = lv.strftime('%A, %b %d Nurse')
        nv, nvBy = get_next_visit_date(pStatus, lv, lvBy, pv, pvBy, admit)
        nvDesc = nv.strftime('%A, %b %d ') + nvBy
        days = (nv - datetime.datetime.today().date()).days
        if forClinician:  # clinician sees stripped down view
            rows.append([pName, rm, lvDesc, nvDesc, days])
        else:
            rows.append([pId, pName, pStatus, rm, np, md, lvDesc, nvDesc, days])
    return sorted(rows, key=lambda x: x[-1])


def get_next_visit_date(pStatus, lv, lvBy, pv, pvBy, admit):
    """Returns: (The date a patient must be seen by,
    who must administer the vist)"""
    if pStatus == 1:  # long term care
        nv = lv + datetime.timedelta(days=60)
        nvBy = 'Nurse/Doctor' if lvBy else 'Doctor'
    else:
        lv = lv or admit
        nv = lv + datetime.timedelta(days=30)
        nvBy = 'Nurse/Doctor' if (lvBy or pvBy) else 'Doctor'
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
    # queries
    addVisit = """INSERT INTO VISIT (patient_id, visit_done_by_doctor,
    visit_date, create_user) VALUES (%s, %s, %s, {})""".format(current_user.id)
    numVisits = "SELECT * FROM VISIT WHERE patient_id=%s"
    updatePstatus = "UPDATE patient SET status=1 WHERE id=%s"
    # add visits
    cursor = mysql.connection.cursor()
    for pId, pStatus, visitDate, visitBy in visits:
        cursor.execute(addVisit, (pId, visitBy, visitDate))
        if pStatus == '4' and cursor.execute(numVisits, (pId,)) > 2:
            cursor.execute(updatePstatus, (pId,))
    mysql.connection.commit()
    flash('Successfully added %s patient visits!' % len(visits), 'success')
    return jsonify({})
