# mUSh

Helper utils to access & manage Ultrastar's song data in Python

# Usage

## With UV
Simplest use case to generate .txt out of audio file (tested with mp3, m4a and ogg):
```sh
$ uv venv
$ uv pip install -r requirements.txt
$ python -m src "path/to/file.mp3"
```

## With Docker or Podman
```sh
$ docker run -it --rm ghcr.io/Mmesek/mUSh "path/to/file.mp3"
```


# Acknowledgements

Other projects similiar to this: 
- [Ultrasinger](https://github.com/rakuri255/UltraSinger): Mostly works. Generates a lot of extra files, however adds a ton of `~` throughout lyrics.
- [Ultrastar-Generator](https://github.com/clem2k/ultrastar-generator): Produces clean lyrics, however during my tests, pitch ended up being "flat".
