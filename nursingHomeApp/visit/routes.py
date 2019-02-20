from __future__ import absolute_import
import datetime
import xlsxwriter
from flask import render_template, flash, request, jsonify, make_response,\
    send_file
from flask_login import current_user
from nursingHomeApp import mysql
from nursingHomeApp.visit import bp
from nursingHomeApp.common import login_required, get_num_floors,\
    get_user_facility_id

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


def get_next_visit_dates(status, last_nurse_visit, last_dr_visit, admit, mcaid):
    """Returns: A tuple of two datetime objects representing the next patient 
    visit, and the next patient visit that must be administered by a doctor.
    These two dates may be the same.
    
    Args:
        status: A string which represents the patient's status. May be one of 
                'Long Term Care', 'Skilled Care / New Admission', 
                'Assisted Living'. A patient may also have a status of 
                'Discharged' but these patients are filtered out before this
                function is called, as they don't have a next visit date.
        last_nurse_visit: datetime object representing last time a nurse visited
                          the patient, will be None if there was no last visit.
        last_doctor_visit: same as last_nurse_visit but for a doctor.
        admit: datetime object representing when a patient was admitted
        mcaid: a boolean representing whether the patient is on medicaid.
    """
    # Determine when the patient was most recently visited. If the patient
    # has not been visited yet, their admit date is instead used.
    last_visit = max(x for x in (last_dr_visit, last_nurse_visit, admit) if x)

    # If a patient is in long term care, they only need to be visited by a dr
    # every 365 days, unless they are on medicaid then it is every 120 days.
    # Additionally they must be visited at a minimum every 60 days (by anyone)
    if status == 'Long Term Care':
        next_dr_visit = (last_dr_visit or last_visit) + datetime.timedelta(days=365 if mcaid else 120)
        next_visit = min(last_visit + datetime.timedelta(days=60), next_dr_visit)
    elif status == 'Skilled Care / New Admission':
        next_visit = last_visit + datetime.timedelta(days=30)
        if last_visit == last_dr_visit:
            next_dr_visit = last_dr_visit + datetime.timedelta(days=60)
        else:
            next_dr_visit = next_visit
    else:  # status is assisted living
        next_visit = next_dr_visit = (last_dr_visit or last_visit) + datetime.timedelta(days=365)
    return next_visit, next_dr_visit


@bp.route("/submit/upcoming", methods=['POST'])
@login_required('upcoming_for_clerk_submit')
def upcoming_for_clerk_submit():
    """This route receieves a form submitted by the user. The form has data on
    visits: when the visits occured, if the visits were administered by a 
    Physician or Nurse, and if the Clerk has received the necessary
    documentation about the visit (they should at some point get from the
    Physician or Nurse 2 documents: the doctors orders and a signed note.)
    
    Request.form is used here instead of a wtform, b/c dynamic form is hard to
    do with wtform. Dynamic meaning the number of form fields will change
    based on the number of active patients in the database.

    The request.form object is an ImmutableMultiDict (see here:
    http://flask.pocoo.org/docs/1.0/api/#flask.Request.form)
    If a field was filled in by the user, that field will show up in this
    dictionary with the key being the field's name attribute, and the value
    being whatever the user entered as the value.

    Only validation done is to ensure %s_visited_on field is filled in.

    After validation, visits are added to the visit table. Also if a patient
    has a status of 'skilled care / new admission' and this is the 3rd visit 
    they have received while in that status, their status changes to long term 
    care. Otherwise a visit doesn't affect their status.

    This route is called via an XHR post request from the upcoming_for_clerk 
    page only accessible to the Clerk users.

    The route returns a json object to that page, with error messages if the
    form didn't validate, otherwise the json object is empty. See below for
    details.
    """
    keys = ['%s_visited_by_md', '%s_visited_on', '%s_status', 
            '%s_note_received', '%s_orders_signed']
    errors, visits = {}, []
    for key in [x for x in request.form if x.endswith('_visited')]:
        patient_id = key.split('_')[0]
        visit = [patient_id] + [request.form.get(x % patient_id) for x in keys]
        visits.append(visit)
        if not request.form.get('%s_visited_on' % patient_id):
            errors['%s_visited_on' % patient_id] = 'This field is required'
    if errors or not visits:
        if not visits:
            flash(('No Visits Added - Please Check the Visited Checkbox To '
                   'Add a Visit'), 'danger')
        return jsonify(errors)
    # add visits
    cursor = mysql.connection.cursor()
    for patient_id, visited_by, date, status, note, orders in visits:
        cursor.execute(INSERT_VISIT, (patient_id, bool(visited_by), date, 
                                      current_user.id, bool(note), bool(orders)))
        if status == 'Skilled Care / New Admission':
            cursor.execute(SELECT_CONSECUTIVE_SKILLED_VISITS, (patient_id,))
            if cursor.fetchall()[0][0] == 2:
                cursor.execute(PATIENT_MOVED_2_LONG_TERM_CARE, (patient_id,))
            else:
                cursor.execute(PATIENT_RECEIVED_SKILLED_VISIT, (patient_id,))
    mysql.connection.commit()
    flash('Successfully added %s patient visits!' % len(visits), 'success')
    return jsonify({})
