import os
from pathlib import Path

import msgspec
from mUSh.song import Song
from mUSh.cli import logger


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
        logger.info(element.playlist, element.song.title)


def add_missing_stems(path: str):
    for element in get_songs(path):
        if element.song.instrumental:
            logger.info("Instrumental stems already exists in %s", element.song.title)
            continue
        logger.info("Adding stems to %s", element.song.title)
        element.song.separate_vocals()
        element.song.write(element.folder)
        element.song.move(element.folder)
