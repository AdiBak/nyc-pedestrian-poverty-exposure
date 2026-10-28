"""Constants and settings shared across the package."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

PROJECTED_CRS = 6538   # NAD83(2011) New York Long Island, meters. Matches the NYC Walks file.
GEOGRAPHIC_CRS = 4326
NYC_COUNTIES = {'005': 'Bronx', '047': 'Brooklyn', '061': 'Manhattan', '081': 'Queens', '085': 'Staten Island'}
HEADLINE_YEARS = (2019, 2020, 2021, 2022, 2023)
WALKS_MEMBER = 'NYC_pednetwork_estimates_counts_2018-2019.geojson'
VOLUME_WEEKDAY = ('predwkdyAM', 'predwkdyMD', 'predwkdyPM')
VOLUME_WEEKEND = ('predwkndAM', 'predwkndMD', 'predwkndPM')
COLAB_DRIVE_DIR = Path('/content/drive/MyDrive/TDSP/nyc_walks')


def default_data_dir() -> Path:
    """Use NYCPED_DATA_DIR if set, then the Colab Drive folder if it exists, then ./data/raw."""
    env = os.environ.get('NYCPED_DATA_DIR')
    if env:
        return Path(env).expanduser()
    if COLAB_DRIVE_DIR.exists():
        return COLAB_DRIVE_DIR
    return Path('data/raw')


@dataclass(frozen=True)
class Settings:
    """Analysis settings. The defaults are the primary specification."""
    data_dir: Path = field(default_factory=default_data_dir)
    site_eps_m: float = 25.0       # crosswalks closer than this form one site
    crash_radius_m: float = 30.0   # a crash belongs to the nearest site within this distance
    street_types: tuple = (1,)     # centerline rw_type 1 is the ordinary street
    years: tuple = HEADLINE_YEARS
    seed: int = 2026

    def path(self, name: str) -> Path:
        return Path(self.data_dir) / name
