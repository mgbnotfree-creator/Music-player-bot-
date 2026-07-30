import os
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
import requests

# -------------------------------------------------------------
# Configuration Variables
# -------------------------------------------------------------
BOT_TOKEN = "8983781306:AAHod4RCSd6G3L_A2stv_GQWLvOWm3S3LvQ"
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


# -------------------------------------------------------------
# Dummy Web Server (Render App ko Active rakhne ke liye)
# -------------------------------------------------------------
class DummyServerHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"JioSaavn Music Bot is Running Live!")

    def log_message(self, format, *args):
        return


def run_dummy_server():
    httpd = HTTPServer(("", 8080), DummyServerHandler)
    httpd.serve_forever()


# -------------------------------------------------------------
# Telegram API Functions
# -------------------------------------------------------------
def send_message(chat_id, text):
    url = f"{BASE_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Message Error: {e}")


def send_audio(chat_id, audio_url, title, performer="Music Bot"):
    url = f"{BASE_URL}/sendAudio"
    payload = {
        "chat_id": chat_id,
        "audio": audio_url,
        "title": title,
        "performer": performer,
        "caption": f"🎧 <b>{title}</b>\n\nDownloaded via JioSaavn Music Bot 🎶",
        "parse_mode": "HTML",
    }
    try:
        res = requests.post(url, json=payload, timeout=30)
        return res.json()
    except Exception as e:
        print(f"Audio Send Error: {e}")
        return None


def get_updates(offset=None):
    url = f"{BASE_URL}/getUpdates"
    params = {"timeout": 30, "offset": offset}
    try:
        res = requests.get(url, params=params, timeout=35)
        if res.status_code == 200:
            return res.json()
    except Exception as e:
        print(f"Update error: {e}")
    return None


# -------------------------------------------------------------
# JioSaavn API Engine (No Youtube Block Issue)
# -------------------------------------------------------------
def search_and_download_saavn(chat_id, song_name):
    send_message(
        chat_id,
        f"🔎 <b>Searching JioSaavn:</b> <i>{song_name}</i>\n⏳ Kripya thoda wait karein...",
    )

    api_url = (
        f"https://saavn.dev/api/search/songs?query={requests.utils.quote(song_name)}&limit=1"
    )

    try:
        response = requests.get(api_url, timeout=15)
        if response.status_code == 200:
            data = response.json()

            if data.get("success") and data.get("data", {}).get("results"):
                song = data["data"]["results"][0]

                title = song.get("name", "Unknown Song")
                artist = (
                    song.get("artists", {})
                    .get("primary", [{}])[0]
                    .get("name", "Various Artists")
                )

                # Get Highest Quality Download URL (320kbps or 160kbps)
                download_urls = song.get("downloadUrl", [])
                audio_url = None

                if download_urls:
                    # Select highest quality available (usually last element)
                    audio_url = download_urls[-1].get("url")

                if audio_url:
                    send_message(
                        chat_id, "⬆️ <b>MP3 Audio Telegram par bhej rahe hain...</b>"
                    )
                    result = send_audio(
                        chat_id, audio_url, title=title, performer=artist
                    )

                    if not result or not result.get("ok"):
                        # If Telegram fails to upload direct link, give direct stream URL
                        send_message(
                            chat_id,
                            f"🎶 <b>Direct Song Stream Link:</b>\n\n"
                            f"<b>Song:</b> {title}\n"
                            f"👉 <a href='{audio_url}'>Click Here to Play/Download MP3</a>",
                        )
                    return

        send_message(
            chat_id,
            "❌ <b>Gaana nahi mila!</b>\nSpelling sahi karke dusra naam likhein.",
        )

    except Exception as e:
        print(f"Saavn API Error: {e}")
        send_message(
            chat_id, "❌ Error: Song fetch karne me dikkat aayi. Phir se try karein."
        )


# -------------------------------------------------------------
# Main Message Handler
# -------------------------------------------------------------
def handle_message(chat_id, text):
    if text == "/start":
        send_message(
            chat_id,
            "👋 <b>Welcome to High Quality MP3 Music Bot! 🎶</b>\n\n"
            "Kisi bhi Hindi, English, ya Regional gaane ka **Naam** likhkar bhejein!\n\n"
            "<i>Example: Agar Tum Saath Ho</i>",
        )
        return

    # Process search in background thread
    threading.Thread(
        target=search_and_download_saavn, args=(chat_id, text)
    ).start()


# -------------------------------------------------------------
# Main Loop
# -------------------------------------------------------------
def main():
    threading.Thread(target=run_dummy_server, daemon=True).start()
    print("Saavn MP3 Bot Active...")
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
    
