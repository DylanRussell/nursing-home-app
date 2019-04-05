import unittest
from testing import BaseTestCase
from nursingHomeApp import mysql



class TestFacilityModule(BaseTestCase):
    """Test facility module"""
    def test_add_facility(self):
        """Test the /add/facility endpoint"""
        # login as site admin - route is only accessible to this user type
        self.login_user('test@siteadmin.com')
        # add a facility
        form_data = {'name': 'Example', 'address': '321 fake st.',
                     'city': 'smallville', 'state': 'NH', 'zipcode': '00001',
                     'floors': '5', 'active': 'y'}
        response = self.client.post('/add/facility', data=form_data,
                                    follow_redirects=True)
        self.assertIn(b'Successfully Added Facility', response.get_data())
        # should now see facility in facility table
        with self.app.app_context():
            cursor = mysql.connection.cursor()
            cursor.execute("SELECT COUNT(*) FROM facility WHERE name='Example'")
            self.assertEqual(cursor.fetchall()[0][0], 1)

    def test_add_clinicians(self):
        """Test the /add/clinicians endpoint"""
        facility_id = 1
        # login as clerk user who belongs to facility with id #1
        self.login_user()
        # simulate clerk adding existing doctor (user id =  #5), who doesn't 
        # already belong to facility 1 to facility 1
        doctor_id = 5
        form_data = {'doctors': str(doctor_id)}
        response = self.client.post('/add/clinicians', data=form_data,
                                    follow_redirects=True)
        msg = b'Added 1 doctors and 0 nurses to your facility!'
        self.assertIn(msg, response.get_data())
        # should now see this doctor user belongs to facility 1
        with self.app.app_context():
            cursor = mysql.connection.cursor()
            cursor.execute("""SELECT facility_id, user_id FROM user_to_facility
                           WHERE user_id=%s""" % doctor_id)
            self.assertEqual(cursor.fetchall()[0], (facility_id, doctor_id))


if __name__ == '__main__':
    unittest.main()
