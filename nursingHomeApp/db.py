from nursingHomeApp import mysql
from flask import current_app

CREATE_TRIGGER = """CREATE TRIGGER `%s` AFTER %s ON `%s` FOR EACH ROW
INSERT INTO %s SELECT (NULL) as pkey, p.* FROM %s p WHERE p.id =  NEW.id"""


def recreate_db(auditTrail=False):
    """Clear existing data/tables and create new tables."""
    cursor = mysql.connection.cursor()
    dbName = current_app.config["MYSQL_DB"]
    cursor.execute("DROP DATABASE IF EXISTS `%s`" % dbName)
    cursor.execute("CREATE DATABASE `%s`" % dbName)
    cursor.execute('use `%s`' % dbName)

    with current_app.open_resource('schema.sql') as f:
        lines = f.read().decode('utf8').split(';')
        for line in lines:
            if auditTrail or 'audit_trail' not in line:  # skip the audit trail tables to speed up unit tests
                cursor.execute(line)

    mysql.connection.commit()


def setup_general(auditTrail=False):
    """add user roles, patient status's, view permissions, triggers"""
    cursor = mysql.connection.cursor()
    with current_app.open_resource('data.sql') as f:
        lines = f.read().decode('utf8').split(';')
        for line in lines:
            cursor.execute(line)

    audit_tables = ['facility', 'user', 'notification', 'patient', 'visit']
    # skip trigger creation (triggers populate the audit trail tables) to speed up unit tests
    if auditTrail:
        for table in audit_tables:
            for operation in ['update', 'insert']:
                audit_table = '%s_audit_trail' % table
                trigger = '%s_audit_trail_after_%s' % (table, operation)
                cursor.execute("DROP TRIGGER IF EXISTS `%s`" % trigger)
                args = (trigger, operation, table, audit_table, table)
                cursor.execute(CREATE_TRIGGER % args)
    mysql.connection.commit()


def add_fake_data():
    """add dummy users, dummy facility"""
    cursor = mysql.connection.cursor()
    with current_app.open_resource('fake_data.sql') as f:
        lines = f.read().decode('utf8').split(';')
        for line in lines:
            cursor.execute(line)
    mysql.connection.commit()
