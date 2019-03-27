from flask import current_app
from nursingHomeApp import mysql

CREATE_TRIGGER = """CREATE TRIGGER `%s` AFTER %s ON `%s` FOR EACH ROW
INSERT INTO %s SELECT (NULL) as pkey, p.* FROM %s p WHERE p.id =  NEW.id"""


def recreate_db(audit_tables=False):
    """Clear existing database and create new database/tables."""
    cursor = mysql.connection.cursor()
    database = current_app.config["MYSQL_DB"]
    cursor.execute("DROP DATABASE IF EXISTS `%s`" % database)
    cursor.execute("CREATE DATABASE `%s`" % database)
    cursor.execute('use `%s`' % database)

    with current_app.open_resource('schema.sql') as f:
        lines = f.read().decode('utf8').split(';')
        for line in lines:
            # optionally skip creation of the audit trail tables
            if audit_tables or 'audit_trail' not in line:
                cursor.execute(line)

    mysql.connection.commit()


def setup_general(audit_tables=False):
    """add user roles, patient status's, view permissions, triggers"""
    cursor = mysql.connection.cursor()
    with current_app.open_resource('data.sql') as f:
        lines = f.read().decode('utf8').split(';')
        for line in lines:
            cursor.execute(line)

    audit_table_names = ['facility', 'user', 'notification', 'patient', 'visit']
    # optioanlly skip trigger creation (triggers populate the audit trail tables)
    if audit_tables:
        for table in audit_table_names:
            for operation in ['update', 'insert']:
                audit_table = '%s_audit_trail' % table
                trigger = '%s_audit_trail_after_%s' % (table, operation)
                cursor.execute("DROP TRIGGER IF EXISTS `%s`" % trigger)
                args = (trigger, operation, table, audit_table, table)
                cursor.execute(CREATE_TRIGGER % args)
    mysql.connection.commit()


def add_fake_data():
    """add some fake data for testing / development"""
    cursor = mysql.connection.cursor()
    with current_app.open_resource('fake_data.sql') as f:
        lines = f.read().decode('utf8').split(';')
        for line in lines:
            cursor.execute(line)
    mysql.connection.commit()
