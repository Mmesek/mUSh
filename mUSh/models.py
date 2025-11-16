"""
Following models has been created based on format specified at https://usdx.eu/format/

:copyright: Mmesek
:version: 2025/11/08
:license: MIT
"""

from enum import Enum
from pathlib import Path
import msgspec


class NoteTypes(Enum):
    NORMAL = ":"
    GOLDEN = "*"
    FREESTYLE = "F"
    RAP = "R"
    RAP_GOLDEN = "G"
    END_OF_PHRASE = "-"
    PLAYER = "P"


class Note(msgspec.Struct):
    note_type: NoteTypes
    start_beat: int
    """If `note_type` is `PLAYER`, this field represents player number"""
    length: int | None = None
    pitch: int | None = None
    text: str | None = None

    def __str__(self):
        if self.length:
            return f"{self.note_type.value} {self.start_beat:.0f} {self.length:.0f} {self.pitch:.0f} {self.text}"
        return f"{self.note_type.value} {self.start_beat:.0f}"


class Song(msgspec.Struct):
    mp3: str = None  # deprecated
    title: str = None
    artist: str = None
    notes: list[Note] = None
    bpm: float = None
    audio: str | None = None
    version: str = "1.0.0"
    gap: float | None = 0
    cover: str | None = None
    background: str | None = None
    video: str | None = None
    videogap: float | None = None
    vocals: str | None = None
    instrumental: str | None = None
    genre: str | None = None
    tags: str | None = None
    edition: str | None = None
    creator: str | None = "mUSh"
    language: str | None = None
    year: int | None = None
    start: float | None = None
    end: float | None = None
    previewstart: str | None = None
    medleystartbeat: int | None = None
    medleyendbeat: int | None = None
    calcmedley: bool | None = None
    p1: str | None = None
    p2: str | None = None
    providedby: str | None = None
    comment: str | None = None

    def __post_init__(self):
        if self.audio:
            self.mp3 = self.audio
        else:
            self.audio = self.mp3

        if any(self.audio.endswith(x) for x in {"mp4", "avi", "webm"}):
            self.video = self.audio

        if not self.title and not self.artist:
            audio = Path(self.audio).name
            a, t = audio.split(".")[0].split(" - ")
            self.artist, self.title = a.strip(), t.strip()
