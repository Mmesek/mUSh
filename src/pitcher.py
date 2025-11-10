import crepe
from scipy.io import wavfile
import numpy as np
from separator import convert


def detect_pitch(path: str):
    result = convert(path, "vocals.mp3", extension="wav")
    sr, audio = wavfile.read(path + "/" + result)
    time, frequencies, confidence, activation = crepe.predict(audio, sr, viterbi=True)

    notes = 12 * (np.log2(np.asanyarray(frequencies)) - np.log2(440.0)) + (69 - 48)
    return time, notes, confidence, activation
