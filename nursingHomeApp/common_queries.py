from flask_login import current_user
from nursingHomeApp import mysql

UPDATE_STATUS_CHOICES = "SELECT id, status FROM patient_status ORDER BY id DESC"
ADD_STATUS_CHOICES = """SELECT id, status FROM patient_status
WHERE id != 3 ORDER by id DESC"""
SELECT_VISIT_INFO = "SELECT visit_done_by_doctor FROM visit WHERE patient_id=%s"
SELECT_MDS = """SELECT u.id, CONCAT_WS(' ', u.first, u.last) FROM user u
JOIN user_to_facility f ON u.id=f.user_id WHERE role='Physician' AND 
f.facility_id IN (SELECT facility_id FROM user_to_facility WHERE user_id=%s)
ORDER BY LOWER(last), first"""
SELECT_NPS = """SELECT convert(u.id, char), CONCAT_WS(' ', u.first, u.last) FROM
user u JOIN user_to_facility f ON u.id=f.user_id WHERE role='Nurse Practitioner'
AND f.facility_id IN (SELECT facility_id FROM user_to_facility WHERE user_id=%s)
ORDER BY LOWER(last), first"""
SELECT_FACILITIES = "SELECT id, name FROM facility order by name"
SELECT_DOCTORS_NOT_AT_FACILITY = """SELECT id, CONCAT_WS(' ', first, last)
FROM user WHERE role='Physician' AND active=1 AND id NOT IN
    (SELECT user_id FROM user_to_facility WHERE facility_id IN
        (SELECT facility_id FROM user_to_facility WHERE user_id=%s))
ORDER BY LOWER(last), LOWER(first)"""
SELECT_NURSES_NOT_AT_FACILITY = """SELECT id, CONCAT_WS(' ', first, last)
FROM user WHERE role='Nurse Practitioner' AND active=1 AND id NOT IN
    (SELECT user_id FROM user_to_facility WHERE facility_id IN
        (SELECT facility_id FROM user_to_facility WHERE user_id=%s))
ORDER BY LOWER(last), LOWER(first)"""
SELECT_FLOOR_CNT = """SELECT num_floors FROM facility WHERE id IN
(SELECT facility_id FROM user_to_facility WHERE user_id=%s)"""
SELECT_FACILITY_ID = "SELECT facility_id FROM user_to_facility WHERE user_id=%s"


def get_update_status_choices():
    """Returns list of patient status id, patient status description for use
    in the UPDATE Patient view
    """
    cursor = mysql.connection.cursor()
    cursor.execute(UPDATE_STATUS_CHOICES)
    return cursor.fetchall()


def get_add_status_choices():
    """Same as the list of update status choices, except excludes the discharged
    status (status 3)
    """
    cursor = mysql.connection.cursor()
    cursor.execute(ADD_STATUS_CHOICES)
    return cursor.fetchall()


def get_all_mds():
    """Gets all Physician users associated with the logged in user's facility
    """
    cursor = mysql.connection.cursor()
    cursor.execute(SELECT_MDS, (current_user.id,))
    return cursor.fetchall()


def get_all_nps():
    """Same as above, except for Nurse users. Also an empty tuple is prepended
    to the list  of tuples ('', ''), to allow the user to select nothing as the 
    patient may not be assigned to a nurse user.
    """
    cursor = mysql.connection.cursor()
    cursor.execute(SELECT_NPS, (current_user.id,))
    return (('', ''),) + cursor.fetchall()


def get_patient_visits(patient_id):
    """SELECTs the boolean value doctor_visit (True if the visit was administered
    by a doctor) for each visit patient_id received.

    Used in form validations to determine if a patient's status can change to
    Long Term Care or Assisted Living - not allowed if the patient hasn't been
    visited by a doctor.
    """
    cursor = mysql.connection.cursor()
    cursor.execute(SELECT_VISIT_INFO, (patient_id,))
    return cursor.fetchall()


def get_facilities():
    """SELECTs facility_id, name from the facility table for use in forms
    """
    cursor = mysql.connection.cursor()
    cursor.execute(SELECT_FACILITIES)
    return cursor.fetchall()


def get_doctors_not_at_facility():
    """Retrieves all doctor users not already belonging to the logged in user's
    facility
    """
    cursor = mysql.connection.cursor()
    cursor.execute(SELECT_DOCTORS_NOT_AT_FACILITY, (current_user.id,))
    return cursor.fetchall()


def get_nurses_not_at_facility():
    """Same as above, but for nurse users"""
    cursor = mysql.connection.cursor()
    cursor.execute(SELECT_NURSES_NOT_AT_FACILITY, (current_user.id,))
    return cursor.fetchall()


def get_num_floors():
    """Gets the number of floors the logged in user's facility has. If the
    user does not belong to a facility (as is the case only with Site Admin
    users), None is returned"""
    cursor = mysql.connection.cursor()
    if cursor.execute(SELECT_FLOOR_CNT, (current_user.id, )):
        return cursor.fetchall()[0][0]


def get_user_facility_id():
    """SELECTs the facility_id the logged in user belongs to
    """
    cursor = mysql.connection.cursor()
    cursor.execute(SELECT_FACILITY_ID, (current_user.id,))
    return cursor.fetchall()[0][0]
