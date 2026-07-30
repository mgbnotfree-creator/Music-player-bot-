import io
import os
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
import requests

# -------------------------------------------------------------
# Configs
# -------------------------------------------------------------
BOT_TOKEN = "8983781306:AAHod4RCSd6G3L_A2stv_GQWLvOWm3S3LvQ"
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    )
}


# -------------------------------------------------------------
# Keep Alive Server
# -------------------------------------------------------------
class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, format, *args):
        return


def start_server():
    port = int(os.environ.get("PORT", 8080))
    HTTPServer(("", port), HealthHandler).serve_forever()


# -------------------------------------------------------------
# Telegram Functions
# -------------------------------------------------------------
def send_msg(chat_id, text):
    try:
        r = requests.post(
            f"{BASE_URL}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=10,
        ).json()
        if r.get("ok"):
            return r["result"]["message_id"]
    except Exception:
        pass
    return None


def edit_msg(chat_id, msg_id, text):
    if not msg_id:
        return
    try:
        requests.post(
            f"{BASE_URL}/editMessageText",
            json={
                "chat_id": chat_id,
                "message_id": msg_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=10,
        )
    except Exception:
        pass


def delete_msg(chat_id, msg_id):
    if not msg_id:
        return
    try:
        requests.post(
            f"{BASE_URL}/deleteMessage",
            json={"chat_id": chat_id, "message_id": msg_id},
            timeout=10,
        )
    except Exception:
        pass


def upload_mp3(chat_id, audio_bytes, title):
    try:
        files = {"audio": (f"{title}.mp3", audio_bytes, "audio/mpeg")}
        data = {
            "chat_id": chat_id,
            "title": title,
            "performer": "Music Player Bot",
            "caption": f"🎧 <b>{title}</b>\n\nDownloaded Successfully! 🎵",
            "parse_mode": "HTML",
        }
        res = requests.post(
            f"{BASE_URL}/sendAudio",
            data=data,
            files=files,
            headers=HEADERS,
            timeout=120,
        )
        return res.json()
    except Exception as e:
        print(f"Upload error: {e}")
        return None


# -------------------------------------------------------------
# Working API Engine (Cobalt + Saavn)
# -------------------------------------------------------------
def get_audio_bytes(user_input):
    # API 1: Public High-Speed Saavn Search Engine
    clean_query = re.sub(
        r"https?://\S+|\(.*?\)|\[.*?\]", "", user_input
    ).strip()
    if not clean_query:
        clean_query = "Phir Mohabbat"

    try:
        url = f"https://saavn.dev/api/search/songs?query={requests.utils.quote(clean_query)}"
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code == 200:
            data = r.json().get("data", {}).get("results", [])
            if data:
                song = data[0]
                title = song.get("name", "Audio Song").replace("&quot;", "")
                download_urls = song.get("downloadUrl", [])
                if download_urls:
                    mp3_url = download_urls[-1].get("url")
                    audio_r = requests.get(
                        mp3_url, headers=HEADERS, timeout=25
                    )
                    if (
                        audio_r.status_code == 200
                        and len(audio_r.content) > 100000
                    ):
                        return audio_r.content, title
    except Exception as e:
        print(f"Saavn Engine Error: {e}")

    # API 2: Direct YouTube Link via Cobalt Instance
    if "youtu" in user_input:
        try:
            cobalt_url = "https://api.cobalt.tools/api/json"
            payload = {
                "url": user_input,
                "downloadMode": "audio",
                "audioFormat": "mp3",
            }
            c_headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
            res = requests.post(
                cobalt_url, json=payload, headers=c_headers, timeout=15
            )
            if res.status_code == 200:
                audio_link = res.json().get("url")
                if audio_link:
                    audio_r = requests.get(
                        audio_link, headers=HEADERS, timeout=30
                    )
                    if (
                        audio_r.status_code == 200
                        and len(audio_r.content) > 100000
                    ):
                        return audio_r.content, "YouTube Audio Track"
        except Exception as e:
            print(f"Cobalt Engine Error: {e}")

    return None, None


# -------------------------------------------------------------
# Main Worker
# -------------------------------------------------------------
def process_request(chat_id, text):
    msg_id = send_msg(
        chat_id,
        f"🔎 <b>Processing:</b> <i>{text[:25]}</i>\n⏳ <i>Downloading MP3 file...</i>",
    )

    audio_bytes, title = get_audio_bytes(text)

    if audio_bytes:
        edit_msg(chat_id, msg_id, "⬆️ <b>Uploading audio to Telegram...</b>")
        res = upload_mp3(chat_id, audio_bytes, title)
        if res and res.get("ok"):
            delete_msg(chat_id, msg_id)
        else:
            edit_msg(
                chat_id,
                msg_id,
                "❌ <b>Upload Failed!</b> File size too large.",
            )
    else:
        edit_msg(
            chat_id,
            msg_id,
            "❌ <b>Gaana nahi mila!</b> Kripya koi dusra song try karein.",
        )


def main():
    threading.Thread(target=start_server, daemon=True).start()
    print("Bot is Running...")
    offset = None

    while True:
        try:
            r = requests.get(
                f"{BASE_URL}/getUpdates",
                params={"timeout": 30, "offset": offset},
                timeout=35,
            )
            if r.status_code == 200:
                data = r.json()
                if data.get("ok"):
                    for update in data.get("result", []):
                        offset = update["update_id"] + 1
                        if "message" in update and "text" in update["message"]:
                            chat_id = update["message"]["chat"]["id"]
                            user_text = update["message"]["text"].strip()
                            if user_text == "/start":
                                send_msg(
                                    chat_id,
                                    "👋 <b>Welcome!</b> Direct song name likhein.",
                                )
                            else:
                                threading.Thread(
                                    target=process_request,
                                    args=(chat_id, user_text),
                                ).start()
        except Exception:
            pass
        time.sleep(1)


if __name__ == "__main__":
    main()
