from moviepy.editor import ImageClip, AudioFileClip, CompositeVideoClip, concatenate_videoclips
def __init__(self, output_dir: Path):
self.output_dir = Path(output_dir)


def _make_frame_image(self, text: str, color_rgb=(20, 160, 255), size=(720, 720)) -> Image:
img = Image.new('RGB', size, color_rgb)
draw = ImageDraw.Draw(img)
# Use default font; for production provide a TTF file
try:
font = ImageFont.truetype("DejaVuSans-Bold.ttf", 28)
except Exception:
font = ImageFont.load_default()
margin = 40
wrapped = textwrap.fill(text, width=30)
draw.multiline_text((margin, margin), wrapped, fill=(255,255,255), font=font)
return img


def generate(self, prompt: str, poem_text: str = None, music_path: Path = None, uid: str = None):
# Create 3-5 frames with different color palettes
frames = []
palettes = [(20,160,255), (200,50,120), (60,180,75), (255,150,20)]
texts = [prompt, (poem_text or '').split('\n')[0]]


for i, pal in enumerate(palettes[:3]):
img = self._make_frame_image(texts[i % len(texts)] or prompt, color_rgb=pal, size=(720,720))
fname = f"frame_{uid or i}_{i}.png"
p = self.output_dir / fname
img.save(p)
frames.append(p)


# Turn frames into ImageClips
clips = [ImageClip(str(p)).set_duration(1.0).resize((720,720)) for p in frames]
video = concatenate_videoclips(clips, method='compose')


# Attach audio if provided
out_fname = f"video_{uid or 'anon'}.mp4"
out_path = self.output_dir / out_fname
if music_path and Path(music_path).exists():
audio = AudioFileClip(str(music_path))
video = video.set_audio(audio.subclip(0, min(video.duration, audio.duration)))
duration = round(video.duration, 2)
else:
duration = round(video.duration, 2)


# write the final video
video.write_videofile(str(out_path), codec='libx264', fps=24, audio_codec='aac', verbose=False, logger=None)


return {'path': out_path, 'duration': duration}