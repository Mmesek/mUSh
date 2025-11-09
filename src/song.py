import msgspec
from models import Note, Song as SongSchema
import separator


class Song(SongSchema):
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
        for attribute in self.__annotations__:
            if attribute != "notes":
                text += f"#{attribute.upper()}={getattr(self, attribute)}\n"

        for note in self.notes:
            text += str(note) + "\n"

        text += "E"
        return text

    def separate_vocals(self, file_path: str = None):
        """Using demucs, separates `vocals` and `instrumental` audio from `audio` or `mp3`"""
        if self.vocals and self.instrumental:
            return
        if file_path:
            audio = file_path + "/" + self.audio
        else:
            audio = self.audio
        output_dir = separator.separate(audio)
        self.vocals = separator.rename_stem(output_dir, "vocals.mp3")
        self.instrumental = separator.rename_stem(output_dir, "no_vocals.mp3")
