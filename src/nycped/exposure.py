"""Pedestrian exposure: crosswalks inferred from the NYC Walks network, grouped into sites."""
from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN

from .config import NYC_COUNTIES, PROJECTED_CRS, VOLUME_WEEKDAY, VOLUME_WEEKEND, WALKS_MEMBER

TRACT_COLUMNS = ['GEOID', 'Poverty_Rate_Percent', 'Walk_Share', 'Transit_Share', 'Commercial_Share',
                 'ZCTA_cluster', 'Total_Population']


def extract_walks_geojson(zip_path, cache_dir) -> Path:
    """Extract the GeoJSON from the NYC Walks supplementary ZIP once and reuse it."""
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    out = cache_dir / WALKS_MEMBER
    if out.exists():
        return out
    with zipfile.ZipFile(zip_path) as z:
        if WALKS_MEMBER not in z.namelist():
            raise FileNotFoundError(f'{WALKS_MEMBER} not found in {zip_path}: {z.namelist()}')
        with z.open(WALKS_MEMBER) as src, open(out, 'wb') as dst:
            shutil.copyfileobj(src, dst, 1 << 20)
    return out


def prepare_segments(seg: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Project, clean the six peak hour volumes and add mean weekday, weekend and overall volumes."""
    seg = seg.to_crs(PROJECTED_CRS).copy()
    vols = list(VOLUME_WEEKDAY + VOLUME_WEEKEND)
    seg[vols] = seg[vols].fillna(0).clip(lower=0)
    seg['vol_wkdy'] = seg[list(VOLUME_WEEKDAY)].mean(axis=1)
    seg['vol_wknd'] = seg[list(VOLUME_WEEKEND)].mean(axis=1)
    seg['vol_peak'] = seg[vols].mean(axis=1)
    seg = seg.reset_index(drop=True)
    seg['seg_id'] = np.arange(len(seg))
    return seg


def read_walks(geojson_path) -> gpd.GeoDataFrame:
    cols = list(VOLUME_WEEKDAY + VOLUME_WEEKEND)
    return prepare_segments(gpd.read_file(geojson_path, engine='pyogrio', columns=cols))


def filter_streets(cl: gpd.GeoDataFrame, street_types=(1,)) -> gpd.GeoDataFrame:
    """Keep active, vehicular centerlines of the chosen road types, with width, speed and lanes."""
    cl = cl.copy()
    for c in ['rw_type', 'status', 'streetwidth', 'posted_speed', 'number_travel_lanes']:
        cl[c] = pd.to_numeric(cl[c], errors='coerce')
    keep = (cl['status'] == 2) & cl['rw_type'].isin(list(street_types)) & (cl['trafdir'] != 'NV')
    cl['truck'] = cl['truck_route_type'].notna().astype(int) if 'truck_route_type' in cl.columns else 0
    return cl.loc[keep, ['streetwidth', 'posted_speed', 'number_travel_lanes', 'truck', 'geometry']]


STREET_COLUMNS = ['rw_type', 'status', 'trafdir', 'streetwidth', 'posted_speed', 'number_travel_lanes',
                  'truck_route_type']


def read_streets(path, street_types=(1,)) -> gpd.GeoDataFrame:
    """Read only the six centerline columns the analysis uses. The full file has about 60 and is large."""
    cl = gpd.read_file(path, engine='pyogrio', columns=STREET_COLUMNS)
    return filter_streets(cl.to_crs(PROJECTED_CRS), street_types)


def infer_crosswalks(seg: gpd.GeoDataFrame, streets: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """A crosswalk is a pedestrian segment that crosses a street centerline.

    A segment that meets several streets takes the attributes of the widest one.
    """
    hit = gpd.sjoin(seg[['seg_id', 'geometry']], streets, how='inner', predicate='intersects')
    widest = (hit.sort_values('streetwidth', ascending=False, na_position='last')
              .drop_duplicates('seg_id')[['seg_id', 'streetwidth', 'posted_speed', 'number_travel_lanes']])
    cross = seg.merge(widest, on='seg_id', how='inner')
    if 'truck' in hit.columns:  # a crosswalk touches a truck route if any street it crosses is one
        cross = cross.merge(hit.groupby('seg_id')['truck'].max().rename('truck'), left_on='seg_id',
                            right_index=True, how='left')
    return cross


def build_sites(cross: gpd.GeoDataFrame, eps_m: float = 25.0) -> pd.DataFrame:
    """Group crosswalks whose midpoints lie within eps_m into sites, mostly intersections."""
    mid = cross.geometry.interpolate(0.5, normalized=True)
    xy = np.c_[mid.x.values, mid.y.values]
    labels = DBSCAN(eps=eps_m, min_samples=1).fit_predict(xy)
    cr = pd.DataFrame({'site': labels, 'x': xy[:, 0], 'y': xy[:, 1], 'vol_peak': cross['vol_peak'].values,
                       'w': cross['streetwidth'].values, 's': cross['posted_speed'].values,
                       'l': cross['number_travel_lanes'].values})
    named = dict(n_cross=('vol_peak', 'size'), site_vol=('vol_peak', 'sum'), max_width=('w', 'max'),
                 max_speed=('s', 'max'), max_lanes=('l', 'max'), x=('x', 'mean'), y=('y', 'mean'))
    if 'truck' in cross.columns:
        cr['truck'] = cross['truck'].values
        named['any_truck'] = ('truck', 'max')
    return cr.groupby('site').agg(**named).reset_index()


def site_points(sites: pd.DataFrame) -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(sites[['site']].copy(), geometry=gpd.points_from_xy(sites['x'], sites['y']),
                            crs=PROJECTED_CRS)


def attach_tracts(sites: pd.DataFrame, tracts: gpd.GeoDataFrame, tract_table: pd.DataFrame) -> pd.DataFrame:
    """Give each site its tract and the tract's poverty, commuting and land use measures.

    Sites in tracts that are not in the tract table are dropped.
    """
    tr = tracts.to_crs(PROJECTED_CRS)[['GEOID', 'geometry']]
    joined = gpd.sjoin(site_points(sites), tr, how='left', predicate='within')
    joined = joined[~joined.index.duplicated(keep='first')]
    out = sites.copy()
    out['GEOID'] = joined['GEOID'].values
    cols = [c for c in TRACT_COLUMNS if c in tract_table.columns]
    out = out.merge(tract_table[cols], on='GEOID', how='inner')
    out['county'] = out['GEOID'].str[2:5].map(NYC_COUNTIES)
    return out


def read_nyc_tracts(zip_path) -> gpd.GeoDataFrame:
    tr = gpd.read_file(zip_path)
    return tr[tr['COUNTYFP'].isin(NYC_COUNTIES)][['GEOID', 'COUNTYFP', 'geometry']]
