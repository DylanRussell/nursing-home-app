from datetime import date
from flask_wtf import FlaskForm
from wtforms import SubmitField, StringField, DateField, BooleanField,\
    HiddenField
from wtforms.validators import DataRequired, Optional
from wtforms_components import SelectField
from wtforms_components import DateRange
from nursingHomeApp.patient.validators import check_if_required, gte_prior_visit,\
    admittance_date_validations, can_status_change 
from nursingHomeApp.common_queries import get_add_status_choices, get_all_mds,\
    get_all_nps, get_update_status_choices
from nursingHomeApp.common_validators import STR_2_NONE



today = lambda: date.today()


class AddPatientForm(FlaskForm):
    """Add a patient to the patient table. Only tricky validation is the
    check_if_required -> see function docstring in validators.py for more
    info.

    Patient's admittance date must be before any visits administered.
    Patient's last visit date must be GTE their last doctor visit date.

    Skilled Visits field only relevant if a patient being added with a status of
    Skilled Care / New Admission, in which case they may have already received
    1 or 2 skilled visits prior to being added.
    """
    first = StringField('First Name', validators=[DataRequired()])
    last = StringField('Last Name', validators=[DataRequired()])
    room = StringField('Room No', validators=[DataRequired()])
    status = SelectField('Patient Status',
                         validators=[DataRequired(), check_if_required],
                         choices=get_add_status_choices, coerce=int)
    skilledVisits = SelectField('Number of Prior Skilled Visits',
                                choices=list(zip(range(3), range(3))), coerce=int)
    md = SelectField("Patient's Physician", validators=[DataRequired()],
                     choices=get_all_mds, coerce=int)
    np = SelectField("Patient's APRN", validators=[Optional()],
                     choices=get_all_nps, filters=[STR_2_NONE])
    lastVisit = DateField('Last Visited Date',
                          validators=[Optional(), DateRange(max=today),
                                      gte_prior_visit])
    priorVisit = DateField('Last Visited by Doctor Date',
                           validators=[Optional(), DateRange(max=today)])
    admittance = DateField('Admittance Date',
                           validators=[DataRequired(), DateRange(max=today),
                                       admittance_date_validations])
    medicaid = BooleanField('Is patient insured through Medicaid?')
    submit = SubmitField('Add')


class UpdatePatientForm(FlaskForm):
    """Updating a field will update the corresponding column in the patient
    table.

    Only tricky validation done here is can_status_change -> see that
    function docstring in validators.py for more details.
    """
    patientId = HiddenField('Patient Number')
    first = StringField('First Name', validators=[DataRequired()])
    last = StringField('Last Name', validators=[DataRequired()])
    room = StringField('Room No', validators=[DataRequired()])
    status = SelectField('Patient Status', validators=[DataRequired(),
                                                       can_status_change],
                         choices=get_update_status_choices, coerce=int)
    skilledVisits = SelectField('Number of Prior Skilled Visits',
                                choices=list(zip(range(3), range(3))), coerce=int)
    md = SelectField("Patient's Physician", validators=[DataRequired()], 
                     choices=get_all_mds, coerce=int)
    np = SelectField("Patient's APRN", validators=[Optional()], 
                     choices=get_all_nps, filters=[STR_2_NONE])
    medicaid = BooleanField('Is patient insured through Medicaid?')
    submit = SubmitField('Update')


# this form is currently depreciated. 
# see bottom of routes.py file for more info
# at the very least some of the validators need to be reworked before it is put back into use

# from flask_wtf.file import FileField, FileAllowed, FileRequired
# from nursingHomeApp.patient.validators import validate_num_lines,\
#     validate_line_len, validate_date_format, validate_required_fields,\
#     validate_mds, validate_nps, validate_status_allowed
# class LoadPatientsForm(FlaskForm):
#     """Load multiple patients into the patient table from a csv file"""
#     upload = FileField('Upload Patients', validators=[
#         FileRequired(),
#         FileAllowed(['csv'], 'csv only!'),
#         validate_num_lines,
#         validate_line_len,
#         validate_date_format,
#         validate_required_fields,
#         validate_mds,
#         validate_nps,
#         validate_status_allowed])
#     submit = SubmitField('Add')
