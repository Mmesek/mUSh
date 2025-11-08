"""
Following models has been created based on format specified at https://usdx.eu/format/

:copyright: Mmesek
:version: 2025/11/08
:license: MIT
"""

from enum import Enum
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
            return f"{self.note_type.value} {self.start_beat} {self.length} {self.pitch} {self.text}"
        return f"{self.note_type.value} {self.start_beat}"


class Song(msgspec.Struct):
    title: str
    artist: str
    mp3: str  # deprecated
    bpm: int
    notes: list[Note]
    audio: str | None = None
    version: str = "1.0.0"
    gap: int | None = None
    cover: str | None = None
    background: str | None = None
    video: str | None = None
    videogap: int | None = None
    vocals: str | None = None
    instrumental: str | None = None
    genre: str | None = None
    tags: str | None = None
    edition: str | None = None
    creator: str | None = None
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
