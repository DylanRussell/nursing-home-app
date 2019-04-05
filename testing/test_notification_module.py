import unittest
from testing import BaseTestCase
from nursingHomeApp import mysql



class TestNotificationModule(BaseTestCase):
    """Test notification module"""
    def test_update_notification(self):
        """Test the /notifications route, used by a logged in user to update
        their notification preferences
        """
        self.login_user('test@Physician.com') # login as physician user
        # update notification preferences
        form_data = {'primaryEmail': 'fake@email.com', 'notifyPrimary': 'y',
                     'numDays': '8', 'notifyPhone': 'y', 'daysBefore': '-9'}
        self.client.post('/notifications', data=form_data)
        # corresponding row in notification table should be updated
        with self.app.app_context():
            cursor = mysql.connection.cursor()
            cursor.execute("""SELECT email, email_notification_on, 
                           email_every_n_days, phone_notification_on, 
                           sms_n_days_advance FROM notification WHERE 
                           user_id=3""")
            self.assertEqual(cursor.fetchone(), ('fake@email.com', 1, 8, 1, -9))
            # numDays field cannot be negative field represents how many days
            # send_notification script should wait between e-mail notifications
            form_data['numDays'] = '-8'
            response = self.client.post('/notifications', data=form_data,
                                        follow_redirects=True)
            self.assertIn('This field must contain a positive integer.', response.get_data())
            form_data['numDays'] = '8'
            # daysBefore must be negative. this field represents number of days
            # before an overdue visit a text notification should be sent by
            # send_notification script.
            form_data['daysBefore'] = '8'
            response = self.client.post('/notifications', data=form_data,
                                        follow_redirects=True)
            self.assertIn('This field must contain a negative integer.', response.get_data())


    def test_opt_out(self):
        """Test the "/opt/out/<int:userId>" route, allows a user to opt out of
        notifications without ever logging in / creating a password
        """
        physician_user_id = 3
        msg = 'You have been opted out of all notifications.'
        response = self.client.get('/opt/out/%s' % physician_user_id, 
                                   follow_redirects=True)
        self.assertIn(msg, response.get_data())
        # user should now be opted out of text/email notifications
        with self.app.app_context():
            cursor = mysql.connection.cursor()
            cursor.execute("""SELECT email_notification_on, notify_designee,
                           phone_notification_on FROM notification WHERE
                           user_id=%s""", (physician_user_id,))
            self.assertEqual(cursor.fetchone(), (0, 0, 0))




if __name__ == '__main__':
    unittest.main()
