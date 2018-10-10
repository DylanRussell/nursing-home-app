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
I developed/tested the app using python 2, but I think it should work fine with python 3.

##### Install the dependencies

```
$ pip install -r requirements.txt
```

You will also need to install **MySQL**, or spin up an Amazon RDS instance

##### Modify config files

Modify the variables in the ```config_{prod/dev/test}_example.py``` to reflect your MySQL connection details, mail server credentials etc.

I am using the [app factory](http://flask.pocoo.org/docs/1.0/patterns/appfactories/) pattern, so the app uses whichever config file is supplied as an argument to the [create_app function](nursingHomeApp/__init__.py) (by default the CLI manager looks for a file named nursingHomeApp/config_test.py).


##### Create the database & schema

```
$ python nursingHomeApp/init_db.py
```

This script creates the database
