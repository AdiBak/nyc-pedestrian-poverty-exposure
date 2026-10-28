"""Downloads, checksums and the data manifest."""
from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import requests

from .config import Settings

WALKS_BASE = ('https://media.springernature.com/original/springer-static/esm/'
              'art%3A10.1038%2Fs44284-025-00383-y/MediaObjects/')
WALKS_FILES = {
    'supp_data_1_network.zip': WALKS_BASE + '44284_2025_383_MOESM3_ESM.zip',
    'supp_data_1_metadata.txt': WALKS_BASE + '44284_2025_383_MOESM4_ESM.txt',
}
CENTERLINE_URL = 'https://data.cityofnewyork.us/resource/inkn-q76z.geojson?$limit=300000'
TRACT_URL = 'https://www2.census.gov/geo/tiger/GENZ2020/shp/cb_2020_36_tract_500k.zip'
SOURCES = {
    **WALKS_FILES,
    'centerline_inkn-q76z.geojson': CENTERLINE_URL,
    'ny_tracts2020.zip': TRACT_URL,
}


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def download(url: str, dest, headers=None, timeout: int = 180) -> dict:
    """Stream a URL to dest, writing to a temporary file first. Returns size and checksum."""
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + '.part')
    h = hashlib.sha256()
    size = 0
    with requests.get(url, stream=True, timeout=timeout, headers=headers or {'User-Agent': 'Mozilla/5.0'}) as r:
        r.raise_for_status()
        with open(tmp, 'wb') as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
                h.update(chunk)
                size += len(chunk)
    shutil.move(str(tmp), str(dest))
    return {'bytes': size, 'sha256': h.hexdigest()}


class Manifest:
    """A JSON record of every file the pipeline downloaded: source, date, size and checksum."""

    def __init__(self, path):
        self.path = Path(path)
        self.entries = json.loads(self.path.read_text()) if self.path.exists() else {}

    def record(self, name: str, url: str, info: dict) -> None:
        self.entries[name] = {'url': url, 'retrieved_utc': datetime.now(timezone.utc).isoformat(timespec='seconds'), **info}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.entries, indent=2, sort_keys=True))


def fetch_all(settings: Settings, force: bool = False) -> Manifest:
    """Download every public source that is missing. Existing files are kept unless force is True."""
    manifest = Manifest(settings.path('MANIFEST.json'))
    for name, url in SOURCES.items():
        dest = settings.path(name)
        if dest.exists() and not force:
            if name not in manifest.entries:
                manifest.record(name, url, {'bytes': dest.stat().st_size, 'sha256': sha256_file(dest)})
            continue
        manifest.record(name, url, download(url, dest))
    return manifest
