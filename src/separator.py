import demucs.separate
import os
from pathlib import Path
import ffmpeg

REUSE_OK = True


def separate(path: str, model: str = "htdemucs_ft", output: str = "out") -> Path:
    result = Path(output) / model / os.path.splitext(Path(path).name)[0]
    if os.path.exists(result):
        if os.path.exists(result / "no_vocals.mp3") and os.path.exists(
            result / "vocals.mp3"
        ):
            print("Stems already exists, skipping")
            return result
    demucs.separate.main(
        ["--mp3", "--two-stems", "vocals", "-n", model, "--out", output, path]
    )
    return result


def convert(
    path: str | Path, stem: str = "no_vocals.mp3", extension: str = "ogg"
) -> str:
    path = Path(path)
    if stem == "no_vocals.mp3":
        stem_type = "INSTRUMENTAL"
    else:
        stem_type = "VOCALS"
    result = f"{path.name} [{stem_type}].{extension}"
    if os.path.exists(path / result):
        if REUSE_OK:
            print("Reusing previous result")
            return result
        print("Deleting old result file")
        os.remove(path / result)
    worker = ffmpeg.FFmpeg().input(path / stem).output(path / result)
    print("Calling FFmpeg with:", worker.arguments)
    worker.execute()
    return result
