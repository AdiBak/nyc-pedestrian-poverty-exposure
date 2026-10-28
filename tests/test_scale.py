import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import box

from nycped import scale as sc
from nycped.config import PROJECTED_CRS


def grid(n=5):
    cells, ids = [], []
    for i in range(n):
        for j in range(n):
            cells.append(box(i * 10, j * 10, (i + 1) * 10, (j + 1) * 10))
            ids.append(f'36061{i:02d}{j:02d}00')
    return gpd.GeoDataFrame({'GEOID': ids}, geometry=cells, crs=PROJECTED_CRS)


def test_adjacency_is_symmetric_and_within_borough():
    g = grid(4)
    county = {gid: 'Manhattan' for gid in g['GEOID']}
    nbrs = sc.adjacency(g, list(g['GEOID']), county)
    for a, others in nbrs.items():
        for b in others:
            assert a in nbrs[b]
    assert len(nbrs[g['GEOID'].iloc[5]]) == 8  # interior cell has eight queen neighbors


def test_random_zones_cover_every_tract_and_stay_contiguous():
    g = grid(6)
    ids = list(g['GEOID'])
    nbrs = sc.adjacency(g, ids, {i: 'Manhattan' for i in ids})
    zone_of = sc.random_zones(ids, nbrs, 4, np.random.default_rng(0))
    assert set(zone_of) == set(ids)
    zones = {}
    for gid, z in zone_of.items():
        zones.setdefault(z, []).append(gid)
    for members in zones.values():
        assert len(members) <= 4
        seen, stack = {members[0]}, [members[0]]
        while stack:
            cur = stack.pop()
            for nb in nbrs.get(cur, []):
                if nb in members and nb not in seen:
                    seen.add(nb)
                    stack.append(nb)
        assert seen == set(members)


def test_aggregate_conserves_totals():
    rng = np.random.default_rng(0)
    t = pd.DataFrame({'GEOID': [f'g{i}' for i in range(12)], 'harm': rng.integers(0, 9, 12),
                      'killed': rng.integers(0, 3, 12), 'vol': rng.uniform(100, 900, 12),
                      'wv': rng.uniform(1e3, 2e4, 12), 'lv': rng.uniform(1e2, 2e3, 12),
                      'sv': rng.uniform(1e3, 2e4, 12), 'pop': rng.integers(1000, 5000, 12),
                      'pov': rng.uniform(5, 40, 12), 'walk': rng.uniform(0, 30, 12),
                      'transit': rng.uniform(0, 60, 12), 'comm': rng.uniform(0, 40, 12),
                      'zip': rng.integers(0, 3, 12), 'county': 'Queens'})
    z = sc.aggregate(t, np.repeat([0, 1, 2], 4))
    assert z['harm'].sum() == t['harm'].sum()
    assert abs(z['pop'].sum() - t['pop'].sum()) < 1e-9
    assert len(z) == 3
