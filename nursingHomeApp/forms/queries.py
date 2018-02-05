from nursingHomeApp import mysql

UPDATE_STATUS_CHOICES = """SELECT id, status FROM patient_status
ORDER BY id DESC"""
ADD_STATUS_CHOICES = """SELECT id, status FROM patient_status
WHERE id != 3 ORDER by id DESC"""
SELECT_VISIT_INFO = """SELECT visit_done_by_doctor FROM visit
WHERE patient_id = %s LIMIT 2"""
SELECT_MDS = """SELECT id, CONCAT_WS(' ', first, last) FROM user
WHERE role='Physician' ORDER BY first, last"""
SELECT_NPS = """SELECT convert(id, char), CONCAT_WS(' ', first, last) FROM user
WHERE role='Nurse Practitioner' ORDER BY first, last"""


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
    cursor.execute(SELECT_MDS)
    return cursor.fetchall()


def get_all_nps():
    cursor = mysql.connection.cursor()
    cursor.execute(SELECT_NPS)
    return (('', ''),) + cursor.fetchall()


def get_patient_visits(patientId):
    cursor = mysql.connection.cursor()
    cursor.execute(SELECT_VISIT_INFO, (patientId,))
    return cursor.fetchall()
