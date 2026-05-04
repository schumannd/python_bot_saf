import time
import requests
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import constants
import secrets

BERLIN = ZoneInfo("Europe/Berlin")
# Cron can stay at a fixed UTC time (e.g. 05:30); we align behavior with Europe/Berlin.
FLOW_START_HOUR = 7
FLOW_START_MINUTE = 20
FLOW_LATE_CUTOFF_HOUR = 7
FLOW_LATE_CUTOFF_MINUTE = 55


def log_line(log_entry):
    timestamp = datetime.now(BERLIN).strftime("%Y-%m-%d %H:%M:%S %Z")
    with open(constants.LOG_FILE, "a") as f:
        f.write(f"[{timestamp}] {log_entry}\n")


def send_msg(msg, tg_user_id):
    proxies = {
        "http": "http://proxy.server:3128",
        "https": "http://proxy.server:3128",
    }
    url = f"https://api.telegram.org/bot{secrets.TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": tg_user_id, "text": msg}
    try:
        response = requests.post(url, json=payload, proxies=proxies, timeout=10)
        print(
            f"DEBUG: Sent message: {msg} \nto {tg_user_id}. Status: {response.status_code}, Response: {response.text}"
        )
    except Exception as e:
        print(f"DEBUG: Critical Error sending TG: {e}")


def send_tg(msg, tg_user_id=None):
    if tg_user_id:
        send_msg(msg, tg_user_id)

    for admin_id in constants.ADMIN_IDS:
        send_msg(msg, admin_id)


def live_recipient_for_weekday(weekday):
    if weekday == 1:
        return constants.LIVE_RECIPIENT_TUESDAY
    if weekday == 2:
        return constants.LIVE_RECIPIENT_WEDNESDAY
    return None


def send_email(recipient):
    msg = MIMEText(
        "Guten Morgen,\n\n"
        "ich melde mich heute ab — ich komme gar nicht.\n"
        "Abmeldung / not coming at all.\n\n"
        "LG Sofia"
    )
    msg["Subject"] = "Abmeldung"
    msg["From"] = constants.GMAIL_USER
    msg["To"] = recipient

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(constants.GMAIL_USER, secrets.GMAIL_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        send_tg(f"⚠️ Email Error: {e}")
        return False


def weekday_label(weekday):
    return ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][weekday]


def sleep_until_flow_start(now_berlin):
    start = now_berlin.replace(
        hour=FLOW_START_HOUR, minute=FLOW_START_MINUTE, second=0, microsecond=0
    )
    if now_berlin >= start:
        return datetime.now(BERLIN)
    delay = (start - now_berlin).total_seconds()
    if delay > 0:
        time.sleep(delay)
    return datetime.now(BERLIN)


def is_past_late_cutoff(now_berlin):
    cutoff = now_berlin.replace(
        hour=FLOW_LATE_CUTOFF_HOUR, minute=FLOW_LATE_CUTOFF_MINUTE, second=0, microsecond=0
    )
    return now_berlin > cutoff


def run_for_weekday(weekday):
    recipient = (
        constants.DEBUG_RECIPIENT
        if constants.DEBUG_MODE
        else live_recipient_for_weekday(weekday)
    )

    with open(constants.STATUS_FILE, "r") as f:
        status = f.read().strip()

    day = weekday_label(weekday)

    if status == "YES":
        precancel_log = f"Pre-cancelled: Skipping {day} run entirely."
        log_line(precancel_log)
        with open(constants.STATUS_FILE, "w") as f:
            f.write("NO")
        send_msg(precancel_log, constants.DEBUG_ID)
        return

    send_at = (datetime.now(BERLIN) + timedelta(minutes=10)).strftime("%H:%M")
    send_tg(
        f"🔔 10-MINUTE WARNING: Abmeldung email sending at {send_at} Berlin. Send 'stop' now to cancel."
    )

    time.sleep(600)

    with open(constants.STATUS_FILE, "r") as f:
        if f.read().strip() == "YES":
            stop_log = f"🛑 'Stop' received during countdown. Email NOT sent ({day})."
            log_line(stop_log)
            send_tg(stop_log)
            with open(constants.STATUS_FILE, "w") as f:
                f.write("NO")
            return

    if send_email(recipient):
        success_log = f"✅ Abmeldung email sent ({day})."
        log_line(success_log)
        send_tg(success_log)
        with open(constants.STATUS_FILE, "w") as f:
            f.write("NO")


def main():
    now_berlin = datetime.now(BERLIN)
    weekday = now_berlin.weekday()

    if weekday not in (1, 2):
        return

    if is_past_late_cutoff(now_berlin):
        log_line(f"Start after {FLOW_LATE_CUTOFF_HOUR:02d}:{FLOW_LATE_CUTOFF_MINUTE:02d} Berlin; skipping.")
        return

    now_berlin = sleep_until_flow_start(now_berlin)
    if is_past_late_cutoff(now_berlin):
        log_line("Passed late cutoff after wait; skipping.")
        return

    run_for_weekday(weekday)


if __name__ == "__main__":
    main()
