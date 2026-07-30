import os
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


# -------------------------------------------------------------
# Dummy Web Server (Render App ko Active rakhne ke liye)
# -------------------------------------------------------------
class DummyServerHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"MP3 Music Bot is Running Live!")

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
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Message Error: {e}")


def send_audio(chat_id, file_path, title):
    url = f"{BASE_URL}/sendAudio"
    try:
        with open(file_path, "rb") as audio:
            files = {"audio": audio}
            data = {
                "chat_id": chat_id,
                "title": title,
                "caption": f"🎧 <b>{title}</b>\n\n🎵 Downloaded via Music Bot",
                "parse_mode": "HTML",
            }
            requests.post(url, data=data, files=files)
    except Exception as e:
        print(f"Audio Send Error: {e}")


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
# MP3 / Audio Downloader Logic
# -------------------------------------------------------------
def download_and_send_song(chat_id, query):
    send_message(chat_id, f"🔎 <b>Searching & Downloading:</b> {query}\n⏳ <i>Kripya wait karein...</i>")

    # Agar link nahi hai, toh YouTube par gaane ka naam search karega
    if not (query.startswith("http://") or query.startswith("https://")):
        search_target = f"ytsearch1:{query}"
    else:
        search_target = query

    # Sirf Audio (M4A/MP3) download karega, Video nahi. 
    # M4A format Telegram par direct as a Music Play hota hai.
    ydl_opts = {
        'format': 'm4a/bestaudio/best',
        'outtmpl': 'downloaded_song.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(search_target, download=True)
            
            if 'entries' in info:
                info = info['entries'][0]

            title = info.get('title', 'Unknown Song')

            # Find the downloaded file
            filename = None
            for f in os.listdir("."):
                if f.startswith("downloaded_song."):
                    filename = f
                    break

            if filename and os.path.exists(filename):
                send_message(chat_id, "⬆️ <b>Telegram par Song upload ho raha hai...</b>")
                send_audio(chat_id, filename, title)
                os.remove(filename)  # Delete file after sending
            else:
                send_message(chat_id, "❌ Song file process nahi ho saki.")

    except Exception as e:
        print(f"Download Error: {e}")
        send_message(chat_id, "❌ <b>Error:</b> Gaana download nahi ho paya. Koi dusra naam try karein.")


# -------------------------------------------------------------
# Main Message Handler
# -------------------------------------------------------------
def handle_message(chat_id, text):
    if text == "/start":
        send_message(
            chat_id,
            "👋 <b>Welcome to MP3 Music Bot! 🎶</b>\n\n"
            "Aap kisi bhi gaane ka <b>Naam</b> likh kar bhej sakte hain ya YouTube Link paste kar sakte hain.\n\n"
            "<i>Example: Tere Sang Yaara</i>",
        )
        return

    # Background me run karega taaki bot hang na ho
    threading.Thread(target=download_and_send_song, args=(chat_id, text)).start()


# -------------------------------------------------------------
# Main Loop
# -------------------------------------------------------------
def main():
    threading.Thread(target=run_dummy_server, daemon=True).start()
    print("MP3 Bot is Running...")
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
    
