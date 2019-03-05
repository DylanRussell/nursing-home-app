from __future__ import absolute_import
import unittest
from testing import BaseTestCase
from nursingHomeApp import mysql



class TestPatientModule(BaseTestCase):
    """Test patient module"""
    def test_add_patient(self):
        """Test the /add/patient route, used for adding a patient"""
        self.login_user() # login as clerk user
        # form_data are add patient required form fields - keys are the field names expected
        # by AddPatient wtform. the 'md' field requires user_id of a user with the role of 
        # 'Physician', used to populate the md_id column in the patient table,
        # which means the patient belongs to that doctor. np field is the same,
        # only for 'Nurse Practitioner' user role, and it is an optional field
        form_data = {'first': 'John', 'last': 'Doe', 'room': '1B', 'status': '2',
                     'skilledVisits': '0', 'md': '3', 'admittance': '2019-01-01',
                     'medicaid': 'y'}
        self.client.post('/add/patient', data=form_data, follow_redirects=True)
        # should now see this patient in the patient table
        with self.app.app_context():
            cursor = mysql.connection.cursor()
            cursor.execute("""SELECT first, last, room_number, status,
                           consecutive_skilled_visits, md_id, has_medicaid
                           FROM patient WHERE first='john'""")
            self.assertEqual(cursor.fetchall(), (('John', 'Doe', '1B', 2, 0, 3, 1),))
            # optionally include when a patient was last visited (lastVisit), and
            # last visited by a doctor (priorVisit). because the 2 dates are the same
            # only 1 row should be added to the visit table
            form_data.update({'priorVisit': '2019-01-09', 'lastVisit': '2019-01-09'})
            self.client.post('/add/patient', data=form_data, follow_redirects=True)
            cursor.execute("SELECT max(id) FROM patient")
            patient_id = cursor.fetchall()[0][0]
            cursor.execute("SELECT COUNT(*) FROM visit WHERE patient_id=%s" % patient_id)
            self.assertEqual(cursor.fetchall()[0][0], 1)
            # if the dates are different, 2 visits are added
            form_data['priorVisit'] = '2019-01-02'
            self.client.post('/add/patient', data=form_data, follow_redirects=True)
            cursor.execute("SELECT max(id) FROM patient")
            patient_id = cursor.fetchall()[0][0]
            cursor.execute("SELECT COUNT(*) FROM visit WHERE patient_id=%s" % patient_id)
            self.assertEqual(cursor.fetchall()[0][0], 2)
        # status 1 is Long Term Care. last visit and last doctor visit are required
        # when a patient is added with this status
        form_data['status'] = '1'
        del form_data['priorVisit']
        del form_data['lastVisit']
        response = self.client.post('/add/patient', data=form_data, follow_redirects=True)
        err_msg = "The last visit date and last doctor visit date are required"
        self.assertIn(err_msg, response.get_data())


    def test_update_patient(self):
        """Test the /update/patient/<id> route, used for updating an individual
        patient in the patient table.
        """
        self.login_user() # login as clerk user
        # changing patient 1's name
        new_name = 'Newname'
        patient_id = 1
        form_data = {'first': new_name, 'last': 'Lastname', 'room': '2', 
                     'status': '2', 'skilledVisits': '0', 'md': '3', 
                     'medicaid': 'y'}
        with self.app.app_context():
            cursor = mysql.connection.cursor()
            cursor.execute("SELECT first FROM patient WHERE id=1")
            old_name = cursor.fetchall()[0][0]
            self.assertNotEqual(old_name, new_name)
            self.client.post('/update/patient/%s' % patient_id, data=form_data)
            cursor.execute("SELECT first FROM patient WHERE id=1")
            self.assertEqual(cursor.fetchall()[0][0], new_name)




if __name__ == '__main__':
    unittest.main()
