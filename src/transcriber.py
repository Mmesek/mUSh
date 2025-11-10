from whisperx import (
    asr as whisper_asr,
    alignment as whisper_alignment,
    audio as whisper_audio,
)


def transcribe(
    audio_file: str,
    device: str = "cuda",
    compute_type: str = "int8",
    batch_size: int = 4,
):
    model = whisper_asr.load_model("large-v3", device, compute_type=compute_type)
    audio = whisper_audio.load_audio(audio_file)
    result = model.transcribe(audio, batch_size=batch_size)
    detected_language = result["language"]
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
        for char in segment["chars"]:
            chars.append(char)
    return chars
