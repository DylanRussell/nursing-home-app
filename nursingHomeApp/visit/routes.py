from __future__ import absolute_import
from nursingHomeApp import mysql
from nursingHomeApp.visit import bp
from flask import render_template, flash, request, jsonify, make_response, send_file
from nursingHomeApp.common import login_required, get_num_floors,\
    get_user_facility_id
from flask_login import current_user
import datetime, StringIO, csv, xlsxwriter


SELECT_CLINICIANS = """SELECT CONCAT_WS(' ', u.first, u.last) FROM user u
JOIN user_to_facility f ON f.user_id=u.id WHERE f.facility_id IN
(SELECT facility_id FROM user_to_facility WHERE user_id=%s)
AND role IN ('Physician', 'Nurse Practitioner') ORDER BY first, last"""
SELECT_PATIENTS = """SELECT p.id, CONCAT_WS(' ', p.first, p.last), s.status,
p.room_number,CONCAT_WS(' ', n.first, n.last), CONCAT_WS(' ', d.first, d.last),
p.admittance_date, p.has_medicaid FROM patient p
JOIN patient_status s ON s.id=p.status
LEFT JOIN user n ON n.id=p.np_id
JOIN user d ON d.id=p.md_id WHERE p.status != 3"""
SELECT_LAST_APRN_VISIT = """SELECT max(visit_date) FROM visit
WHERE patient_id=%s AND visit_done_by_doctor=0"""
SELECT_LAST_DR_VISIT = """SELECT max(visit_date) FROM visit
WHERE patient_id=%s AND visit_done_by_doctor=1"""
INSERT_VISIT = """INSERT INTO VISIT (patient_id, visit_done_by_doctor,
visit_date, create_user, note_received, orders_signed)
VALUES (%s, %s, %s, %s, %s, %s)"""
PATIENT_MOVED_2_LONG_TERM_CARE = """UPDATE patient SET status=1,
consecutive_skilled_visits=0, update_date=NOW() WHERE id=%s"""
SELECT_VISITS = """SELECT v.id, CONCAT_WS(' ', p.first, p.last),
CONCAT_WS(' ', n.first, n.last), DATE_FORMAT(v.visit_date, '%%Y-%%m-%%d'),
v.visit_done_by_doctor, v.note_received, v.orders_signed FROM visit v
JOIN patient p ON p.id=v.patient_id JOIN user n ON n.id=p.md_id
AND p.facility_id=%s
WHERE v.create_date > DATE_SUB(curdate(), INTERVAL 5 WEEK)
OR v.note_received != 1 OR v.orders_signed != 1
ORDER BY v.visit_date DESC"""
UPDATE_VISIT = """UPDATE visit SET visit_date=%s, note_received=%s,
orders_signed=%s, visit_done_by_doctor=%s, update_user=%s WHERE id=%s"""
SELECT_CONSECUTIVE_SKILLED_VISITS = """SELECT consecutive_skilled_visits
FROM patient WHERE id=%s"""
PATIENT_RECEIVED_SKILLED_VISIT = """UPDATE patient SET
consecutive_skilled_visits = consecutive_skilled_visits + 1,
update_date=NOW() WHERE id=%s"""


@bp.route("/upcoming/clinician", methods=['GET'])
@login_required('upcoming_for_clinician')
def upcoming_for_clinician():
    rows = format_patient_info(get_patient_info(current_user.id), True)
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    return render_template('visit/upcoming_for_clinician.html', patients=rows,
                           today=today)


def format_visits_for_report(rows):
    data = []
    h = ["Name", "Room", "Next Required Visit (Doctor or APRN)", "Next Required Doctor Visit", "Doctor", "Last Visit by APRN", "Last Visit by Doctor"]
    for pId, name, status, rm, np, md, nvDays, nvByDrDays, nv, nvByDr, lvByN, lvByDr in rows:
        data.append([name, rm, nv, nvByDr, md, lvByN, lvByDr, nvDays])
    return h, sorted(data, key=lambda x: (x[-4], x[-1]))


def write_to_xlsx(headers, rows):
    workbook = xlsxwriter.Workbook('Upcoming_Visits.xlsx')
    header = workbook.add_format({'bold': True, 'border': 1})
    sheet = workbook.add_worksheet(name='Upcoming Visits')
    sheet.write_row(0, 0, headers, header)
    data = workbook.add_format({'border': 1})
    upcoming = workbook.add_format({'border': 1, 'bg_color': '#DC4C46'})
    for rowNum, row in enumerate(rows, 1):
        nvDays = row.pop()
        fmt = upcoming if nvDays < 8 else data
        sheet.write_row(rowNum, 0, row, fmt)
    workbook.close()


@bp.route("/prior", methods=['GET', 'POST'])
@login_required('prior_visits')
def prior_visits():
    visits = get_prior_visits()
    if request.method == 'POST':
        prev = {x[0]: x[3:] for x in visits}
        errors, visits = {}, []
        for key in [x for x in request.form if x.endswith('_visited_on')]:
            vId = int(key.split('_')[0])
            vDate = request.form.get(key)
            byDr, note, order = (int(request.form.get(x % vId) == 'on') for x in ('%s_visited_by_md', '%s_note_received', '%s_orders_signed'))
            if prev[vId] != (vDate, byDr, note, order):
                visits.append((vId, vDate, byDr, note, order))
            if not vDate:  # visit date a required field...
                errors["%s_visited_on" % vId] = 'This field is required'
        if not visits:
            flash('No Visits Updated - No Changes Were Made', 'danger')
        elif not errors:
            cursor = mysql.connection.cursor()
            for vId, vDate, byDr, note, order in visits:
                cursor.execute(UPDATE_VISIT, (vDate, note, order, byDr, current_user.id, vId))
            mysql.connection.commit()
            flash('Successfully updated %s patient visits!' % len(visits), 'success')
        return jsonify(errors)  # if errors dict empty, client side code will refresh the page and flashed messages will appear
    return render_template('visit/prior_visits.html', visits=visits)


@bp.route("/upcoming", methods=['GET', 'POST'])
@login_required('upcoming_for_clerk')
def upcoming_for_clerk():
    rows = format_patient_info(get_patient_info())
    if request.method == 'POST':
        write_to_xlsx(*format_visits_for_report(rows))
        return send_file("../Upcoming_Visits.xlsx")
    clinicians = get_clinicians()
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    return render_template('visit/upcoming_for_clerk.html', numFloors=get_num_floors(),
                           clinicians=clinicians, patients=rows, today=today,
                           curFloor=current_user.floor)


def get_prior_visits():
    cursor = mysql.connection.cursor()
    cursor.execute(SELECT_VISITS, (get_user_facility_id(), ))
    return cursor.fetchall()


def get_clinicians():
    cursor = mysql.connection.cursor()
    cursor.execute(SELECT_CLINICIANS, (current_user.id, ))
    return [x[0] for x in cursor.fetchall()]


def get_patient_info(clinicianId=None):
    """Gets patients id, name, status, room no, nurse's name, doctor's name,
    admit date, last nurse visit, last doctor visit all active patients"""
    patients = []
    q = SELECT_PATIENTS
    if clinicianId:
        q += " AND (p.NP_ID=%s OR p.MD_ID=%s)" % (clinicianId, clinicianId)
    else:
        q += " AND facility_id=%s" % get_user_facility_id()
    cursor = mysql.connection.cursor()
    cursor.execute(q)
    for p in cursor.fetchall():
        pId = p[0]
        for visit in [SELECT_LAST_APRN_VISIT, SELECT_LAST_DR_VISIT]:
            if cursor.execute(visit, (pId,)):
                p += cursor.fetchone()
            else:
                p += (None,)
        patients.append(p)
    return patients


def fmt_date(x):
    return x.strftime('%m/%d/%Y') if x else ''


def format_patient_info(patients, forClinician=False):
    rows = []
    for pId, name, status, rm, np, md, admit, mcaid, lvByN, lvByDr in patients:
        today = datetime.datetime.today().date()
        nv, nvByDr = get_next_visit_dates(status, lvByN, lvByDr, admit, mcaid)
        nvDays, nvByDrDays = ((nv - today).days, (nvByDr - today).days)
        visits = map(fmt_date, (nv, nvByDr, lvByN, lvByDr))
        if nv == nvByDr:
            visits[0] += ' (Doctor)'
        if forClinician:  # clinician sees stripped down view
            rows.append([name, rm, nvDays, nvByDrDays] + visits)
        else:
            rows.append([pId, name, status, rm, np, md, nvDays, nvByDrDays] + visits)
    return rows


def get_next_visit_dates(status, lvByN, lvByDr, admit, mcaid):
    """Returns: Next patient visit, next patient visit that must be
    administered by a doctor. lvByNurse and lvByDr may both be null"""
    if lvByDr and lvByN:
        lv = max(lvByDr, lvByN)
    else:
        lv = lvByDr or lvByN or admit
    if status == 'Long Term Care':
        nvByDr = (lvByDr or lv) + datetime.timedelta(days=365 if mcaid else 120)
        nv = min(lv + datetime.timedelta(days=60), nvByDr)
    elif status == 'Skilled Care / New Admission':
        nv = lv + datetime.timedelta(days=30)
        if lv == lvByDr:
            nvByDr = lvByDr + datetime.timedelta(days=60)
        else:
            nvByDr = nv
    else:  # status is assisted living
        nv = nvByDr = (lvByDr or lv) + datetime.timedelta(days=365)
    return nv, nvByDr


@bp.route("/submit/upcoming", methods=['POST'])
@login_required('upcoming_for_clerk_submit')
def upcoming_for_clerk_submit():
    keys = ['%s_visited_by_md', '%s_visited_on', '%s_status', '%s_note_received', '%s_orders_signed']
    errors, visits = {}, []
    for key in [x for x in request.form if x.endswith('_visited')]:
        pId = key.split('_')[0]
        visit = [pId] + [request.form.get(x % pId) for x in keys]
        visits.append(visit)
        if not visit[2]:  # visit date a required field...
            errors["%s_visited_on" % pId] = 'This field is required'
    if errors or not visits:
        if not visits:
            flash('No Visits Added - Must Select the Visited Checkbox To Add a Visit', 'danger')
        return jsonify(errors)
    # add visits
    curUser = current_user.id
    cursor = mysql.connection.cursor()
    for pId, visitBy, visitDate, pStatus, note, orders in visits:
        cursor.execute(INSERT_VISIT, (pId, bool(visitBy), visitDate, curUser, bool(note), bool(orders)))
        # if patient has been visited in skilled care 3 times, they are moved to long term care
        if pStatus == 'Skilled Care / New Admission':
            cursor.execute(SELECT_CONSECUTIVE_SKILLED_VISITS, (pId,))
            if cursor.fetchall()[0][0] == 2:
                cursor.execute(PATIENT_MOVED_2_LONG_TERM_CARE, (pId,))
            else:
                cursor.execute(PATIENT_RECEIVED_SKILLED_VISIT, (pId,))
    mysql.connection.commit()
    flash('Successfully added %s patient visits!' % len(visits), 'success')
    return jsonify({})
