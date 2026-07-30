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
# Web Server (Keep Alive)
# -------------------------------------------------------------
class DummyServerHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"Music Bot is Active!")

    def log_message(self, format, *args):
        return


def run_dummy_server():
    httpd = HTTPServer(("", 8080), DummyServerHandler)
    httpd.serve_forever()


# -------------------------------------------------------------
# Telegram Functions
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
        print(f"Update error: {e}")
    return None


# -------------------------------------------------------------
# Piped API Engine (Bypasses YouTube Blocks)
# -------------------------------------------------------------
def fetch_audio_from_piped(query_or_url):
    video_id = None

    # Check if input is a YouTube URL
    if "youtu.be/" in query_or_url:
        video_id = query_or_url.split("youtu.be/")[1].split("?")[0].split("&")[0]
    elif "youtube.com/watch" in query_or_url:
        match = re.search(r"v=([a-zA-Z0-9_-]+)", query_or_url)
        if match:
            video_id = match.group(1)

    piped_instances = [
        "https://pipedapi.kavin.rocks",
        "https://api.piped.private.coffee",
        "https://pipedapi.mha.fi",
    ]

    # If not a URL, search by song name
    if not video_id:
        for instance in piped_instances:
            try:
                search_url = f"{instance}/search?q={requests.utils.quote(query_or_url)}&filter=music_songs"
                res = requests.get(search_url, headers=HEADERS, timeout=8)
                if res.status_code == 200:
                    data = res.json()
                    items = data.get("items", [])
                    if items:
                        url_path = items[0].get("url", "")
                        if "/watch?v=" in url_path:
                            video_id = url_path.split("/watch?v=")[1]
                            break
            except Exception as e:
                print(f"Search failed on {instance}: {e}")

    if not video_id:
        return None

    # Fetch Audio Stream URL using Video ID
    for instance in piped_instances:
        try:
            stream_url = f"{instance}/streams/{video_id}"
            res = requests.get(stream_url, headers=HEADERS, timeout=10)
            if res.status_code == 200:
                data = res.json()
                title = data.get("title", "Song Audio")
                uploader = data.get("uploader", "Music Bot")
                audio_streams = data.get("audioStreams", [])

                if audio_streams:
                    # Pick highest bitrate audio stream
                    best_audio = sorted(
                        audio_streams,
                        key=lambda x: x.get("bitrate", 0),
                        reverse=True,
                    )[0]
                    return {
                        "title": title,
                        "artist": uploader,
                        "audio_url": best_audio.get("url"),
                    }
        except Exception as e:
            print(f"Stream fetch failed on {instance}: {e}")

    return None


# -------------------------------------------------------------
# Request Processor
# -------------------------------------------------------------
def process_song_request(chat_id, query_text):
    send_message(
        chat_id,
        f"🔎 <b>Searching MP3:</b> <i>{query_text}</i>\n⏳ <i>Wait karein...</i>",
    )

    song_info = fetch_audio_from_piped(query_text)

    if song_info and song_info.get("audio_url"):
        title = song_info["title"]
        artist = song_info["artist"]
        audio_url = song_info["audio_url"]

        send_message(
            chat_id, "⬆️ <b>MP3 Song Telegram par upload ho raha hai...</b>"
        )

        result = send_audio(chat_id, audio_url, title=title, performer=artist)

        # Fallback direct download link if Telegram audio send times out
        if not result or not result.get("ok"):
            send_message(
                chat_id,
                f"🎧 <b>Song Download Link Ready:</b>\n\n"
                f"🎵 <b>{title}</b>\n\n"
                f"👉 <a href='{audio_url}'>Click Here To Play/Download MP3</a>",
            )
    else:
        send_message(
            chat_id,
            "❌ <b>Gaana nahi mila!</b>\n\n"
            "Kripya sahi naam likhein (Jaise: <code>Kesariya</code> ya <code>Tere Sang Yaara</code>).",
        )


# -------------------------------------------------------------
# Main Message Handler
# -------------------------------------------------------------
def handle_message(chat_id, text):
    if text == "/start":
        send_message(
            chat_id,
            "👋 <b>Welcome to MP3 Music Bot! 🎶</b>\n\n"
            "Gaane ka **Naam** likhein ya **YouTube Link** paste karein!\n\n"
            "<i>Example: Kesariya</i>",
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
    print("Piped Engine Music Bot Running...")
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
    
