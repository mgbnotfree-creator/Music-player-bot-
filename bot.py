import os
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
import requests
import yt_dlp

# -------------------------------------------------------------
# Configuration
# -------------------------------------------------------------
BOT_TOKEN = "8983781306:AAHod4RCSd6G3L_A2stv_GQWLvOWm3S3LvQ"
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


# -------------------------------------------------------------
# Web Server (Keep Alive for Render)
# -------------------------------------------------------------
class DummyServerHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"Music Bot is Active & Running!")

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
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Send Message Error: {e}")


def send_audio(chat_id, file_path, title, performer="Music Bot"):
    url = f"{BASE_URL}/sendAudio"
    try:
        with open(file_path, "rb") as file_data:
            files = {"audio": file_data}
            data = {
                "chat_id": chat_id,
                "title": title,
                "performer": performer,
                "caption": f"🎧 <b>{title}</b>\n\nDownloaded via Music Bot 🎵",
                "parse_mode": "HTML",
            }
            res = requests.post(url, data=data, files=files, timeout=120)
            return res.json()
    except Exception as e:
        print(f"Send Local File Error: {e}")
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
# Anti-Bot Bypass YT-DLP Downloader Engine
# -------------------------------------------------------------
def download_audio_with_bypass(query_or_url, output_filename="song.m4a"):
    # If URL is provided, use direct URL, else use search query
    if "youtu.be/" in query_or_url or "youtube.com/" in query_or_url:
        search_target = query_or_url
    else:
        search_target = f"ytsearch1:{query_or_url}"

    # Anti-block configuration: Emulates Android Client to bypass Cloud Blocks
    ydl_opts = {
        "format": "m4a/bestaudio/best",
        "outtmpl": output_filename,
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "web"],
                "skip": ["dash", "hls"],
            }
        },
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Android 12; Mobile; rv:109.0) Gecko/109.0"
                " Firefox/112.0"
            )
        },
    }

    try:
        if os.path.exists(output_filename):
            os.remove(output_filename)

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(search_target, download=True)
            if "entries" in info:
                info = info["entries"][0]

            title = info.get("title", "Unknown Track")
            uploader = info.get("uploader", "Artist")

            if os.path.exists(output_filename):
                return {
                    "file_path": output_filename,
                    "title": title,
                    "artist": uploader,
                }
    except Exception as e:
        print(f"YT-DLP Engine Download Failed: {e}")

    return None


# -------------------------------------------------------------
# Process Request Logic
# -------------------------------------------------------------
def process_song_request(chat_id, user_text):
    # Shorten long log text
    display_name = user_text
    if len(display_name) > 35:
        display_name = display_name[:32] + "..."

    send_message(
        chat_id,
        f"🔎 <b>Searching & Processing:</b> <i>{display_name}</i>\n⏳ <i>Song download ho raha hai, wait karein...</i>",
    )

    # Output file unique per thread
    file_id = f"song_{chat_id}_{int(time.time())}.m4a"

    song_result = download_audio_with_bypass(user_text, file_id)

    if song_result and os.path.exists(song_result["file_path"]):
        send_message(
            chat_id, "⬆️ <b>MP3 Audio Telegram par upload ho raha hai...</b>"
        )

        res = send_audio(
            chat_id,
            song_result["file_path"],
            title=song_result["title"],
            performer=song_result["artist"],
        )

        # Cleanup local file after uploading
        if os.path.exists(song_result["file_path"]):
            os.remove(song_result["file_path"])

        if not res or not res.get("ok"):
            send_message(
                chat_id,
                "❌ <b>Upload Error:</b> Telegram par file send karne me dikkat aayi. Phir se try karein.",
            )
    else:
        send_message(
            chat_id,
            "❌ <b>Gaana nahi mil saka!</b>\n\n"
            "Kripya song ka sahi naam likhein (Jaise: <code>Phir Mohabbat Murder 2</code>) ya exact YouTube Link bhejien.",
        )


# -------------------------------------------------------------
# Main Message Router
# -------------------------------------------------------------
def handle_message(chat_id, text):
    if text == "/start":
        send_message(
            chat_id,
            "👋 <b>Welcome to High Quality MP3 Music Bot! 🎶</b>\n\n"
            "Gaane ka **Naam** likhein ya **YouTube Link** bhejien!\n\n"
            "<i>Example: Phir Mohabbat Murder 2</i>",
        )
        return

    threading.Thread(
        target=process_song_request, args=(chat_id, text)
    ).start()


# -------------------------------------------------------------
# Main Polling Loop
# -------------------------------------------------------------
def main():
    threading.Thread(target=run_dummy_server, daemon=True).start()
    print("Anti-Block Music Bot Active...")
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
        
