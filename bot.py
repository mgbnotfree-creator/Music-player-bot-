import io
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
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    )
}


# -------------------------------------------------------------
# Keep Alive Web Server (Render Web Service Requirement)
# -------------------------------------------------------------
class DummyServerHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"Music Player Bot is Running Perfectly!")

    def log_message(self, format, *args):
        return


def run_dummy_server():
    httpd = HTTPServer(("", 8080), DummyServerHandler)
    httpd.serve_forever()


# -------------------------------------------------------------
# Telegram API Helpers (Multipart Buffer File Upload)
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


def upload_audio_file(chat_id, audio_bytes, filename, title, performer):
    url = f"{BASE_URL}/sendAudio"
    payload = {
        "chat_id": chat_id,
        "title": title,
        "performer": performer,
        "caption": f"🎧 <b>{title}</b>\n\nDownloaded via Music Bot 🎵",
        "parse_mode": "HTML",
    }
    files = {"audio": (filename, audio_bytes, "audio/mpeg")}
    try:
        res = requests.post(
            url, data=payload, files=files, headers=HEADERS, timeout=60
        )
        return res.json()
    except Exception as e:
        print(f"File Upload Error: {e}")
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
# High-Speed Audio Download Engines
# -------------------------------------------------------------
def search_and_download_audio(user_text):
    # 1. Format YouTube or Song Query
    search_query = user_text.strip()

    # Search via Saavn API Engine
    try:
        clean_name = re.sub(
            r"https?://\S+|official|video|song|full|hd|lyrical|4k",
            "",
            search_query,
            flags=re.I,
        ).strip()
        if not clean_name:
            clean_name = "Phir Mohabbat"

        api_url = f"https://saavn.dev/api/search/songs?query={requests.utils.quote(clean_name)}"
        res = requests.get(api_url, headers=HEADERS, timeout=10)

        if res.status_code == 200:
            data = res.json()
            results = data.get("data", {}).get("results", [])
            if results:
                song = results[0]
                title = (
                    song.get("name", "Song")
                    .replace("&quot;", "")
                    .replace("&#039;", "")
                    .replace("&amp;", "&")
                )
                artists = song.get("artists", {}).get("primary", [])
                artist_name = (
                    artists[0].get("name") if artists else "Music Bot"
                )

                urls = song.get("downloadUrl", [])
                if urls:
                    # Prefer medium quality 160kbps to download fast on Render memory
                    audio_url = urls[-1].get("url")
                    audio_res = requests.get(
                        audio_url, headers=HEADERS, timeout=25
                    )
                    if (
                        audio_res.status_code == 200
                        and len(audio_res.content) > 100000
                    ):
                        return {
                            "title": title,
                            "artist": artist_name,
                            "bytes": audio_res.content,
                            "filename": f"{title}.mp3",
                        }
    except Exception as e:
        print(f"Primary Search Failed: {e}")

    # Backup Direct Stream Engine
    try:
        sc_url = f"https://jiosaavn-api-v3.vercel.app/search?query={requests.utils.quote(search_query)}"
        res2 = requests.get(sc_url, headers=HEADERS, timeout=10)
        if res2.status_code == 200:
            songs = res2.json()
            if isinstance(songs, list) and len(songs) > 0:
                song = songs[0]
                dl_url = song.get("media_url") or song.get("url")
                if dl_url:
                    audio_res = requests.get(
                        dl_url, headers=HEADERS, timeout=25
                    )
                    if (
                        audio_res.status_code == 200
                        and len(audio_res.content) > 100000
                    ):
                        return {
                            "title": song.get("song", "Music Track"),
                            "artist": song.get("singers", "Music Bot"),
                            "bytes": audio_res.content,
                            "filename": "audio.mp3",
                        }
    except Exception as e:
        print(f"Backup Stream Failed: {e}")

    return None


# -------------------------------------------------------------
# Worker Thread Logic
# -------------------------------------------------------------
def process_song_request(chat_id, user_text):
    send_message(
        chat_id,
        f"🔎 <b>Searching & Processing:</b> <i>{user_text[:25]}</i>\n⏳ <i>MP3 File Download & Upload ho rahi hai, 5-10 sec wait karein...</i>",
    )

    audio_data = search_and_download_audio(user_text)

    if audio_data:
        title = audio_data["title"]
        artist = audio_data["artist"]
        bytes_data = audio_data["bytes"]
        filename = audio_data["filename"]

        # Directly send binary MP3 file through Telegram API
        result = upload_audio_file(
            chat_id, bytes_data, filename, title, artist
        )

        if not result or not result.get("ok"):
            send_message(
                chat_id,
                "❌ <b>Upload Error!</b> File size zyaada hone ki waja se Telegram server refuse kar raha hai.",
            )
    else:
        send_message(
            chat_id,
            "❌ <b>Gaana nahi mila!</b>\n\n"
            "Kripya kisi specific song ka direct naam likhein (Jaise: <code>Kesariya</code> ya <code>Phir Mohabbat</code>).",
        )


# -------------------------------------------------------------
# Message Router
# -------------------------------------------------------------
def handle_message(chat_id, text):
    if text == "/start":
        send_message(
            chat_id,
            "👋 <b>Welcome to High Quality MP3 Music Bot! 🎶</b>\n\n"
            "Kisi bhi song ka **Naam** likh kar bhejein!\n\n"
            "<i>Example: Phir Mohabbat</i>",
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
    print("Direct File Upload Bot Active...")
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
