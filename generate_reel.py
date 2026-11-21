import os
import re
import json
import subprocess
import requests
import gdown

APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbzaXBD2kpE3c-lBTSh31XGNWettsR4qW3Fec3InvxslAOeW2bIeoHdDXnvgvxzv34p1fA/exec"
REPO_RAW_BASE = "https://raw.githubusercontent.com/sayyedfarhanali/mandir-reel-automation/main"

def main():
    print("Fetching next pending post from Google Sheet...")
    resp = requests.get(APPS_SCRIPT_URL, timeout=60)
    data = resp.json()

    if data.get("status") != "ok":
        print("No pending post found:", data)
        return

    row = data["row"]
    post_no = re.sub(r"[^a-zA-Z0-9_-]", "_", str(data["postNo"]))
    image_url = data["imageUrl"]
    audio_url = data["audioUrl"]

    print(f"Processing Row {row} (Post: {post_no})")

    # Download image and audio/video clip from Google Drive
    gdown.download(image_url, "input_image.jpg", quiet=False, fuzzy=True)
    gdown.download(audio_url, "input_audio.mp4", quiet=False, fuzzy=True)

    os.makedirs("reels", exist_ok=True)
    output_filename = f"reels/reel_{post_no}_row{row}.mp4"

    # Create 1080x1920 HD Vertical Reel (blurred background + full image so quote never crops)
    filter_complex = (
        "[0:v]split=2[bg][fg];"
        "[bg]scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,boxblur=20:5[bgb];"
        "[fg]scale=1080:1920:force_original_aspect_ratio=decrease[fgb];"
        "[bgb][fgb]overlay=(W-w)/2:(H-h)/2,format=yuv420p[v]"
    )

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", "input_image.jpg",
        "-i", "input_audio.mp4",
        "-filter_complex", filter_complex,
        "-map", "[v]", "-map", "1:a",
        "-c:v", "libx264", "-tune", "stillimage", "-r", "30",
        "-c:a", "aac", "-b:a", "192k", "-ar", "44100",
        "-shortest", "-t", "15",
        "-movflags", "+faststart",
        output_filename
    ]

    subprocess.run(cmd, check=True)
    print(f"Reel generated: {output_filename}")

    # Save metadata so workflow can update Google Sheet right after git push
    video_url = f"{REPO_RAW_BASE}/{output_filename}"
    with open("reel_meta.json", "w") as f:
        json.dump({"row": row, "videoUrl": video_url}, f)

if __name__ == "__main__":
    main()
