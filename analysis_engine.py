"""Optional on-device visual matching and speech transcription. No external media scraping."""
import os
import subprocess
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.webp'}
VIDEO_EXTS = {'.mp4', '.mov', '.m4v', '.webm'}
AUDIO_EXTS = {'.wav', '.mp3', '.m4a', '.ogg'}


def get_visual_model():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer('sentence-transformers/clip-ViT-B-32')


def get_audio_model():
    from faster_whisper import WhisperModel
    return WhisperModel('tiny', device='cpu', compute_type='int8')


def _frames(filename, raw, max_frames=8):
    suffix = Path(filename).suffix.lower()
    if suffix in IMAGE_EXTS:
        import io
        with Image.open(io.BytesIO(raw)) as source:
            yield source.convert('RGB').copy()
    elif suffix in VIDEO_EXTS:
        import cv2
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as target:
            target.write(raw)
            path = target.name
        cap = None
        try:
            cap = cv2.VideoCapture(path)
            total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            if total > 0:
                indices = np.unique(np.linspace(0, max(0, total - 1), num=min(max_frames, total), dtype=int))
                for index in indices:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, int(index))
                    ok, frame = cap.read()
                    if ok:
                        yield Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            else:
                for _ in range(max_frames):
                    ok, frame = cap.read()
                    if not ok:
                        break
                    yield Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        finally:
            if cap:
                cap.release()
            os.unlink(path)


def image_similarity(filename, raw, search_terms, model):
    """Returns max cosine similarity; heuristic threshold should be adjusted by users."""
    if not search_terms:
        return None
    images = list(_frames(filename, raw))
    if not images:
        return None
    prompts = [f'a photo or video of {term.lstrip("#")}' for term in search_terms]
    img_vectors = np.asarray(model.encode(images, normalize_embeddings=True))
    text_vectors = np.asarray(model.encode(prompts, normalize_embeddings=True))
    return float((img_vectors @ text_vectors.T).max())


def transcribe_media(filename, raw, model):
    suffix = Path(filename).suffix.lower()
    if suffix not in VIDEO_EXTS | AUDIO_EXTS:
        return ''
    with tempfile.TemporaryDirectory() as folder:
        src = str(Path(folder) / ('input' + suffix))
        wav = str(Path(folder) / 'audio.wav')
        Path(src).write_bytes(raw)
        # ffmpeg is needed to extract audio from video (also standardizes audio-only inputs).
        cmd = ['ffmpeg', '-nostdin', '-v', 'error', '-y', '-i', src,
               '-vn', '-ac', '1', '-ar', '16000', wav]
        try:
            subprocess.run(cmd, capture_output=True, check=True, timeout=180)
        except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return ''
        segments, _ = model.transcribe(wav, beam_size=1)
        return ' '.join(s.text.strip() for s in segments)
