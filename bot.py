import os
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
import requests
import yt_dlp

BOT_TOKEN = "8983781306:AAHod4RCSd6G3L_A2stv_GQWLvOWm3S3LvQ"
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


class DummyServerHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"All-in-One Downloader Bot is Running!")

    def log_message(self, format, *args):
        return


def run_dummy_server():
    httpd = HTTPServer(("", 8080), DummyServerHandler)
    httpd.serve_forever()


def send_message(chat_id, text):
    url = f"{BASE_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Error: {e}")


def send_video_file(chat_id, file_path, title):
    url = f"{BASE_URL}/sendVideo"
    try:
        with open(file_path, "rb") as video:
            files = {"video": video}
            data = {
                "chat_id": chat_id,
                "caption": f"🎬 <b>{title}</b>\n\nDownloaded via Media Downloader",
                "parse_mode": "HTML",
            }
            requests.post(url, data=data, files=files)
    except Exception as e:
        print(f"Error sending video: {e}")


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


def download_media(chat_id, link_or_query):
    send_message(chat_id, "⏳ <b>Downloading Video/Audio...</b>")

    ydl_opts = {
        "format": "best[ext=mp4]/best",
        "outtmpl": "downloaded_media.%(ext)s",
        "quiet": True,
        "max_filesize": 48 * 1024 * 1024,  # Under 50MB limit for Telegram
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(link_or_query, download=True)
            title = info.get("title", "Downloaded Video")

            filename = "downloaded_media.mp4"
            if not os.path.exists(filename):
                for f in os.listdir("."):
                    if f.startswith("downloaded_media."):
                        filename = f
                        break

            if os.path.exists(filename):
                send_message(chat_id, "⬆️ <b>Uploading to Telegram...</b>")
                send_video_file(chat_id, filename, title)
                os.remove(filename)
            else:
                send_message(chat_id, "❌ Download failed.")

    except Exception as e:
        print(f"Error: {e}")
        send_message(
            chat_id,
            "❌ Media process nahi ho paya. File size 50MB se badi ho sakti hai ya link invalid hai.",
        )


def handle_message(chat_id, text):
    if text == "/start":
        send_message(
            chat_id,
            "👋 <b>Welcome to Media Downloader Bot!</b>\n\n"
            "YouTube, Instagram Reels, ya kisi bhi supported URL ka link bhejein, main direct video bhej dunga!",
        )
        return

    if text.startswith("http://") or text.startswith("https://"):
        threading.Thread(
            target=download_media, args=(chat_id, text)
        ).start()
    else:
        send_message(chat_id, "⚠️ Please ek valid **Video URL** bhejein!")


def main():
    threading.Thread(target=run_dummy_server, daemon=True).start()
    print("Bot started...")
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
    
