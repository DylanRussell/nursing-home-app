from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import SubmitField, StringField, DateField, BooleanField,\
    HiddenField
from wtforms.validators import DataRequired, Optional
from wtforms_components import SelectField
from wtforms_components import DateRange
from datetime import datetime
from nursingHomeApp.forms.patient_validators import check_if_required,\
    admittance_date_validations, can_status_change, validate_num_lines,\
    validate_line_len, validate_date_format, validate_required_fields,\
    validate_mds, validate_nps, validate_status_allowed, gte_prior_visit
from nursingHomeApp.forms.queries import get_add_status_choices, get_all_mds,\
    get_all_nps, get_update_status_choices
from nursingHomeApp.forms.notification_forms import STR_2_NONE


class AddPatientForm(FlaskForm):
    first = StringField('First Name', validators=[DataRequired()])
    last = StringField('Last Name', validators=[DataRequired()])
    room = StringField('Room No', validators=[DataRequired()])
    status = SelectField('Patient Status',
                         validators=[DataRequired(), check_if_required],
                         choices=get_add_status_choices, coerce=int)
    md = SelectField("Patient's Physician", validators=[DataRequired()],
                     choices=get_all_mds, coerce=int)
    np = SelectField("Patient's APRN", validators=[Optional()],
                     choices=get_all_nps, filters=[STR_2_NONE])
    lastVisit = DateField('Last Visited Date', validators=[Optional(), DateRange(max=datetime.now().date), gte_prior_visit])
    priorVisit = DateField('Last Visited by Doctor Date', validators=[Optional(), DateRange(max=datetime.now().date)])
    admittance = DateField('Admittance Date', validators=[Optional(), DateRange(max=datetime.now().date), admittance_date_validations])
    medicaid = BooleanField('Is patient insured through Medicaid?')
    submit = SubmitField('Add')


class UpdatePatientForm(FlaskForm):
    patientId = HiddenField('Patient Number')
    first = StringField('First Name', validators=[DataRequired()])
    last = StringField('Last Name', validators=[DataRequired()])
    room = StringField('Room No', validators=[DataRequired()])
    status = SelectField('Patient Status', validators=[DataRequired(), can_status_change], choices=get_update_status_choices, coerce=int)
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
