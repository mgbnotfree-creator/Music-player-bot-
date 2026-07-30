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

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
        " like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}


# -------------------------------------------------------------
# Web Server for Render
# -------------------------------------------------------------
class HealthCheckHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"Music Downloader Bot Active!")

    def log_message(self, format, *args):
        return


def run_health_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("", port), HealthCheckHandler)
    server.serve_forever()


# -------------------------------------------------------------
# Telegram API Wrappers
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


def upload_audio_stream(chat_id, audio_bytes, filename, title, performer):
    url = f"{BASE_URL}/sendAudio"
    payload = {
        "chat_id": chat_id,
        "title": title,
        "performer": performer,
        "caption": f"🎧 <b>{title}</b>\n\nDownloaded via Music Bot 🎵",
        "parse_mode": "HTML",
    }
    try:
        files = {"audio": (filename, audio_bytes, "audio/mpeg")}
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
# Dual Engine (Saavn High Quality API + Direct YT Direct Stream)
# -------------------------------------------------------------
def fetch_audio_bytes(query_text):
    clean_query = re.sub(
        r"https?://\S+|\(.*?\)|\[.*?\]|official|video|lyrical",
        "",
        query_text,
        flags=re.I,
    ).strip()
    if not clean_query:
        clean_query = "Phir Mohabbat"

    # ENGINE 1: Saavn API (Fastest & Best Quality Audio File)
    try:
        api_url = f"https://saavn.dev/api/search/songs?query={requests.utils.quote(clean_query)}"
        res = requests.get(api_url, headers=HEADERS, timeout=8)
        if res.status_code == 200:
            results = res.json().get("data", {}).get("results", [])
            if results:
                song = results[0]
                title = (
                    song.get("name", "Song")
                    .replace("&quot;", "")
                    .replace("&#039;", "")
                    .replace("&amp;", "&")
                )
                artists = song.get("artists", {}).get("primary", [])
                performer = artists[0].get("name") if artists else "Music Bot"

                dl_urls = song.get("downloadUrl", [])
                if dl_urls:
                    target_url = dl_urls[-1].get(
                        "url"
                    )  # Highest quality audio
                    audio_res = requests.get(
                        target_url, headers=HEADERS, timeout=20
                    )
                    if (
                        audio_res.status_code == 200
                        and len(audio_res.content) > 200000
                    ):
                        return (
                            audio_res.content,
                            f"{title}.mp3",
                            title,
                            performer,
                        )
    except Exception as e:
        print(f"Saavn Engine Error: {e}")

    # ENGINE 2: Direct YT Stream without FFmpeg Dependency
    try:
        target = (
            query_text
            if query_text.startswith("http")
            else f"ytsearch1:{clean_query} song"
        )

        ydl_opts = {
            "format": "m4a/bestaudio/best",
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "user_agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            ),
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(target, download=False)
            if "entries" in info and info["entries"]:
                info = info["entries"][0]

            direct_stream_url = info.get("url")
            title = info.get("title", "Music Song")
            performer = info.get("uploader", "Music Bot")

            if direct_stream_url:
                audio_res = requests.get(
                    direct_stream_url, headers=HEADERS, timeout=25
                )
                if (
                    audio_res.status_code == 200
                    and len(audio_res.content) > 200000
                ):
                    return audio_res.content, f"{title}.m4a", title, performer
    except Exception as e:
        print(f"YT Direct Engine Error: {e}")

    return None, None, None, None


# -------------------------------------------------------------
# Processing Request Logic
# -------------------------------------------------------------
def process_song_request(chat_id, user_text):
    msg_id = send_message(
        chat_id,
        f"🔎 <b>Searching & Processing MP3:</b> <i>{user_text[:25]}</i>\n⏳ <i>5-10 seconds wait karein...</i>",
    )

    audio_bytes, filename, title, performer = fetch_audio_bytes(user_text)

    if audio_bytes:
        edit_message(
            chat_id,
            msg_id,
            "⬆️ <b>MP3 Track Telegram par upload ho raha hai...</b>",
        )

        res = upload_audio_stream(
            chat_id, audio_bytes, filename, title, performer
        )

        if res and res.get("ok"):
            delete_message(chat_id, msg_id)
        else:
            edit_message(
                chat_id,
                msg_id,
                "❌ <b>Upload Error!</b> File size zyaada hone ki wajah se upload nahi ho paya.",
            )
    else:
        edit_message(
            chat_id,
            msg_id,
            "❌ <b>Gaana nahi mila!</b>\n\n"
            "Kripya kisi specific song ka direct naam likhein (Jaise: <code>Kesariya</code> ya <code>Phir Mohabbat</code>).",
        )


# -------------------------------------------------------------
# Main Polling Loop
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
    print("Dual Direct Stream Engine Active...")
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
