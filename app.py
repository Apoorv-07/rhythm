

import os
import uuid
import json
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from generators.poem_generator import PoemGenerator
from generators.music_generator import MusicGenerator
from generators.animation_generator import AnimationGenerator
from models.database import init_db, save_content


# Config
BASE_DIR = Path(__file__).parent
OUT_DIR = BASE_DIR / "generated_files"
OUT_DIR.mkdir(exist_ok=True)


app = Flask(__name__)
CORS(app)


# Initialize DB
init_db()


# Instantiate generators (they are lightweight wrappers; replace internals with ML models later)
poem_gen = PoemGenerator()
music_gen = MusicGenerator(output_dir=OUT_DIR)
anim_gen = AnimationGenerator(output_dir=OUT_DIR)




@app.route('/generate', methods=['POST'])
def generate_all():
"""Generate poem/song + music + video from a short prompt.
Input JSON: {"prompt": "a night of rhythmandcolors", "mode": "both"}
Returns structured JSON:
{
"id": "...",
"prompt": "...",
"poem": {"text": "..."},
"music": {"file": "/files/xxx.mp3", "bpm": 120, "duration": 3.0},
"video": {"file": "/files/xxx.mp4", "duration": 3.0}
}
"""
data = request.get_json() or {}
prompt = (data.get('prompt') or '').strip()
if not prompt:
return jsonify({"error": "prompt is required"}), 400


mode = data.get('mode', 'both') # poem|song|both
task_id = uuid.uuid4().hex


# 1) Poem / Song lyrics (structured plain text)
poem_text = poem_gen.generate(prompt, style='festive')


# 2) Music (audio file) - returns metadata and filename
music_meta = music_gen.generate(prompt, reference_text=poem_text, uid=task_id)


# 3) Animation (video file) - uses generated music and poem to create a short clip
video_meta = anim_gen.generate(prompt, poem_text=poem_text, music_path=music_meta['path'], uid=task_id)


# Save structured result in DB
save_content(task_id, prompt, poem_text, str(music_meta['path'].name), str(video_meta['path'].name))


response = {
'id': task_id,
'prompt': prompt,
'poem': {'text': poem_text},
'music': {
'file': f"/files/{music_meta['path'].name}",
'duration': music_meta.get('duration'),
'bpm': music_meta.get('bpm')
},
'video': {
'file': f"/files/{video_meta['path'].name}",
'duration': video_meta.get('duration')
}
}


return jsonify(response)




@app.route('/asr', methods=['POST'])
def asr_endpoint():
"""Accept an audio file and return transcript. This is a stub — integrate faster-whisper or another ASR here.
Form: multipart/form-data with key 'audio'.
"""
if 'audio' not in request.files:
return jsonify({'error': 'audio file required (key=audio)'}), 400
f = request.files['audio']
temp_path = OUT_DIR / f"asr_{uuid.uuid4().hex}.wav"
f.save(temp_path)


# Basic stub: echo filename as "transcript". Replace with ASR model call (faster-whisper, whisper, etc.)
transcript = f"[ASR_STUB] saved to {temp_path.name} - implement ASR integration"
return jsonify({'transcript': transcript})




@app.route('/files/<path:filename>')
def serve_file(filename):
return send_from_directory(OUT_DIR, filename, as_attachment=False)




if __name__ == '__main__':
app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))