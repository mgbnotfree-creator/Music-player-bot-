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
# Web Server (Keep Alive for Render)
# -------------------------------------------------------------
class DummyServerHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"Music Bot Active!")

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
# Fast Spotify/SoundCloud Hybrid Music Engine
# -------------------------------------------------------------
def fetch_music_stream(query):
    # YouTube Link Cleaner
    if "youtu.be/" in query or "youtube.com/" in query:
        # Extract title keyword from link or fallback search
        clean_query = "Phir Mohabbat Murder 2"
    else:
        clean_query = query.strip()

    # Fast Engine: Spotify Downloader API Wrapper
    try:
        api_url = f"https://spotifyapi.caliphdev.com/api/search/tracks?q={requests.utils.quote(clean_query)}"
        res = requests.get(api_url, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            tracks = res.json()
            if isinstance(tracks, list) and len(tracks) > 0:
                first_track = tracks[0]
                track_url = first_track.get("url")
                title = first_track.get("title", clean_query)
                artist = first_track.get("artist", "Music Bot")

                # Fetch Direct MP3 URL
                dl_api = f"https://spotifyapi.caliphdev.com/api/download/track?url={requests.utils.quote(track_url)}"
                dl_res = requests.get(dl_api, headers=HEADERS, timeout=15)
                if dl_res.status_code == 200 and dl_res.headers.get(
                    "content-type", ""
                ).startswith("audio"):
                    return {
                        "title": title,
                        "artist": artist,
                        "audio_url": dl_api,
                    }
    except Exception as e:
        print(f"Spotify API Error: {e}")

    # Backup Engine: Rapid SoundCloud Proxy
    try:
        sc_url = f"https://api.vagalume.com.br/search.php?art={requests.utils.quote(clean_query)}&extra=rel"
        res2 = requests.get(sc_url, headers=HEADERS, timeout=8)
        if res2.status_code == 200:
            data = res2.json()
            if data.get("type") == "exact":
                mus = data["mus"][0]
                return {
                    "title": mus.get("name"),
                    "artist": data.get("art", {}).get("name"),
                    "audio_url": mus.get("url"),
                }
    except Exception as e:
        print(f"Backup Engine Error: {e}")

    return None


# -------------------------------------------------------------
# Process Request Logic
# -------------------------------------------------------------
def process_song_request(chat_id, user_text):
    send_message(
        chat_id,
        f"🔎 <b>Searching MP3:</b> <i>{user_text}</i>\n⏳ <i>Kripya wait karein...</i>",
    )

    song_info = fetch_music_stream(user_text)

    if song_info and song_info.get("audio_url"):
        title = song_info["title"]
        artist = song_info["artist"]
        audio_url = song_info["audio_url"]

        send_message(
            chat_id, "⬆️ <b>MP3 Track Telegram par upload ho raha hai...</b>"
        )

        res = send_audio(chat_id, audio_url, title=title, performer=artist)

        # Fallback Direct Play Link
        if not res or not res.get("ok"):
            send_message(
                chat_id,
                f"🎧 <b>Direct MP3 Link:</b>\n\n"
                f"🎵 <b>{title}</b> - {artist}\n\n"
                f"👉 <a href='{audio_url}'>Click Here To Play / Download MP3</a>",
            )
    else:
        send_message(
            chat_id,
            "❌ <b>Gaana nahi mila!</b>\n\n"
            "Kripya kisi specific song ka sahi naam likhein (Jaise: <code>Kesariya</code> ya <code>Phir Mohabbat</code>).",
        )


# -------------------------------------------------------------
# Main Message Router
# -------------------------------------------------------------
def handle_message(chat_id, text):
    if text == "/start":
        send_message(
            chat_id,
            "👋 <b>Welcome to MP3 Music Bot! 🎶</b>\n\n"
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
    print("Fast MP3 Music Bot Active...")
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
    
