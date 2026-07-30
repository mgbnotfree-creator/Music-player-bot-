import asyncio
import os
import re
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import yt_dlp

BOT_TOKEN = "8983781306:AAHod4RCSd6G3L_A2stv_GQWLvOWm3S3LvQ"

# -------------------------------------------------------------
# Keep-Alive Web Server for Render
# -------------------------------------------------------------
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"Bot Server Running!")

    def log_message(self, format, *args):
        return

def run_health_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("", port), HealthCheckHandler)
    server.serve_forever()

# -------------------------------------------------------------
# Core Download Handler (yt-dlp Modern Engine)
# -------------------------------------------------------------
def download_audio_yt_dlp(search_query):
    # Check if input is a direct link or query
    if not (search_query.startswith("http://") or search_query.startswith("https://")):
        # Clean user query for ytsearch
        clean_query = re.sub(r'\(.*?\)|\[.*?\]', '', search_query).strip()
        search_target = f"ytsearch1:{clean_query} song"
    else:
        search_target = search_query

    output_filename = "downloaded_song.mp3"
    if os.path.exists(output_filename):
        try:
            os.remove(output_filename)
        except Exception:
            pass

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': 'downloaded_song.%(ext)s',
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }

    # Alternative fallback options if ffmpeg isn't installed on Render environment
    ydl_opts_fallback = {
        'format': 'bestaudio[ext=m4a]/bestaudio/best',
        'outtmpl': 'downloaded_song.%(ext)s',
        'noplaylist': True,
        'quiet': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(search_target, download=True)
            if 'entries' in info and info['entries']:
                info = info['entries'][0]
            
            title = info.get('title', 'Unknown Song')
            performer = info.get('uploader', 'Music Bot')
            
            # Find the generated file
            for file in os.listdir('.'):
                if file.startswith('downloaded_song'):
                    return file, title, performer
    except Exception as e:
        print(f"Standard YTDLP failed, trying fallback: {e}")
        try:
            with yt_dlp.YoutubeDL(ydl_opts_fallback) as ydl:
                info = ydl.extract_info(search_target, download=True)
                if 'entries' in info and info['entries']:
                    info = info['entries'][0]
                
                title = info.get('title', 'Unknown Song')
                performer = info.get('uploader', 'Music Bot')

                for file in os.listdir('.'):
                    if file.startswith('downloaded_song'):
                        return file, title, performer
        except Exception as ex:
            print(f"Fallback YTDLP failed too: {ex}")

    return None, None, None

# -------------------------------------------------------------
# Telegram Bot Commands & Message Handlers
# -------------------------------------------------------------
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_html(
        "👋 <b>Welcome to High Quality MP3 Downloader! 🎵</b>\n\n"
        "Bhai bas kisi bhi song ka **Naam** ya **YouTube Link** bhejo!\n\n"
        "<i>Example: Phir Mohabbat</i>"
    )

async def handle_song_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text.strip()
    status_msg = await update.message.reply_html(
        f"🔎 <b>Searching & Downloading MP3:</b> <i>{user_text[:30]}</i>\n⏳ <i>Bas 5-10 sec wait karein...</i>"
    )

    loop = asyncio.get_running_loop()
    
    # Run heavy download in thread to prevent blocking bot updates
    file_path, title, performer = await loop.run_in_executor(
        None, download_audio_yt_dlp, user_text
    )

    if file_path and os.path.exists(file_path):
        await status_msg.edit_text("⬆️ <b>Uploading audio file to Telegram...</b>")
        try:
            with open(file_path, 'rb') as audio_file:
                await update.message.reply_audio(
                    audio=audio_file,
                    title=title,
                    performer=performer,
                    caption=f"🎧 <b>{title}</b>\n\nDownloaded via Music Bot 🎵",
                    parse_mode="HTML"
                )
            await status_msg.delete()
        except Exception as e:
            await status_msg.edit_text(f"❌ <b>Upload error:</b> {e}")
        finally:
            if os.path.exists(file_path):
                os.remove(file_path)
    else:
        await status_msg.edit_text(
            "❌ <b>Gaana nahi mila!</b>\n\n"
            "Kripya kisi specific song ka sahi naam ya YouTube link bhejein."
        )

# -------------------------------------------------------------
# Main Execution
# -------------------------------------------------------------
def main():
    # Start web server thread
    threading.Thread(target=run_health_server, daemon=True).start()

    # Initialize Telegram Application
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_song_request))

    print("Modern Bot Engine Started...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
    
