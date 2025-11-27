import os
from pathlib import Path

import msgspec

from mUSh.cli import logger
from mUSh.cover import fetch_cover
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
        if song_path.endswith("license.txt"):
            continue
        folder = Path(song_path).parent
        playlist = folder.parent
        try:
            songs.append(LibrarySong(folder, playlist.name, Song.read(song_path)))
        except (TypeError, msgspec.ValidationError) as ex:
            logger.error("Couldn't read %s due to %s", song_path, ex)
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
        try:
            element.song.separate_vocals()
            element.song.write(element.song.get_path(""))
            element.song.move(element.folder)
        except Exception as ex:
            logger.warning("Couldn't save %s due to %s", element.song.title, ex)


def add_missing_covers(path: str):
    for element in get_songs(path):
        if element.song.cover:
            logger.info("Cover already exists in %s", element.song.title)
            continue
        if out := fetch_cover(
            element.song.artist, element.song.title, element.song.get_path("")
        ):
            logger.info("Adding cover to %s", element.song.title)
            element.song.cover = out.name
            element.song.write(element.song.get_path(""))
        else:
            logger.info("Couldn't add cover to %s", element.song.title)


