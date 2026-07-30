import json
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
import requests

# -------------------------------------------------------------
# Configuration Variables
# -------------------------------------------------------------
BOT_TOKEN = "8983781306:AAHod4RCSd6G3L_A2stv_GQWLvOWm3S3LvQ"

# RapidAPI Pocket FM Credentials
API_KEY = "458a3845d8msh0e188bebe00200ep1933e2jsnc7b9327ac320"
API_HOST = "pocket-fm-api1.p.rapidapi.com"

OWNER_USERNAME = "@MGB_NOT_FREE_2"
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


# -------------------------------------------------------------
# Dummy Server (24/7 Hosting Ke Liye)
# -------------------------------------------------------------
class DummyServerHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"Pocket FM Downloader Bot is Running Live!")

    def log_message(self, format, *args):
        return


def run_dummy_server():
    server_address = ("", 8080)
    httpd = HTTPServer(server_address, DummyServerHandler)
    print("Server running on port 8080...")
    httpd.serve_forever()


# -------------------------------------------------------------
# Telegram Helper Functions
# -------------------------------------------------------------
def send_message(chat_id, text):
    """Message bhejne ke liye"""
    url = f"{BASE_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Error sending message: {e}")


def send_audio(chat_id, audio_url, title="Pocket FM Episode"):
    """Telegram par Direct Audio File Bhejne ke liye"""
    url = f"{BASE_URL}/sendAudio"
    payload = {
        "chat_id": chat_id,
        "audio": audio_url,
        "caption": f"🎧 <b>{title}</b>\n\nDownloaded via Pocket FM Bot"
    }
    try:
        res = requests.post(url, json=payload)
        return res.json()
    except Exception as e:
        print(f"Error sending audio: {e}")
        return None


def get_updates(offset=None):
    """New messages fetch karne ke liye"""
    url = f"{BASE_URL}/getUpdates"
    params = {"timeout": 30, "offset": offset}
    try:
        response = requests.get(url, params=params, timeout=35)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Error fetching updates: {e}")
    return None


# -------------------------------------------------------------
# Pocket FM API Handler (Audio Fetching Logic)
# -------------------------------------------------------------
def fetch_pocketfm_audio(search_query):
    """RapidAPI se Pocket FM Audio URL nikalta hai"""
    url = "https://pocket-fm-api1.p.rapidapi.com/genre-misplaced-trust-search"
    
    querystring = {
        "query": search_query,
        "genre": "42c1d04b966fd7b9"
    }
    headers = {
        "x-rapidapi-key": API_KEY,
        "x-rapidapi-host": API_HOST,
        "Content-Type": "application/json"
    }

    try:
        response = requests.get(url, headers=headers, params=querystring, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data
        else:
            return None
    except Exception as e:
        print(f"API Error: {e}")
        return None


# -------------------------------------------------------------
# Main Message Handler
# -------------------------------------------------------------
def handle_message(chat_id, text):
    if text == "/start":
        send_message(chat_id, "👋 <b>Welcome to Pocket FM Downloader Bot!</b>\n\nKisi bhi Pocket FM show ya episode ka naam likhkar bhejo.")
        return

    send_message(chat_id, f"🔎 Searching Pocket FM for: <b>{text}</b>...")

    api_result = fetch_pocketfm_audio(text)

    if api_result:
        # Audio URL extract karna
        # Note: Pocket FM API me audio key ka naam 'media_url' ya 'stream_url' ho sakta hai
        audio_link = None
        
        if isinstance(api_result, dict):
            audio_link = api_result.get("media_url") or api_result.get("stream_url") or api_result.get("audio_url")
        
        if audio_link:
            send_message(chat_id, "⬇️ Downloading & Sending Audio...")
            send_audio(chat_id, audio_link, title=text)
        else:
            # Agar direct link nahi mila toh JSON response display kar dega
            json_str = json.dumps(api_result, indent=2)
            if len(json_str) > 3500:
                json_str = json_str[:3500] + "..."
            send_message(chat_id, f"📋 <b>API Data Found:</b>\n<pre>{json_str}</pre>")
    else:
        send_message(chat_id, "❌ Episode/Show nahi mila ya API me problem hai.")


# -------------------------------------------------------------
# Main Loop
# -------------------------------------------------------------
def main():
    server_thread = threading.Thread(target=run_dummy_server, daemon=True)
    server_thread.start()

    print("Pocket FM Bot running...")
    offset = None

    while True:
        updates = get_updates(offset)
        if updates and updates.get("ok"):
            for update in updates.get("result", []):
                offset = update["update_id"] + 1
                if "message" in update and "text" in update["message"]:
                    chat_id = update["message"]["chat"]["id"]
                    incoming_text = update["message"]["text"].strip()
                    handle_message(chat_id, incoming_text)
        time.sleep(1)


if __name__ == "__main__":
    main()
