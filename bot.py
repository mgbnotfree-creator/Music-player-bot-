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
# Dummy Server (Render Active Keeping)
# -------------------------------------------------------------
class DummyServerHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"TeraBox Downloader Active!")

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
        res = requests.post(url, json=payload, timeout=20).json()
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
# Multi-API TeraBox Link Extractor
# -------------------------------------------------------------
def clean_terabox_url(url):
    """Normalize any terabox variant URL to standard domain"""
    pattern = r"https?://(?:www\.)?([a-zA-Z0-9-]+\.)+(?:com|app|net|fun|tech)/s/([a-zA-Z0-9_-]+)"
    match = re.search(pattern, url)
    if match:
        s_id = match.group(2)
        return f"https://www.terabox.app/sharing/link?surl={s_id}"
    return url


def get_terabox_direct_link(terabox_url):
    clean_url = clean_terabox_url(terabox_url)

    # API Method 1: Terabox-DL API
    try:
        api_1 = f"https://terabox-dl.qtcloud.workers.dev/api/get-info?shorturl={terabox_url.split('/s/')[-1]}"
        res = requests.get(api_1, timeout=10)
        if res.status_code == 200:
            d = res.json()
            if "downloadLink" in d:
                return {
                    "download_url": d["downloadLink"],
                    "title": d.get("fileName", "TeraBox File"),
                }
    except Exception as e:
        print(f"API 1 Failed: {e}")

    # API Method 2: Link-API Worker
    try:
        api_2 = f"https://terabox.app.link-api.workers.dev/?url={clean_url}"
        res = requests.get(api_2, timeout=10)
        if res.status_code == 200:
            d = res.json()
            dl = d.get("download_link") or d.get("url")
            if dl:
                return {
                    "download_url": dl,
                    "title": d.get("file_name", "TeraBox File"),
                }
    except Exception as e:
        print(f"API 2 Failed: {e}")

    # API Method 3: Direct Web Worker API
    try:
        api_3 = f"https://api.freeterabox.com/api/get-download?url={terabox_url}"
        res = requests.get(api_3, timeout=10)
        if res.status_code == 200:
            d = res.json()
            if d.get("status") and d.get("url"):
                return {
                    "download_url": d.get("url"),
                    "title": d.get("filename", "TeraBox Video"),
                }
    except Exception as e:
        print(f"API 3 Failed: {e}")

    return None


# -------------------------------------------------------------
# Message Handling
# -------------------------------------------------------------
def handle_message(chat_id, text):
    if text == "/start":
        send_message(
            chat_id,
            "👋 <b>Welcome to TeraBox Downloader Bot!</b>\n\n"
            "Koi bhi TeraBox video link yahan paste karein!",
        )
        return

    # Check for TeraBox / 1024terabox domain keywords
    if any(
        k in text.lower()
        for k in [
            "terabox",
            "1024terabox",
            "teraboxapp",
            "freeterabox",
            "neodrive",
        ]
    ):
        urls = re.findall(r"(https?://[^\s]+)", text)
        if urls:
            target_url = urls[0]
            send_message(
                chat_id,
                "🔗 <b>TeraBox Link Detected!</b>\n⏳ Direct Download Link Extract ho raha hai...",
            )

            file_info = get_terabox_direct_link(target_url)

            if file_info and file_info.get("download_url"):
                d_url = file_info["download_url"]
                title = file_info["title"]

                send_message(
                    chat_id, "⬇️ <b>Video Telegram par Send kar rahe hain...</b>"
                )

                # Send directly to Telegram
                result = send_video(chat_id, d_url, title=title)

                # If Telegram fails (e.g., File Size > 50MB restriction)
                if not result or not result.get("ok"):
                    send_message(
                        chat_id,
                        f"📁 <b>File Fast Download Link:</b>\n\n"
                        f"<b>Title:</b> {title}\n\n"
                        f"👉 <a href='{d_url}'>Click Here to Download Video</a>\n\n"
                        f"💡 <i>Tip: Link ko browser me khol kar Fast Download karein!</i>",
                    )
            else:
                send_message(
                    chat_id,
                    "❌ Is link se video Extract nahi ho paya.\n\n"
                    "<i>Karan: File private ho sakti hai ya TeraBox Server Busy hai.</i>",
                )
        return

    send_message(
        chat_id,
        "⚠️ Please ek valid TeraBox Link bhejein!\n\n<i>Example: https://1024terabox.com/s/...</i>",
    )


# -------------------------------------------------------------
# Main Loop
# -------------------------------------------------------------
def main():
    threading.Thread(target=run_dummy_server, daemon=True).start()
    print("TeraBox Bot Active...")
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
        
