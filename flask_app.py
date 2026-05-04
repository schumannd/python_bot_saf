from flask import Flask, request
import requests
import constants
import secrets
from datetime import datetime

def log_message(log_entry):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(constants.MESSAGE_LOG_FILE, "a") as f:
        f.write(f"[{timestamp}] {log_entry}\n")

app = Flask(__name__)

# --- HEALTH CHECK ROUTE ---
@app.route('/')
def home():
    return f"Bot is alive! Status file: {constants.STATUS_FILE}"

@app.route('/webhook', methods=['POST'])
def webhook():
    # Mandatory Proxy for Free Tier
    proxies = {'http': 'http://proxy.server:3128', 'https': 'http://proxy.server:3128'}

    data = request.get_json()
    if not data or "message" not in data:
        return "OK", 200

    msg_obj = data["message"]
    user_id = msg_obj["from"]["id"]
    text = msg_obj.get("text", "").lower()

    log_message(f"{user_id}: {text}")

    # LOGGING: This will appear in your 'Server Log' (not Error Log)
    print(f"Received: '{text}' from {user_id}")

    if user_id in constants.ADMIN_IDS:
        if "info" in text:
            with open(constants.STATUS_FILE, "r") as f:
                email_status = f.read().strip()
            with open(constants.LOG_FILE, "r") as f:
                log_content = f.read().strip()
            reply = (
                f"📊 Debug Info:\n\n"
                f"Coming email cancelled (YES=skip next send): {email_status}\n\n"
                f"Email history debug log:\n{log_content}"
            )
        elif "stop" in text.lower():
            with open(constants.STATUS_FILE, "w") as f:
                f.write("YES")
            reply = "🛑 STOP RECEIVED. Next Abmeldung email cancelled."
        elif "reset" in text:
            with open(constants.STATUS_FILE, "w") as f:
                f.write("NO")
            reply = "🔄 RESET RECEIVED. Next email will send unless you stop again."
        else:
            reply = "I'm listening. Try 'info', 'stop' or 'reset'."
    else:
        # If the ID is wrong, we want to know!
        reply = f"Hello my little friend!"

    # Send the reply
    url = f"https://api.telegram.org/bot{secrets.TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": user_id, "text": reply}, proxies=proxies, timeout=5)
    except Exception as e:
        print(f"Reply failed: {e}")

    return "OK", 200

