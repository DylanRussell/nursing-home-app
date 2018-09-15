from nursingHomeApp import mysql
from flask_login import current_user

UPDATE_STATUS_CHOICES = """SELECT id, status FROM patient_status
ORDER BY id DESC"""
ADD_STATUS_CHOICES = """SELECT id, status FROM patient_status
WHERE id != 3 ORDER by id DESC"""
SELECT_VISIT_INFO = """SELECT visit_done_by_doctor FROM visit
WHERE patient_id = %s"""
SELECT_MDS = """SELECT u.id, CONCAT_WS(' ', u.first, u.last) FROM user u
JOIN user_to_facility f ON u.id=f.user_id WHERE role='Physician'"""
SELECT_NPS = """SELECT convert(u.id, char), CONCAT_WS(' ', u.first, u.last)
FROM user u JOIN user_to_facility f ON u.id=f.user_id
WHERE role='Nurse Practitioner'"""
SELECT_FACILITIES = """SELECT id, name FROM facility order by name"""
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


def get_update_status_choices():
    cursor = mysql.connection.cursor()
    cursor.execute(UPDATE_STATUS_CHOICES)
    return cursor.fetchall()


def get_add_status_choices():
    cursor = mysql.connection.cursor()
    cursor.execute(ADD_STATUS_CHOICES)
    return cursor.fetchall()


def get_all_mds():
    cursor = mysql.connection.cursor()
    q = SELECT_MDS + """ AND f.facility_id IN (SELECT facility_id
                    FROM user_to_facility WHERE user_id=%s)
                    ORDER BY LOWER(last), first""" % current_user.id
    cursor.execute(q)
    return cursor.fetchall()


def get_all_nps():
    cursor = mysql.connection.cursor()
    q = SELECT_NPS + """ AND f.facility_id IN (SELECT facility_id
                    FROM user_to_facility WHERE user_id=%s)
                    ORDER BY LOWER(last), first""" % current_user.id
    cursor.execute(q)
    return (('', ''),) + cursor.fetchall()


def get_patient_visits(patientId):
    cursor = mysql.connection.cursor()
    cursor.execute(SELECT_VISIT_INFO, (patientId,))
    return cursor.fetchall()


def get_facilities():
    cursor = mysql.connection.cursor()
    cursor.execute(SELECT_FACILITIES)
    return cursor.fetchall()


def get_doctors_not_at_facility():
    cursor = mysql.connection.cursor()
    cursor.execute(SELECT_DOCTORS_NOT_AT_FACILITY, (current_user.id,))
    return cursor.fetchall()


def get_nurses_not_at_facility():
    cursor = mysql.connection.cursor()
    cursor.execute(SELECT_NURSES_NOT_AT_FACILITY, (current_user.id,))
    return cursor.fetchall()
