"""Tests that need the downloaded data. They run only when NYCPED_DATA_DIR points at it."""
import json
import os
from importlib import resources
from pathlib import Path

import pytest

from nycped import exposure as ex
from nycped.config import Settings

DATA = os.environ.get('NYCPED_DATA_DIR')
pytestmark = pytest.mark.integration


@pytest.mark.skipif(not DATA or not (Path(DATA or '.') / 'supp_data_1_network.zip').exists(),
                    reason='NYC Walks data not available')
def test_crosswalk_and_site_counts_match_the_published_run():
    s = Settings()
    expected = json.loads(resources.files('nycped').joinpath('expected_results.json').read_text())['integration']
    geojson = ex.extract_walks_geojson(s.path('supp_data_1_network.zip'), s.path('cache'))
    seg = ex.read_walks(geojson)
    streets = ex.read_streets(s.path('centerline_inkn-q76z.geojson'), s.street_types)
    cross = ex.infer_crosswalks(seg, streets)
    assert len(cross) == expected['crosswalk_segments']
    assert len(ex.build_sites(cross, 25)) == expected['sites_25m']
