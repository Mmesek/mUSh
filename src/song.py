import msgspec
from models import Note, Song as SongSchema
import separator
import transcriber
import pitcher


class Song(SongSchema):
    _path: str = None

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
        with open(path, "r", encoding="utf-8", errors="ignore") as file:
            return cls.parse(file.read())

    def dump(self) -> str:
        """Dumps structure into a text form"""
        text = ""
        for attribute in super().__annotations__:
            if attribute.startswith("_"):
                continue
            if attribute != "notes":
                text += f"#{attribute.upper()}={getattr(self, attribute)}\n"

        for note in self.notes:
            text += str(note) + "\n"

        text += "E"
        return text

    def get_path(self, file: str):
        if self._path:
            return self._path + "/" + file
        return file

    def separate_vocals(self, file_path: str = None):
        """Using demucs, separates `vocals` and `instrumental` audio from `audio` or `mp3`"""
        if self.vocals and self.instrumental:
            return

        output_dir = separator.separate(self.get_path(self.audio))
        self.vocals = separator.convert(output_dir, "vocals.mp3")
        self.instrumental = separator.convert(output_dir, "no_vocals.mp3")

    def transcribe_vocals(self, file_path: str = None):
        """Using whisperx, transcribes `vocals`"""
        if not self.vocals:
            self.separate_vocals(file_path)

        self._transcription = transcriber.transcribe(self.get_path(self.vocals))

    def pitch_vocals(self, file_path: str = None):
        """Using crepe, detects pitch of `vocals`"""
        if not self.vocals:
            self.separate_vocals(file_path)

        self._pitch_result = pitcher.detect_pitch(self.get_path(self.vocals))

    def build_notes(self):
        pass
