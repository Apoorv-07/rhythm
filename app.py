from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
import uuid
from pathlib import Path
from poem_generator import generate_poem
from music_generator import generate_music
from video_generator import generate_video

# Flask app setup
app = Flask(__name__)
CORS(app)

# Storage paths
OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)

@app.route("/generate", methods=["POST"])
def generate():
    """Generate poem/song + music + video from a short prompt."""
    data = request.get_json()
    prompt = data.get("prompt")
    if not prompt:
        return jsonify({"error": "No prompt provided"}), 400

    # Unique ID for this generation
    gen_id = str(uuid.uuid4())

    try:
        # Generate poem
        poem_text = generate_poem(prompt)
        poem_file = OUTPUT_DIR / f"{gen_id}_poem.txt"
        with open(poem_file, "w", encoding="utf-8") as f:
            f.write(poem_text)

        # Generate music
        music_file = OUTPUT_DIR / f"{gen_id}_music.wav"
        generate_music(prompt, str(music_file))

        # Generate video
        video_file = OUTPUT_DIR / f"{gen_id}_video.mp4"
        generate_video(prompt, str(music_file), str(video_file))

        return jsonify({
            "poem": str(poem_file),
            "music": str(music_file),
            "video": str(video_file)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/download/<file_id>", methods=["GET"])
def download(file_id):
    """Download generated files by ID."""
    matching_files = list(OUTPUT_DIR.glob(f"{file_id}*"))
    if not matching_files:
        return jsonify({"error": "File not found"}), 404
    return send_file(matching_files[0], as_attachment=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)