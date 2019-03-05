from wtforms.validators import ValidationError
from nursingHomeApp.common_queries import get_patient_visits



# error messages
VISITS_REQUIRED = ('The last visit date and last doctor visit date '
                   'are required when adding a patient in Long Term Care or '
                   'Assisted Living.')
LAST_VISIT_MISSING = ('Please include the Last Visit Date. '
                      'If it is the same as the Last Doctor Visit Date, put the '
                      'same date.')
INVALID_DR_VISIT = ('Last Doctor Visit Must have come before or be equal to '
                    'the Last Visit date')
ADMIT_DATE_AFTER_LV = "Admittance date cannot be after last visit date."
ADMIT_DATE_AFTER_PV = "Admittance date cannot be after last doctor visit date."
VISIT_DATE_REQS = ('Patient must have at least 2 visits done, 1 of them by a '
                   'Doctor in order to move into Long Term Care or Skilled Care')


def gte_prior_visit(form, field):
    """The last doctor visit must be LTE the last overall visit, also if
    the last doctor visit was input by user, the last overall visit must
    also be specified (ok if the two are the same).
    """
    if form.priorVisit.data and not form.lastVisit.data:
        raise ValidationError(LAST_VISIT_MISSING)
    elif form.priorVisit.data and form.lastVisit.data:
        if form.priorVisit.data > form.lastVisit.data:
            raise ValidationError(INVALID_DR_VISIT)


def check_if_required(form, field):
    """If a patient being added has a status of 1 (Long Term Care) or 4 
    (Assissted Living), they have been at the facility past the New Admission
    stage and must have been visited by a doctor at some point, hence the
    visit date fields become required.

    When calculating the next visit date for a patient with a status of
    Long Term Care or Assisted Living, the last visit date is assumed to
    exist, so it is required here.

    If a patient has a status of 2 (Skilled Care / New Admission), this 
    assumption is not made, and if a prior visit doesn't exist the admittance
    date is instead used to determine when the next visit should occur.
    """
    if form.status.data in {1, 4}:
        if not form.lastVisit.data or not form.priorVisit.data:
            raise ValidationError(VISITS_REQUIRED)


def admittance_date_validations(form, field):
    """The patient cannot have been visited BEFORE they were admitted.
    """
    if form.admittance.data and form.lastVisit.data:
        if form.admittance.data > form.lastVisit.data:
            raise ValidationError(ADMIT_DATE_AFTER_LV)
    if form.admittance.data and form.priorVisit.data:
        if form.admittance.data > form.priorVisit.data:
            raise ValidationError(ADMIT_DATE_AFTER_PV)


def can_status_change(form, field):
    """If a patient is being updated to a status of 1 (Long Term Care) or 4 
    (Assissted Living), they have been at the facility past the New Admission
    stage and must have been visited by a doctor at some point, hence the
    visit date fields become required.
    """
    if form.status.data in {1, 4}:
        visits = get_patient_visits(form.patientId.data)
        if len(visits) < 2 or not any(v[0] for v in visits):
            raise ValidationError(VISIT_DATE_REQS)


# everything below this line was for the LoadPatientForm (currently depreciated), 
# may need to be reworked


# import csv
# from datetime import datetime
# from wtforms.validators import StopValidation
# from nursingHomeApp.common_queries import get_all_nps, get_all_mds

# error messages

# INVALID_PATIENT_STATUS = """The Patient Status '%s' on row %s is invalid.
# Patient status must be one of: Skilled Care, Long Term Care, New Admission."""
# PATIENT_COUNT_REQUIRED = "Must be between 1 and 1000 patients in file."
# NUM_COLS_REQUIRED = "Rows must be 12 fields long. Row %s has only %s fields."
# REQUIRED_FIELDS = """First Name, LastName, Room No, Patient Status,
# Patient's MD are required fields. At least 1 field is missing from row %s."""
# INVALID_DATE_FMT = """Invalid date format on row %s.
# Valid date format is: YYYY-mm-dd."""
# PHYSICIAN_NOT_FOUND = """Physician '%s' on row %s not found. Make sure just
# first and last name are listed, and that they have been added as a user."""
# NURSE_NOT_FOUND = """Nurse '%s' on row %s not found. Make sure just first and
# last name are listed, and that they have been added as a user."""

# def validate_status_allowed(form, field):
#     """lv == Last Vist, lvByDr == Last Visit by Doctor"""
#     # no longer accurate - skilled care and new admission were combined into 1 status
#     VALID_PATIENT_STATUS = {'skilled care', 'long term care', 'new admission', 'assisted living'}
#     reader = csv.reader(form.upload.data, skipinitialspace=True)
#     next(reader)
#     for i, row in enumerate(reader, 2):
#         first, last, room, status, md, np, lv, lvByDr, admit, medicaid = row
#         status = ' '.join(x for x in status.split(' ') if x).lower()
#         if status in {'long term care', 'skilled care', 'assisted living'} and (not lv or not lvByDr):
#             form.upload.data.seek(0)
#             raise ValidationError(VISITS_REQUIRED)
#         elif status not in VALID_PATIENT_STATUS:
#             form.upload.data.seek(0)
#             raise ValidationError(INVALID_PATIENT_STATUS % (status, i))
#     form.upload.data.seek(0)


# def validate_num_lines(form, field):
#     numLines = sum(1 for line in form.upload.data)
#     form.upload.data.seek(0)
#     if not 2 <= numLines <= 1000:
#         raise StopValidation(PATIENT_COUNT_REQUIRED)


# def validate_line_len(form, field):
#     reader = csv.reader(form.upload.data, skipinitialspace=True)
#     next(reader)
#     for i, row in enumerate(reader, 2):
#         if len(row) == 10 or not any(row):
#             continue
#         raise StopValidation(NUM_COLS_REQUIRED % (i, len(row)))
#     form.upload.data.seek(0)


# def validate_required_fields(form, field):
#     reader = csv.reader(form.upload.data, skipinitialspace=True)
#     next(reader)
#     for i, row in enumerate(reader, 2):
#         first, last, room, status, md, np, lv, lvByDr, admit, medicaid = row
#         if not any([first, last, room, status, md]):
#             form.upload.data.seek(0)
#             raise ValidationError(REQUIRED_FIELDS % i)
#     form.upload.data.seek(0)


# def validate_date_format(form, field):
#     reader = csv.reader(form.upload.data, skipinitialspace=True)
#     next(reader)
#     for i, row in enumerate(reader, 2):
#         first, last, room, status, md, np, lv, lvByDr, admit, medicaid = row
#         for dt in (lv, lvByDr, admit):
#             if dt:
#                 try:
#                     dt = datetime.strptime(dt, '%Y-%m-%d').date()
#                 except ValueError:
#                     form.upload.data.seek(0)
#                     raise ValidationError(INVALID_DATE_FMT % i)
#     form.upload.data.seek(0)


# def validate_mds(form, field):
#     mds = {x[1].lower() for x in get_all_mds()}
#     reader = csv.reader(form.upload.data, skipinitialspace=True)
#     next(reader)
#     for i, row in enumerate(reader, 2):
#         first, last, room, status, md, np, lv, lvByDr, admit, medicaid = row
#         md = ' '.join(x for x in md.split(' ') if x).lower()
#         if md not in mds:
#             form.upload.data.seek(0)
#             raise ValidationError(PHYSICIAN_NOT_FOUND % (md, i))
#     form.upload.data.seek(0)


# def validate_nps(form, field):
#     nps = {x[1].lower() for x in get_all_nps()}
#     reader = csv.reader(form.upload.data, skipinitialspace=True)
#     next(reader)
#     for i, row in enumerate(reader, 2):
#         first, last, room, status, md, np, lv, lvByDr, admit, medicaid = row
#         np = ' '.join(x for x in np.split(' ') if x).lower()
#         if np and np not in nps:
#             form.upload.data.seek(0)
#             raise ValidationError(NURSE_NOT_FOUND % (np, i))
#     form.upload.data.seek(0)
