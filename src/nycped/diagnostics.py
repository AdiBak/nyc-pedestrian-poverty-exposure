"""Checks a reviewer is likely to ask for. Spatial dependence, street class and truck routes, and error in the ACS poverty rate."""
from __future__ import annotations

import gc

import numpy as np
import pandas as pd
import scipy.sparse as sp
from sklearn.neighbors import NearestNeighbors

from .models import (POVERTY, PRIMARY, design_matrix, fit_poisson, fmt_rr, irls_poisson, poisson_fixed_effects,
                     rhs_for, rr_per10)


def knn_weights(xy: np.ndarray, k: int = 8) -> sp.csr_matrix:
    """Row standardized k nearest neighbor weights."""
    idx = NearestNeighbors(n_neighbors=k + 1).fit(xy).kneighbors(xy, return_distance=False)
    n = len(xy)
    return sp.csr_matrix((np.full(n * k, 1.0 / k), (np.repeat(np.arange(n), k), idx[:, 1:].ravel())), shape=(n, n))


def morans_i(xy: np.ndarray, values, k: int = 8, n_perm: int = 199, seed: int = 0) -> dict:
    """Moran's I with a permutation p value. Near zero means no spatial pattern in the values."""
    z = np.asarray(values, dtype=float)
    z = z - z.mean()
    W = knn_weights(xy, k)
    denom = float((z ** 2).sum())
    obs = float(z @ (W @ z) / denom)
    rng = np.random.default_rng(seed)
    perms = np.array([float((zp := rng.permutation(z)) @ (W @ zp) / denom) for _ in range(n_perm)])
    return {'I': obs, 'expected': -1.0 / (len(z) - 1), 'perm_mean': float(perms.mean()),
            'perm_sd': float(perms.std()), 'p_value': float((1 + (perms >= obs).sum()) / (n_perm + 1))}


def residual_autocorrelation(d: pd.DataFrame, y: str = 'harm', k: int = 8, n_perm: int = 199) -> dict:
    """Moran's I of the primary model's residuals, for sites and for tracts."""
    res = fit_poisson(d, y, rhs_for(PRIMARY))
    mu = np.asarray(res.mu)
    yy = d[y].values.astype(float)
    del res
    gc.collect()
    out = {'sites': morans_i(d[['x', 'y']].values, (yy - mu) / np.sqrt(mu), k, n_perm)}
    t = d.assign(r=yy - mu).groupby('GEOID').agg(r=('r', 'sum'), x=('x', 'mean'), y=('y', 'mean'))
    out['tracts'] = morans_i(t[['x', 'y']].values, t['r'].values, k, n_perm)
    return out


def grid_cells(d: pd.DataFrame, size_m: float) -> pd.Series:
    gx = np.floor(d['x'] / size_m).astype(int).astype(str)
    gy = np.floor(d['y'] / size_m).astype(int).astype(str)
    return gx + '_' + gy


def clustering_sensitivity(d: pd.DataFrame, y: str = 'harm') -> pd.DataFrame:
    """The primary poverty ratio with standard errors clustered at different spatial scales."""
    keys = {'ZIP area (primary)': d['ZCTA_cluster'].astype(str), 'tract': d['GEOID'],
            '1 km grid cell': grid_cells(d, 1000), '2 km grid cell': grid_cells(d, 2000),
            '4 km grid cell': grid_cells(d, 4000)}
    rows = []
    for label, g in keys.items():
        dd = d.assign(_cl=g.values)
        res = fit_poisson(dd, y, rhs_for(PRIMARY), cluster='_cl')
        rr = rr_per10(res)
        rows.append({'clustering': label, 'clusters': int(dd['_cl'].nunique()), 'poverty_rr': fmt_rr(rr),
                     'rr': rr[0], 'lo': rr[1], 'hi': rr[2]})
        del res
        gc.collect()
    return pd.DataFrame(rows)


def block_bootstrap(d: pd.DataFrame, groups, y: str = 'harm', n_boot: int = 300, seed: int = 5) -> dict:
    """Percentile interval for the poverty ratio from resampling whole blocks of sites."""
    yv, Xv, names = design_matrix(d, y, rhs_for(PRIMARY))
    i_pov = names.index(POVERTY)
    codes = pd.factorize(pd.Series(groups).astype(str))[0]
    rows_by = [np.where(codes == g)[0] for g in range(codes.max() + 1)]
    b0 = irls_poisson(Xv, yv, iters=80)
    rng = np.random.default_rng(seed)
    draws = []
    for _ in range(n_boot):
        pick = rng.integers(0, len(rows_by), len(rows_by))
        idx = np.concatenate([rows_by[g] for g in pick])
        try:
            draws.append(irls_poisson(Xv[idx], yv[idx], beta0=b0)[i_pov])
        except np.linalg.LinAlgError:
            continue
    lo, hi = np.percentile(np.exp(10 * np.array(draws)), [2.5, 97.5])
    return {'point': float(np.exp(10 * b0[i_pov])), 'lo': float(lo), 'hi': float(hi), 'blocks': len(rows_by),
            'n_ok': len(draws)}


def zip_fixed_effects(d: pd.DataFrame, y: str = 'harm') -> tuple:
    """Poverty ratio from variation within ZIP areas only. Replaces the borough effects with ZIP area effects."""
    yv, Xv, names = design_matrix(d, y, rhs_for('C + tract controls'))
    keep = [i for i, nme in enumerate(names) if nme != 'Intercept']
    fe = pd.factorize(d['ZCTA_cluster'])[0]
    fit = poisson_fixed_effects(Xv[:, keep], yv, fe)
    j = [names[i] for i in keep].index(POVERTY)
    b, se = fit['beta'][j], fit['se'][j]
    return float(np.exp(10 * b)), float(np.exp(10 * (b - 1.96 * se))), float(np.exp(10 * (b + 1.96 * se)))


def truck_route_check(d: pd.DataFrame, y: str = 'harm') -> pd.DataFrame:
    """Add a truck route flag as a partial stand-in for heavy vehicle traffic, then split by route.

    The flag says whether any street the crosswalks cross is a designated truck route.
    It is a street class proxy, not a measure of vehicle volume.
    """
    base = rhs_for(PRIMARY)
    rows = []
    res = fit_poisson(d, y, base)
    rows.append({'model': 'primary (model D)', 'sites': len(d), 'poverty_rr': fmt_rr(rr_per10(res)),
                 'rr': rr_per10(res)[0], 'lo': rr_per10(res)[1], 'hi': rr_per10(res)[2], 'truck_route_rr': ''})
    res = fit_poisson(d, y, base + ' + any_truck')
    truck = float(np.exp(res.params['any_truck']))
    rows.append({'model': 'plus truck route flag', 'sites': len(d), 'poverty_rr': fmt_rr(rr_per10(res)),
                 'rr': rr_per10(res)[0], 'lo': rr_per10(res)[1], 'hi': rr_per10(res)[2],
                 'truck_route_rr': f'{truck:.2f}'})
    del res
    gc.collect()
    for label, mask in [('sites on no truck route', d['any_truck'] == 0), ('sites on a truck route', d['any_truck'] == 1)]:
        sub = d[mask]
        res = fit_poisson(sub, y, base)
        rows.append({'model': label, 'sites': len(sub), 'poverty_rr': fmt_rr(rr_per10(res)),
                     'rr': rr_per10(res)[0], 'lo': rr_per10(res)[1], 'hi': rr_per10(res)[2], 'truck_route_rr': ''})
        del res
        gc.collect()
    return pd.DataFrame(rows)


def poverty_error_simex(d: pd.DataFrame, moe: pd.DataFrame, z: float = 1.645, lams=(0.5, 1.0, 1.5, 2.0),
                        n_rep: int = 20, seed: int = 2026, y: str = 'harm') -> dict:
    """Sensitivity of the poverty ratio to sampling error in the ACS tract poverty rate.

    moe has columns GEOID and poverty_moe, the ACS 90 percent margin of error in points. Standard errors are
    moe divided by z. Noise is added once per tract, as the error is shared by all sites in a tract, then the
    coefficients are extrapolated back to zero error.
    """
    codes, tracts = pd.factorize(d['GEOID'])
    se = pd.Series(tracts).to_frame('GEOID').merge(moe[['GEOID', 'poverty_moe']], on='GEOID', how='left')
    n_missing = int(se['poverty_moe'].isna().sum())
    se_t = (se['poverty_moe'].fillna(se['poverty_moe'].median()) / z).values
    pov_t = d.groupby('GEOID')[POVERTY].first().reindex(tracts).values
    reliability = float(1 - np.mean(se_t ** 2) / np.var(pov_t, ddof=1))
    tr = d.groupby('GEOID').first().reindex(tracts)
    Z = np.column_stack([np.ones(len(tr)), tr['Walk_Share'], tr['Transit_Share'], tr['Commercial_Share'],
                         pd.get_dummies(tr['county'], drop_first=True).values.astype(float)])
    coef = np.linalg.lstsq(Z, pov_t, rcond=None)[0]
    # Reliability among tracts that look alike on the other controls, which is what the model compares
    cond_rel = float(1 - np.mean(se_t ** 2) / np.var(pov_t - Z @ coef, ddof=Z.shape[1]))
    yv, Xv, names = design_matrix(d, y, rhs_for(PRIMARY))
    i_pov = names.index(POVERTY)
    b0 = irls_poisson(Xv, yv, iters=80)
    b0 = irls_poisson(Xv, yv, beta0=b0)
    rng = np.random.default_rng(seed)
    pts = {0.0: b0[i_pov]}
    for lam in lams:
        acc = []
        for _ in range(n_rep):
            Xs = Xv.copy()
            Xs[:, i_pov] = Xv[:, i_pov] + rng.normal(0, np.sqrt(lam) * se_t)[codes]
            acc.append(irls_poisson(Xs, yv, beta0=b0)[i_pov])
        pts[lam] = float(np.mean(acc))
    L = np.array(sorted(pts))
    v = np.array([pts[k] for k in L])
    return {'reliability': reliability, 'conditional_reliability': cond_rel, 'tracts': len(tracts),
            'tracts_missing_moe': n_missing,
            'mean_se_points': float(se_t.mean()), 'naive_rr': float(np.exp(10 * b0[i_pov])),
            'simex_quadratic_rr': float(np.exp(10 * np.polyval(np.polyfit(L, v, 2), -1.0))),
            'simex_linear_rr': float(np.exp(10 * np.polyval(np.polyfit(L, v, 1), -1.0)))}
