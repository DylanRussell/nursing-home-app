import unittest
from warnings import filterwarnings
from flask_script import Manager
import MySQLdb as mdb
from nursingHomeApp import create_app
from nursingHomeApp.db import recreate_db, setup_general, add_fake_data
from nursingHomeApp.send_notifications import send_notifications


manager = Manager(create_app)
# which config file should be used by the app factory function - defaults to dev.
manager.add_option('-c', '--config', dest='config_file', 
                   default='nursingHomeApp.config_dev', required=False)


@manager.command
def notify():
    """
    Run the send_notifications function. A cronjob calls this from the 
    command line. Cronjob setup by elastic beanstalk on deployment.

    See .ebextensions/notification stuff
    """
    send_notifications()

@manager.command
def test():
    """Run the unit tests."""
    filterwarnings('ignore', category=mdb.Warning)
    tests = unittest.TestLoader().discover('testing')
    unittest.TextTestRunner(verbosity=2).run(tests)


@manager.command
def recreate(audit_trail=False):
    """
    Recreates a local database & schema. You probably should not use this on
    production. audit_trail if set to True will create a bunch of audit trail
    tables to track any change made by users.
    """
    recreate_db(audit_trail)


@manager.command
def fake_data():
    """
    Adds fake data to the database.
    """
    add_fake_data()


@manager.command
def setup(audit_trail=False):
    """
    Runs the set-up needed for local development. Basically user roles,
    patient status's, view permissions. If audit_trail set to True, a bunch
    of database triggers are created to populate the audit trail tables.
    """
    setup_general(audit_trail)


if __name__ == '__main__':
    manager.run()
