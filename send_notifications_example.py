from datetime import datetime, timedelta
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
import smtplib
import time
import traceback
import jinja2
import MySQLdb
import pytz
from tabulate import tabulate
from twilio.rest import Client

ADMINS = ['LIST_OF_ADMIN_EMAILS']
MYSQL_HOST = 'YOUR_MYSQL_HOST'
MYSQL_USER = 'YOUR_MYSQL_UNAME'
MYSQL_PASSWORD = 'YOUR_MYSQL_PW'
MYSQL_DB = 'YOUR_DB'
MAIL_SERVER = 'smtp.gmail.com:587'
MAIL_USE_TLS = True
MAIL_USERNAME = 'YOUR_EMAIL'
MAIL_PASSWORD = 'YOUR_MAIL_PW'
HEADERS = [['Name', 'Facility', 'Room', 'Last Visit', 
            'Next Required Visit (Doctor or Nurse)', 'Next Required Doctor Visit']]
HOMEPAGE = 'YOUR_HOMEPAGE_URL'
OPT_OUT_URL = '%s/opt/out/%s' % (HOMEPAGE, '%s')
INTRO = "Hello %s %s,\n\n Below are your patient's upcoming visit dates.\n\n"
MORE_INFO = ("\n\nFor more information regarding upcoming visits, login to your"
             " account here: %s\n\n" % HOMEPAGE)
OUTRO = ("\n\nFollow this link if you would like all notifications turned off:"
         " %s" % OPT_OUT_URL)
TEXT_ALERT = ("You have %s patient(s) due for a visit by %s or earlier at the"
              " Nursing Facility. The following patient(s) are due for"
              " a visit: %s. For a complete list please login on YOUR_HOMEPAGE.")
TWILIO_ACCOUNT_SID = "YOUR_TWILIO_ACCOUNT_SID"
TWILIO_AUTH_TOKEN = "YOUR_TWILIO_ACCOUNT_AUTH_TOKEN"
TWILIO_PHONE = "YOUR_TWILIO_PHONE_NUM"
SELECT_PATIENTS = """SELECT p.id, CONCAT_WS(' ', p.first, p.last), s.status,
p.room_number, p.admittance_date, p.has_medicaid, f.name FROM patient p
JOIN patient_status s ON s.id=p.status JOIN facility f ON f.id=p.facility_id
WHERE p.status != 3 AND (p.NP_ID=%s OR p.MD_ID=%s)"""
SELECT_LAST_APRN_VISIT = """SELECT max(visit_date) FROM visit
WHERE patient_id=%s AND visit_done_by_doctor=0"""
SELECT_LAST_DR_VISIT = """SELECT max(visit_date) FROM visit
WHERE patient_id=%s AND visit_done_by_doctor=1"""
SELECT_NOTIFICATIONS = """SELECT u.first, u.last, u.role, n.email,
n.designee_email, n.email_notification_on, n.notify_designee,
n.email_every_n_days, n.phone, n.phone_notification_on, n.sms_n_days_advance,
n.user_id, n.email_last_sent, n.text_last_sent FROM notification n
JOIN user u ON u.id=n.user_id"""
EMAIL_SENT = "UPDATE notification SET email_last_sent=NOW() WHERE user_id=%s"
TEXT_SENT = "UPDATE notification SET text_last_sent=NOW() WHERE user_id=%s"


def main():
    """See if text or email notifications need to be sent out"""
    conn = MySQLdb.connect(host=MYSQL_HOST, passwd=MYSQL_PASSWORD, db=MYSQL_DB,
                           user=MYSQL_USER)
    cursor = conn.cursor()
    # right now the app is running in a nursing home located on the east coast
    # only matters for sending out texts - only should send texts during daytime.
    current_tz = pytz.timezone('US/Eastern')
    current_hour = datetime.now(current_tz).hour
    today = datetime.now(current_tz).date()
    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    cursor.execute(SELECT_NOTIFICATIONS)
    # SELECT each clinician's (nurse or physician user) notification preferences
    # Only physician and nurse practitioner user role's receive notifications
    for (first, last, role, primary_email, secondary_email, notify_primary_email, 
         notify_secondary_email, days_between_email_notification, phone,
         notify_by_phone, days_before_overdue_text, clinician_id, last_email, 
         last_text) in cursor.fetchall():
        # fetch list of patient's assiged to the clinician (will be empty if none)
        patients = get_patient_info(clinician_id, cursor)
        # send an email every N days, where N is specified by user and stored in
        # the Notification table
        email_by = (last_email + timedelta(days=days_between_email_notification)).date()
        if email_by <= today and patients:
            # determine which email address's to send notification to, based on users preferences
            to = []
            if primary_email and notify_primary_email:
                to.append(primary_email)
            if secondary_email and notify_secondary_email:
                to.append(secondary_email)
            if to: # only send email if there is someone to send it to
                # generate the body of the email (html & plaintext)
                formatted = format_patient_info(patients)
                html = render_jinja_html('notification_template.html', first=first,
                                         last=last, patients=formatted,
                                         opt_out_url=OPT_OUT_URL % clinician_id,
                                         homepage=HOMEPAGE)
                plain = tabulate([x[:-2] for x in formatted], headers=HEADERS)
                plain = INTRO % (first, last) + plain + MORE_INFO + OUTRO % clinician_id
                send_email(to, "Your Upcoming Patient Visits", html, plain)
                # update last e-mail sent timestamp
                cursor.execute(EMAIL_SENT, (clinician_id,))
        # days_before_overdue_text is another notification preference set by the user
        # it is an integer value (can be negative)
        notify_by = today + timedelta(days=days_before_overdue_text)
        # send a text at most once every week
        dont_notify_before = (last_text + timedelta(days=7)).date()
        # only send a text between the hours of 9 and 6 east coast time
        # only send if the user has text notifications on
        # for now only physicians receieve text message notifications
        if (phone and notify_by_phone and dont_notify_before <= today
                and 9 < current_hour <= 18 and role == 'Physician'):
            overdue_patients = []
            for (_, name, status, _, admit, mcaid, _, last_nurse_visit,
                 last_dr_visit) in patients:
                next_visit, next_doctor_visit = get_next_visit_dates(status,
                                                                     last_nurse_visit,
                                                                     last_dr_visit,
                                                                     admit, mcaid)
                if next_visit <= notify_by and next_visit == next_doctor_visit:
                    # anonomize patient names
                    name = ' '.join('%s****%s' % (x[0], x[-1]) for x in name.split())
                    overdue_patients.append(name)
            if overdue_patients:
                if not phone.startswith('1'):
                    phone = '1' + phone
                phone = '+' + phone
                msg = TEXT_ALERT % (len(overdue_patients),
                                    notify_by.strftime("%m/%d/%Y"),
                                    ", ".join(overdue_patients))
                client.messages.create(phone, body=msg, from_=TWILIO_PHONE)
                # update last text sent timestamp
                cursor.execute(TEXT_SENT, (clinician_id,))
    conn.commit()
    conn.close()


def send_email(to, subject, html, plaintext):
    """Sends an email.
    Args:
        subject: the subject of the email (a String)
        to: List of recipients (Strings)
        html: body of the email as HTML
        plaintext: body of the email as a plaintext value
    """
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = MAIL_USERNAME
    msg['To'] = ', '.join(to)
    if plaintext:
        part1 = MIMEText(plaintext, 'plain')
        msg.attach(part1)
    if html:
        part2 = MIMEText(html, 'html')
        msg.attach(part2)
    server = smtplib.SMTP(MAIL_SERVER)
    server.ehlo()
    server.starttls()
    server.login(MAIL_USERNAME, MAIL_PASSWORD)
    server.sendmail(MAIL_USERNAME, to, msg.as_string())
    server.quit()


def render_jinja_html(file_name, **context):
    """Renders a HTML file written using jinja's templating"""
    return jinja2.Environment(loader=jinja2.FileSystemLoader('')).get_template(file_name).render(context)


def get_patient_info(clinician_id, cursor):
    """Gets patients id, name, status, room no, nurse's name, doctor's name,
    admit date, last visit date, last visit by doctor date for all active
    patients assigned to the clinician"""
    patients = []
    cursor.execute(SELECT_PATIENTS % (clinician_id, clinician_id))
    for patient in cursor.fetchall():
        for visit in [SELECT_LAST_APRN_VISIT, SELECT_LAST_DR_VISIT]:
            if cursor.execute(visit, (patient[0],)):
                patient += cursor.fetchone()
            else:
                patient += (None,)
        patients.append(patient)
    return patients


def format_patient_info(patients):
    """Takes list of patient data fetched from the database (see get_patient_info)
    and makes minor changes for display to user.
    """
    rows = []
    for (_, name, status, room, admit, mcaid, facility, last_nurse_visit,
         last_dr_visit) in patients:
        # anonomize patient name
        name = ' '.join('%s****%s' % (x[0], x[-1]) for x in name.split())
        if not last_nurse_visit and not last_dr_visit:
            last_visit = 'None'
        elif last_dr_visit and (not last_nurse_visit or last_dr_visit > last_nurse_visit):
            last_visit = last_dr_visit.strftime('%m/%d/%Y, Doctor')
        else:
            # APRN == Nurse
            last_visit = last_nurse_visit.strftime('%m/%d/%Y, APRN')
        next_visit, next_dr_visit = get_next_visit_dates(status, last_nurse_visit, 
                                                         last_dr_visit, admit, mcaid)
        visit_description = next_visit.strftime('%m/%d/%Y')
        next_dr_visit_description = next_dr_visit.strftime('%m/%d/%Y')
        if next_visit == next_dr_visit:
            visit_description += ' (Doctor)'
        # number of days until due date
        today = datetime.today().date()
        days_to_visit = (today - next_visit).days
        days_to_dr_visit = (today - next_dr_visit).days
        rows.append([name, facility, room, last_visit, visit_description,
                     next_dr_visit_description, days_to_visit, days_to_dr_visit])
    return sorted(rows, key=lambda x: (x[1], x[-1]))


def get_next_visit_dates(status, last_nurse_visit, last_dr_visit, admit, mcaid):
    """Returns: A tuple of two datetime objects representing the next patient 
    visit, and the next patient visit that must be administered by a doctor.
    These two dates may be the same.
    
    Args:
        status: A string which represents the patient's status. May be one of 
                'Long Term Care', 'Skilled Care / New Admission', 
                'Assisted Living'. A patient may also have a status of 
                'Discharged' but these patients are filtered out before this
                function is called, as they don't have a next visit date.
        last_nurse_visit: datetime object representing last time a nurse visited
                          the patient, will be None if there was no last visit.
        last_dr_visit: same as last_nurse_visit but for a doctor.
        admit: datetime object representing when a patient was admitted
        mcaid: a boolean representing whether the patient is on medicaid.
    """
    # Determine when the patient was most recently visited. If the patient
    # has not been visited yet, their admit date is instead used.
    last_visit = max(x for x in (last_dr_visit, last_nurse_visit, admit) if x)

    # If a patient is in long term care, they only need to be visited by a dr
    # every 365 days, unless they are on medicaid then it is every 120 days.
    # Additionally they must be visited at a minimum every 60 days (by anyone)
    if status == 'Long Term Care':
        # if a patient is in long term care, an assumption is made that they
        # must have ben visited by a doctor at some point in the past
        next_dr_visit = last_dr_visit + timedelta(days=365 if mcaid else 120)
        next_visit = min(last_visit + timedelta(days=60), next_dr_visit)
    # If a patient is in Skilled Care / New Admission then 3 visits 30 days apart
    # are required, the first of which must be administered by a doctor. After
    # that visit, the doctor is required to make a second visit before 60 days -
    # same requirement as Long Term Care
    elif status == 'Skilled Care / New Admission':
        next_visit = last_visit + timedelta(days=30)
        if last_visit == last_dr_visit:
            next_dr_visit = last_dr_visit + timedelta(days=60)
        else:
            next_dr_visit = next_visit
    # status is assisted living. this requires the patient be seen annually by
    # a doctor. that is the only requirement.
    else:
        next_visit = next_dr_visit = last_dr_visit + timedelta(days=365)
    return next_visit, next_dr_visit


if __name__ == '__main__':
    # run in endless loop, if crashes sends an email w/ traceback
    try:
        while True:
            main()
            time.sleep(300)
    except Exception:
        send_email(ADMINS, "Error in send_notifications.py script", None, traceback.format_exc())
