from flask_wtf import FlaskForm
from wtforms import SubmitField, StringField, HiddenField, BooleanField
from wtforms.validators import DataRequired
from wtforms_components import SelectField, SelectMultipleField
from nursingHomeApp.common_queries import get_doctors_not_at_facility, get_nurses_not_at_facility

states = ["AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DC", "DE", "FL", "GA",
          "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
          "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
          "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
          "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY"]


class AddFacilityForm(FlaskForm):
    facilityId = HiddenField('Facility Number')
    name = StringField('Facility Name', validators=[DataRequired()])
    address = StringField('Street Address', validators=[DataRequired()])
    city = StringField('City', validators=[DataRequired()])
    state = SelectField('State', validators=[DataRequired()],
                        choices=[(x, x) for x in states])
    zipcode = StringField('Zipcode', validators=[DataRequired()])
    floors = SelectField('Number of Floors', validators=[DataRequired()],
                         choices=[(x, x) for x in range(1, 50)], coerce=int)
    active = BooleanField('Active')
    submit = SubmitField('Add')


class AddCliniciansForm(FlaskForm):
    doctors = SelectMultipleField('Add Doctors', render_kw={"multiple": "multiple"},
                                   choices=get_doctors_not_at_facility, coerce=int)
    nurses = SelectMultipleField('Add Nurses', render_kw={"multiple": "multiple"},
                                  choices=get_nurses_not_at_facility, coerce=int)
    submit = SubmitField('Add Clinicians')
