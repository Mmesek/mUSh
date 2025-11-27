from pathlib import Path

import requests

from mUSh.cli import logger


def _itunes_search(artist: str, title: str) -> dict | None:
    """
    Query the iTunes Search API for a specific track.
    Returns the first matching result dictionary or None if nothing matches.
    """
    base_url = "https://itunes.apple.com/search"
    # iTunes expects a single term; we combine artist and title for better precision.
    params = {
        "term": f"{artist} - {title}",
        "media": "music",
        "entity": "song",
        "limit": 5,  # a few results - we’ll pick the best match later
        "explicit": "yes",  # include explicit tracks
    }

    try:
        resp = requests.get(base_url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.debug(f"[!] iTunes lookup failed: {exc}")
        return None

    if data.get("resultCount", 0) == 0:
        return None

    # Simple heuristic: exact match on both artistName and trackName (case-insensitive)
    for result in data["results"]:
        if (
            result.get("artistName", "").lower() == artist.lower()
            and result.get("trackName", "").lower() == title.lower()
        ):
            return result

    # Fallback: just return the first result
    return data["results"][0]


def _best_artwork_url(result: dict) -> str | None:
    """
    iTunes provides several artwork URLs (30x30, 60x60, 100x100, etc.).
    The key `artworkUrl100` is the smallest guaranteed size.
    To get a higher-resolution version, replace the dimension suffix.
    """
    url = result.get("artworkUrl100")
    if not url:
        return None

    # Replace the trailing "...100x100bb.jpg" with "...600x600bb.jpg"
    # (600px works for most entries; if unavailable the server falls back gracefully.)
    high_res = url.replace("100x100bb", "600x600bb")
    return high_res


def fetch_cover(artist: str, title: str, out_dir: str = ".") -> Path | None:
    """
    Main helper - returns the local Path of the saved image, or None on failure.
    """
    result = _itunes_search(artist, title)
    if not result:
        logger.debug("[!] No matching track found.")
        return None

    img_url = _best_artwork_url(result)
    if not img_url:
        logger.debug("[!] No artwork URL found in the iTunes response.")
        return None

    try:
        img_resp = requests.get(img_url, timeout=10)
        img_resp.raise_for_status()
    except Exception as exc:
        logger.debug(f"[!] Failed to download artwork: {exc}")
        return None

    # Build a safe filename: Artist - Title.jpg
    safe_name = f"{artist} - {title}".replace("/", "_")
    out_path = Path(out_dir) / f"{safe_name}.jpg"

    try:
        out_path.write_bytes(img_resp.content)
        logger.debug(f"[+] Cover saved to: {out_path.resolve()}")
        return out_path
    except Exception as exc:
        logger.debug(f"[!] Could not write file: {exc}")
        return None
