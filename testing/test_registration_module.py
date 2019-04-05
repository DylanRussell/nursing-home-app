import unittest
from flask import request, url_for
from flask_login import current_user
from testing import BaseTestCase
from nursingHomeApp import mysql, mail
from nursingHomeApp.registration.routes import CAN_ADD



class TestRegistrationModule(BaseTestCase):
    """Test registration module"""
    def test_login(self):
        """Test All Possible Login Scenarios"""
        options = [
            ('', 'abc123', 'This field is required.', False),
            ('test@clerk.com', '', 'This field is required.', False),
            ('doesnotexist@gmail.com', 'abab', 
             'This e-mail is not associated with an account', False),
            ('test@clerk.com', 'badpassword', 'Incorrect Password', False),
            ('test@clerk.com', 'abc123', 'You Have Been Logged In!', True)
            ]
        for email, pword, message, authenticated in options:
            # preserve request context and session - required to keep current_user object around
            with self.client:
                response = self.login_user(email, pword)
                self.assertIn(message, response.get_data())
                self.assertTrue(current_user.is_authenticated == authenticated)

    def test_login_required_decorator(self):
        """Test the view decorator used to restrict access to a view based on 
        user role.
        """
        with self.client:
            # add_patient view has the login_required decorator, so it cannot be
            # accessed without being logged in
            response = self.client.get('/add/patient', follow_redirects=True)
            self.assertIn('You must be logged in to view this page.', response.get_data())
            # user should be redirected to login page
            self.assertEqual(request.path, url_for('registration.login'))
        with self.app.app_context():
            cursor = mysql.connection.cursor()
            # get the bit representing the add_facility view
            cursor.execute("SELECT bit FROM permission WHERE name='add_facility'")
            add_facility_bit = cursor.fetchall()[0][0]
            # get the bit representing the add_patient views
            cursor.execute("SELECT bit FROM permission WHERE name='add_patient'")
            add_patient_bit = cursor.fetchall()[0][0]
            # get the bit mask representing which views the clerk can access
            cursor.execute("SELECT role_value FROM user_role WHERE role='Clerk'")
            clerk_mask = cursor.fetchall()[0][0]
        access_denied = 'You are not authorized to view this page.'
        # login as clerk
        self.login_user()
        with self.client:
            # clerk has add_patient_bit set, so is allowed to access that page
            self.assertEqual(clerk_mask & add_patient_bit, add_patient_bit)
            response = self.client.get('/add/patient', follow_redirects=True)
            self.assertNotIn(access_denied, response.get_data())
            self.assertEqual(request.path, url_for('patient.add_patient'))
            # clerk does not have the add_facility_bit set, so is not allowed
            # access, and redirected to login page
            self.assertEqual(clerk_mask & add_facility_bit, 0)
            response = self.client.get('/add/facility', follow_redirects=True)
            self.assertIn(access_denied, response.get_data())
            self.assertEqual(request.path, url_for('registration.login'))
        

    def test_toggle_user(self):
        """Test the `toggle_user` endpoint. Users may toggle other users active 
        state. If a user's active state is 0, they can't login. A Facility Admin
        User can toggle all Users except Site Admins, a Clerk cannot toggle any 
        Users -- the canRemove dictionary in the registration module represents
        this mapping.
        """

        # login as facility admin

        self.login_user('test@facilityadmin.com', 'abc123')

        options = [
            (2, 'Cannot add or remove yourself.'),  # test@facilityadmin user
            (1, 'Users status has been updated.'),  # test@clerk user
            (4, 'You are not allowed to add or remove this type of user.') # test@siteadmin user
        ]
        for userid, message in options:
            response = self.client.get('/toggle/%s' % userid, 
                                       follow_redirects=True)
            self.assertIn(message, response.get_data())

        # Clerk User should be set inactive in database
        with self.app.app_context():
            cursor = mysql.connection.cursor()
            cursor.execute("SELECT id FROM user WHERE active=0 AND id=1")
            self.assertEqual(cursor.fetchall(), ((1,),))

        # toggle active state a second time should reactivate user
        self.client.get('/toggle/1')
        with self.app.app_context():
            cursor = mysql.connection.cursor()
            cursor.execute("SELECT id FROM user WHERE active=1 AND id=1")
            self.assertEqual(cursor.fetchall(), ((1,),))

        # toggle a third time to set inactive again
        self.client.get('/toggle/1')
        self.logout()
        with self.client:
            # Clerk User should now not be allowed to login
            self.login_user('test@clerk.com', 'abc123')
            self.assertFalse(current_user.is_authenticated)


    def test_add_user(self):
        """test the add_user endpoint"""
        pword = 'abc123'
        # Nurse/Physician Users don't have permission to view the add_user page
        unauthorized = 'You are not authorized to view this page.'
        self.login_user('test@physician.com', pword)
        response = self.client.get('/add/user', follow_redirects=True)
        self.assertIn(unauthorized, response.get_data())

        # administrative tasks (like adding users) are left to the Clerks/Admins
        self.login_user('test@clerk.com', pword)
        response = self.client.get('/add/user', follow_redirects=True)
        self.assertNotIn(unauthorized, response.get_data())

        # clerk users can only add physician / nurse practitioner users
        self.assertEqual(['Physician', 'Nurse Practitioner'], CAN_ADD['Clerk'])

        form_data = {'first':'bob', 'last': 'russ', 'email': 'test@test.com',
                     'role': 'Physician', 'facility': '1'}

        with self.app.app_context():
            with mail.record_messages() as outbox:
                # add physician user
                response = self.client.post('/add/user', data=form_data, 
                                            follow_redirects=True)
                self.assertIn('User successfully added!', response.get_data())
                # when user is added an email is sent to them asking for sign up,
                # actual email sending suppressed during testing, see here:
                # https://pythonhosted.org/Flask-Mail/
                self.assertEqual(len(outbox), 1)
                self.assertEqual(outbox[0].subject, "Sign Up For visitMinder")
            cursor = mysql.connection.cursor()
            # user should now exist in users table
            cursor.execute("""SELECT role, first, last, password, active
                           FROM user WHERE email='test@test.com'""")
            self.assertEqual(cursor.fetchone(), ('Physician', 'Bob', 'Russ', 
                                                 None, 1))
            # user should exist in user_to_facility mapping table
            # all users except site admins are mapped to 1 or more facilities
            cursor.execute("""SELECT facility_id FROM user_to_facility WHERE
                           user_id=(SELECT id FROM user WHERE
                           email='test@test.com')""")
            self.assertEqual(cursor.fetchone(), (1,))
            # only Physician/Nurse users receive notifications, so a row should now
            # exist in notifications table. for other user roles this is not true
            cursor.execute("""SELECT email FROM notification WHERE 
                           email='test@test.com'""")
            self.assertEqual(cursor.fetchone(), ('test@test.com',))

        # clerk user not allowed to add a site admin user
        form_data['role'] = 'Site Admin'
        response = self.client.post('/add/user', data=form_data, 
                                    follow_redirects=True)
        self.assertIn('Not a valid choice', response.get_data())





if __name__ == '__main__':
    unittest.main()
