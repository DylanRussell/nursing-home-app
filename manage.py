from nursingHomeApp import create_app
from nursingHomeApp.db import recreate_db, setup_general, add_fake_data
from flask_script import Manager
from warnings import filterwarnings
import MySQLdb as mdb
import unittest


app = create_app('nursingHomeApp.config_dev')
manager = Manager(app)


@manager.command
def test():
    """Run the unit tests."""
    filterwarnings('ignore', category=mdb.Warning)
    tests = unittest.TestLoader().discover('testing')
    unittest.TextTestRunner(verbosity=2).run(tests)


@manager.command
def recreate():
    """
    Recreates a local database. You probably should not use this on
    production.
    """
    recreate_db(True)


@manager.command
def fake_data():
    """
    Adds fake data to the database.
    """
    add_fake_data()


@manager.command
def setup():
    """Runs the set-up needed for local development."""
    setup_general(True)


if __name__ == '__main__':
    manager.run()
