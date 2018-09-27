from nursingHomeApp import mysql
from flask import current_app

CREATE_TRIGGER = """CREATE TRIGGER `%s` AFTER %s ON `%s` FOR EACH ROW
INSERT INTO %s SELECT (NULL) as pkey, p.* FROM %s p WHERE p.id =  NEW.id"""


def init_db():
    """Clear existing data and create new tables."""
    cursor = mysql.connection.cursor()
    cursor.execute("DROP DATABASE IF EXISTS `flaskdbtest`")
    cursor.execute("CREATE DATABASE `flaskdbtest`")
    cursor.execute('use `flaskdbtest`')
    audit_tables = ['facility', 'user', 'notification', 'patient', 'visit']

    with current_app.open_resource('schema.sql') as f:
        lines = f.read().decode('utf8').split(';')
        for line in lines:
            if line.strip() and 'audit_trail' not in line:  # skip the audit trail tables to speed up unit tests
                cursor.execute(line)

    # add user roles, patient status, view permissions,
    # a test facility, test users
    with current_app.open_resource('data.sql') as f:
        lines = f.read().decode('utf8').split(';')
        for line in lines:
            if line.strip():
                cursor.execute(line)

    # add triggers to populate audit trail tables...
    # commenting out for now to speed up unit tests
    # for table in audit_tables:
    #     for operation in ['update', 'insert']:
    #         audit_table = '%s_audit_trail' % table
    #         trigger = '%s_audit_trail_after_%s' % (table, operation)
    #         cursor.execute("DROP TRIGGER IF EXISTS `%s`" % trigger)
    #         args = (trigger, operation, table, audit_table, table)
    #         cursor.execute(CREATE_TRIGGER % args)
    mysql.connection.commit()
