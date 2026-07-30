import json
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
import requests

# -------------------------------------------------------------
# Configuration
# -------------------------------------------------------------
BOT_TOKEN = "8983781306:AAHod4RCSd6G3L_A2stv_GQWLvOWm3S3LvQ"
API_KEY = "458a3845d8msh0e188bebe00200ep1933e2jsnc7b9327ac320"
API_HOST = "pocket-fm-api1.p.rapidapi.com"

BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


# -------------------------------------------------------------
# Dummy Server (Render Server Keep Alive)
# -------------------------------------------------------------
class DummyServerHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"Pocket FM Bot Server Active!")

    def log_message(self, format, *args):
        return


def run_dummy_server():
    httpd = HTTPServer(("", 8080), DummyServerHandler)
    httpd.serve_forever()


# -------------------------------------------------------------
# Telegram Functions
# -------------------------------------------------------------
def send_message(chat_id, text):
    url = f"{BASE_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Error sending message: {e}")


def send_audio(chat_id, audio_url, title="Pocket FM Episode"):
    url = f"{BASE_URL}/sendAudio"
    payload = {
        "chat_id": chat_id,
        "audio": audio_url,
        "caption": f"🎧 <b>{title}</b>\n\nDownloaded via Pocket FM Bot",
    }
    try:
        return requests.post(url, json=payload).json()
    except Exception as e:
        print(f"Error sending audio: {e}")
        return None


def get_updates(offset=None):
    url = f"{BASE_URL}/getUpdates"
    params = {"timeout": 30, "offset": offset}
    try:
        res = requests.get(url, params=params, timeout=35)
        if res.status_code == 200:
            return res.json()
    except Exception as e:
        print(f"Error getting updates: {e}")
    return None


# -------------------------------------------------------------
# API Call Functions
# -------------------------------------------------------------
def fetch_player_audio(show_id):
    """Fetch Audio Stream from Player Endpoint"""
    url = "https://pocket-fm-api1.p.rapidapi.com/player"
    payload = {"id": show_id}
    headers = {
        "x-rapidapi-key": API_KEY,
        "x-rapidapi-host": API_HOST,
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(
            url, json=payload, headers=headers, timeout=10
        )
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Player API Error: {e}")
    return None


def fetch_search(query):
    """Search Query Call"""
    url = "https://pocket-fm-api1.p.rapidapi.com/genre-misplaced-trust-search"
    querystring = {"query": query, "genre": "42c1d04b966fd7b9"}
    headers = {"x-rapidapi-key": API_KEY, "x-rapidapi-host": API_HOST}

    try:
        response = requests.get(
            url, headers=headers, params=querystring, timeout=10
        )
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Search API Error: {e}")
    return None


# -------------------------------------------------------------
# Main Message Processing
# -------------------------------------------------------------
def handle_message(chat_id, text):
    if text == "/start":
        send_message(
            chat_id,
            "👋 <b>Welcome to Pocket FM Bot!</b>\n\n"
            "• Show ka naam search karein (e.g. <code>The Story of CEO</code>)\n"
            "• Ya direct Pocket FM Link paste karein!",
        )
        return

    # 1. LINK DETECTION (Pocket FM URL Handling)
    if "pocketfm.com/show/" in text:
        # Link se Show ID extract karna (e.g., f629196ee7df34287ef2672e91fda9f939e9d02d)
        match = re.search(r"show/([a-zA-F0-9]+)", text)
        if match:
            show_id = match.group(1)
            send_message(
                chat_id,
                "🔗 <b>Pocket FM Link Detected!</b>\n⏳ Audio fetch ho raha hai...",
            )

            player_data = fetch_player_audio(show_id)
            if player_data:
                audio_url = (
                    player_data.get("media_url")
                    or player_data.get("stream_url")
                    or player_data.get("audio_url")
                )
                if audio_url:
                    send_message(
                        chat_id, "⬇️ <b>Audio File Sending...</b>"
                    )
                    send_audio(
                        chat_id,
                        audio_url,
                        title=player_data.get("title", "Pocket FM Audio"),
                    )
                    return
            send_message(
                chat_id,
                "❌ Is link se audio extract nahi ho paya. RapidAPI limit check karein.",
            )
            return

    # 2. DIRECT DOWNLOAD COMMAND
    if text.startswith("/download_"):
        show_id = text.replace("/download_", "").strip()
        send_message(chat_id, "⏳ <b>Audio link fetch ho raha hai...</b>")

        player_data = fetch_player_audio(show_id)
        if player_data:
            audio_url = (
                player_data.get("media_url")
                or player_data.get("stream_url")
                or player_data.get("audio_url")
            )
            if audio_url:
                send_message(chat_id, "⬇️ <b>Audio bhej rahe hain...</b>")
                send_audio(
                    chat_id,
                    audio_url,
                    title=player_data.get("title", "Pocket FM Audio"),
                )
                return

        send_message(chat_id, "❌ Audio nahi mil paya.")
        return

    # 3. TEXT SEARCH
    send_message(chat_id, f"🔎 Searching for: <b>{text}</b>...")
    search_data = fetch_search(text)

    if search_data and isinstance(search_data, list):
        reply_text = f"📚 <b>Search Results:</b>\n\n"
        for item in search_data[:5]:
            title = item.get("title", "Unknown")
            entity_id = item.get("entity_id", "")
            reply_text += (
                f"📖 <b>{title}</b>\n"
                f"👉 Click to Download: /download_{entity_id}\n"
                f"───────────────\n"
            )
        send_message(chat_id, reply_text)
    else:
        send_message(
            chat_id,
            "❌ <b>Show nahi mila.</b>\n\n"
            "💡 <i>Tip: Pocket FM app se show ka <b>Link</b> copy karke yahan paste karein!</i>",
        )


# -------------------------------------------------------------
# Main Loop
# -------------------------------------------------------------
def main():
    threading.Thread(target=run_dummy_server, daemon=True).start()
    print("Bot is running...")
    offset = None

    while True:
        updates = get_updates(offset)
        if updates and updates.get("ok"):
            for update in updates.get("result", []):
                offset = update["update_id"] + 1
                if "message" in update and "text" in update["message"]:
                    handle_message(
                        update["message"]["chat"]["id"],
                        update["message"]["text"].strip(),
                    )
        time.sleep(1)


if __name__ == "__main__":
    main()
