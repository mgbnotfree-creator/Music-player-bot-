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
        " like Gecko) Chrome/122.0.0.0 Safari/537.36"
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
        self.wfile.write(b"Music Player Bot Online!")

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
# Clean User Input & Extract YouTube Title
# -------------------------------------------------------------
def extract_clean_query(text):
    text = text.strip()

    # Case 1: If YouTube URL is passed, get title from oEmbed API
    if "youtu.be/" in text or "youtube.com/" in text:
        try:
            oembed_url = f"https://www.youtube.com/oembed?url={text}&format=json"
            res = requests.get(oembed_url, headers=HEADERS, timeout=5)
            if res.status_code == 200:
                yt_title = res.json().get("title", "")
                if yt_title:
                    text = yt_title
        except Exception:
            pass

    # Clean YouTube metadata tags like "| Official Video", "HD", Movie Name extra noise
    text = re.sub(
        r"https?://\S+", "", text
    )  # Remove URL if remaining fallback
    text = re.sub(
        r"\(.*?\)|\[.*?\]", "", text
    )  # Remove (Official Video) [HD] etc.
    text = re.sub(
        r"(?i)official|video|song|full|hd|lyrical|movie|4k|version", "", text
    )
    text = text.replace("|", " ").replace("-", " ").strip()

    # If user wrote 'Phir Mohabbat Murder 2', strip long words down to main query if needed
    words = text.split()
    if len(words) > 4:
        text = " ".join(words[:4])

    return text if text else "Phir Mohabbat"


# -------------------------------------------------------------
# JioSaavn API Audio Engine (Primary & Fallback)
# -------------------------------------------------------------
def fetch_direct_mp3_saavn(song_query):
    encoded_query = requests.utils.quote(song_query)

    # Engine 1: Saavn.dev API
    try:
        url1 = f"https://saavn.dev/api/search/songs?query={encoded_query}"
        res1 = requests.get(url1, headers=HEADERS, timeout=8)
        if res1.status_code == 200:
            data = res1.json()
            results = data.get("data", {}).get("results", [])
            if results:
                song = results[0]
                title = song.get("name", song_query)
                title = (
                    title.replace("&quot;", "")
                    .replace("&#039;", "")
                    .replace("&amp;", "&")
                )

                artists = song.get("artists", {}).get("primary", [])
                artist_name = (
                    artists[0].get("name") if artists else "Music Bot"
                )

                download_urls = song.get("downloadUrl", [])
                if download_urls:
                    audio_url = download_urls[-1].get("url")  # Highest quality
                    return {
                        "title": title,
                        "artist": artist_name,
                        "url": audio_url,
                    }
    except Exception as e:
        print(f"Saavn.dev Error: {e}")

    # Engine 2: Saavn V3 Backup Engine
    try:
        url2 = f"https://jiosaavn-api-v3.vercel.app/search?query={encoded_query}"
        res2 = requests.get(url2, headers=HEADERS, timeout=8)
        if res2.status_code == 200:
            data = res2.json()
            if isinstance(data, list) and len(data) > 0:
                song = data[0]
                audio_url = song.get("media_url") or song.get("url")
                if audio_url:
                    return {
                        "title": song.get("song", song_query),
                        "artist": song.get("singers", "Music Bot"),
                        "url": audio_url,
                    }
    except Exception as e:
        print(f"JioSaavn V3 Error: {e}")

    return None


# -------------------------------------------------------------
# Process Request Loop
# -------------------------------------------------------------
def process_song_request(chat_id, raw_input):
    clean_query = extract_clean_query(raw_input)

    send_message(
        chat_id,
        f"🔎 <b>Searching MP3:</b> <i>{clean_query}</i>\n⏳ <i>Wait karein, download ho raha hai...</i>",
    )

    song_data = fetch_direct_mp3_saavn(clean_query)

    if song_data and song_data.get("url"):
        title = song_data["title"]
        artist = song_data["artist"]
        mp3_url = song_data["url"]

        send_message(
            chat_id, "⬆️ <b>MP3 Track Telegram par upload ho raha hai...</b>"
        )

        res = send_audio(chat_id, mp3_url, title=title, performer=artist)

        # Fallback Direct Link if Telegram Upload times out
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
            "Kripya kisi specific song ka simple naam likhein.\n"
            "<i>Example: Kesariya ya Phir Mohabbat</i>",
        )


# -------------------------------------------------------------
# Main Message Router
# -------------------------------------------------------------
def handle_message(chat_id, text):
    if text == "/start":
        send_message(
            chat_id,
            "👋 <b>Welcome to High Quality MP3 Music Bot! 🎶</b>\n\n"
            "Kisi bhi song ka **Naam** ya **YouTube Link** bhejien!\n\n"
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
    print("Zero-Failure Music Bot Active...")
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
        
