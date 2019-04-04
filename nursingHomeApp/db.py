from flask import current_app
from nursingHomeApp import mysql, bcrypt

CREATE_TRIGGER = """CREATE TRIGGER `%s` AFTER %s ON `%s` FOR EACH ROW
INSERT INTO %s SELECT (NULL) as pkey, p.* FROM %s p WHERE p.id =  NEW.id"""

INSERT_ADMIN_USER = """INSERT INTO user (role, first, last, email, password, 
email_confirmed, active, create_user) VALUES ('Site Admin', %s, %s, %s, %s, 1, 1, 0)"""


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


def add_admin_user(first, last, email, password):
    """INSERTs a user with the role of Site Admin into the user table"""
    cursor = mysql.connection.cursor()
    password = bcrypt.generate_password_hash(password)
    cursor.execute(INSERT_ADMIN_USER, (first, last, email, password))
    mysql.connection.commit()
