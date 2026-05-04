import time
import requests
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import constants
import secrets

BERLIN = ZoneInfo("Europe/Berlin")
# Cron runs at fixed UTC (e.g. 05:30); waits below align sends with Europe/Berlin local morning.
FLOW_START_HOUR = 7
FLOW_START_MINUTE = 20
FLOW_LATE_CUTOFF_HOUR = 7
FLOW_LATE_CUTOFF_MINUTE = 55
COUNTDOWN_SECONDS = 600

PA_PROXY = {"http": "http://proxy.server:3128", "https": "http://proxy.server:3128"}

WEEKDAY_SHORT = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")

LIVE_RECIPIENT = {
    1: constants.LIVE_RECIPIENT_TUESDAY,
    2: constants.LIVE_RECIPIENT_WEDNESDAY,
}


def log_line(entry):
    ts = datetime.now(BERLIN).strftime("%Y-%m-%d %H:%M:%S %Z")
    with open(constants.LOG_FILE, "a") as f:
        f.write(f"[{ts}] {entry}\n")


def read_status():
    with open(constants.STATUS_FILE) as f:
        return f.read().strip()


def write_status(value):
    with open(constants.STATUS_FILE, "w") as f:
        f.write(value)


def send_msg(chat_id, text):
    url = f"https://api.telegram.org/bot{secrets.TELEGRAM_TOKEN}/sendMessage"
    try:
        r = requests.post(
            url, json={"chat_id": chat_id, "text": text}, proxies=PA_PROXY, timeout=10
        )
        print(f"DEBUG: TG to {chat_id} status={r.status_code} body={r.text}")
    except Exception as e:
        print(f"DEBUG: TG error to {chat_id}: {e}")


def send_tg(text, also_chat_id=None):
    if also_chat_id is not None:
        send_msg(also_chat_id, text)
    for admin_id in constants.ADMIN_IDS:
        send_msg(admin_id, text)


def send_email(to_addr):
    body = MIMEText(
        "Guten Morgen,\n\n"
        "ich schaffe es heute leider nicht mehr zu kommen.\n\n"
        "Viele Grüße, Sofia"
    )
    body["Subject"] = "Abmeldung"
    body["From"] = constants.GMAIL_USER
    body["To"] = to_addr

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
            s.login(constants.GMAIL_USER, secrets.GMAIL_PASSWORD)
            s.send_message(body)
        write_status("NO")
        return True
    except Exception as e:
        send_tg(f"⚠️ Email Error: {e}")
        return False


def flow_start_dt(now):
    return now.replace(
        hour=FLOW_START_HOUR, minute=FLOW_START_MINUTE, second=0, microsecond=0
    )


def sleep_until_flow_start(now):
    start = flow_start_dt(now)
    hhmm = f"{FLOW_START_HOUR:02d}:{FLOW_START_MINUTE:02d}"
    if now >= start:
        log_line(
            f"Flow-start sleep: 0s (past {hhmm} Berlin; now {now:%Y-%m-%d %H:%M:%S %Z})."
        )
        return datetime.now(BERLIN)
    delay = start - now
    secs = delay.total_seconds()
    log_line(
        f"Flow-start sleep: {secs:.0f}s (~{secs / 60:.2f} min) until {start:%H:%M} Berlin "
        f"(started {now:%Y-%m-%d %H:%M:%S %Z})."
    )
    time.sleep(secs)
    woke = datetime.now(BERLIN)
    log_line(f"Flow-start sleep: done ({secs:.0f}s); now {woke:%Y-%m-%d %H:%M:%S %Z}.")
    return woke


def is_past_late_cutoff(now):
    cutoff = now.replace(
        hour=FLOW_LATE_CUTOFF_HOUR,
        minute=FLOW_LATE_CUTOFF_MINUTE,
        second=0,
        microsecond=0,
    )
    return now > cutoff


def stop_abort_after_countdown(day):
    """If user cancelled via Telegram (YES): clear NO, notify, return True (= do not send)."""
    if read_status() != "YES":
        return False
    msg = f"🛑 'Stop' received during countdown. Email NOT sent ({day})."
    log_line(msg)
    send_tg(msg)
    write_status("NO")
    return True


def run_send_flow(weekday):
    recipient = (
        constants.DEBUG_RECIPIENT
        if constants.DEBUG_MODE
        else LIVE_RECIPIENT[weekday]
    )

    day = WEEKDAY_SHORT[weekday]

    if read_status() == "YES":
        line = f"Pre-cancelled: Skipping {day} run entirely."
        log_line(line)
        write_status("NO")
        send_msg(constants.DEBUG_ID, line)
        return

    send_at = datetime.now(BERLIN) + timedelta(seconds=COUNTDOWN_SECONDS)
    send_tg(
        f"🔔 10-MINUTE WARNING: Abmeldung email sending at {send_at:%H:%M} Berlin. "
        "Send 'stop' now to cancel."
    )

    time.sleep(COUNTDOWN_SECONDS)

    if stop_abort_after_countdown(day):
        return

    berlin_now = datetime.now(BERLIN)
    if is_past_late_cutoff(berlin_now):
        line = (
            f"Late cutoff after countdown ({berlin_now:%Y-%m-%d %H:%M:%S %Z}); no send ({day})."
        )
        log_line(line)
        cutoff_hm = f"{FLOW_LATE_CUTOFF_HOUR:02d}:{FLOW_LATE_CUTOFF_MINUTE:02d}"
        send_tg(
            f"⏭️ Kein Versand ({day}): nach Wartezeit später als {cutoff_hm} Berlin."
        )
        return

    if stop_abort_after_countdown(day):
        return

    if send_email(recipient):
        ok = f"✅ Abmeldung email sent ({day})."
        log_line(ok)
        send_tg(ok)


def main():
    constants.ensure_runtime_files()

    now = datetime.now(BERLIN)
    wd = now.weekday()
    if wd not in LIVE_RECIPIENT:
        return

    if is_past_late_cutoff(now):
        log_line(
            f"Start after {FLOW_LATE_CUTOFF_HOUR:02d}:{FLOW_LATE_CUTOFF_MINUTE:02d} Berlin; skipping."
        )
        return

    now = sleep_until_flow_start(now)
    if is_past_late_cutoff(now):
        log_line("Passed late cutoff after flow-start sleep; skipping.")
        return

    run_send_flow(wd)


if __name__ == "__main__":
    main()
