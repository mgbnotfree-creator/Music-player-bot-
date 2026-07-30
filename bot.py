import os
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
import requests

# -------------------------------------------------------------
# Bot Configuration
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
# Dummy Web Server (Render App Ko Alive Rakhne Ke Liye)
# -------------------------------------------------------------
class DummyServerHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"Music Bot Alive!")

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
        res = requests.post(url, json=payload, headers=HEADERS, timeout=30)
        return res.json()
    except Exception as e:
        print(f"Send Audio Error: {e}")
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
# Proxy-Mesh Invidious/Piped Engine (Bypasses Cloud IP Blocks)
# -------------------------------------------------------------
INVIDIOUS_INSTANCES = [
    "https://inv.riverside.rocks",
    "https://invidious.nerdvpn.de",
    "https://vid.puffyan.us",
    "https://invidious.flokinet.to",
]


def extract_video_id(user_text):
    # If input is a YouTube Link
    yt_match = re.search(
        r"(?:v=|\/|youtu\.be\/)([a-zA-Z0-9_-]{11})", user_text
    )
    if yt_match:
        return yt_match.group(1)

    # Clean non-music terms from title queries
    clean_query = re.sub(
        r"https?://\S+|official|video|song|full|hd|lyrical|4k",
        "",
        user_text,
        flags=re.I,
    ).strip()

    # If it's a song name, search via Invidious Instances
    for instance in INVIDIOUS_INSTANCES:
        try:
            search_api = f"{instance}/api/v1/search?q={requests.utils.quote(clean_query)}&type=video"
            res = requests.get(search_api, headers=HEADERS, timeout=6)
            if res.status_code == 200:
                items = res.json()
                if items and len(items) > 0:
                    return items[0].get("videoId")
        except Exception:
            continue

    return None


def get_audio_stream_url(video_id):
    for instance in INVIDIOUS_INSTANCES:
        try:
            video_api = f"{instance}/api/v1/videos/{video_id}"
            res = requests.get(video_api, headers=HEADERS, timeout=6)
            if res.status_code == 200:
                data = res.json()
                title = data.get("title", "Song Audio")
                author = data.get("author", "Music Bot")

                adaptive_formats = data.get("adaptiveFormats", [])
                audio_streams = [
                    fmt
                    for fmt in adaptive_formats
                    if fmt.get("type", "").startswith("audio/")
                ]

                if audio_streams:
                    # Pick best bitrate audio format
                    audio_streams.sort(
                        key=lambda x: int(x.get("bitrate", 0)), reverse=True
                    )
                    best_audio = audio_streams[0]
                    return {
                        "title": title,
                        "artist": author,
                        "audio_url": best_audio.get("url"),
                    }
        except Exception:
            continue

    return None


# -------------------------------------------------------------
# Request Processor Logic
# -------------------------------------------------------------
def process_song_request(chat_id, user_input):
    send_message(
        chat_id,
        f"🔎 <b>Searching MP3 Stream...</b>\n⏳ <i>Kripya wait karein...</i>",
    )

    vid_id = extract_video_id(user_input)

    if not vid_id:
        send_message(
            chat_id,
            "❌ <b>Gaana nahi mila!</b>\n\n"
            "Kripya simple format me song ka naam likhein.\n"
            "<i>Example: Kesariya ya Phir Mohabbat</i>",
        )
        return

    song_info = get_audio_stream_url(vid_id)

    if song_info and song_info.get("audio_url"):
        title = song_info["title"]
        artist = song_info["artist"]
        audio_url = song_info["audio_url"]

        send_message(
            chat_id, "⬆️ <b>MP3 Track Telegram par upload ho raha hai...</b>"
        )

        res = send_audio(chat_id, audio_url, title=title, performer=artist)

        # Direct Audio Link Backup
        if not res or not res.get("ok"):
            send_message(
                chat_id,
                f"🎧 <b>Direct MP3 Audio Ready:</b>\n\n"
                f"🎵 <b>{title}</b> - {artist}\n\n"
                f"👉 <a href='{audio_url}'>Click Here To Play/Download MP3</a>",
            )
    else:
        send_message(
            chat_id,
            "❌ <b>Gaana nahi mila!</b>\n\n"
            "Server block ki wajah se stream fetch nahi ho saki. Direct short song name try karein (Jaise: <code>Kesariya</code>).",
        )


# -------------------------------------------------------------
# Main Message Router
# -------------------------------------------------------------
def handle_message(chat_id, text):
    if text == "/start":
        send_message(
            chat_id,
            "👋 <b>Welcome to High Quality MP3 Music Bot! 🎶</b>\n\n"
            "Gaane ka **Naam** likhein ya **YouTube Link** bhejien!\n\n"
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
    print("Multi-Proxy Music Bot Running...")
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
    
