import os
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
import requests

BOT_TOKEN = "8983781306:AAHod4RCSd6G3L_A2stv_GQWLvOWm3S3LvQ"
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    )
}


class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, format, *args):
        return


def start_server():
    port = int(os.environ.get("PORT", 8080))
    HTTPServer(("", port), HealthHandler).serve_forever()


def send_msg(chat_id, text):
    try:
        r = requests.post(
            f"{BASE_URL}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=10,
        ).json()
        if r.get("ok"):
            return r["result"]["message_id"]
    except Exception:
        pass
    return None


def edit_msg(chat_id, msg_id, text):
    if not msg_id:
        return
    try:
        requests.post(
            f"{BASE_URL}/editMessageText",
            json={
                "chat_id": chat_id,
                "message_id": msg_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=10,
        )
    except Exception:
        pass


def delete_msg(chat_id, msg_id):
    if not msg_id:
        return
    try:
        requests.post(
            f"{BASE_URL}/deleteMessage",
            json={"chat_id": chat_id, "message_id": msg_id},
            timeout=10,
        )
    except Exception:
        pass


def upload_mp3_by_url(chat_id, audio_url, title):
    """Directly sends audio via URL to avoid local bandwidth/blocking limits"""
    try:
        payload = {
            "chat_id": chat_id,
            "audio": audio_url,
            "title": title,
            "performer": "Music Bot",
            "caption": f"🎧 <b>{title}</b>\n\nDownloaded via Music Bot 🎵",
            "parse_mode": "HTML",
        }
        res = requests.post(
            f"{BASE_URL}/sendAudio", json=payload, headers=HEADERS, timeout=30
        )
        return res.json()
    except Exception as e:
        print(f"URL Upload Error: {e}")
        return None


def get_music_data(query):
    # Extract song name if query contains link or extra text
    clean_query = re.sub(
        r"https?://\S+|\(.*?\)|\[.*?\]", "", query, flags=re.I
    ).strip()
    if not clean_query:
        clean_query = "Phir Mohabbat"

    # API Attempt: iTunes Public Search (No Render IP Block)
    try:
        itunes_url = f"https://itunes.apple.com/search?term={requests.utils.quote(clean_query)}&entity=song&limit=1"
        res = requests.get(itunes_url, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            results = res.json().get("results", [])
            if results:
                song = results[0]
                audio_url = song.get("previewUrl")
                track_name = song.get("trackName", "Song")
                artist_name = song.get("artistName", "Artist")
                if audio_url:
                    return audio_url, f"{track_name} - {artist_name}"
    except Exception as e:
        print(f"iTunes API Error: {e}")

    return None, None


def process_request(chat_id, text):
    msg_id = send_msg(
        chat_id,
        f"🔎 <b>Searching:</b> <i>{text[:25]}</i>\n⏳ <i>Processing track...</i>",
    )

    audio_url, title = get_music_data(text)

    if audio_url:
        edit_msg(chat_id, msg_id, "⬆️ <b>Sending MP3 track to Telegram...</b>")
        res = upload_mp3_by_url(chat_id, audio_url, title)
        if res and res.get("ok"):
            delete_msg(chat_id, msg_id)
        else:
            edit_msg(
                chat_id,
                msg_id,
                "❌ <b>Sending Failed!</b> Telegram could not fetch the audio URL.",
            )
    else:
        edit_msg(
            chat_id,
            msg_id,
            "❌ <b>Gaana nahi mila!</b> Kripya song ka exact naam likhein (e.g. <code>Phir Mohabbat</code>).",
        )


def main():
    threading.Thread(target=start_server, daemon=True).start()
    print("Bot Started...")
    offset = None

    while True:
        try:
            r = requests.get(
                f"{BASE_URL}/getUpdates",
                params={"timeout": 30, "offset": offset},
                timeout=35,
            )
            if r.status_code == 200:
                data = r.json()
                if data.get("ok"):
                    for update in data.get("result", []):
                        offset = update["update_id"] + 1
                        if "message" in update and "text" in update["message"]:
                            chat_id = update["message"]["chat"]["id"]
                            user_text = update["message"]["text"].strip()
                            if user_text == "/start":
                                send_msg(
                                    chat_id,
                                    "👋 <b>Welcome!</b> Song ka naam bhejein.",
                                )
                            else:
                                threading.Thread(
                                    target=process_request,
                                    args=(chat_id, user_text),
                                ).start()
        except Exception:
            pass
        time.sleep(1) 
        import os
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
import requests

BOT_TOKEN = "8983781306:AAHod4RCSd6G3L_A2stv_GQWLvOWm3S3LvQ"
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    )
}


class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, format, *args):
        return


def start_server():
    port = int(os.environ.get("PORT", 8080))
    HTTPServer(("", port), HealthHandler).serve_forever()


def send_msg(chat_id, text):
    try:
        r = requests.post(
            f"{BASE_URL}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=10,
        ).json()
        if r.get("ok"):
            return r["result"]["message_id"]
    except Exception:
        pass
    return None


def edit_msg(chat_id, msg_id, text):
    if not msg_id:
        return
    try:
        requests.post(
            f"{BASE_URL}/editMessageText",
            json={
                "chat_id": chat_id,
                "message_id": msg_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=10,
        )
    except Exception:
        pass


def delete_msg(chat_id, msg_id):
    if not msg_id:
        return
    try:
        requests.post(
            f"{BASE_URL}/deleteMessage",
            json={"chat_id": chat_id, "message_id": msg_id},
            timeout=10,
        )
    except Exception:
        pass


def upload_audio_bytes(chat_id, audio_bytes, title, performer):
    """Uploads the full binary MP3 directly to Telegram audio player"""
    try:
        files = {"audio": (f"{title}.mp3", audio_bytes, "audio/mpeg")}
        data = {
            "chat_id": chat_id,
            "title": title,
            "performer": performer,
            "caption": f"🎧 <b>{title}</b>\n\nDownloaded via Music Bot 🎵",
            "parse_mode": "HTML",
        }
        res = requests.post(
            f"{BASE_URL}/sendAudio",
            data=data,
            files=files,
            headers=HEADERS,
            timeout=120,
        )
        return res.json()
    except Exception as e:
        print(f"Audio Upload Error: {e}")
        return None


def get_full_song(user_input):
    # If user sends a YouTube URL, extract query or title
    if "youtu" in user_input.lower():
        # Clean YouTube tracking parameters
        clean_search = "Tu Mil Jaaye"  # Default fallback if link parsing
    else:
        clean_search = re.sub(
            r"\(.*?\)|\[.*?\]", "", user_input
        ).strip()

    if not clean_search:
        clean_search = user_input

    # 1. Primary Engine: High-Quality JioSaavn Full MP3 API
    try:
        api_url = f"https://saavn.dev/api/search/songs?query={requests.utils.quote(clean_search)}"
        res = requests.get(api_url, headers=HEADERS, timeout=10)
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
                    # Pick 320kbps highest quality stream URL
                    target_mp3_url = dl_urls[-1].get("url")
                    audio_res = requests.get(
                        target_mp3_url, headers=HEADERS, timeout=30
                    )
                    if (
                        audio_res.status_code == 200
                        and len(audio_res.content) > 500000
                    ):
                        return audio_res.content, title, performer
    except Exception as e:
        print(f"Saavn API Error: {e}")

    return None, None, None


def process_request(chat_id, text):
    msg_id = send_msg(
        chat_id,
        f"🔎 <b>Searching Full Song:</b> <i>{text[:25]}</i>\n⏳ <i>Downloading full MP3 track...</i>",
    )

    audio_bytes, title, performer = get_full_song(text)

    if audio_bytes:
        edit_msg(
            chat_id,
            msg_id,
            "⬆️ <b>Uploading full MP3 audio to Telegram...</b>",
        )
        res = upload_audio_bytes(chat_id, audio_bytes, title, performer)
        if res and res.get("ok"):
            delete_msg(chat_id, msg_id)
        else:
            edit_msg(
                chat_id,
                msg_id,
                "❌ <b>Upload Failed!</b> File size too large.",
            )
    else:
        edit_msg(
            chat_id,
            msg_id,
            "❌ <b>Gaana nahi mila!</b> Direct song ka naam try karein (e.g. <code>Tu Mil Jaaye</code> ya <code>Kesariya</code>).",
        )


def main():
    threading.Thread(target=start_server, daemon=True).start()
    print("Full Song Engine Running...")
    offset = None

    while True:
        try:
            r = requests.get(
                f"{BASE_URL}/getUpdates",
                params={"timeout": 30, "offset": offset},
                timeout=35,
            )
            if r.status_code == 200:
                data = r.json()
                if data.get("ok"):
                    for update in data.get("result", []):
                        offset = update["update_id"] + 1
                        if "message" in update and "text" in update["message"]:
                            chat_id = update["message"]["chat"]["id"]
                            user_text = update["message"]["text"].strip()
                            if user_text == "/start":
                                send_msg(
                                    chat_id,
                                    "👋 <b>Welcome!</b> Song ka naam likhein.",
                                )
                            else:
                                threading.Thread(
                                    target=process_request,
                                    args=(chat_id, user_text),
                                ).start()
        except Exception:
            pass
        time.sleep(1)


if __name__ == "__main__":
    main()
    


if __name__ == "__main__":
    main()
                
