#!/usr/bin/env python
from __future__ import absolute_import
import sys
from nursingHomeApp import bcrypt, mysql
from flask import current_app


def main():
    """Main entry point for script."""
    with current_app.app_context():
        cursor = mysql.connection.cursor()

        print 'Enter email address: ',
        email = raw_input()
        print 'Enter password: ',
        password = raw_input()
        print 'Enter password again: ',
        assert password == raw_input()
        print 'Enter first name: ',
        first = raw_input()
        print 'Enter last name: ',
        last = raw_input()
        print 'Enter role: ',
        role = raw_input()
        print 'Enter floor: ',
        floor = raw_input()
        cursor.execute("""INSERT INTO user (role, first, last,
                email, floor, password, email_confirmed, confirmed_on) VALUES
                (%s, %s, %s, %s, %s, %s, 1, NOW())""", (role, first, last,
                    email, floor, bcrypt.generate_password_hash(password)))
        userId = cursor.lastrowid
        print 'Enter facility id: ',
        facility = raw_input()
        if facility:
            cursor.execute("INSERT INTO user_to_facility (user_id, facility_id) VALUES (%s, %s)", (userId, facility))
        mysql.connection.commit()
        print 'User added.'


if __name__ == '__main__':
    sys.exit(main())
