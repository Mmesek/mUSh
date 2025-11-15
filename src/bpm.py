import librosa


def analyze_bpm(path: str):
    y, sr = librosa.load(path)
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
    return tempo[0]


def get_multiplier(real_bpm: float) -> int:
    """Calculates the multiplier for the BPM"""

    if real_bpm == 0:
        raise Exception("BPM is 0")

    multiplier = 1
    result = 0
    while result < 400:
        result = real_bpm * multiplier
        multiplier += 1
    return multiplier - 2
