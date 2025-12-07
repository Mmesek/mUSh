import argparse
from pathlib import Path
from mUSh.cli import logger
from mUSh.song import Song
from mUSh.library import add_cover


parser = argparse.ArgumentParser()
parser.add_argument("-filepath", help="Path to file to process")
parser.add_argument(
    "-output",
    help="Path to cache directory where output will be stored. Default is `out`",
    default="out",
)
parser.add_argument(
    "-library",
    help="Path to Ultrastar library",
    default="mUSh",
)


def process_file(path):
    s = Song(audio=path.name, _path=path.absolute().resolve().parent)
    logger.info("Song `%s` by `%s` initiated", s.title, s.artist)
    s.build_notes()
    add_cover(s)
    logger.info("Notes built")
    destination = s.move(args.library)
    logger.info("Moved to library")
    s.write(destination)
    logger.info("Written result to %s", args.output)


if __name__ == "__main__":
    args = parser.parse_args()
    logger.info("New instance started")
    path = Path(args.filepath)
    if path.is_dir():
        paths = path.walk()
    else:
        paths = [["", "", [path]]]
    for parent, dirs, files in paths:
        for file in files:
            path = parent / file
            try:
                process_file(path)
            except ValueError:
                continue
