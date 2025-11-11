import librosa


def analyze_bpm(path: str):
    y, sr = librosa.load(path)
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
    return tempo[0]
