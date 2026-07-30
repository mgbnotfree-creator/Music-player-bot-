import os
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
import requests

# -------------------------------------------------------------
# Configuration
# -------------------------------------------------------------
BOT_TOKEN = "8983781306:AAHod4RCSd6G3L_A2stv_GQWLvOWm3S3LvQ"
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
        " like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}


# -------------------------------------------------------------
# Dummy Web Server (Render App Ko Alive Rakhne Ke Liye)
# -------------------------------------------------------------
class DummyServerHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"Music Bot is Online!")

    def log_message(self, format, *args):
        return


def run_dummy_server():
    httpd = HTTPServer(("", 8080), DummyServerHandler)
    httpd.serve_forever()


# -------------------------------------------------------------
# Telegram API Helpers
# -------------------------------------------------------------
def send_message(chat_id, text):
    url = f"{BASE_URL}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    try:
        requests.post(url, json=payload, headers=HEADERS)
    except Exception as e:
        print(f"Send Message Error: {e}")


def send_audio(chat_id, audio_url, title, performer="Music Bot"):
    url = f"{BASE_URL}/sendAudio"
    payload = {
        "chat_id": chat_id,
        "audio": audio_url,
        "title": title,
        "performer": performer,
        "caption": f"🎧 <b>{title}</b>\n\nDownloaded via MP3 Music Bot 🎵",
        "parse_mode": "HTML",
    }
    try:
        res = requests.post(url, json=payload, headers=HEADERS, timeout=30)
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
        print(f"Update Error: {e}")
    return None


# -------------------------------------------------------------
# Deezer Global Music Search Engine (100% Guaranteed No Block)
# -------------------------------------------------------------
def search_deezer_music(song_name):
    # Cleaning the query
    clean_name = re.sub(r"https?://\S+", "", song_name).strip()
    if not clean_name:
        return None

    api_url = f"https://api.deezer.com/search?q={requests.utils.quote(clean_name)}&limit=1"

    try:
        res = requests.get(api_url, headers=HEADERS, timeout=12)
        if res.status_code == 200:
            data = res.json()
            if data.get("data") and len(data["data"]) > 0:
                first_track = data["data"][0]

                title = first_track.get("title", "Song")
                artist = first_track.get("artist", {}).get(
                    "name", "Unknown Artist"
                )
                audio_preview = first_track.get("preview")  # Direct MP3 Link

                if audio_preview:
                    return {
                        "title": title,
                        "artist": artist,
                        "audio_url": audio_preview,
                    }
    except Exception as e:
        print(f"Deezer Search Error: {e}")

    return None


# -------------------------------------------------------------
# Process Request Logic
# -------------------------------------------------------------
def process_song_search(chat_id, query_text):
    send_message(
        chat_id,
        f"🔎 <b>Searching MP3:</b> <i>{query_text}</i>\n⏳ <i>Kripya wait karein...</i>",
    )

    song_info = search_deezer_music(query_text)

    if song_info and song_info.get("audio_url"):
        title = song_info["title"]
        artist = song_info["artist"]
        audio_url = song_info["audio_url"]

        send_message(
            chat_id, "⬆️ <b>MP3 Track Telegram par upload ho raha hai...</b>"
        )

        res = send_audio(chat_id, audio_url, title=title, performer=artist)

        # Fallback Link if Telegram direct upload fails
        if not res or not res.get("ok"):
            send_message(
                chat_id,
                f"🎧 <b>Song MP3 Ready:</b>\n\n"
                f"🎵 <b>{title}</b> - {artist}\n\n"
                f"👉 <a href='{audio_url}'>Click Here To Play / Download MP3</a>",
            )
    else:
        send_message(
            chat_id,
            "❌ <b>Gaana nahi mila!</b>\n\n"
            "Kripya kisi specific song ka sahi English/Hindi naam likhein (Jaise: <code>Kesariya</code> ya <code>Believer</code>).",
        )


# -------------------------------------------------------------
# Main Message Handler
# -------------------------------------------------------------
def handle_message(chat_id, text):
    if text == "/start":
        send_message(
            chat_id,
            "👋 <b>Welcome to High Quality MP3 Music Bot! 🎶</b>\n\n"
            "Kisi bhi song ka <b>Naam</b> likh kar bhejein!\n\n"
            "<i>Example: Kesariya</i>",
        )
        return

    threading.Thread(
        target=process_song_search, args=(chat_id, text)
    ).start()


# -------------------------------------------------------------
# Main Loop
# -------------------------------------------------------------
def main():
    threading.Thread(target=run_dummy_server, daemon=True).start()
    print("Music Bot Active...")
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
