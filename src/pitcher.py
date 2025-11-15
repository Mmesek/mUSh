import msgspec
import crepe
from scipy.io import wavfile
import numpy as np

from separator import convert


class Pitch(msgspec.Struct):
    time: float
    frequency: float
    confidence: float


def detect_pitch(path: str):
    result = convert(path, "vocals.mp3", extension="wav")
    sr, audio = wavfile.read(path / result)
    times, frequencies, confidences, _ = crepe.predict(audio, sr, viterbi=True)

    notes = 12 * (np.log2(np.asanyarray(frequencies)) - np.log2(440.0)) + (69 - 48)
    return {
        "time": [float(t) for t in times],
        "freq": [float(n) for n in notes],
        "confidence": [float(c) for c in confidences],
    }
