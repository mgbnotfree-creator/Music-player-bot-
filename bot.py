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
# Dummy Web Server (Render App Ko Active Rakhne Ke Liye)
# -------------------------------------------------------------
class DummyServerHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"YouTube Downloader Bot Active!")

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
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Error sending message: {e}")


def send_video_file(chat_id, file_path, title):
    url = f"{BASE_URL}/sendVideo"
    try:
        with open(file_path, "rb") as video:
            files = {"video": video}
            data = {
                "chat_id": chat_id,
                "caption": f"🎬 <b>{title}</b>\n\nDownloaded via Bot 🚀",
                "parse_mode": "HTML",
            }
            requests.post(url, data=data, files=files)
    except Exception as e:
        print(f"Error sending video: {e}")


def send_audio_file(chat_id, file_path, title):
    url = f"{BASE_URL}/sendAudio"
    try:
        with open(file_path, "rb") as audio:
            files = {"audio": audio}
            data = {
                "chat_id": chat_id,
                "title": title,
                "caption": f"🎧 <b>{title}</b>\n\nDownloaded via Bot 🎶",
                "parse_mode": "HTML",
            }
            requests.post(url, data=data, files=files)
    except Exception as e:
        print(f"Error sending audio: {e}")


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
# Downloader Logic (360p Compressed Format for <50MB Limit)
# -------------------------------------------------------------
def download_media(chat_id, link_or_query):
    send_message(chat_id, "⏳ <b>Downloading Media (Fast Mode)...</b>")

    ydl_opts = {
        "format": "best[filesize<45M]/bestvideo[height<=360]+bestaudio/best[height<=360]/best",
        "outtmpl": "downloaded_media.%(ext)s",
        "quiet": True,
        "no_warnings": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(link_or_query, download=True)
            title = info.get("title", "Downloaded File")

            filename = None
            for f in os.listdir("."):
                if f.startswith("downloaded_media."):
                    filename = f
                    break

            if filename and os.path.exists(filename):
                send_message(
                    chat_id, "⬆️ <b>Telegram par upload ho raha hai...</b>"
                )

                if filename.endswith(".mp4") or filename.endswith(".mkv"):
                    send_video_file(chat_id, filename, title)
                else:
                    send_audio_file(chat_id, filename, title)

                os.remove(filename)  # Cleanup temp file
            else:
                send_message(chat_id, "❌ Download file process nahi ho saki.")

    except Exception as e:
        print(f"Download Error: {e}")
        send_message(
            chat_id, "❌ Error: Link process karne me samasya aayi."
        )


# -------------------------------------------------------------
# Message Handling
# -------------------------------------------------------------
def handle_message(chat_id, text):
    if text == "/start":
        send_message(
            chat_id,
            "👋 <b>Welcome to Video & Song Downloader Bot!</b>\n\n"
            "Koi bhi YouTube Video/Song link yahan paste karein!",
        )
        return

    if text.startswith("http://") or text.startswith("https://"):
        threading.Thread(
            target=download_media, args=(chat_id, text)
        ).start()
    else:
        send_message(
            chat_id,
            "⚠️ Please ek valid URL (YouTube/Song Link) bhejein!",
        )


# -------------------------------------------------------------
# Main Loop
# -------------------------------------------------------------
def main():
    threading.Thread(target=run_dummy_server, daemon=True).start()
    print("Bot is running successfully...")
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
    
