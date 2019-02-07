# nursing-home-app

## Summary

Web-based nursing home application is intended for regular use by nurses, physicians, and nursing home administrators.  
It is used to help facilities comply with the regulatory requirements around frequency of patient visits by nurses and physicians.
A single instance of the app can support use by multiple facilities.
It can be configured to send out SMS or email reminders when a patient visit is overdue.


## Setting up

##### Clone the repo

```
$ git clone https://github.com/DylanRussell/nursing-home-app
$ cd nursing-home-app
```

##### Initialize a virtualenv

```
$ pip install virtualenv
$ virtualenv -p python2 env
$ source env/bin/activate
```
##### Install the dependencies

```
$ pip install -r requirements.txt
```

You will also need to install **MySQL**, or spin up an Amazon RDS instance

##### Modify config files

Modify the variables in the ```config_{prod/dev/test}_example.py``` to reflect your MySQL connection details, mail server credentials etc.

I am using the [app factory](http://flask.pocoo.org/docs/1.0/patterns/appfactories/) pattern, so the app uses whichever config file is supplied as an argument to the [create_app function](nursingHomeApp/__init__.py). 

The [CLI manager](manage.py) used below, looks for a file nursingHomeApp/config_test.py when creating the database, adding fake data etc.


##### Create the database & schema

```
$ python manage.py recreate
```

#### Other setup (e.g. creating roles in database)

```
$ python manage.py setup
```

#### [Optional] Add fake data to the database

```
$ python manage.py fake_data
```

This will create 4 different users, with 4 different roles.

pw: abc123

usernames:
test@physician.com
test@clerk.com
test@facilityadmin.com
test@siteadmin.com

#### Running the tests

```
$ python manage.py test
```
