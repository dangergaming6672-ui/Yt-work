import os
import subprocess
import tempfile
from pathlib import Path

import streamlit as st
import yt_dlp

st.set_page_config(page_title="ClipForge AI", page_icon="🎬", layout="centered")

st.title("🎬 ClipForge AI")
st.caption("Long video → Shorts | MVP · Review before download")

st.info(
    "Paste a video URL you own or have permission to edit. Automatic mode suggests evenly spaced 30–60 second sections; it does not yet use semantic AI to understand the story."
)

def ffmpeg_available():
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"], capture_output=True, text=True, timeout=10
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False

def probe_duration(path):
    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(path)
        ],
        capture_output=True, text=True, check=True, timeout=30
    )
    return float(result.stdout.strip())

def make_clip(source, output, start, duration, vertical):
    cmd = ["ffmpeg", "-y", "-ss", str(start), "-i", str(source),
           "-t", str(duration), "-map", "0:v:0", "-map", "0:a?"]
    if vertical:
        # Scale to fill 1080x1920 and crop the centre. MVP crop is centre-based.
        cmd += ["-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"]
    cmd += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(output)]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    if result.returncode != 0:
        raise RuntimeError(result.stderr[-1800:])

if not ffmpeg_available():
    st.error("FFmpeg is not installed. See README.md for setup instructions.")
    st.stop()

video_url = st.text_input(
    "Paste YouTube video URL",
    placeholder="https://www.youtube.com/watch?v=...",
    help="Use a public video you own or have permission to edit. Some videos may not be downloadable due to platform restrictions."
)

if st.button("Fetch video from URL", type="primary"):
    if not video_url.strip().startswith(("https://www.youtube.com/", "https://youtu.be/")):
        st.error("Please enter a valid YouTube video URL (youtube.com or youtu.be).")
        st.stop()
    workdir = Path(tempfile.mkdtemp(prefix="clipforge_"))
    output_template = str(workdir / "source.%(ext)s")
    options = {
        "format": "bestvideo*+bestaudio/best",
        "outtmpl": output_template,
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "max_filesize": 800 * 1024 * 1024,
    }
    try:
        with st.spinner("Fetching video… this may take a few minutes."):
            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(video_url.strip(), download=True)
            candidates = [p for p in workdir.iterdir() if p.is_file() and p.name.startswith("source.")]
            if not candidates:
                raise RuntimeError("Downloaded video file was not found.")
            source_path = candidates[0]
            st.session_state["clipforge_source_path"] = str(source_path)
            st.session_state["clipforge_workdir"] = str(workdir)
            st.session_state["clipforge_video_title"] = info.get("title", "Video")
            st.session_state.pop("auto_starts", None)
            st.session_state.pop("manual_segments", None)
            st.session_state.pop("rendered_clips", None)
    except Exception as exc:
        st.error(f"Could not fetch this video: {exc}")
        st.stop()

source_value = st.session_state.get("clipforge_source_path")
if not source_value or not Path(source_value).exists():
    st.markdown("### How it works")
    st.markdown("1. Paste a YouTube URL for a video you own or have permission to edit.\n2. Fetch the video.\n3. Generate clip suggestions, review them, and download approved clips.")
    st.stop()

source_path = Path(source_value)
workdir = Path(st.session_state.get("clipforge_workdir", source_path.parent))
try:
    duration = probe_duration(source_path)
except Exception as exc:
    st.error(f"Could not read this video: {exc}")
    st.stop()

st.success(f"Video loaded: {st.session_state.get('clipforge_video_title', 'Video')} · {duration/60:.1f} minutes")
st.video(str(source_path))

st.subheader("1. Choose clip settings")
clip_length = st.slider("Target clip length (seconds)", min_value=30, max_value=60, value=45, step=5)
vertical = st.checkbox("Convert to vertical 9:16 for Shorts/Reels", value=True)

mode = st.radio("Clip selection mode", ["Automatic suggestions", "Manual timestamps", "Both"], horizontal=False)

suggestions = []
if mode in ["Automatic suggestions", "Both"]:
    st.caption("Automatic suggestions are evenly spaced sections for this MVP, not AI-ranked highlights.")
    if st.button("Generate automatic clip suggestions", type="primary"):
        if duration < 10:
            st.warning("Video is too short to create useful clips.")
        else:
            starts = []
            # Spread clips across the full video, avoid creating a final clip shorter than 15 sec.
            step = max(clip_length, int(duration / min(10, max(1, int(duration // clip_length)))))
            cursor = 0.0
            while cursor + min(clip_length, duration - cursor) <= duration + 0.01 and len(starts) < 10:
                if duration - cursor < 15:
                    break
                starts.append(cursor)
                cursor += step
            st.session_state["auto_starts"] = starts
            st.success(f"Created {len(starts)} suggested segments. Review them below.")

if mode in ["Manual timestamps", "Both"]:
    st.subheader("Add a manual clip")
    c1, c2 = st.columns(2)
    with c1:
        manual_start = st.number_input("Start time (seconds)", min_value=0.0, max_value=max(0.0, duration-1), value=0.0, step=1.0)
    with c2:
        manual_end = st.number_input("End time (seconds)", min_value=1.0, max_value=max(1.0, duration), value=float(min(clip_length, duration)), step=1.0)
    if st.button("Add manual clip"):
        if manual_end <= manual_start:
            st.error("End time must be after start time.")
        elif manual_end - manual_start < 5:
            st.error("Please choose a segment at least 5 seconds long.")
        else:
            st.session_state.setdefault("manual_segments", [])
            st.session_state["manual_segments"].append((float(manual_start), float(manual_end)))
            st.success("Manual segment added.")

segments = []
if mode in ["Automatic suggestions", "Both"]:
    for i, start in enumerate(st.session_state.get("auto_starts", []), start=1):
        segments.append({"label": f"Auto suggestion {i}", "start": start, "end": min(duration, start + clip_length)})
if mode in ["Manual timestamps", "Both"]:
    for i, (start, end) in enumerate(st.session_state.get("manual_segments", []), start=1):
        segments.append({"label": f"Manual clip {i}", "start": start, "end": min(duration, end)})

st.subheader("2. Review and approve")
if not segments:
    st.write("No clips yet. Generate automatic suggestions or add a manual timestamp.")
    st.stop()

approved = []
for idx, seg in enumerate(segments):
    with st.expander(f"{seg['label']} · {seg['start']:.1f}s–{seg['end']:.1f}s", expanded=(idx == 0)):
        st.write(f"Duration: {seg['end'] - seg['start']:.1f} seconds")
        if st.checkbox(f"Approve {seg['label']} for export", key=f"approve_{mode}_{idx}_{seg['start']}"):
            approved.append((idx, seg))

if st.button("Create approved clips", type="primary", disabled=(len(approved) == 0)):
    export_dir = workdir / "exports"
    export_dir.mkdir(exist_ok=True)
    progress = st.progress(0)
    status = st.empty()
    outputs = []
    for n, (idx, seg) in enumerate(approved, start=1):
        out = export_dir / f"clipforge_clip_{n:02d}.mp4"
        status.write(f"Rendering clip {n} of {len(approved)}…")
        try:
            make_clip(source_path, out, seg["start"], seg["end"] - seg["start"], vertical)
            outputs.append((seg, out))
        except Exception as exc:
            st.error(f"Failed to render {seg['label']}: {exc}")
        progress.progress(n / len(approved))
    status.write("Rendering finished.")
    st.session_state["rendered_clips"] = [(s["label"], s["start"], s["end"], str(p)) for s, p in outputs]

rendered = st.session_state.get("rendered_clips", [])
if rendered:
    st.subheader("3. Preview and download")
    for label, start, end, path in rendered:
        p = Path(path)
        if p.exists():
            st.markdown(f"**{label}** · {end-start:.1f} seconds")
            st.video(str(p))
            st.download_button(
                label=f"Download {label}",
                data=p.read_bytes(),
                file_name=p.name,
                mime="video/mp4",
                key=f"download_{p.name}"
            )

st.divider()
st.caption("Use only videos you own or have permission to edit. URL fetching may fail for age-restricted, private, or platform-blocked videos. Processing happens on the app host; do not use private or sensitive footage.")
