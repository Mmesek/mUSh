from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from whisperx import (
        asr as whisper_asr,
        alignment as whisper_alignment,
        audio as whisper_audio,
    )
else:
    import whisperx as whisper_asr
    import whisperx as whisper_alignment
    import whisperx as whisper_audio
# NOTE: This is not perfect
# but at least allows having both proper typing support & lazy loading at runtime
import msgspec


class Utterance(msgspec.Struct):
    char: str
    start: float = None
    end: float = None
    score: float = None


def transcribe(
    audio_file: str,
    device: str = "cuda",
    compute_type: str = "int8",
    batch_size: int = 4,
    language: str = None,
    model_name="large-v3",
    character_level: bool = True,
):
    model = whisper_asr.load_model(model_name, device, compute_type=compute_type)
    audio = whisper_audio.load_audio(audio_file)
    result = model.transcribe(audio, batch_size=batch_size, language=language)
    detected_language = language or result["language"]
    model_a, metadata = whisper_alignment.load_align_model(
        language_code=detected_language, device=device
    )
    result_aligned = whisper_alignment.align(
        result["segments"],
        model_a,
        metadata,
        audio,
        device,
        return_char_alignments=True,
    )
    chars = []
    for segment in result_aligned["segments"]:
        for char in segment["chars" if character_level else "words"]:
            chars.append(char)
    return chars, detected_language
