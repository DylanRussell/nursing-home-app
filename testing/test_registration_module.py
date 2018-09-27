from __future__ import absolute_import
import sys, unittest
sys.path.append(".")
from testing import BaseTestCase
from nursingHomeApp import mysql
from flask_login import current_user


class TestRegistrationModule(BaseTestCase):

    def test_login(self):
        """Test All Possible Login Scenarios"""
        for email, pw, message, authenticated in [('', 'abc123', 'This field is required.', False),
                                                  ('test@clerk.com', '', 'This field is required.', False),
                                                  ('doesnotexist@gmail.com', 'abab', 'This email is not associated with an account', False),
                                                  ('test@clerk.com', 'badpassword', 'Incorrect Password', False),
                                                  ('test@clerk.com', 'abc123', 'You Have Been Logged In!', True)]:
            with self.client:  # preserve request context and session
                response = self.client.post('/', data={'email': email, 'pw': pw}, follow_redirects=True)
                self.assertIn(message, response.data)
                self.assertTrue(current_user.is_authenticated == authenticated)

    def test_toggle_user(self):
        """Test the `toggle_user` endpoint. Users may toggle other users active state.
        If a user's active state is 0, they can't login. A Facility Admin User can toggle
        all Users except Site Admins, a Clerk cannot toggle any Users -- the canRemove dictionary
        in the config file represents the complete ruleset."""

        # login as facility admin

        self.login_user('test@facilityadmin.com', 'abc123')

        # set Clerk User (userId == 1) inactive
        for userId, message in [(2, 'Cannot add or remove yourself.'),
                                (1, 'Users status has been updated.'),  # Clerk User
                                (4, 'You are not allowed to add or remove this type of user.')]:  # Site Admin User
            response = self.client.get('/toggle/%s' % userId, follow_redirects=True)
            self.assertIn(message, response.data)

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
            response = self.client.post('/', data={'email': 'test@clerk.com', 'pw': 'abc123'})
            self.assertFalse(current_user.is_authenticated)


if __name__ == '__main__':
    unittest.main()
