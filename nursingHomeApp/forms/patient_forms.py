from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import SubmitField, StringField, DateField, BooleanField, HiddenField
from wtforms.validators import DataRequired, ValidationError, Optional, StopValidation
from wtforms_components import SelectField
from wtforms_components import DateRange
from nursingHomeApp import mysql
from datetime import datetime
import csv


def validate_status_allowed(form, field):
    reader = csv.reader(form.upload.data, skipinitialspace=True)
    next(reader)
    for i, row in enumerate(reader, 2):
        first, last, room, status, md, np, lv, lvBy, pv, pvBy, admittance = row
        status = ' '.join(x for x in status.split(' ') if x).lower()
        if status in {'long term care', 'skilled care'}:  # long term care is 1, skilled care is 2
            if not lv or not pv:
                form.upload.data.seek(0)
                raise ValidationError('If patient is in Long Term Care or Skilled Care, the dates of the last 2 visits are requried.')
        if status == 'long term care' and not lvBy and not pvBy:
            form.upload.data.seek(0)
            raise ValidationError('For a patient to go into Long Term Care, one of the last 2 visits must have been done by a doctor.')
    form.upload.data.seek(0)


def validate_status(form, field):
    valid = {x[1].lower() for x in get_add_status_choices()}
    reader = csv.reader(form.upload.data, skipinitialspace=True)
    next(reader)
    for i, row in enumerate(reader, 2):
        first, last, room, status, md, np, lv, lvBy, pv, pvBy, admittance = row
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
        if len(row) == 11 or not any(row):
            continue
        raise StopValidation('Each row must be 11 fields long. Row %s has only %s fields.' % (i, len(row)))
    form.upload.data.seek(0)


def validate_required_fields(form, field):
    reader = csv.reader(form.upload.data, skipinitialspace=True)
    next(reader)
    for i, row in enumerate(reader, 2):
        first, last, room, status, md, np, lv, lvByD, pv, pvByD, admittance = row
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
        first, last, room, status, md, np, lv, lvByD, pv, pvByD, admittance = row
        for fieldName, dt in [('Last Visit', lv), ('Second to Last Visit', pv), ('Admittance Date', admittance)]:
            try:
                if dt and datetime.strptime(dt, '%Y-%m-%d').date() > today:
                    form.upload.data.seek(0)
                    raise ValidationError('%s on row %s is currently a future date.' % (fieldName, i))
            except ValueError:
                form.upload.data.seek(0)
                raise ValidationError('The field %s on row %s is using an invalid date format. Valid date format is: YYYY-mm-dd' % (fieldName, i))
    form.upload.data.seek(0)


def validate_mds(form, field):
    mds = {x[1].lower() for x in get_all_mds()}
    reader = csv.reader(form.upload.data, skipinitialspace=True)
    next(reader)
    for i, row in enumerate(reader, 2):
        first, last, room, status, md, np, lv, lvByD, pv, pvByD, admittance = row
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
        first, last, room, status, md, np, lv, lvByD, pv, pvByD, admittance = row
        np = ' '.join(x for x in np.split(' ') if x).lower()
        if np not in nps:
            form.upload.data.seek(0)
            raise ValidationError('Nurse %s on row %s not found. Make sure just first and last name are listed, and that they have been added as a user.' % (np, i))
    form.upload.data.seek(0)


def get_add_status_choices():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT id, status FROM patient_status WHERE id != 3")
    return cursor.fetchall()


def get_update_status_choices():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT id, status FROM patient_status WHERE id != 4")
    return cursor.fetchall()


def get_all_mds():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT id, CONCAT_WS(' ', first, last) FROM user WHERE role='Medical Doctor' ORDER BY first, last")
    return cursor.fetchall()


def get_all_nps():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT convert(id, char), CONCAT_WS(' ', first, last) FROM user WHERE role='Nurse Practicioner' ORDER BY first, last")
    return (('', ''),) + cursor.fetchall()


def gt_prior_visit(form, field):
    if form.priorVisit.data and not form.lastVisit.data:
        raise ValidationError('Cannot have second to last visit, and not have last visit.')
    if form.priorVisit.data and form.lastVisit.data:
        if form.priorVisit.data >= form.lastVisit.data:
            raise ValidationError('Last visit must come after second to last visit.')


def check_if_required(form, field):
    if form.status.data in {1, 2}:  # long term care is 1, skilled care is 2
        if not form.lastVisit.data or not form.priorVisit.data:
            raise ValidationError('If patient is in Long Term Care or Skilled Care, the dates of the last 2 visits are requried.')
    if form.status.data == 1 and not form.lastVisitBy.data and not form.priorVisitBy.data:
        raise ValidationError('For a patient to go into Long Term Care, one of the last 2 visits must have been done by a doctor.')


def admittance_date_validations(form, field):
    if not form.admittance.data and form.status.data == 4:
        raise ValidationError('If patient is a new admission, their admittance date is requred')
    if form.admittance.data and form.lastVisit.data and form.admittance.data > form.lastVisit.data:
        raise ValidationError('Admittance date cannot be after last visit date')
    if form.admittance.data and form.priorVisit.data and form.admittance.data > form.priorVisit.data:
        raise ValidationError('Admittance date cannot be after second to last visit date')


def can_status_change(form, field):
    if form.status.data == 1 or form.status.data == 2: # long term care is 1, skilled care is 2
        cursor = mysql.connection.cursor()
        numVisits = cursor.execute("SELECT visit_done_by_doctor FROM visit WHERE patient_id = %s" % (form.patientId.data,))
        if numVisits < 2:
            raise ValidationError('For a patient to go into long term or skilled care, they must have been visited at least 2 times.')
        if form.status.data == 1 and not any(x[0] for x in cursor.fetchall()):
            raise ValidationError('For a patient to go into long term care, they must have already been visited by a doctor at least 1 time.')


class AddPatientForm(FlaskForm):
    first = StringField('First Name', validators=[DataRequired()])
    last = StringField('Last Name', validators=[DataRequired()])
    room = StringField('Room No', validators=[DataRequired()])
    status = SelectField('Patient Status', validators=[DataRequired(), check_if_required], choices=get_add_status_choices, coerce=int)
    md = SelectField("Patient's MD", validators=[DataRequired()], choices=get_all_mds, coerce=int)
    np = SelectField("Patient's NP", validators=[Optional()], choices=get_all_nps, filters=[lambda x: x or None])
    lastVisit = DateField('Last Visited Date', validators=[Optional(), DateRange(max=datetime.now().date), gt_prior_visit])
    lastVisitBy = BooleanField('Last Vist Done by a Doctor?')
    priorVisit = DateField('Second to Last Visited Date', validators=[Optional(), DateRange(max=datetime.now().date)])
    priorVisitBy = BooleanField('Second to Last Vist Done by a Doctor?')
    admittance = DateField('Admittance Date', validators=[Optional(), DateRange(max=datetime.now().date), admittance_date_validations])
    submit = SubmitField('Add')


class UpdatePatientForm(FlaskForm):
    patientId = HiddenField('Patient Number')
    first = StringField('First Name', validators=[DataRequired()])
    last = StringField('Last Name', validators=[DataRequired()])
    room = StringField('Room No', validators=[DataRequired()])
    status = SelectField('Patient Status', validators=[DataRequired(), can_status_change], choices=get_update_status_choices, coerce=int)
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
        validate_status_allowed])
    submit = SubmitField('Add')
