from __future__ import absolute_import
import sys, unittest
sys.path.append(".")
from nursingHomeApp import create_app
from nursingHomeApp.db import init_db


class BaseTestCase(unittest.TestCase):

    def setUp(self):
        self.app = create_app('nursingHomeApp.config_test')
        self.client = self.app.test_client()
        with self.app.app_context():
            init_db()

    def login_user(self, user='test@clerk.com', pw='abc123'):
        """Login a user. This is in the BaseTestCase class b/c it will
        be called by many different test modules"""
        self.client.post('/', data=dict(email=user, pw=pw))

    def logout(self):
        self.client.get('/logout')


if __name__ == '__main__':
    unittest.main()
