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


# -------------------------------------------------------------
# Dummy Web Server (Render Active Keep)
# -------------------------------------------------------------
class DummyServerHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"YouTube Media Downloader Active!")

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
        print(f"Error sending message: {e}")


def send_video(chat_id, video_url, title="Downloaded Video"):
    url = f"{BASE_URL}/sendVideo"
    payload = {
        "chat_id": chat_id,
        "video": video_url,
        "caption": f"🎬 <b>{title}</b>\n\nDownloaded via Music Bot 🚀",
        "parse_mode": "HTML",
    }
    try:
        return requests.post(url, json=payload, timeout=25).json()
    except Exception as e:
        print(f"Error sending video: {e}")
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
# Fast Media Extractor (Cobalt API)
# -------------------------------------------------------------
def get_media_url_cobalt(youtube_url):
    api_url = "https://api.cobalt.tools/api/json"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    payload = {
        "url": youtube_url,
        "vQuality": "360",  # Low size format for fast Telegram send
        "isAudioOnly": False,
    }

    try:
        res = requests.post(api_url, json=payload, headers=headers, timeout=12)
        if res.status_code == 200:
            data = res.json()
            if data.get("status") in ["stream", "picker", "redirect"]:
                return data.get("url")
    except Exception as e:
        print(f"Cobalt Main API Error: {e}")

    # Fallback Cobalt Instance
    try:
        alt_api = "https://cobalt.qil.dev/api/json"
        res = requests.post(alt_api, json=payload, headers=headers, timeout=12)
        if res.status_code == 200:
            data = res.json()
            if data.get("url"):
                return data.get("url")
    except Exception as e:
        print(f"Cobalt Fallback Error: {e}")

    return None


# -------------------------------------------------------------
# Message Processor
# -------------------------------------------------------------
def download_media_process(chat_id, youtube_url):
    send_message(chat_id, "⏳ <b>Processing Media (Fast Server)...</b>")

    direct_url = get_media_url_cobalt(youtube_url)

    if direct_url:
        send_message(
            chat_id, "⬇️ <b>Telegram par video send kar rahe hain...</b>"
        )
        result = send_video(chat_id, direct_url, title="YouTube Media")

        # If direct video upload fails on Telegram
        if not result or not result.get("ok"):
            send_message(
                chat_id,
                f"🎬 <b>Direct Stream / Download Link:</b>\n\n"
                f"👉 <a href='{direct_url}'>Click Here to Download Media</a>\n\n"
                f"💡 <i>Tip: Telegram limit ki wajah se link par click karke direct download karein!</i>",
            )
    else:
        send_message(
            chat_id,
            "❌ <b>Error:</b> Video extract nahi ho payi. Kuch der baad try karein.",
        )


def handle_message(chat_id, text):
    if text == "/start":
        send_message(
            chat_id,
            "👋 <b>Welcome to Fast Media Downloader Bot!</b>\n\n"
            "Koi bhi YouTube, Instagram, ya Song Link yahan paste karein!",
        )
        return

    if "youtube.com" in text or "youtu.be" in text or "http" in text:
        urls = re.findall(r"(https?://[^\s]+)", text)
        if urls:
            threading.Thread(
                target=download_media_process, args=(chat_id, urls[0])
            ).start()
            return

    send_message(chat_id, "⚠️ Please ek valid **Video URL** bhejein!")


# -------------------------------------------------------------
# Main Loop
# -------------------------------------------------------------
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
        
