import time, MySQLdb, datetime, smtplib, traceback, jinja2, pytz
from tabulate import tabulate
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
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
headers = [['Name', 'Facility', 'Room', 'Last Visit', 'Next Required Visit (Doctor or Nurse)', 'Next Required Doctor Visit']]
homepage = 'YOUR_HOMEPAGE_URL'
opt_out_url = '%s/opt/out/%s' % (homepage, '%s')
INTRO = "Hello %s %s,\n\n Below are your patient's upcoming visit dates.\n\n"
MORE_INFO = "\n\nFor more information regarding upcoming visits, login to your account here: %s\n\n" % homepage
OUTRO = "\n\nFollow this link if you would like all notifications turned off: %s" % opt_out_url
TEXT_ALERT = "You have %s patient(s) due for a visit by %s or earlier. The following patient(s) are due for a visit: %s. For a complete list please login on YOUR_HOMEPAGE_URL."
account_sid = "YOUR_TWILIO_ACCOUNT_SID"
auth_token = "YOUR_TWILIO_ACCOUNT_AUTH_TOKEN"
myPhone = "YOUR_PHONE_NUM"
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
    conn = MySQLdb.connect(host=MYSQL_HOST, passwd=MYSQL_PASSWORD, db=MYSQL_DB, user=MYSQL_USER)
    cursor = conn.cursor()
    tz = pytz.timezone('US/Eastern')
    curHour = datetime.datetime.now(tz).hour
    today = datetime.datetime.now(tz).date()
    client = Client(account_sid, auth_token)
    cursor.execute(SELECT_NOTIFICATIONS)
    for notification in cursor.fetchall():
        (first, last, role, email, designee, emailOn, designeeOn, nDays, phone,
            phOn, smsDays, userId, lastEmail, lastText) = notification
        patients = get_patient_info(userId, cursor)
        # send email every N days, where N is specified by user and stored in the Notification table
        nextEmail = (lastEmail + datetime.timedelta(days=nDays)).date()
        if (email and emailOn or designee and designeeOn) and nextEmail <= today and patients:
            to = []
            if email and emailOn:
                to.append(email)
            if designee and designeeOn:
                to.append(designee)
            formatted = format_patient_info(patients)
            # plaintext added in case e-mail provider doesn't accept HTML message
            html = render_jinja_html('notification_template.html', first=first,
                                     last=last, patients=formatted,
                                     opt_out_url=opt_out_url % userId,
                                     homepage=homepage)
            plain = tabulate([x[:-2] for x in formatted], headers=headers)
            plain = INTRO % (first, last) + plain + MORE_INFO + OUTRO % userId
            send_email(to, "Your Upcoming Patient Visits", html, plain)
            # update last e-mail sent timestamp
            cursor.execute(EMAIL_SENT, (userId,))
        notifyBy = today + datetime.timedelta(days=smsDays)
        # send a text at most once every week - User can configure a larger time period if desired, or turn off text notifications entirely.
        nextText = lastText + datetime.timedelta(days=7)
        # only send a text between the hours of 9 and 6 east coast time.
        if phone and phOn and nextText.date() <= today and 9 < curHour <= 18:
            toVisit = []
            for pId, name, status, rm, admit, mcaid, facility, lv, lvByDr in patients:
                nv, nvByDr = get_next_visit_dates(status, lv, lvByDr, admit, mcaid)
                # for now only physicians receieve text message notifications
                if nv <= notifyBy and (nv == nvByDr) == (role == 'Physician'):
                    # anonomize patient names
                    name = ' '.join('%s****%s' % (x[0], x[-1]) for x in name.split())
                    toVisit.append(name)
            if toVisit:
                if not phone.startswith('1'):
                    phone = '1' + phone
                phone = '+' + phone
                msg = TEXT_ALERT % (len(toVisit), notifyBy.strftime("%m/%d/%Y"), ", ".join(toVisit))
                client.messages.create(phone, body=msg, from_=myPhone)
                cursor.execute(TEXT_SENT, (userId,))
    conn.commit()
    conn.close()


def send_email(to, subject, html, plaintext):
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
    return jinja2.Environment(loader=jinja2.FileSystemLoader('')).get_template(file_name).render(context)


def get_patient_info(userId, cursor):
    """Gets patients id, name, status, room no, nurse's name, doctor's name,
    admit date, last visit date, last visit by doctor date for all active
    patients assigned to the user"""
    patients = []
    cursor.execute(SELECT_PATIENTS % (userId, userId))
    for p in cursor.fetchall():
        for visit in [SELECT_LAST_APRN_VISIT, SELECT_LAST_DR_VISIT]:
            if cursor.execute(visit, (p[0],)):
                p += cursor.fetchone()
            else:
                p += (None,)
        patients.append(p)
    return patients


def format_patient_info(patients):
    rows = []
    for pId, name, status, rm, admit, mcaid, facility, lvByN, lvByDr in patients:
        # anonomize patient name
        name = ' '.join('%s****%s' % (x[0], x[-1]) for x in name.split())
        if not lvByN and not lvByDr:
            lvDesc = 'None'
        elif lvByDr and (not lvByN or lvByDr > lvByN):
            lvDesc = lvByDr.strftime('%m/%d/%Y, Doctor')
        else:
            # APRN == Nurse
            lvDesc = lvByN.strftime('%m/%d/%Y, APRN')
        nv, nvByDr = get_next_visit_dates(status, lvByN, lvByDr, admit, mcaid)
        nvDesc, nvByDrDesc = (dt.strftime('%m/%d/%Y') for dt in (nv, nvByDr))
        if nvDesc == nvByDrDesc:
            nvDesc += ' (Doctor)'
        # number of days until due date
        nvDays, nvByDrDays = ((x - datetime.datetime.today().date()).days for x in (nv, nvByDr))
        rows.append([name, facility, rm, lvDesc, nvDesc, nvByDrDesc, nvDays, nvByDrDays])
    return sorted(rows, key=lambda x: (x[1], x[-1]))


def get_next_visit_dates(status, lvByN, lvByDr, admit, mcaid):
    """Returns: Next patient visit, next patient visit that must be
    administered by a doctor. lvByN and lvByDr inputs may both be null"""
    if lvByDr and lvByN:
        lv = max(lvByDr, lvByN)
    else:
        lv = lvByDr or lvByN or admit
    if status == 'Long Term Care':
        nvByDr = (lvByDr or lv) + datetime.timedelta(days=365 if mcaid else 120)
        nv = min(lv + datetime.timedelta(days=60), nvByDr)
    elif status == 'Skilled Care / New Admission':
        nv = lv + datetime.timedelta(days=30)
        if lv == lvByDr:
            nvByDr = lvByDr + datetime.timedelta(days=60)
        else:
            nvByDr = nv
    else:  # status is assisted living
        nv = nvByDr = (lvByDr or lv) + datetime.timedelta(days=365)
    return nv, nvByDr


if __name__ == '__main__':
    # run in endless loop, if crashes sends an email w/ traceback
    try:
        while True:
            main()
            time.sleep(300)
    except:
        send_email(ADMINS, "Error in send_notifications.py script", None, traceback.format_exc())
