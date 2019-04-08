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

Note: This app requires python v3+

```
$ pip install virtualenv
$ virtualenv -p python env
$ source env/bin/activate
```
##### Install the dependencies

```
$ pip install -r requirements.txt
```

You will also need to install **MySQL**, or spin up an Amazon RDS instance

##### Modify config files

Modify the variables in the ```config_{prod/dev/test}_example.py``` to reflect your MySQL connection details, mail server credentials, error log e-mail recipients etc.

I am using the [app factory](http://flask.pocoo.org/docs/1.0/patterns/appfactories/) pattern, so the app uses whichever config file is supplied as an argument to the [create_app function](nursingHomeApp/__init__.py). 

The [CLI manager](manage.py) used below, by default passes the filename 'nursingHomeApp.config_dev.py' to the create_app function. Make use of the -c argument if you want the app or associated scripts to run with a different config file.


##### Create the database & schema

```
$ python manage.py recreate
```

#### Other required setup (e.g. creating roles in database)


```
$ python manage.py setup
```

#### Create a site admin user

```
python manage.py create_admin_user -f YourFirstName -l YourLastName -e YourEmail -p YourPassword
```

#### [Test / Development Only] Add test data to the database

```
$ python manage.py fake_data
```

This will create 4 different users, with 4 different roles you can use to login.

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

## More detail


#### Permissions / User Roles

A user's role determines which views they have access to. Each view requiring a login (almost all views) has been assigned a unique bit in the permission table. Each user role has been assigned a bit mask in the user_role table. If the bit associated with a view name is set in the bit mask, then that user role is allowed access to the view.

A user's role may also restrict what they can do within a view. For example a user with the role of ```Site Admin``` can remove (set inactive) existing user's from the ```view_users``` view, while a user with the role of ```Clerk``` cannot, even though the ```Clerk``` user has access to the view.

A user's role may also restrict what data is shown inside a view. For example a user with the role of ```Physician``` will only see the patient's belonging to them inside the ```view_patients``` view, while a ```Clerk``` user will see all the patient's belonging to a given ```facility```.

There are currently 6 different user roles.

```Physician``` and ```Nurse Practitioner``` users can view their patients to see when they were last visited, and when they need to be visited again. They can update their notification preferences.

```Clerk``` users handle most of the administrative work inside the app: creating/updating patients and visits, adding ```Physician``` or ```Nurse Practitioner``` users etc.

```Clerk Manager``` is the same as ```Clerk```, except they can add or remove users with the role of ```Clerk```.

```Site Admin``` can access every view, and can remove (set inactive) or add a user of any other role.

```Facility Admin``` is similar to ```Site Admin``` in that they can access every view, but the data shown will be limited to the ```facility``` the user belongs to. Also they will only be able to add or remove user's belonging to their ```facility```


#### Registration

Mostly copied from the [explore flask tutorial.](http://exploreflask.com/en/latest/users.html)

Flask-Login does the session management stuff. itsdangerous is used to create/validate tokens sent to emails. Tokens validate a user's email when an account is created or a user forgets their password.

#### Patient

In the patient table, the following patient data is stored: name, if they are on medicaid, room number, status, admittance date and who their Physician (md_id column) and Nurse (np_id column) are. There is also a visit table which stores when a patient was visited, and who administered the visit.

This is the minimal amount of data needed to determine when the patient should be visited next, and to send out meaningful notifications to the Physician or Nurse.

Patient data can be added, updated, viewed, and downloaded into a csv file. Patient data cannot be deleted, but a patient's status can be updated to 'discharged'. Once in that state, no more notifications will be sent out for that patient, and the patient will no longer show up on the view_patients page.

In general there is no 'Hard Delete' function, only soft deletions, meaning an active flag is set to 0.

Other than Discharged, there are 3 possible states a patient can be in:

1. 'Skilled Care / New Admission' is the status a patient is given when they enter the nursing facility, or are in need of more intensive care. Patients with this status must be visited more often in general, and also more often by their Physician.
2. 'Long Term Care' is the status given to most patients, and corresponds to less frequent visits.
3. 'Assisted Living' status means the patient only needs to be visited once a year, and that visit must be aministered by a Physician.

Patient status basically only matters when calculating the next visit dates. For more detail regarding how that works, see the get_next_visit_dates function in the [visit.routes module.](nursingHomeApp/visit/routes.py)

#### Notification

For now only Physician users receieve notifications. Twilio is used for sending out text notifications, and a gmail account for e-mail notifications. A user can update their notification preferences by filling out a form which will update the notification table upon submission (see the /notifications endpoint [here](nursingHomeApp/notification/routes.py)).

See the [send_notifications.py script](nursingHomeApp/send_notifications.py) for how the notification table is used in sending out email/text notifications. This script is run via a cron job every 30 minutes (see [here](.ebextensions) for more on how this is configured).


#### Facility

This module hasn't received very much use yet, as the web app has only been used by a single nursing facility (instead of a group of facilities). The idea is that multiple facilities can use a single version of the web application / MySQL database at the same time. This module is mostly for adding/updating/viewing the facility table and the user_to_facility mapping table.

Users are restricted to only seeing data from the facility (or facilities) to which they belong. For example a Facility Admin user will only be able to view patients who belong to the same facility as them. 

Site Admin users are the exception - they do not belong to any facility, and can view data from any or all facilities.

Clerk/Clerk Manager/Facility Admin all belong to a single facility.

Physicians and Nurses may not be employed by any one facility and may make visits to multiple facilities, and thus can belong to multiple facilities. There are form validations to prevent the same Physician or Nurse from being added as a user multiple times. There is a [route](nursingHomeApp/facility/routes.py) named 'add_clinicians', which allows Clerk or Admin users to add an existing Nurse or Physician to their facility.

#### Visit

This module is for adding/updating/viewing visits, and is mostly used by Clerk users. A visit is made up of a date and 3 boolean values: one for if the visit was administered by a doctor, and the other two for administrative documents the Clerks are required to receive after a visit has been administered. Visit date and who administered the last visit are needed to determine when the next visit should occur.

One tricky piece of logic the app keeps track of here: a patient with a status of 'Skilled Care / New Admission' is moved to the 'Long Term Care' status after 3 consecutive 30 day visits. This is the only status that changes after a set number of visits. The logic for this is contained in the [/submit/upcoming route](nursingHomeApp/visit/routes.py).


#### Other

Create audit trail tables, and triggers to populate the tables by including the -a option when running the recreate or setup commands (i.e. ```python manage.py recreate -a```). For each of the 5 tables a user can modify (facility, user, notification, patient, visit) an audit trail table with the same schema will be created, and ON UPDATE/INSERT triggers will be created to populate those tables.

I haven't used these for anything yet. I think they may be required by HIPPA.

To view a full list of commands and arguments run ```python manage.py -?```.

This app is a work in progress. It has been in use at a single nursing home, and seems to work reasonably well. Below are some questions I would like to have answers to:

What exactly is required by HIPAA?
What are other nursing homes using to ensure visits are made on time?
How do the requirements around visits change from facility to facility or state to state?

Ideas for new features:

A way for the end user to configure the requirements around when a visit must occur and who (Doctor or Nurse) should administer it. Right now this logic is hardcoded into the app.

A way for the user to see if a facility has been meeting it's visit requirements.