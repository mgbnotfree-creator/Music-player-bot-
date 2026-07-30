import os
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
import requests
import yt_dlp

# -------------------------------------------------------------
# Bot Configurations
# -------------------------------------------------------------
BOT_TOKEN = "8983781306:AAHod4RCSd6G3L_A2stv_GQWLvOWm3S3LvQ"
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    )
}


# -------------------------------------------------------------
# Keep-Alive Web Server for Render Free Tier
# -------------------------------------------------------------
class HealthCheckHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"Music Downloader Server Running!")

    def log_message(self, format, *args):
        return


def run_health_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("", port), HealthCheckHandler)
    server.serve_forever()


# -------------------------------------------------------------
# Pure Telegram API Calls (No 'telegram' package needed)
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
        res = requests.post(
            url, json=payload, headers=HEADERS, timeout=10
        ).json()
        if res.get("ok"):
            return res.get("result", {}).get("message_id")
    except Exception as e:
        print(f"Send Msg Error: {e}")
    return None


def edit_message(chat_id, message_id, text):
    if not message_id:
        return
    url = f"{BASE_URL}/editMessageText"
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    try:
        requests.post(url, json=payload, headers=HEADERS, timeout=10)
    except Exception as e:
        print(f"Edit Msg Error: {e}")


def delete_message(chat_id, message_id):
    if not message_id:
        return
    url = f"{BASE_URL}/deleteMessage"
    payload = {"chat_id": chat_id, "message_id": message_id}
    try:
        requests.post(url, json=payload, headers=HEADERS, timeout=10)
    except Exception:
        pass


def upload_audio_file(chat_id, filepath, title, performer):
    url = f"{BASE_URL}/sendAudio"
    payload = {
        "chat_id": chat_id,
        "title": title,
        "performer": performer,
        "caption": f"🎧 <b>{title}</b>\n\nDownloaded via Music Bot 🎵",
        "parse_mode": "HTML",
    }
    try:
        with open(filepath, "rb") as f:
            files = {"audio": (os.path.basename(filepath), f, "audio/mpeg")}
            res = requests.post(
                url, data=payload, files=files, headers=HEADERS, timeout=120
            )
            return res.json()
    except Exception as e:
        print(f"Audio Upload Error: {e}")
        return None


def get_updates(offset=None):
    url = f"{BASE_URL}/getUpdates"
    params = {"timeout": 30, "offset": offset}
    try:
        res = requests.get(url, params=params, timeout=35)
        if res.status_code == 200:
            return res.json()
    except Exception as e:
        print(f"Get Updates Error: {e}")
    return None


# -------------------------------------------------------------
# High Performance Downloader Engine (yt-dlp)
# -------------------------------------------------------------
def download_audio(search_query):
    if search_query.startswith("http://") or search_query.startswith(
        "https://"
    ):
        target = search_query
    else:
        clean_text = re.sub(
            r"\(.*?\)|\[.*?\]", "", search_query
        ).strip()  # Clean query
        target = f"ytsearch1:{clean_text} song"

    out_file = f"song_{int(time.time())}.mp3"

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": out_file,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "user_agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        ),
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(target, download=True)
            if "entries" in info and info["entries"]:
                info = info["entries"][0]

            title = info.get("title", "Audio Track")
            performer = info.get("uploader", "Music Bot")

            if os.path.exists(out_file):
                return out_file, title, performer
    except Exception as e:
        print(f"yt-dlp Download Failed: {e}")

    return None, None, None


# -------------------------------------------------------------
# Worker Request Handling
# -------------------------------------------------------------
def process_song_request(chat_id, user_text):
    msg_id = send_message(
        chat_id,
        f"🔎 <b>Searching & Downloading MP3:</b> <i>{user_text[:25]}</i>\n⏳ <i>Bas 5-10 seconds wait karein...</i>",
    )

    file_path, title, performer = download_audio(user_text)

    if file_path and os.path.exists(file_path):
        edit_message(
            chat_id,
            msg_id,
            "⬆️ <b>MP3 Audio file Telegram par upload ho rahi hai...</b>",
        )

        res = upload_audio_file(chat_id, file_path, title, performer)

        # Remove local file after attempt
        try:
            os.remove(file_path)
        except Exception:
            pass

        if res and res.get("ok"):
            delete_message(chat_id, msg_id)
        else:
            edit_message(
                chat_id,
                msg_id,
                "❌ <b>Upload Error!</b> File size zyaada hone ki wajah se Telegram ne reject kar diya.",
            )
    else:
        edit_message(
            chat_id,
            msg_id,
            "❌ <b>Gaana nahi mila!</b>\n\n"
            "Kripya kisi specific song ka sahi naam ya YouTube link bhejein.",
        )


# -------------------------------------------------------------
# Main Telegram Polling Loop
# -------------------------------------------------------------
def handle_message(chat_id, text):
    if text == "/start":
        send_message(
            chat_id,
            "👋 <b>Welcome to High Quality MP3 Downloader! 🎵</b>\n\n"
            "Kisi bhi song ka **Naam** ya **YouTube Link** bhejien!\n\n"
            "<i>Example: Phir Mohabbat</i>",
        )
        return

    threading.Thread(
        target=process_song_request, args=(chat_id, text)
    ).start()


def main():
    threading.Thread(target=run_health_server, daemon=True).start()
    print("Clean Native Polling Engine Started...")
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
    
