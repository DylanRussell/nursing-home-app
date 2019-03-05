from __future__ import absolute_import
import json
import unittest
from testing import BaseTestCase
from nursingHomeApp import mysql



class TestVisitModule(BaseTestCase):
    """Test visit module"""
    def test_add_visits(self):
        """Test the /submit/upcoming route, used for adding visits"""
        self.login_user() # login as clerk user
        # this route expects the patient_id (1 in this case) prepended to the field keys
        form_data = {'1_visited_by_md': '', '1_visited_on':'2019-02-15',
                     '1_status': 'Long Term Care', '1_note_received': 'on',
                     '1_visited': 'on'}
        self.client.post('/submit/upcoming', data=form_data)
        # should now see this visit in db table 'visit'
        with self.app.app_context():
            cursor = mysql.connection.cursor()
            cursor.execute("""SELECT patient_id, visit_done_by_doctor,
                           note_received, orders_signed FROM visit WHERE 
                           visit_date=%s""", (form_data['1_visited_on'],))
            self.assertEqual(cursor.fetchall(), ((1, 0, 1, 0),))
            # visited_on is a required field
        del form_data['1_visited_on']
        response = self.client.post('/submit/upcoming', data=form_data)
        errors = json.loads(response.get_data())
        self.assertEqual(errors['1_visited_on'], 'This field is required')
        form_data['1_visited_on'] = '2019-02-15'
        # add two visits in single request
        form_data.update({'2_visited_by_md': '', '2_visited_on':'2019-02-15',
                          '2_status': 'Long Term Care',
                          '2_note_received': 'on', '2_visited': 'on'})
        self.client.post('/submit/upcoming', data=form_data)
        with self.app.app_context():
            cursor = mysql.connection.cursor()
            cursor.execute("""SELECT COUNT(*) FROM visit WHERE visit_date=%s
                           """, (form_data['1_visited_on'],))
            self.assertEqual(cursor.fetchall()[0][0], 3)
        form_data = {'3_visited_by_md': '', '3_visited_on':'2019-02-15',
                     '3_status': 'Skilled Care / New Admission', '3_note_received': 'on',
                     '3_visited': 'on'}
        # patient 3 has a status of Skilled Care / New Admission. after 3
        # visits (which should happen within 30 days of eachother, and 2 of
        # which should be done by a doctor) patients with this status are 
        # moved to long term care. This is the only status that changes 
        # automatically.
        for _ in range(3):
            self.client.post('/submit/upcoming', data=form_data)
        with self.app.app_context():
            cursor = mysql.connection.cursor()
            # status should now be long term care, and consecutive visit
            # counter should be reset
            cursor.execute("""SELECT s.status, p.consecutive_skilled_visits
                           FROM PATIENT p JOIN PATIENT_STATUS s ON 
                           p.status=s.id WHERE p.id=3""")
            self.assertEqual(cursor.fetchall()[0], ('Long Term Care', 0))


    def test_update_visits(self):
        """Test the /prior route, used for updating existing visits"""
        self.login_user() # login as clerk
        # this route expects the visit_id (1 in this case) prepended to the field keys
        form_data = {'1_visited_on':'2019-02-15', '1_visited_by_md': 'on', 
                     '1_note_received': 'on', '1_orders_signed': 'on'}
        self.client.post('/prior', data=form_data)
        # should now see this visit updated in db table 'visit'
        with self.app.app_context():
            cursor = mysql.connection.cursor()
            cursor.execute("""SELECT visit_done_by_doctor, note_received, 
                           orders_signed FROM visit WHERE id=1""")
            self.assertEqual(cursor.fetchall(), ((1, 1, 1),))
        # for the boolean fields, a value of 'on' means True, and a missing 
        # key means False
        form_data = {'1_visited_on':'2019-02-15'}
        self.client.post('/prior', data=form_data)
        with self.app.app_context():
            cursor = mysql.connection.cursor()
            cursor.execute("""SELECT visit_done_by_doctor, note_received, 
                           orders_signed FROM visit WHERE id=1""")
            self.assertEqual(cursor.fetchall(), ((0, 0, 0),))
        # visited_on is a required field
        form_data['1_visited_on'] = ''
        response = self.client.post('/prior', data=form_data)
        errors = json.loads(response.get_data())
        self.assertEqual(errors['1_visited_on'], 'This field is required')
        # update two visits in single request
        form_data = {'1_visited_on': '2010-02-15', '2_visited_on': '2010-02-15'}
        self.client.post('/prior', data=form_data)
        with self.app.app_context():
            cursor = mysql.connection.cursor()
            cursor.execute("""SELECT COUNT(*) FROM visit WHERE visit_date=%s
                           """, (form_data['1_visited_on'],))
            self.assertEqual(cursor.fetchall()[0][0], 2)



if __name__ == '__main__':
    unittest.main()
