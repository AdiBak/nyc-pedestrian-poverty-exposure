"""Pedestrian harm crashes and their assignment to sites.

Input is a small table made once from the NYC crash data, with columns year, lat, lon, ped_inj, ped_kill.
Script scripts/00_export_processed_inputs.py writes it from the Milestone 5 session.
"""
from __future__ import annotations

import geopandas as gpd
import numpy as np
import pandas as pd

from .config import GEOGRAPHIC_CRS, PROJECTED_CRS

REQUIRED = ['year', 'lat', 'lon', 'ped_inj', 'ped_kill']


def to_points(df: pd.DataFrame) -> gpd.GeoDataFrame:
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise ValueError(f'crash table is missing columns {missing}')
    return gpd.GeoDataFrame(df[['year', 'ped_inj', 'ped_kill']].reset_index(drop=True),
                            geometry=gpd.points_from_xy(df['lon'], df['lat']), crs=GEOGRAPHIC_CRS).to_crs(PROJECTED_CRS)


def load_ped_harm_crashes(path) -> gpd.GeoDataFrame:
    return to_points(pd.read_csv(path))


def assign_to_sites(crash_pts: gpd.GeoDataFrame, site_pts: gpd.GeoDataFrame, radius_m: float = 30.0):
    """Assign each crash to the nearest site within radius_m. Returns the assigned crashes and the share assigned."""
    near = gpd.sjoin_nearest(crash_pts, site_pts[['site', 'geometry']], how='left', max_distance=radius_m)
    near = near[~near.index.duplicated(keep='first')]
    ok = near[near['site'].notna()]
    return ok, len(ok) / max(len(crash_pts), 1)


def site_counts(assigned: pd.DataFrame, years) -> pd.DataFrame:
    """Harm crashes and deaths per site, in total and by year (columns y2019... and k2019...)."""
    tot = assigned.groupby('site').agg(harm=('site', 'size'), killed=('ped_kill', 'sum'))
    hy = assigned.groupby(['site', 'year']).size().unstack(fill_value=0)
    ky = assigned.groupby(['site', 'year'])['ped_kill'].sum().unstack(fill_value=0)
    out = tot.copy()
    for yr in years:
        out[f'y{yr}'] = hy[yr] if yr in hy.columns else 0
        out[f'k{yr}'] = ky[yr] if yr in ky.columns else 0
    return out.fillna(0)
