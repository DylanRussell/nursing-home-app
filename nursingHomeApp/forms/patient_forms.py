from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import SubmitField, StringField, DateField
from wtforms.validators import DataRequired, ValidationError, Optional, StopValidation
from wtforms_components import SelectField
from wtforms_components import DateRange
from nursingHomeApp import mysql
from datetime import datetime
import csv


def validate_status(form, field):
    valid = {x[1].lower() for x in patient_status_choices()}
    reader = csv.reader(form.upload.data, skipinitialspace=True)
    next(reader)
    for i, row in enumerate(reader, 2):
        first, last, room, status, md, mdV, np, npV, admittance = row
        status = ' '.join(x for x in status.split(' ') if x).lower()
        if status not in valid:
            form.upload.data.seek(0)
            raise ValidationError('Status %s on row %s is not a valid status. Make sure the patient status is valid.' % (status, i))
    form.upload.data.seek(0)


def validate_num_lines(form, field):
    numLines = sum(1 for line in form.upload.data)
    if numLines < 2 or numLines > 1000:
        raise StopValidation('Must be between 1 and 1000 patients in file.')
    form.upload.data.seek(0)


def validate_line_len(form, field):
    reader = csv.reader(form.upload.data, skipinitialspace=True)
    next(reader)
    for i, row in enumerate(reader, 2):
        if len(row) == 9 or not any(row):
            continue
        raise StopValidation('Each row must be 9 fields long. Row %s has only %s fields.' % (i, len(row)))
    form.upload.data.seek(0)


def validate_required_fields(form, field):
    reader = csv.reader(form.upload.data, skipinitialspace=True)
    next(reader)
    for i, row in enumerate(reader, 2):
        first, last, room, status, md, mdV, np, npV, admittance = row
        if not any([first, last, room, status, md]):
            form.upload.data.seek(0)
            raise ValidationError("""First Name, LastName, Room No, Patient Status, Patients MD are required fields.
                                        At least 1 field is missing from row %s""" % i)
    form.upload.data.seek(0)


def validate_date_format(form, field):
    today = datetime.today().date()
    reader = csv.reader(form.upload.data, skipinitialspace=True)
    next(reader)
    for i, row in enumerate(reader, 2):
        first, last, room, status, md, mdV, np, npV, admittance = row
        for fieldName, dt in [('Last Visit by MD', mdV), ('Last Visit by NP', npV), ('Admittance Date', admittance)]:
            try:
                if dt and datetime.strptime(dt, '%Y-%m-%d').date() > today:
                    form.upload.data.seek(0)
                    raise ValidationError('%s on row %s is currently a future date.' % (fieldName, i))
            except ValueError:
                form.upload.data.seek(0)
                raise ValidationError('The field %s on row %s is using an invalid date format. Valid date format is: YYYY-mm-dd' % (fieldName, i))
    form.upload.data.seek(0)


def validate_at_least_1_date(form, field):
    reader = csv.reader(form.upload.data, skipinitialspace=True)
    next(reader)
    for i, row in enumerate(reader, 2):
        first, last, room, status, md, mdV, np, npV, admittance = row
        if not any([mdV, npV, admittance]):
            form.upload.data.seek(0)
            raise ValidationError('One of Last Visited by NP, Last Visited by MD, Admittance date required. Missing from row %s' % i)
    form.upload.data.seek(0)


def validate_mds(form, field):
    mds = {x[1].lower() for x in get_all_mds()}
    reader = csv.reader(form.upload.data, skipinitialspace=True)
    next(reader)
    for i, row in enumerate(reader, 2):
        first, last, room, status, md, mdV, np, npV, admittance = row
        md = ' '.join(x for x in md.split(' ') if x).lower()
        if md not in mds:
            form.upload.data.seek(0)
            raise ValidationError('Doctor %s on row %s not found. Make sure just first and last name are listed, and that they have been added as a user.' % (md, i))
    form.upload.data.seek(0)


def validate_nps(form, field):
    nps = {x[1].lower() for x in get_all_nps()}
    reader = csv.reader(form.upload.data, skipinitialspace=True)
    next(reader)
    for i, row in enumerate(reader, 2):
        first, last, room, status, md, mdV, np, npV, admittance = row
        np = ' '.join(x for x in np.split(' ') if x).lower()
        if np not in nps:
            form.upload.data.seek(0)
            raise ValidationError('Nurse %s on row %s not found. Make sure just first and last name are listed, and that they have been added as a user.' % (md, i))
    form.upload.data.seek(0)


def patient_status_choices():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT id, status FROM patient_status")
    return cursor.fetchall()


def get_all_mds():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT id, CONCAT_WS(' ', first, last) FROM user WHERE role='Medical Doctor' ORDER BY first, last")
    return cursor.fetchall()


def get_all_nps():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT convert(id, char), CONCAT_WS(' ', first, last) FROM user WHERE role='Nurse Practicioner' ORDER BY first, last")
    return (('', ''),) + cursor.fetchall()


def is_date_selected(form, field):
    if not any([form.lastMDVisit.data, form.lastNPVisit.data, form.admittance.data]):
        raise ValidationError('One of Last Visited by MD, Last Visited by NP, Admittance Date Must be Selected')


def patient_has_md(form, field):
    if not form.np.data:
        raise ValidationError("Cannot select a list visited by NP date, without also selecting the patient's NP")


class AddPatientForm(FlaskForm):
    first = StringField('First Name', validators=[DataRequired()])
    last = StringField('Last Name', validators=[DataRequired()])
    room = StringField('Room No', validators=[DataRequired()])
    status = SelectField('Patient Status', validators=[DataRequired(), is_date_selected], choices=patient_status_choices, coerce=int)
    md = SelectField("Patient's MD", validators=[DataRequired()], choices=get_all_mds, coerce=int)
    lastMDVisit = DateField('Last Visited by MD', validators=[Optional(), DateRange(max=datetime.now().date)])
    np = SelectField("Patient's NP", validators=[Optional()], choices=get_all_nps, filters=[lambda x: x or None])
    lastNPVisit = DateField('Last Visited by NP', validators=[Optional(), patient_has_md, DateRange(max=datetime.now().date)])
    admittance = DateField('Admittance Date', validators=[Optional(), DateRange(max=datetime.now().date)])
    submit = SubmitField('Add')


class UpdatePatientForm(FlaskForm):
    first = StringField('First Name', validators=[DataRequired()])
    last = StringField('Last Name', validators=[DataRequired()])
    room = StringField('Room No', validators=[DataRequired()])
    status = SelectField('Patient Status', validators=[DataRequired()], choices=patient_status_choices, coerce=int)
    md = SelectField("Patient's MD", validators=[DataRequired()], choices=get_all_mds, coerce=int)
    np = SelectField("Patient's NP", validators=[Optional()], choices=get_all_nps, filters=[lambda x: x or None])
    submit = SubmitField('Update')


class LoadPatientsForm(FlaskForm):
    upload = FileField('Upload Patients', validators=[
        FileRequired(),
        FileAllowed(['csv'], 'csv only!'),
        validate_num_lines,
        validate_line_len,
        validate_date_format,
        validate_required_fields,
        validate_status,
        validate_mds,
        validate_nps,
        validate_at_least_1_date])
    submit = SubmitField('Add')
