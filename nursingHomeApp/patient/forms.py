from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import SubmitField, StringField, DateField, BooleanField,\
    HiddenField
from wtforms.validators import DataRequired, Optional
from wtforms_components import SelectField
from wtforms_components import DateRange
from datetime import date
from nursingHomeApp.patient.validators import check_if_required,\
    admittance_date_validations, can_status_change, validate_num_lines,\
    validate_line_len, validate_date_format, validate_required_fields,\
    validate_mds, validate_nps, validate_status_allowed, gte_prior_visit
from nursingHomeApp.common_queries import get_add_status_choices, get_all_mds,\
    get_all_nps, get_update_status_choices
from nursingHomeApp.common_validators import STR_2_NONE


def get_todays_date():
    return date.today()


class AddPatientForm(FlaskForm):
    first = StringField('First Name', validators=[DataRequired()])
    last = StringField('Last Name', validators=[DataRequired()])
    room = StringField('Room No', validators=[DataRequired()])
    status = SelectField('Patient Status',
                         validators=[DataRequired(), check_if_required],
                         choices=get_add_status_choices, coerce=int)
    skilledVisits = SelectField('Number of Prior Skilled Visits', choices=[(str(x), str(x)) for x in range(3)])
    md = SelectField("Patient's Physician", validators=[DataRequired()],
                     choices=get_all_mds, coerce=int)
    np = SelectField("Patient's APRN", validators=[Optional()],
                     choices=get_all_nps, filters=[STR_2_NONE])
    lastVisit = DateField('Last Visited Date', validators=[Optional(), DateRange(max=get_todays_date), gte_prior_visit])
    priorVisit = DateField('Last Visited by Doctor Date', validators=[Optional(), DateRange(max=get_todays_date)])
    admittance = DateField('Admittance Date', validators=[DataRequired(), DateRange(max=get_todays_date), admittance_date_validations])
    medicaid = BooleanField('Is patient insured through Medicaid?')
    submit = SubmitField('Add')


class UpdatePatientForm(FlaskForm):
    patientId = HiddenField('Patient Number')
    first = StringField('First Name', validators=[DataRequired()])
    last = StringField('Last Name', validators=[DataRequired()])
    room = StringField('Room No', validators=[DataRequired()])
    status = SelectField('Patient Status', validators=[DataRequired(), can_status_change], choices=get_update_status_choices, coerce=int)
    skilledVisits = SelectField('Number of Prior Skilled Visits', choices=zip(range(3), range(3)), coerce=int)
    md = SelectField("Patient's Physician", validators=[DataRequired()], choices=get_all_mds, coerce=int)
    np = SelectField("Patient's APRN", validators=[Optional()], choices=get_all_nps, filters=[STR_2_NONE])
    medicaid = BooleanField('Is patient insured through Medicaid?')
    submit = SubmitField('Update')


class LoadPatientsForm(FlaskForm):
    upload = FileField('Upload Patients', validators=[
        FileRequired(),
        FileAllowed(['csv'], 'csv only!'),
        validate_num_lines,
        validate_line_len,
        validate_date_format,
        validate_required_fields,
        validate_mds,
        validate_nps,
        validate_status_allowed])
    submit = SubmitField('Add')
