import time
import requests
import smtplib
from email.mime.text import MIMEText
import constants
import secrets
from datetime import datetime

def log_line(log_entry):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(constants.LOG_FILE, "a") as f:
        f.write(f"[{timestamp}] {log_entry}\n")

def send_msg(msg, tg_user_id):
    # Explicitly define the mandatory PythonAnywhere proxy
    proxies = {
        'http': 'http://proxy.server:3128',
        'https': 'http://proxy.server:3128'
    }
    url = f"https://api.telegram.org/bot{secrets.TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": tg_user_id, "text": msg}
    try:
        response = requests.post(url, json=payload, proxies=proxies, timeout=10)
        # This will print in your Bash console so you can see the error
        print(f"DEBUG: Sent message: {msg} \nto {tg_user_id}. Status: {response.status_code}, Response: {response.text}")
    except Exception as e:
        print(f"DEBUG: Critical Error sending TG: {e}")

def send_tg(msg, tg_user_id=None):
    if tg_user_id:
        send_msg(msg, tg_user_id)

    for admin_id in constants.ADMIN_IDS:
        send_msg(msg, admin_id)

def send_email():
    recipient = constants.DEBUG_RECIPIENT if constants.DEBUG_MODE else constants.LIVE_RECIPIENT
    msg = MIMEText("Guten Morgen. \nIch verspäte mich heute etwas. \n\nLG Sofia")
    msg['Subject'] = "Verspätung"
    msg['From'] = constants.GMAIL_USER
    msg['To'] = recipient

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(constants.GMAIL_USER, constants.GMAIL_PASSWORD)
            server.send_message(msg)
        with open(constants.STATUS_FILE, "w") as f:
            f.write("NO")
        return True
    except Exception as e:
        send_tg(f"⚠️ Email Error: {e}")
        return False

# --- EXECUTION LOGIC ---
now = datetime.now()
day_of_week = now.strftime("%A")

if day_of_week == "Tuesday":
    # 1. IMMEDIATE CHECK: Was it cancelled earlier?
    with open(constants.STATUS_FILE, "r") as f:
        status = f.read().strip()

    if status == "YES":
        precancel_log = "Pre-cancelled: Skipping Tuesday run entirely."
        log_line(precancel_log)

        # RESET FOR NEXT WEEK: Prepare for next Tuesday
        with open(constants.STATUS_FILE, "w") as f:
            f.write("NO")

        send_msg(precancel_log, constants.DEBUG_ID)
        exit()

    # 2. WARNING PHASE: Only happens if status was "NO"
    send_tg("🔔 10-MINUTE WARNING: Sickness note sending at 07:50. Send 'stop' now to cancel.")

    # 3. WAIT THE 10 MINUTES
    time.sleep(600)

    # 4. FINAL CHECK: In case you sent 'stop' during the 10-minute wait
    with open(constants.STATUS_FILE, "r") as f:
        if f.read().strip() == "YES":
            stop_log = "🛑 'Stop' received during countdown. Email NOT sent."
            log_line(stop_log)
            send_tg(stop_log)
            # Reset for next week
            with open(constants.STATUS_FILE, "w") as f:
                f.write("NO")
        else:
            if send_email():
                success_log = "✅ Email successfully sent to Faculty."
                log_line(success_log)
                send_tg(success_log)
                # No need to reset here if you want it to be "NO" by default
                # But it's already "NO", so we're good.
else:
    send_msg(f"Today is {day_of_week}. Exit.", constants.DEBUG_ID)

