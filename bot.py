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
# Dummy Server (Render Server Active Rakhne Ke Liye)
# -------------------------------------------------------------
class DummyServerHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"TeraBox Downloader Bot is Running Live!")

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
        print(f"Error sending message: {e}")


def send_video(chat_id, video_url, title="TeraBox Video"):
    url = f"{BASE_URL}/sendVideo"
    payload = {
        "chat_id": chat_id,
        "video": video_url,
        "caption": f"🎬 <b>{title}</b>\n\nDownloaded via TeraBox Bot 🚀",
        "parse_mode": "HTML",
    }
    try:
        res = requests.post(url, json=payload).json()
        return res
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
        print(f"Error getting updates: {e}")
    return None


# -------------------------------------------------------------
# TeraBox Link Extractor API
# -------------------------------------------------------------
def get_terabox_direct_link(terabox_url):
    """Free Open Source TeraBox API Extractor"""
    api_url = f"https://terabox.app.link-api.workers.dev/?url={terabox_url}"

    try:
        response = requests.get(api_url, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if "download_link" in data or "url" in data:
                return {
                    "download_url": data.get("download_link")
                    or data.get("url"),
                    "title": data.get("file_name", "TeraBox File"),
                }
    except Exception as e:
        print(f"TeraBox Extractor Error: {e}")

    # Alternative Fallback API
    try:
        alt_api = f"https://api.terabox.com.py/api?url={terabox_url}"
        res = requests.get(alt_api, timeout=15)
        if res.status_code == 200:
            d = res.json()
            if d.get("status") == True:
                return {
                    "download_url": d.get("downloadUrl"),
                    "title": d.get("title", "TeraBox File"),
                }
    except Exception as e:
        print(f"Fallback API Error: {e}")

    return None


# -------------------------------------------------------------
# Message Handling
# -------------------------------------------------------------
def handle_message(chat_id, text):
    if text == "/start":
        send_message(
            chat_id,
            "👋 <b>Welcome to TeraBox Downloader Bot!</b>\n\n"
            "Koi bhi TeraBox Link yahan bhejein, main aapko direct video/file bhej dunga! 📁",
        )
        return

    # Check if text contains a TeraBox link
    if "terabox" in text or "neodrive" in text or "freeterabox" in text:
        # Extract URL from text
        urls = re.findall(r"(https?://[^\s]+)", text)
        if urls:
            target_url = urls[0]
            send_message(
                chat_id,
                "🔗 <b>TeraBox Link Detected!</b>\n⏳ Direct Download Link Fetch ho raha hai...",
            )

            file_info = get_terabox_direct_link(target_url)

            if file_info and file_info.get("download_url"):
                send_message(
                    chat_id, "⬇️ <b>Video Telegram par bhej rahe hain...</b>"
                )
                result = send_video(
                    chat_id,
                    file_info["download_url"],
                    title=file_info["title"],
                )

                if not result or not result.get("ok"):
                    # File size is too large for Telegram API direct link method
                    send_message(
                        chat_id,
                        f"📁 <b>Direct Stream Link:</b>\n\n"
                        f"<code>{file_info['download_url']}</code>\n\n"
                        f"💡 <i>Note: Agar video badi hai toh uper diye link par click karke browser se download karein!</i>",
                    )
            else:
                send_message(
                    chat_id,
                    "❌ Is link ka direct audio/video extract nahi ho paya. Link sahi hai ya nahi check karein.",
                )
        return

    send_message(
        chat_id,
        "⚠️ Please ek valid **TeraBox URL** bhejein!\n\n<i>Example: https://terabox.com/s/...</i>",
    )


# -------------------------------------------------------------
# Main Loop
# -------------------------------------------------------------
def main():
    threading.Thread(target=run_dummy_server, daemon=True).start()
    print("TeraBox Bot Started...")
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
