import json
import os
from pathlib import Path

import msgspec
import pitcher
import separator
import transcriber
from bpm import analyze_bpm
from cli import logger
from merge import NoteCollection, get_multiplier
from models import Note, NoteTypes
from models import Song as SongSchema

OUTPUT_DIR = "out"
HTDEMUCS_MODEL = "htdemucs_ft"


class FileOperations(SongSchema):
    _cache: Path = None

    @classmethod
    def parse(cls, text: str) -> "Song":
        """Reads .txt file and parses it's structure"""
        data = {"notes": []}
        if not text.startswith("#"):
            raise TypeError("Not a valid .txt file")
        for line in text.splitlines():
            line = line.strip()
            if line == "E":
                continue
            elif line.startswith("#"):
                key, value = line.split(":", 1)
                if value[0].isdigit():
                    value = value.replace(",", ".")
                data[key.strip("#").lower()] = value
            else:
                note = dict(zip(Note.__annotations__, line.split(" ", 4)))
                data["notes"].append(msgspec.convert(note, Note, strict=False))

        return msgspec.convert(data, cls, strict=False)

    @classmethod
    def read(cls, path: str) -> "Song":
        logger.info("Reading %s", path)
        with open(path, "r", encoding="utf-8", errors="ignore") as file:
            return cls.parse(file.read())

    def dump(self) -> str:
        """Dumps structure into a text form"""
        if not self.notes:
            self.build_notes()
        logger.debug("Dumping song `%s` data to Ultrastar text", self.title)
        text = ""
        for attribute in super().__annotations__:
            if attribute.startswith("_"):
                continue
            if attribute != "notes":
                if not (value := getattr(self, attribute)):
                    continue
                if super().__annotations__[attribute] is float:
                    text += f"#{attribute.upper()}:{value:.2f}\n"
                else:
                    text += f"#{attribute.upper()}:{value}\n"

        for note in self.notes:
            text += str(note) + "\n"

        text += "E"
        return text

    def write(self, path: str, text: str = None):
        if not text:
            text = self.dump()
        logger.debug("Writing song `%s` data to %s", self.title, path)
        with open(
            path + "/" + self.artist + " - " + self.title + ".txt",
            "w",
            newline="",
            encoding="utf-8",
        ) as file:
            file.writelines(text)

    def cache_result(self, path: str, data, key: str):
        logger.debug("Caching result %s to %s", key, path)
        import json

        os.makedirs(path / "cache", exist_ok=True)

        with open(
            path / f"cache/{key}_{self.title}.json", "w", newline="", encoding="utf-8"
        ) as file:
            json.dump(msgspec.to_builtins(data), file)

    def read_cache(self, path: str, key: str):
        cached_file = self._cache / f"cache/{key}_{self.title}.json"
        if os.path.exists(cached_file):
            logger.debug("Reading cached data of %s from %s", key, path)
            with open(cached_file, "r", newline="", encoding="utf-8") as file:
                try:
                    return json.load(file)
                except IndexError:
                    logger.warning("Cached %s is invalid. Removing.")
                    os.remove(cached_file)

    def get_path(self, file: str):
        if self._path:
            return str(self._path) + "/" + file
        return file

    def get_cache(self, file: str):
        if self._cache:
            return str(self._cache) + "/" + file
        return file


class Song(FileOperations):
    _path: str = None
    _transcription: list[transcriber.Utterance] = None
    _pitch_result: list[pitcher.Pitch] = None
    _real_bpm: float = None

    def __post_init__(self):
        super().__post_init__()
        self._path = str(Path(self.audio).parent)
        self._cache = (
            Path(OUTPUT_DIR)
            / HTDEMUCS_MODEL
            / os.path.splitext(Path(self.audio).name)[0]
        )

    def separate_vocals(self, file_path: str = None):
        """Using demucs, separates `vocals` and `instrumental` audio from `audio` or `mp3`"""
        if self.vocals and self.instrumental:
            logger.debug("Vocals and instrumental are already separated. Skipping.")
            return

        logger.info("Separating vocals from %s", self.audio)
        output_dir = separator.separate(self.get_path(self.audio))
        self.vocals = separator.convert(output_dir, "vocals.mp3")
        self.instrumental = separator.convert(output_dir, "no_vocals.mp3")

    def transcribe_vocals(self, file_path: str = None):
        """Using whisperx, transcribes `vocals`"""
        if not self.vocals:
            logger.debug("Vocals are not separated. Separating first.")
            self.separate_vocals(file_path)

        if self._transcription:
            logger.debug("Transcription is already available. Skipping.")
            return

        if _cached := self.read_cache(self._cache, "transcription"):
            logger.debug("Transcription is cached. Skipping.")
            self._transcription = _cached
            return

        logger.info("Transcribing vocals from %s", self.vocals)
        self._transcription = transcriber.transcribe(self.get_cache(self.vocals))
        self.cache_result(self._cache, self._transcription, "transcription")

    def pitch_vocals(self, file_path: str = None):
        """Using crepe, detects pitch of `vocals`"""
        if not self.vocals:
            logger.debug("Vocals are not separated. Separating first.")
            self.separate_vocals(file_path)

        if self._pitch_result:
            logger.debug("Pitch is already available. Skipping.")
            return
        if _cached := self.read_cache(self._cache, "pitch"):
            logger.debug("Pitch is cached. Skipping.")
            self._pitch_result = _cached
            return

        logger.info("Detecting pitch of vocals from %s", self.vocals)
        self._pitch_result = pitcher.detect_pitch(self._cache)
        self.cache_result(self._cache, self._pitch_result, "pitch")

    def analyze_bpm(self):
        if self.bpm:
            logger.debug("BPM is already available. Skipping.")
            return
        if _cached := self.read_cache(self._cache, "bpm"):
            logger.debug("BPM is cached. Skipping.")
            self.bpm = _cached["bpm"]
            self._real_bpm = _cached["real_bpm"]
            return

        logger.info("Analyzing BPM from %s", self.audio)
        self._real_bpm = analyze_bpm(self.get_path(self.audio))
        self.bpm = self._real_bpm / 4 * get_multiplier(self._real_bpm / 4)
        self.cache_result(
            self._cache,
            {"bpm": float(self.bpm), "real_bpm": float(self._real_bpm)},
            "bpm",
        )
        logger.info("Detected BPM: %s", self.bpm)

    def build_notes(self):
        if not self.bpm:
            logger.debug("BPM is not available. Analyzing first.")
            self.analyze_bpm()
        if not self._transcription:
            logger.debug("Transcription is not available. Transcribing first.")
            self.transcribe_vocals()
        if not self._pitch_result:
            logger.debug("Pitch is not available. Detecting first.")
            self.pitch_vocals()

        logger.info("Building notes from transcription and pitch")
        notes = NoteCollection(self._transcription, self._pitch_result)
        if not self.gap:
            self.gap = notes.result["start"][1]
            logger.debug("Setting notes gap to %s", self.gap)
            notes.result["start"] -= self.gap
            self.gap = int(self.gap * 1000)
            logger.debug("Setting gap to %s", self.gap)
        else:
            logger.debug("Setting notes gap to %s", self.gap / 1000)
            notes.result["start"] -= self.gap / 1000

        (
            notes
            # .set_gap()
            .apply_bpm(self._real_bpm)
            .merge_punctuation()
            .merge_chars()
            .merge_spaces()
            .running_bag()
            .normalize_duration()
            # .insert_breaks()
        )
        notes = notes.result.to_numpy()
        logger.info("Normalizing `NoteCollection` into list of `Note`s")
        self.notes = [
            Note(
                NoteTypes.NORMAL,
                row[0],
                row[1],
                row[2],
                row[3],
            )
            if row[3] != "--"
            else Note(NoteTypes.END_OF_PHRASE, row[0])
            for row in notes
        ]
