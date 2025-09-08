class ContentRecord:
def __init__(self, id, prompt, poem, music_file, video_file):
self.id = id
self.prompt = prompt
self.poem = poem
self.music_file = music_file
self.video_file = video_file


def to_dict(self):
return {
'id': self.id,
'prompt': self.prompt,
'poem': self.poem,
'music_file': self.music_file,
'video_file': self.video_file
}