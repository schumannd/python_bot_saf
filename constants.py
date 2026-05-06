# --- TELEGRAM SETTINGS ---
import os

ADMIN_IDS = [
    13025101, # Davi
    5682098430 # Saf
    ]
DEBUG_ID = 13025101 # Davi

# --- EMAIL SETTINGS ---
GMAIL_USER = "sofia.fralova@gmail.com"

LIVE_RECIPIENT_TUESDAY = "samia.shakra@elisabethstift.berlin"
LIVE_RECIPIENT_WEDNESDAY = "aline.theobald@elisabethstift.berlin"  # replace with the real Wednesday address
DEBUG_RECIPIENT = "dnstra@gmail.com"

DEBUG_MODE = False

# --- FILE PATHS ---
# Using absolute paths ensures the Scheduled Task can find the file
STATUS_FILE = "/home/schumannd/tg_bot_saf/cancel_email.txt"
LOG_FILE = "/home/schumannd/tg_bot_saf/email_logs.txt"
MESSAGE_LOG_FILE = "/home/schumannd/tg_bot_saf/message_logs.txt"


def ensure_runtime_files():
    """Create STATUS / logs if missing so cron + Flask never die on first read."""
    if not os.path.isfile(STATUS_FILE):
        with open(STATUS_FILE, "w") as f:
            f.write("NO")
    if not os.path.isfile(LOG_FILE):
        open(LOG_FILE, "a").close()
    if not os.path.isfile(MESSAGE_LOG_FILE):
        open(MESSAGE_LOG_FILE, "a").close()

