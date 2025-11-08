import msgspec
from models import Note, Song as SongSchema


class Song(SongSchema):
    @classmethod
    def read(cls, text: str) -> "Song":
        """Reads .txt file and parses it's structure"""
        data = {"notes": []}
        for line in text.splitlines():
            line = line.strip()
            if line == "E":
                continue
            elif line.startswith("#"):
                key, value = line.split(":", 1)
                data[key.strip("#").lower()] = value
            else:
                note = dict(zip(Note.__annotations__, line.split(" ", 4)))
                data["notes"].append(msgspec.convert(note, Note, strict=False))

        return msgspec.convert(data, cls, strict=False)

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
