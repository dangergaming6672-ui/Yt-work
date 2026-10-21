# ClipForge AI — starter MVP

A beginner-friendly Streamlit website prototype for clipping **your own videos**. It supports:
- Video upload
- Automatic evenly-spaced clip suggestions
- Manual start/end timestamps
- 30–60 second target length
- Optional 9:16 centre crop
- Review/approval before rendering
- Preview and download of approved clips

## Important MVP limitation

Automatic mode does **not** yet understand the video's meaning or rank viral moments. It creates evenly spaced suggestions. A later version can add speech transcription, highlight scoring, face-aware cropping, subtitles, and YouTube OAuth uploads.

## Run locally

This is easiest on a laptop/desktop. Android can access the website in a browser after you deploy it, but running the video processing server directly on an Android phone is not the recommended beginner setup.

1. Install Python 3.10+.
2. Install FFmpeg (both `ffmpeg` and `ffprobe` must be on PATH).
   - Windows: install an FFmpeg build and add its `bin` folder to PATH.
   - macOS: `brew install ffmpeg`
   - Debian/Ubuntu: `sudo apt install ffmpeg`
3. Unzip this project and open a terminal in the project folder.
4. Create a virtual environment (optional but recommended):
   ```bash
   python -m venv .venv
   ```
5. Activate it:
   - Windows: `.venv\\Scripts\\activate`
   - macOS/Linux: `source .venv/bin/activate`
6. Install Python requirements:
   ```bash
   pip install -r requirements.txt
   ```
7. Start the website:
   ```bash
   streamlit run app.py
   ```
8. Open the local address shown by Streamlit.

## Deploy for Android browser access

You can deploy the app to a hosting service that supports Streamlit and FFmpeg. `packages.txt` requests FFmpeg on compatible Streamlit Community Cloud builds. Hosting limits, memory, processing time, and file-size restrictions may apply. Test with a short sample video first.

## Safety and publishing

- Upload only videos you own or have permission to edit.
- This MVP never uploads to YouTube; it only renders and downloads approved clips.
- YouTube upload can be added later using the official YouTube Data API and Google OAuth, with private uploads and a final approval step.
- Do not put API keys or OAuth secrets directly into source code.
