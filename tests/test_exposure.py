import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import LineString, Point, box

from nycped import crashes as cr
from nycped import exposure as ex
from nycped.config import PROJECTED_CRS, VOLUME_WEEKDAY, VOLUME_WEEKEND


def toy_streets():
    return gpd.GeoDataFrame(
        {'rw_type': [1, 6, 1], 'status': [2, 2, 2], 'trafdir': ['TW', 'NV', 'TW'],
         'streetwidth': [30, 15, 36], 'posted_speed': [25, np.nan, 30], 'number_travel_lanes': [2, 1, 3],
         'truck_route_type': ['2', None, None]},
        geometry=[LineString([(0, 0), (200, 0)]), LineString([(100, -50), (100, 50)]),
                  LineString([(0, 500), (200, 500)])], crs=PROJECTED_CRS)


def toy_segments():
    geoms = [LineString([(0, 8), (200, 8)]), LineString([(0, -8), (200, -8)]),
             LineString([(50, -8), (50, 8)]), LineString([(60, -8), (60, 8)]), LineString([(180, -8), (180, 8)])]
    vols = [100, 100, 200, 300, 50]
    df = gpd.GeoDataFrame({c: vols for c in VOLUME_WEEKDAY + VOLUME_WEEKEND}, geometry=geoms, crs=PROJECTED_CRS)
    return ex.prepare_segments(df)


def test_filter_streets_drops_paths():
    streets = ex.filter_streets(toy_streets())
    assert len(streets) == 2
    assert set(streets['streetwidth']) == {30.0, 36.0}


def test_crosswalks_are_the_segments_that_cross_a_street():
    streets = ex.filter_streets(toy_streets())
    cross = ex.infer_crosswalks(toy_segments(), streets)
    assert sorted(cross['seg_id']) == [2, 3, 4]
    assert set(cross['streetwidth']) == {30.0}


def test_sites_group_nearby_crosswalks():
    streets = ex.filter_streets(toy_streets())
    cross = ex.infer_crosswalks(toy_segments(), streets)
    sites = ex.build_sites(cross, eps_m=25)
    assert len(sites) == 2
    big = sites.sort_values('n_cross').iloc[-1]
    assert big['n_cross'] == 2
    assert big['site_vol'] == 500
    assert big['max_lanes'] == 2
    assert abs(big['x'] - 55) < 1e-6


def test_crash_assignment_and_counts():
    streets = ex.filter_streets(toy_streets())
    sites = ex.build_sites(ex.infer_crosswalks(toy_segments(), streets), eps_m=25)
    pts = ex.site_points(sites)
    crashes = gpd.GeoDataFrame({'year': [2019, 2020, 2021], 'ped_inj': [1, 1, 0], 'ped_kill': [0, 0, 1]},
                               geometry=[Point(58, 2), Point(200, 0), Point(400, 0)], crs=PROJECTED_CRS)
    assigned, share = cr.assign_to_sites(crashes, pts, radius_m=30)
    assert len(assigned) == 2
    assert abs(share - 2 / 3) < 1e-9
    counts = cr.site_counts(assigned, years=[2019, 2020, 2021])
    assert counts['harm'].sum() == 2
    assert counts['y2019'].sum() == 1 and counts['y2020'].sum() == 1 and counts['y2021'].sum() == 0
    assert counts['killed'].sum() == 0


def test_attach_tracts_drops_sites_outside_the_table():
    streets = ex.filter_streets(toy_streets())
    sites = ex.build_sites(ex.infer_crosswalks(toy_segments(), streets), eps_m=25)
    tracts = gpd.GeoDataFrame({'GEOID': ['36061000100', '36047000200']},
                              geometry=[box(0, -50, 100, 50), box(100, -50, 250, 50)], crs=PROJECTED_CRS)
    table = pd.DataFrame({'GEOID': ['36061000100'], 'Poverty_Rate_Percent': [20.0], 'Walk_Share': [10.0],
                          'Transit_Share': [30.0], 'Commercial_Share': [5.0], 'ZCTA_cluster': [1],
                          'Total_Population': [4000]})
    out = ex.attach_tracts(sites, tracts, table)
    assert len(out) == 1
    assert out['county'].iloc[0] == 'Manhattan'


def test_truck_route_flag_reaches_crossings_and_sites():
    streets = ex.filter_streets(toy_streets())
    cross = ex.infer_crosswalks(toy_segments(), streets)
    assert (cross['truck'] == 1).all()
    sites = ex.build_sites(cross, eps_m=25)
    assert (sites['any_truck'] == 1).all()
