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
# Dummy Web Server (Render App Active Rakhne Ke Liye)
# -------------------------------------------------------------
class DummyServerHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"MP3 Music Bot Active & Running!")

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
        "caption": f"🎧 <b>{title}</b>\n\n🎵 Downloaded via Music Bot",
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
# Multi-Engine JioSaavn Music Fetcher
# -------------------------------------------------------------
def fetch_song_from_saavn(song_name):
    encoded_query = requests.utils.quote(song_name)

    # Engine 1: Saavn.dev API
    try:
        url1 = (
            f"https://saavn.dev/api/search/songs?query={encoded_query}&limit=1"
        )
        r1 = requests.get(url1, headers=HEADERS, timeout=10)
        if r1.status_code == 200:
            d1 = r1.json()
            if d1.get("success") and d1.get("data", {}).get("results"):
                song = d1["data"]["results"][0]
                dl_urls = song.get("downloadUrl", [])
                if dl_urls:
                    return {
                        "title": song.get("name", song_name),
                        "artist": song.get("artists", {})
                        .get("primary", [{}])[0]
                        .get("name", "Artist"),
                        "audio_url": dl_urls[-1].get("url"),
                    }
    except Exception as e:
        print(f"Engine 1 Error: {e}")

    # Engine 2: Saavn.me Backup API
    try:
        url2 = (
            f"https://saavn.me/search/songs?query={encoded_query}&page=1&limit=1"
        )
        r2 = requests.get(url2, headers=HEADERS, timeout=10)
        if r2.status_code == 200:
            d2 = r2.json()
            if d2.get("status") == "SUCCESS" and d2.get("data", {}).get(
                "results"
            ):
                song = d2["data"]["results"][0]
                dl_urls = song.get("downloadUrl", [])
                if dl_urls:
                    return {
                        "title": song.get("name", song_name),
                        "artist": song.get("primaryArtists", "Artist"),
                        "audio_url": dl_urls[-1].get("link")
                        or dl_urls[-1].get("url"),
                    }
    except Exception as e:
        print(f"Engine 2 Error: {e}")

    return None


# -------------------------------------------------------------
# Process Song Search
# -------------------------------------------------------------
def process_song_search(chat_id, query_text):
    # Agar user ne URL bhej diya, toh URL me se song name guess karein
    if "http://" in query_text or "https://" in query_text:
        query_text = (
            query_text.replace("https://youtu.be/", "")
            .replace("https://www.youtube.com/watch?v=", "")
            .split("?")[0]
        )
        if not query_text or len(query_text) < 3:
            send_message(
                chat_id,
                "⚠️ <b>Kripya Link ki jagah Gaane ka Naam likhein!</b>\n\n<i>Example: Agar Tum Saath Ho</i>",
            )
            return

    send_message(
        chat_id,
        f"🔎 <b>Searching MP3 Song:</b> <i>{query_text}</i>\n⏳ <i>Wait karein...</i>",
    )

    song_data = fetch_song_from_saavn(query_text)

    if song_data and song_data.get("audio_url"):
        title = song_data["title"]
        artist = song_data["artist"]
        audio_url = song_data["audio_url"]

        send_message(chat_id, "⬆️ <b>MP3 Song Telegram par upload ho raha hai...</b>")

        result = send_audio(chat_id, audio_url, title=title, performer=artist)

        if not result or not result.get("ok"):
            send_message(
                chat_id,
                f"🎧 <b>Song Download Link Ready:</b>\n\n"
                f"🎵 <b>{title}</b> - {artist}\n\n"
                f"👉 <a href='{audio_url}'>Click Here To Play / Download MP3</a>",
            )
    else:
        send_message(
            chat_id,
            "❌ <b>Gaana nahi mila!</b>\n\n"
            "💡 <i>Tip: Sahi spelling ke sath gaane ka naam likhein (Jaise: <b>Kesariya</b> ya <b>Tere Sang Yaara</b>).</i>",
        )


# -------------------------------------------------------------
# Main Message Handler
# -------------------------------------------------------------
def handle_message(chat_id, text):
    if text == "/start":
        send_message(
            chat_id,
            "👋 <b>Welcome to High Quality MP3 Music Bot! 🎶</b>\n\n"
            "Bas kisi bhi gaane ka **Naam** (Name) likh kar bhejein!\n\n"
            "<i>Example: Agar Tum Saath Ho</i>",
        )
        return

    threading.Thread(
        target=process_song_search, args=(chat_id, text)
    ).start()


# -------------------------------------------------------------
# Main Loop
# -------------------------------------------------------------
def main():
    threading.Thread(target=run_dummy_server, daemon=True).start()
    print("Multi-Engine Music Bot Active...")
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
    
