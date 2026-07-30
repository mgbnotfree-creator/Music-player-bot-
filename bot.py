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

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
        " like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}


# -------------------------------------------------------------
# Web Server (Keep Render Alive)
# -------------------------------------------------------------
class DummyServerHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"Full Song MP3 Bot is Running!")

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
        requests.post(url, json=payload, headers=HEADERS)
    except Exception as e:
        print(f"Send Message Error: {e}")


def send_audio(chat_id, audio_input, title, performer="Music Bot"):
    url = f"{BASE_URL}/sendAudio"

    # If input is a web URL
    if str(audio_input).startswith("http"):
        payload = {
            "chat_id": chat_id,
            "audio": audio_input,
            "title": title,
            "performer": performer,
            "caption": f"🎧 <b>{title}</b>\n\nDownloaded via Music Bot 🎵",
            "parse_mode": "HTML",
        }
        try:
            res = requests.post(url, json=payload, headers=HEADERS, timeout=30)
            return res.json()
        except Exception as e:
            print(f"Send Audio Link Error: {e}")
            return None
    else:
        # If input is a local file
        try:
            with open(audio_input, "rb") as file_data:
                files = {"audio": file_data}
                data = {
                    "chat_id": chat_id,
                    "title": title,
                    "performer": performer,
                    "caption": f"🎧 <b>{title}</b>\n\nDownloaded via Music Bot 🎵",
                    "parse_mode": "HTML",
                }
                res = requests.post(
                    url, data=data, files=files, headers=HEADERS, timeout=60
                )
                return res.json()
        except Exception as e:
            print(f"Send Local File Error: {e}")
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
# Extract Query or Video ID from YouTube Link
# -------------------------------------------------------------
def clean_user_input(text):
    text = text.strip()

    # YouTube URL check
    yt_match = re.search(
        r"(?:v=|\/|youtu\.be\/)([a-zA-Z0-9_-]{11})", text
    )
    if yt_match:
        video_id = yt_match.group(1)
        return {"type": "yt_id", "value": video_id}

    return {"type": "name", "value": text}


# -------------------------------------------------------------
# Multi-Source Full Audio Downloader Engine
# -------------------------------------------------------------
def fetch_full_mp3(input_data):
    # Method 1: JioSaavn Unofficial Clean API (Full 320kbps/160kbps MP3)
    if input_data["type"] == "name":
        search_query = input_data["value"]
        try:
            saavn_api = f"https://saavn.dev/api/search/songs?query={requests.utils.quote(search_query)}"
            res = requests.get(saavn_api, headers=HEADERS, timeout=10)
            if res.status_code == 200:
                data = res.json()
                if data.get("success") and data.get("data", {}).get("results"):
                    song = data["data"]["results"][0]
                    title = song.get("name", search_query)
                    title = (
                        title.replace("&quot;", "")
                        .replace("&#039;", "")
                        .replace("&amp;", "&")
                    )

                    artist_list = song.get("artists", {}).get("primary", [])
                    artist = (
                        artist_list[0].get("name", "Artist")
                        if artist_list
                        else "Music Bot"
                    )

                    download_urls = song.get("downloadUrl", [])
                    if download_urls:
                        audio_url = download_urls[-1].get("url")
                        return {
                            "title": title,
                            "artist": artist,
                            "audio_url": audio_url,
                        }
        except Exception as e:
            print(f"Saavn Engine Error: {e}")

    # Method 2: Cobalt Public API Engine (Handles YouTube Links & Full Extracts)
    try:
        if input_data["type"] == "yt_id":
            target_url = f"https://www.youtube.com/watch?v={input_data['value']}"
        else:
            target_url = f"ytsearch1:{input_data['value']}"

        cobalt_api = "https://api.cobalt.tools/api/json"
        payload = {
            "url": (
                target_url
                if input_data["type"] == "yt_id"
                else f"https://www.youtube.com/results?search_query={requests.utils.quote(input_data['value'])}"
            ),
            "isAudioOnly": True,
            "aFormat": "mp3",
        }
        c_headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        res = requests.post(
            cobalt_api, json=payload, headers=c_headers, timeout=12
        )
        if res.status_code == 200:
            c_data = res.json()
            if c_data.get("url"):
                return {
                    "title": input_data["value"],
                    "artist": "Music Bot",
                    "audio_url": c_data["url"],
                }
    except Exception as e:
        print(f"Cobalt Engine Error: {e}")

    return None


# -------------------------------------------------------------
# Request Processing Thread
# -------------------------------------------------------------
def process_song_request(chat_id, user_text):
    parsed_input = clean_user_input(user_text)

    display_name = user_text
    if len(display_name) > 40:
        display_name = display_name[:37] + "..."

    send_message(
        chat_id,
        f"🔎 <b>Full MP3 Search:</b> <i>{display_name}</i>\n⏳ <i>Downloading...</i>",
    )

    song_info = fetch_full_mp3(parsed_input)

    if song_info and song_info.get("audio_url"):
        title = song_info["title"]
        artist = song_info["artist"]
        audio_url = song_info["audio_url"]

        send_message(
            chat_id, "⬆️ <b>Full Song Telegram par upload ho raha hai...</b>"
        )

        res = send_audio(chat_id, audio_url, title=title, performer=artist)

        # Direct Link Backup if Upload Fails
        if not res or not res.get("ok"):
            send_message(
                chat_id,
                f"🎧 <b>Full MP3 Song Stream Link:</b>\n\n"
                f"🎵 <b>{title}</b> - {artist}\n\n"
                f"👉 <a href='{audio_url}'>Click Here To Play / Download MP3</a>",
            )
    else:
        send_message(
            chat_id,
            "❌ <b>Gaana nahi mil saka!</b>\n\n"
            "Kripya simple format me song ka naam likhein:\n"
            "<i>Example: <code>Phir Mohabbat Murder 2</code></i>",
        )


# -------------------------------------------------------------
# Main Message Router
# -------------------------------------------------------------
def handle_message(chat_id, text):
    if text == "/start":
        send_message(
            chat_id,
            "👋 <b>Welcome to Full MP3 Music Bot! 🎶</b>\n\n"
            "Aap **Gaane Ka Naam** ya **YouTube Link** bhej sakte hain!\n\n"
            "<i>Example: Phir Mohabbat Murder 2</i>",
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
    print("Full Song Music Bot Online...")
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
                    
