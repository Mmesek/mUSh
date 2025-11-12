# mUSh

Helper utils to access & manage Ultrastar's song data in Python. Makes conversion of audio files into Ultrastar accepted songs a breeze, with (currently) a *letter* level pitch markers. 

# Usage

> NOTE
Commands below this block are... currently not tested so instead there's a Work in Progress workflow *I'm* using specifically, so treat this as an official hack:

```sh
# This step happens automatically on my end, just adding it for the clarity, YMMV
$ source .venv/bin/activate
# WhisperX uses some codecs not available in newer version. Besides, torch needs to be installed using proper CUDA version. (For GTX 1070 that's cu126 afaik)
$ uv pip install 'torchaudio<2.9' torch --index-url https://download.pytorch.org/whl/cu126
# Below allows WhisperX to properly load models and perform speech transcription
$ export LD_LIBRARY_PATH=.venv/lib/python3.13/site-packages/nvidia/cudnn/lib/
# Using library as a module like below probably needs some additional import tweaks
$ python src/__main__.py "path/to/file.m4a"
```
Et voila, you should now have a workable `file.txt` located in your output directory alongside converted OGG files with stems of original audio for karaoke mode. You may need to tweak songs in editor though.

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
