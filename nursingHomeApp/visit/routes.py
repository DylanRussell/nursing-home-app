from datetime import timedelta, datetime
import io
from flask import render_template, flash, request, jsonify, Response
from flask_login import current_user
import xlsxwriter
from nursingHomeApp import mysql
from nursingHomeApp.visit import bp
from nursingHomeApp.common_queries import get_num_floors, get_user_facility_id
from nursingHomeApp.registration.routes import login_required


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
    """Only users with the role Physician or Nurse Practitioner have permission 
    to access this page.

    This view contains a table of upcoming visits with a row for each active 
    patient belonging to the logged in clinician.
    """
    patients = prepare_patient_info(get_patient_info(current_user.id), True)
    return render_template('visit/upcoming_for_clinician.html',
                           patients=patients,
                           today=datetime.now().strftime('%Y-%m-%d'))


def write_to_xlsx(rows):
    """Writes patient / visit data to an in-memory excel workbook. Then
    that file is read into a flask Response object. Headers are added and then
    the Response object is returned.

    Args:
        rows: a list of lists. each list contains a single patient's 
              upcoming visit info (see get_patient_info and prepare_patient_info 
              functions).
    Returns:
        response: A flask Response object containing the in-memory workbook to
                  be returned to the user.
    """

    # filter out information user doesn't need to see like the patient_id
    filtered_rows = []
    for (_, name, _, room, _, doctor, days_until_next_visit, _, next_visit, 
         next_dr_visit, last_nurse_visit, last_doctor_visit) in rows:
        filtered_rows.append([name, room, next_visit, next_dr_visit, doctor,
                              last_nurse_visit, last_doctor_visit, 
                              days_until_next_visit])
    # sort ascending by doctor name, days_until_next_visit
    filtered_rows.sort(key=lambda x: (x[-4], x[-1]))
    # header row
    headers = ["Name", "Room", "Next Required Visit (Doctor or APRN)", 
               "Next Required Doctor Visit", "Doctor", "Last Visit by APRN",
               "Last Visit by Doctor"]
    # Create an in-memory output file for the new workbook.
    output = io.StringIO()
    # Create workbook
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    sheet = workbook.add_worksheet('Upcoming Visits')
    # Create formats
    header = workbook.add_format({'bold': True, 'border': 1})
    upcoming = workbook.add_format({'border': 1, 'bg_color': '#DC4C46'})
    data = workbook.add_format({'border': 1})
    # write data
    sheet.write_row(0, 0, headers, header)
    for row_number, row in enumerate(filtered_rows, 1):
        days_until_next_visit = row.pop()
        fmt = upcoming if days_until_next_visit < 8 else data
        sheet.write_row(row_number, 0, row, fmt)
    # Close the workbook before streaming the data.
    workbook.close()
    # Rewind the buffer.
    output.seek(0)
    # Flask response
    response = Response(output.read(), 200)

    file_name = 'Upcoming_Visits_{}.xlsx'.format(datetime.now())

    # HTTP headers for forcing file download
    response.headers = {
        'Pragma': 'public',
        'Expires': '0',
        'Cache-Control': 'must-revalidate, private',
        'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'Content-Disposition': 'attachment; filename="%s";' % file_name,
        'Content-Transfer-Encoding': 'binary',
        'Content-Length': len(response.data)
        }
    return response


@bp.route("/prior", methods=['GET', 'POST'])
@login_required('prior_visits')
def prior_visits():
    """Only users with the role Clerk or Clerk Manager have permission to access
    this page.

    All incomplete visits (incomplete meaning one of the doctors note /
    signed orders were missing when the visit was added) OR visits added in the 
    last 5 weeks (regardless of if they are incomplete) are listed in a table.

    From this view the Clerk user can update the visit date, if the visit was
    administered by a doctor/nurse, and if they receieved either of
    the 2 forms above.

    Similar to the upcoming_for_clerk_submit route in that the Request.form
    object is used instead of a wtform due to dynamic forms being difficult
    to generate with wtforms.

    Both of these routes should be refactored to use a wtform - here
    is a possible starting point:
    https://stackoverflow.com/questions/12353603/dynamic-forms-from-variable-length-elements-wtforms

    Current approach is for each visit sent to the view, 4 form fields are 
    generated in the template. The name attributes given to these fields, which
    map to keys in the request.form dictionary are:  %s_visited_by_md,
    %s_note_received, %s_orders_signed, %s_visited_on where %s is replaced
    by the id of the visit. The visit_id is prepended to each name attribute
    in order to differentiate the fields - so we can determine which visit
    each field corresponds to in the visit database table.

    If a field doesn't validate (in this case the only validation done is 
    to ensure the visit_date field isn't empty) the field name is used as a
    key in a dictionary named errors, and the value is the error message.

    Then in the template there is some javascript code which will append the
    error message to the DOM beside the field which generated the error.

    If there aren't any errors the visit table is updated and an empty
    errors dictionary is returned to the template. There is javascript code in
    the template which will refresh the page if the errors dictionary is empty.

    The same approach is used in the upcoming_for_clerk_submit route, except
    that route INSERTs new visits, and the patient_id is prepended to the
    field name instead of the visit_id for use in the INSERT statement.
    """
    visits = get_prior_visits()
    if request.method == 'POST':
        # map visit_id to a tuple: (visit_date, doctor_visit, note, order)
        # this will be used to check if any data regarding the visit changed
        # and thus needs to be updated in the db
        prev = {x[0]: x[3:] for x in visits}
        errors, visits = {}, []
        keys = ['%s_visited_by_md', '%s_note_received', '%s_orders_signed']
        for visit_date_key in [x for x in request.form if x.endswith('_visited_on')]:
            visit_id = int(visit_date_key.split('_')[0])
            visit_date = request.form.get(visit_date_key)
            doctor_visit, note, order = (int(bool(request.form.get(x % visit_id)))
                                         for x in keys)
            if not visit_date:  # visit date a required field...
                errors[visit_date_key] = 'This field is required'
            elif prev[visit_id] != (visit_date, doctor_visit, note, order):
                # user updated this visit
                visits.append((visit_id, visit_date, doctor_visit, note, order))
        if not visits:
            flash('No Visits Updated - No Changes Were Made', 'danger')
        elif not errors:
            cursor = mysql.connection.cursor()
            for visit_id, visit_date, doctor_visit, note, order in visits:
                args = (visit_date, note, order, doctor_visit, current_user.id, 
                        visit_id)
                cursor.execute(UPDATE_VISIT, args)
            mysql.connection.commit()
            flash('Successfully updated %s visits!' % len(visits), 'success')
        return jsonify(errors)
    return render_template('visit/prior_visits.html', visits=visits)


@bp.route("/upcoming", methods=['GET', 'POST'])
@login_required('upcoming_for_clerk')
def upcoming_for_clerk():
    """Only users with the role Clerk or Clerk Manager have permission to
    access this page. Clerk users are responsible for most of the data entry on
    the site. Clerk users belong to a single facility.

    This view contains a table of upcoming visits with a row for each active 
    patient belonging to the logged in user's facility.

    From this view the Clerk user can mark if an upcoming visit has occured - 
    see the upcoming_for_clerk_submit route below (this route is called
    via an ajax call from the view).

    Also from this view the Clerk can download the contents of the table
    into an excel file by hitting a download button which submits a POST
    request to this route.
    """
    patients = prepare_patient_info(get_patient_info())
    if request.method == 'POST':
        return write_to_xlsx(patients)
    return render_template('visit/upcoming_for_clerk.html', 
                           numFloors=get_num_floors(), patients=patients,
                           today=datetime.now().strftime('%Y-%m-%d'),
                           clinicians=get_clinicians(),
                           curFloor=current_user.floor)


def get_prior_visits():
    """SELECTs all visits that occured in the logged in user's facility that
    were added in the last 5 weeks, OR which are missing either the doctor's
    note or the signed order's both of which are forms that must be obtained
    by the Clerk after each visit.

    Called from the prior_visits route accessible only to Clerk users.
    """
    cursor = mysql.connection.cursor()
    cursor.execute(SELECT_VISITS, (get_user_facility_id(),))
    return cursor.fetchall()


def get_clinicians():
    """Get all clinicians belonging to the logged in user's facility for use in 
    the upcoming_for_clerk view - Clerk users can select a clinician and the 
    list of patients will be filtered to only show patients that belong to the 
    selected clinician.

    Returns list of strings (clinician names).
    """
    cursor = mysql.connection.cursor()
    cursor.execute(SELECT_CLINICIANS, (current_user.id, ))
    return [x[0] for x in cursor.fetchall()]


def get_patient_info(clinician_id=None):
    """Retrieves patient & visit data. If a clinician_id is given, only active 
    patients that belong to that clinician are fetched from the database. 
    Otherwise all active patients that belong to the logged in user's facility
    are retrieved.
    
    If the function is called from the upcoming_for_clinician route, a route
    only accessible to clinicians (Physician / Nurse users), then the function is
    called with a clinician_id.

    The function is also called from the upcoming_for_clerk route without the
    clinician_id argument, this route is only accessible to clerks. Clerks 
    belong to a single facility, so it is safe to fetch just those patients 
    belonging to that facility.

    Args: 
        clinician_id: id of a user with the role of Physician or Nurse
                      Practitioner
    Returns:
        patients: list of tuples. each tuple has 9 elements: patients id, name,
                  status, room no, nurse's name, doctor's name, admit date, 
                  last nurse visit (or None if doesn't exist), 
                  last doctor visit (or None if doesn't exist).
    """
    patients = []
    query = SELECT_PATIENTS
    if clinician_id is not None:
        query += " AND (p.NP_ID=%s OR p.MD_ID=%s)" % (clinician_id, clinician_id)
    else:
        query += " AND facility_id=%s" % get_user_facility_id()
    cursor = mysql.connection.cursor()
    cursor.execute(query)
    for patient in cursor.fetchall():
        patient_id = patient[0]
        for select_last_visit in [SELECT_LAST_APRN_VISIT, SELECT_LAST_DR_VISIT]:
            if cursor.execute(select_last_visit, (patient_id,)):
                patient += cursor.fetchone()
            else:
                patient += (None,)
        patients.append(patient)
    return patients


def fmt_date(date):
    """Format Date for display to user"""
    return date.strftime('%m/%d/%Y') if date else ''


def prepare_patient_info(patients, for_clinician=False):
    """Take the list of patient & visit data fetched from the database, and
    calculates when the next visit / next doctor visit should occur.

    Returns just the information needed for the view - the upcoming_for_clinician
    view is a simpler view that displays a list of patients and when they need
    to be seen. The upcoming_for_clerk view is more complicated in that it 
    allows the clerks to add new visits to the database. It requires more
    information - such as the patient's id # in the database, not needed in the
    view for clinicians.

    Also format dates as strings for display to the user

    Args:
        patient: list of tuples retrieved in the get_patient_info function
        for_clinician: boolean which is True if the patient info should
                       be prepared for the upcoming_for_clinican view or
                       False if being prepared for the upcoming_for_clerk view

    Returns: list of lists for use in the upcoming_for_clerk/clinican views
    """
    patients_modified = []
    today = datetime.today().date()
    for (patient_id, name, status, room, nurse, doctor, admit, mcaid,
         last_nurse_visit, last_doctor_visit) in patients:
        next_visit, next_dr_visit = get_next_visit_dates(status, 
                                                         last_nurse_visit, 
                                                         last_doctor_visit, 
                                                         admit, mcaid)
        days_until_next_visit = (next_visit - today).days
        days_until_next_dr_visit = (next_dr_visit - today).days
        visits = [fmt_date(x) for x in (next_visit, next_dr_visit,
                                        last_nurse_visit, last_doctor_visit)]
        if next_visit == next_dr_visit:
            visits[0] += ' (Doctor)'
        if for_clinician:
            patients_modified.append([name, room, days_until_next_visit,
                                      days_until_next_dr_visit] + visits)
        else:
            patients_modified.append([patient_id, name, status, room, nurse, 
                                      doctor, days_until_next_visit, 
                                      days_until_next_dr_visit] + visits)
    return patients_modified


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
        # if a patient is in long term care, an assumption is made that they
        # must have ben visited by a doctor at some point in the past
        next_dr_visit = last_dr_visit + timedelta(days=365 if mcaid else 120)
        next_visit = min(last_visit + timedelta(days=60), next_dr_visit)
    # If a patient is in Skilled Care / New Admission then 3 visits 30 days apart
    # are required, the first of which must be administered by a doctor. After
    # that visit, the doctor is required to make a second visit before 60 days -
    # same requirement as Long Term Care
    elif status == 'Skilled Care / New Admission':
        next_visit = last_visit + timedelta(days=30)
        if last_visit == last_dr_visit:
            next_dr_visit = last_dr_visit + timedelta(days=60)
        else:
            next_dr_visit = next_visit
    # status is assisted living. this requires the patient be seen annually by
    # a doctor. that is the only requirement.
    else:
        next_visit = next_dr_visit = last_dr_visit + timedelta(days=365)
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

    Only validation done is to ensure %s_visited_on field is filled in, 
    where %s is the patient_id preprended to each field name attribute
    in order to determine which patient the visit corresponds to.

    After validation, visits are added to the visit table. Also if a patient
    has a status of 'skilled care / new admission' and this is the 3rd visit 
    they have received while in that status, their status changes to long term 
    care. Otherwise a visit doesn't affect their status.

    This route is called via an XHR post request from the upcoming_for_clerk 
    page only accessible to the Clerk users.

    The route returns a json object to that page, with error messages if the
    form didn't validate, otherwise the json object is empty.
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
