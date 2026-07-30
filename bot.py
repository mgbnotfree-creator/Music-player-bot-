def download_media(chat_id, link_or_query):
    send_message(chat_id, "⏳ <b>Downloading Audio/Video (Fast Mode)...</b>")

    # YouTube videos ko small size (360p) me download karega taaki 50MB limit cross na ho
    ydl_opts = {
        "format": "best[filesize<45M]/bestvideo[height<=360]+bestaudio/best[height<=360]/best",
        "outtmpl": "downloaded_media.%(ext)s",
        "quiet": True,
        "no_warnings": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(link_or_query, download=True)
            title = info.get("title", "Downloaded Media")

            filename = None
            for f in os.listdir("."):
                if f.startswith("downloaded_media."):
                    filename = f
                    break

            if filename and os.path.exists(filename):
                send_message(
                    chat_id, "⬆️ <b>Telegram par upload ho raha hai...</b>"
                )

                # Send file as Video or Document based on format
                if filename.endswith(".mp4") or filename.endswith(".mkv"):
                    send_video_file(chat_id, filename, title)
                else:
                    send_audio_file(chat_id, filename, title)

                os.remove(filename)  # Delete temp file
            else:
                send_message(
                    chat_id,
                    "❌ File process nahi ho saki. Dusra link try karein.",
                )

    except Exception as e:
        print(f"Download Error: {e}")
        send_message(
            chat_id,
            "❌ <b>Error:</b> Video 50MB se badi hai ya YouTube block kar raha hai.",
                    )
            
