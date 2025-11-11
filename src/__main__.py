import argparse

from cli import logger
from song import Song

parser = argparse.ArgumentParser()
parser.add_argument("filepath", help="Path to file to process")
parser.add_argument(
    "output",
    help="Path to cache directory where output will be stored. Default is `out`",
    default="out",
)

if __name__ == "__main__":
    args = parser.parse_args()
    logger.info("New instance started")
    s = Song(args.filepath)
    logger.info("Song %s - %s initiated", s.title, s.artist)
    s.build_notes()
    logger.info("Notes built")
    s.write(args.output)
    logger.info("Written result to %s", args.output)
