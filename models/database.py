import sqlite3
from pathlib import Path


DB_PATH = Path(__file__).parent.parent / 'creative_studio.db'


def init_db():
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS outputs (
id TEXT PRIMARY KEY,
prompt TEXT,
poem TEXT,
music_file TEXT,
video_file TEXT
)''')
conn.commit()
conn.close()




def save_content(id: str, prompt: str, poem: str, music_file: str, video_file: str):
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()
c.execute('INSERT OR REPLACE INTO outputs (id, prompt, poem, music_file, video_file) VALUES (?, ?, ?, ?, ?)',
(id, prompt, poem, music_file, video_file))
conn.commit()
conn.close()