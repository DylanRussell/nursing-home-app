import unittest
from nursingHomeApp import create_app
from nursingHomeApp.db import recreate_db, setup_general, add_fake_data


class BaseTestCase(unittest.TestCase):
    """Base test class all unit test class's will inhereit from"""
    def setUp(self):
        self.app = create_app('nursingHomeApp.config_test')
        self.client = self.app.test_client()
        with self.app.app_context():
            recreate_db()
            setup_general()
            add_fake_data()

    def login_user(self, user='test@clerk.com', pword='abc123'):
        """Login a user. This is in the BaseTestCase class b/c it will
        be called by many different test modules
        """
        return self.client.post('/', data=dict(email=user, pw=pword),
                                follow_redirects=True)

    def logout(self):
        """logout user"""
        self.client.get('/logout')


if __name__ == '__main__':
    unittest.main()
