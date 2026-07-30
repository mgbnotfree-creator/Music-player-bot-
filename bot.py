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
# Web Server (Keep Alive)
# -------------------------------------------------------------
class DummyServerHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"Music Bot is Active!")

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
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    try:
        requests.post(url, json=payload, headers=HEADERS)
    except Exception as e:
        print(f"Message Error: {e}")


def send_audio(chat_id, audio_url, title, performer="Music Bot"):
    url = f"{BASE_URL}/sendAudio"
    payload = {
        "chat_id": chat_id,
        "audio": audio_url,
        "title": title,
        "performer": performer,
        "caption": f"🎧 <b>{title}</b>\n\nDownloaded via Music Bot 🎵",
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
        print(f"Update error: {e}")
    return None


# -------------------------------------------------------------
# Reliable Audio Engine (Direct JioSaavn Unofficial API)
# -------------------------------------------------------------
def get_song_audio(query):
    # Query Clean Up
    clean_query = (
        query.replace("https://youtu.be/", "")
        .replace("https://www.youtube.com/watch?v=", "")
        .strip()
    )

    # API Request to Saavn Server
    api_url = f"https://saavn.dev/api/search/songs?query={requests.utils.quote(clean_query)}"

    try:
        res = requests.get(api_url, headers=HEADERS, timeout=12)
        if res.status_code == 200:
            data = res.json()
            if data.get("success") and data.get("data", {}).get("results"):
                song = data["data"]["results"][0]

                title = song.get("name", "Unknown Song")
                # Clean html tags from title
                title = (
                    title.replace("&quot;", "")
                    .replace("&#039;", "")
                    .replace("&amp;", "&")
                )

                artist = "Music Bot"
                primary_artists = song.get("artists", {}).get("primary", [])
                if primary_artists:
                    artist = primary_artists[0].get("name", "Music Bot")

                download_urls = song.get("downloadUrl", [])
                if download_urls:
                    # High quality URL select karega
                    audio_url = download_urls[-1].get("url")
                    return {
                        "title": title,
                        "artist": artist,
                        "audio_url": audio_url,
                    }
    except Exception as e:
        print(f"Saavn Error: {e}")

    return None


# -------------------------------------------------------------
# Request Handler
# -------------------------------------------------------------
def process_song_request(chat_id, text):
    # Multiple names detection check
    if " ya " in text.lower() or " or " in text.lower():
        send_message(
            chat_id,
            "⚠️ <b>Ek baar me sirf EK gaane ka naam likhein!</b>\n\n"
            "Example: <code>Kesariya</code>",
        )
        return

    send_message(
        chat_id,
        f"🔎 <b>Searching MP3:</b> <i>{text}</i>\n⏳ <i>Wait karein...</i>",
    )

    song_info = get_song_audio(text)

    if song_info and song_info.get("audio_url"):
        title = song_info["title"]
        artist = song_info["artist"]
        audio_url = song_info["audio_url"]

        send_message(
            chat_id, "⬆️ <b>MP3 Song Telegram par upload ho raha hai...</b>"
        )

        res = send_audio(chat_id, audio_url, title=title, performer=artist)

        if not res or not res.get("ok"):
            send_message(
                chat_id,
                f"🎧 <b>Direct MP3 Link Ready:</b>\n\n"
                f"🎵 <b>{title}</b> - {artist}\n\n"
                f"👉 <a href='{audio_url}'>Click Here To Play / Download MP3</a>",
            )
    else:
        send_message(
            chat_id,
            "❌ <b>Gaana nahi mila!</b>\n\n"
            "Sirf ek gaane ka clear naam likhein (Jaise: <code>Kesariya</code>).",
        )


# -------------------------------------------------------------
# Main Message Router
# -------------------------------------------------------------
def handle_message(chat_id, text):
    if text == "/start":
        send_message(
            chat_id,
            "👋 <b>Welcome to MP3 Music Bot! 🎶</b>\n\n"
            "Kisi bhi EK gaane ka **Naam** likh kar bhejein!\n\n"
            "<i>Example: Kesariya</i>",
        )
        return

    threading.Thread(
        target=process_song_request, args=(chat_id, text)
    ).start()


# -------------------------------------------------------------
# Main Loop
# -------------------------------------------------------------
def main():
    threading.Thread(target=run_dummy_server, daemon=True).start()
    print("Music Bot Running...")
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
        
