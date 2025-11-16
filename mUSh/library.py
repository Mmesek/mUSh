import os
from pathlib import Path

import msgspec
from mUSh.song import Song


class LibrarySong(msgspec.Struct):
    folder: str
    playlist: str
    song: Song


def iterate_songs(path: str):
    for root, dirs, files in os.walk(path):
        for file in files:
            if file.endswith(".txt"):
                yield os.path.join(root, file)


def get_songs(path: str) -> list[LibrarySong]:
    songs = []
    for song_path in iterate_songs(path):
        folder = Path(song_path).parent
        playlist = folder.parent
        try:
            songs.append(LibrarySong(folder, playlist.name, Song.read(song_path)))
        except TypeError:
            continue
    return songs


def list_library(path: str):
    for element in get_songs(path):
        print(element.playlist, element.song.title)
