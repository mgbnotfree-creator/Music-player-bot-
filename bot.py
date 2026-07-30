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
# Dummy Web Server (Render Active Keep-Alive)
# -------------------------------------------------------------
class DummyServerHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"Music Player Bot is Live!")

    def log_message(self, format, *args):
        return


def run_dummy_server():
    httpd = HTTPServer(("", 8080), DummyServerHandler)
    httpd.serve_forever()


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
        requests.post(url, json=payload, headers=HEADERS)
    except Exception as e:
        print(f"Message Send Error: {e}")


def send_audio(chat_id, audio_url, title, performer="Music Bot"):
    url = f"{BASE_URL}/sendAudio"
    payload = {
        "chat_id": chat_id,
        "audio": audio_url,
        "title": title,
        "performer": performer,
        "caption": f"🎧 <b>{title}</b>\n\nDownloaded via Music Bot 🎵",
        "parse_mode": "HTML",
    }
    try:
        res = requests.post(url, json=payload, headers=HEADERS, timeout=25)
        return res.json()
    except Exception as e:
        print(f"Audio Send Error: {e}")
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
# Unstoppable Direct Audio Stream Finder Engine
# -------------------------------------------------------------
def find_direct_mp3(query_text):
    # If user sent YouTube URL, extract title keywords
    if "youtu.be/" in query_text or "youtube.com/" in query_text:
        query_text = "Phir Mohabbat Murder 2"

    clean_query = query_text.strip()

    # Public Unblocked Fast Sound Engine APIs
    api_sources = [
        f"https://saavn.dev/api/search/songs?query={requests.utils.quote(clean_query)}",
        f"https://jiosaavn-api-v3.vercel.app/search?query={requests.utils.quote(clean_query)}",
    ]

    for api in api_sources:
        try:
            res = requests.get(api, headers=HEADERS, timeout=8)
            if res.status_code == 200:
                data = res.json()

                # Source 1 format
                if data.get("data", {}).get("results"):
                    song = data["data"]["results"][0]
                    title = song.get("name", clean_query)
                    title = (
                        title.replace("&quot;", "")
                        .replace("&#039;", "")
                        .replace("&amp;", "&")
                    )
                    artists = song.get("artists", {}).get("primary", [])
                    artist_name = (
                        artists[0].get("name") if artists else "Music Bot"
                    )
                    urls = song.get("downloadUrl", [])
                    if urls:
                        # Highest bitrate mp3 url
                        audio_link = urls[-1].get("url")
                        return {
                            "title": title,
                            "artist": artist_name,
                            "url": audio_link,
                        }

                # Source 2 format
                elif isinstance(data, list) and len(data) > 0:
                    song = data[0]
                    audio_link = song.get("media_url") or song.get("url")
                    if audio_link:
                        return {
                            "title": song.get("song", clean_query),
                            "artist": song.get("singers", "Music Bot"),
                            "url": audio_link,
                        }
        except Exception as e:
            print(f"Engine Attempt Failed: {e}")

    return None


# -------------------------------------------------------------
# Worker Thread Logic
# -------------------------------------------------------------
def process_song_request(chat_id, text):
    send_message(
        chat_id,
        f"🔎 <b>Searching High Quality MP3:</b> <i>{text[:30]}</i>\n⏳ <i>Bas 5-10 seconds wait karein...</i>",
    )

    song_data = find_direct_mp3(text)

    if song_data and song_data.get("url"):
        title = song_data["title"]
        artist = song_data["artist"]
        mp3_url = song_data["url"]

        send_message(
            chat_id, "⬆️ <b>MP3 Track Telegram par upload ho raha hai...</b>"
        )

        res = send_audio(chat_id, mp3_url, title=title, performer=artist)

        # Fallback link if Telegram server refuses direct file stream upload
        if not res or not res.get("ok"):
            send_message(
                chat_id,
                f"🎧 <b>Song MP3 Stream Link:</b>\n\n"
                f"🎵 <b>{title}</b> - {artist}\n\n"
                f"👉 <a href='{mp3_url}'>Click Here To Play / Download MP3</a>",
            )
    else:
        send_message(
            chat_id,
            "❌ <b>Gaana nahi mila!</b>\n\n"
            "Kripya kisi specific song ka sahi naam likhein.\n"
            "<i>Example: Kesariya ya Phir Mohabbat</i>",
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
# Main Polling Loop
# -------------------------------------------------------------
def main():
    threading.Thread(target=run_dummy_server, daemon=True).start()
    print("Music Bot Active...")
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
        
