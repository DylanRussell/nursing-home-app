# nursing-home-app

## Summary
Web-based Visitminder is intended for regular use by nurses, physicians, and nursing home administrators.  
It is used to help practitioners comply with the regulatory requirements around frequency of patient visits by nurses and physicians. 
Simple data entry encourages use.  
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

I have included 3 example config files - one for development, one for testing, one for production.

I am using the [app factory](http://flask.pocoo.org/docs/1.0/patterns/appfactories/) pattern, so the app uses whichever config file is supplied as an argument to the create_app function (by default it looks for a file named config_prod.py).

Modify the variables in the ```config_{prod/dev/test}_example.py``` to reflect your MySQL connection details, and mail server credentials.


##### Create the database

```
$ python nursingHomeApp/init_db.py
```

This script creates the database
