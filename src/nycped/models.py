"""Site level count models. Poisson with cluster robust errors is the primary estimator."""
from __future__ import annotations

import gc

import numpy as np
import pandas as pd
import patsy
import statsmodels.api as sm
import statsmodels.formula.api as smf

POVERTY = 'Poverty_Rate_Percent'
DESIGN = 'log_vol + width10 + lanes + speed5'
CONTROLS = ' + n_cross_z + Walk_Share_z + Transit_Share_z + Commercial_Share_z'
SPECS = {
    'A volume only': 'log_vol',
    'B + street design': DESIGN,
    'C + tract controls': DESIGN + CONTROLS,
    'D + borough (primary)': DESIGN + CONTROLS + ' + C(county)',
}
PRIMARY = 'D + borough (primary)'
CLUSTER = 'ZCTA_cluster'


def rhs_for(spec: str) -> str:
    return f'{POVERTY} + {SPECS[spec]}'


def prepare_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Rename older column names and add any model variable that is missing."""
    d = df.copy()
    rename = {'harm_crashes': 'harm', 'ped_killed': 'killed', 'ped_injured': 'injured'}
    d = d.rename(columns={k: v for k, v in rename.items() if k in d.columns and v not in d.columns})
    if 'log_vol' not in d:
        d['log_vol'] = np.log(d['site_vol'].clip(lower=1))
    if 'width10' not in d:
        d['width10'] = d['max_width'] / 10
    if 'speed5' not in d:
        d['speed5'] = d['max_speed'] / 5
    if 'lanes' not in d:
        d['lanes'] = d['max_lanes']
    for c in ['Walk_Share', 'Transit_Share', 'Commercial_Share', 'n_cross']:
        if c + '_z' not in d:
            d[c + '_z'] = (d[c] - d[c].mean()) / d[c].std()
    for pref in ('y', 'k'):  # early and late period totals from the per-year counts, when present
        years = sorted(int(c[1:]) for c in d.columns if c.startswith(pref) and c[1:].isdigit())
        if years and f'{pref}_early' not in d:
            d[f'{pref}_early'] = d[[f'{pref}{y}' for y in years if y <= 2021]].sum(axis=1)
            d[f'{pref}_late'] = d[[f'{pref}{y}' for y in years if y >= 2022]].sum(axis=1)
    return d


def fit_poisson(d: pd.DataFrame, y: str, rhs: str, offset=None, cluster: str = CLUSTER):
    groups = pd.factorize(d[cluster])[0]
    model = smf.glm(f'{y} ~ {rhs}', data=d, family=sm.families.Poisson(), offset=offset)
    return model.fit(cov_type='cluster', cov_kwds={'groups': groups})


def fit_nb_glm(d: pd.DataFrame, y: str, rhs: str, cluster: str = CLUSTER):
    """Negative binomial GLM with alpha from the moment estimator on the Poisson fit."""
    pois = fit_poisson(d, y, rhs, cluster=cluster)
    mu = np.asarray(pois.mu)
    yy = d[y].values
    alpha = max(float((mu * (((yy - mu) ** 2 - yy) / mu)).sum() / (mu * mu).sum()), 1e-6)
    groups = pd.factorize(d[cluster])[0]
    model = smf.glm(f'{y} ~ {rhs}', data=d, family=sm.families.NegativeBinomial(alpha=alpha))
    return model.fit(cov_type='cluster', cov_kwds={'groups': groups}), alpha


def rr_per10(res, term: str = POVERTY):
    """Rate ratio per 10 point increase, with a 95 percent interval. Returns (rr, lo, hi)."""
    lo, hi = res.conf_int().loc[term]
    return float(np.exp(10 * res.params[term])), float(np.exp(10 * lo)), float(np.exp(10 * hi))


def fmt_rr(t) -> str:
    return f'{t[0]:.2f} ({t[1]:.2f} to {t[2]:.2f})'


def ladder(d: pd.DataFrame, y: str = 'harm') -> pd.DataFrame:
    """Models A to D with Poisson and negative binomial estimates of the poverty rate ratio."""
    rows = []
    for spec in SPECS:
        rhs = rhs_for(spec)
        p = fit_poisson(d, y, rhs)
        nb, alpha = fit_nb_glm(d, y, rhs)
        rows.append({'model': spec, 'poisson': fmt_rr(rr_per10(p)), 'negbin': fmt_rr(rr_per10(nb)),
                     'alpha': round(alpha, 2), 'volume_elasticity': round(float(p.params['log_vol']), 2),
                     'rr': rr_per10(p)[0]})
        del p, nb
        gc.collect()  # statsmodels results are large, so free them between specifications
    return pd.DataFrame(rows)


def frequency_severity(d: pd.DataFrame) -> dict:
    """Split the death gap into more harm crashes (frequency) and more fatal crashes (severity)."""
    rhs = rhs_for(PRIMARY)
    freq = fit_poisson(d, 'harm', rhs)
    has = d[d['harm'] > 0].copy()
    sev = fit_poisson(has, 'killed', rhs, offset=np.log(has['harm'].values))
    total = fit_poisson(d, 'killed', rhs)
    return {'frequency': rr_per10(freq), 'severity': rr_per10(sev), 'total': rr_per10(total),
            'sites_with_crash': int(len(has))}


def irls_poisson(X: np.ndarray, y: np.ndarray, beta0=None, iters: int = 40, tol: float = 1e-9) -> np.ndarray:
    """Fast Poisson regression by iteratively reweighted least squares."""
    beta = np.zeros(X.shape[1]) if beta0 is None else np.array(beta0, dtype=float)
    for _ in range(iters):
        eta = X @ beta
        mu = np.exp(np.clip(eta, -20, 20))
        z = eta + (y - mu) / mu
        XtW = X.T * mu
        new = np.linalg.solve(XtW @ X, XtW @ z)
        done = np.max(np.abs(new - beta)) < tol
        beta = new
        if done:
            break
    return beta


def design_matrix(d: pd.DataFrame, y: str, rhs: str):
    yS, XS = patsy.dmatrices(f'{y} ~ {rhs}', d, return_type='dataframe')
    return yS.iloc[:, 0].values.astype(float), XS.values.astype(float), list(XS.columns)


def cluster_bootstrap(d: pd.DataFrame, y: str = 'killed', rhs: str | None = None, n_boot: int = 500,
                      seed: int = 7, cluster: str = CLUSTER) -> dict:
    """Percentile interval for the poverty rate ratio from resampling whole clusters."""
    rhs = rhs or rhs_for(PRIMARY)
    yv, Xv, names = design_matrix(d, y, rhs)
    i_pov = names.index(POVERTY)
    cidx = pd.factorize(d[cluster])[0]
    rows_by_cluster = [np.where(cidx == g)[0] for g in range(cidx.max() + 1)]
    b0 = irls_poisson(Xv, yv, iters=80)
    rng = np.random.default_rng(seed)
    draws = []
    for _ in range(n_boot):
        pick = rng.integers(0, len(rows_by_cluster), len(rows_by_cluster))
        idx = np.concatenate([rows_by_cluster[g] for g in pick])
        try:
            draws.append(irls_poisson(Xv[idx], yv[idx], beta0=b0)[i_pov])
        except np.linalg.LinAlgError:
            continue
    lo, hi = np.percentile(np.exp(10 * np.array(draws)), [2.5, 97.5])
    return {'point': float(np.exp(10 * b0[i_pov])), 'lo': float(lo), 'hi': float(hi), 'n_ok': len(draws),
            'n_clusters': len(rows_by_cluster)}


def poisson_fixed_effects(X: np.ndarray, y: np.ndarray, fe, iters: int = 60, tol: float = 1e-10,
                          small_sample: bool = True) -> dict:
    """Poisson regression with one set of fixed effects, with standard errors clustered on those same groups.

    X must not contain an intercept, because the fixed effects absorb it. The fixed effects are eliminated
    analytically, so memory use stays small even with hundreds of groups. This is the lean route for the
    ZIP area fixed effects check, validated against the dense statsmodels fit in the tests.
    """
    fe = np.asarray(fe)
    n, k = X.shape
    G = int(fe.max()) + 1
    beta = np.zeros(k)
    ybar = np.bincount(fe, weights=y, minlength=G) / np.maximum(np.bincount(fe, minlength=G), 1)
    alpha = np.log(np.maximum(ybar, 1e-3))
    for _ in range(iters):
        eta = X @ beta + alpha[fe]
        mu = np.exp(np.clip(eta, -20, 20))
        z = eta + (y - mu) / mu
        XtWX = (X.T * mu) @ X
        XtWD = np.vstack([np.bincount(fe, weights=mu * X[:, c], minlength=G) for c in range(k)])
        dw = np.bincount(fe, weights=mu, minlength=G)
        XtWz = X.T @ (mu * z)
        DtWz = np.bincount(fe, weights=mu * z, minlength=G)
        S = XtWX - (XtWD / dw) @ XtWD.T
        new_beta = np.linalg.solve(S, XtWz - (XtWD / dw) @ DtWz)
        alpha = (DtWz - XtWD.T @ new_beta) / dw
        done = np.max(np.abs(new_beta - beta)) < tol
        beta = new_beta
        if done:
            break
    mu = np.exp(np.clip(X @ beta + alpha[fe], -20, 20))
    XtWX = (X.T * mu) @ X
    XtWD = np.vstack([np.bincount(fe, weights=mu * X[:, c], minlength=G) for c in range(k)])
    dw = np.bincount(fe, weights=mu, minlength=G)
    S = XtWX - (XtWD / dw) @ XtWD.T
    Sinv = np.linalg.inv(S)
    r = y - mu
    cluster_scores = np.vstack([np.bincount(fe, weights=r * X[:, c], minlength=G) for c in range(k)]).T
    meat = cluster_scores.T @ cluster_scores
    adj = (G / (G - 1)) * ((n - 1) / (n - k - G)) if small_sample else 1.0
    cov = adj * Sinv @ meat @ Sinv
    return {'beta': beta, 'se': np.sqrt(np.diag(cov)), 'groups': G}
