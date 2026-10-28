"""Robustness checks: measurement error in the volumes, time periods and leaving out boroughs."""
from __future__ import annotations

import gc

import numpy as np
import pandas as pd

from .models import POVERTY, PRIMARY, design_matrix, fit_poisson, irls_poisson, rhs_for, rr_per10, fmt_rr


def simex(d: pd.DataFrame, y: str = 'harm', reliabilities=(0.95, 0.9, 0.8, 0.7), lams=(0.5, 1.0, 1.5, 2.0),
          n_rep: int = 12, seed: int = 2026) -> pd.DataFrame:
    """Simulation extrapolation for classical error in log volume.

    For an assumed reliability, extra noise is added at several multiples of the error variance,
    the model is refit, and coefficients are extrapolated back to zero error. Read the result as a
    plausible range. Model predictions often behave like Berkson error, which does not bias the
    volume coefficient.
    """
    yv, Xv, names = design_matrix(d, y, rhs_for(PRIMARY))
    i_pov, i_vol = names.index(POVERTY), names.index('log_vol')
    var_obs = float(d['log_vol'].var())
    b0 = irls_poisson(Xv, yv, iters=80)
    b0 = irls_poisson(Xv, yv, beta0=b0)
    naive = (b0[i_pov], b0[i_vol])
    rng = np.random.default_rng(seed)
    rows = []
    for rel in reliabilities:
        s2 = (1 - rel) * var_obs
        pts = {0.0: naive}
        for lam in lams:
            acc = []
            for _ in range(n_rep):
                Xs = Xv.copy()
                Xs[:, i_vol] = Xv[:, i_vol] + rng.normal(0, np.sqrt(lam * s2), len(Xv))
                bs = irls_poisson(Xs, yv, beta0=b0)
                acc.append((bs[i_pov], bs[i_vol]))
            pts[lam] = tuple(np.mean(acc, axis=0))
        L = np.array(sorted(pts))
        pov = np.array([pts[k][0] for k in L])
        vol = np.array([pts[k][1] for k in L])
        rows.append({
            'assumed_reliability': rel,
            'poverty_rr_naive': float(np.exp(10 * naive[0])),
            'poverty_rr_simex_quadratic': float(np.exp(10 * np.polyval(np.polyfit(L, pov, 2), -1.0))),
            'poverty_rr_simex_linear': float(np.exp(10 * np.polyval(np.polyfit(L, pov, 1), -1.0))),
            'elasticity_naive': float(naive[1]),
            'elasticity_simex_quadratic': float(np.polyval(np.polyfit(L, vol, 2), -1.0)),
        })
    return pd.DataFrame(rows)


def by_period(d: pd.DataFrame, years, outcome: str = 'harm') -> pd.DataFrame:
    """Poverty rate ratio for 2019 to 2021, 2022 to 2023 and each year."""
    pref = 'y' if outcome == 'harm' else 'k'
    targets = [('2019 to 2021', f'{pref}_early'), ('2022 to 2023', f'{pref}_late')]
    targets += [(str(yr), f'{pref}{yr}') for yr in years]
    rows = []
    for label, col in targets:
        res = fit_poisson(d, col, rhs_for(PRIMARY))
        rr = rr_per10(res)
        del res
        gc.collect()  # free the large statsmodels result before the next fit
        rows.append({'period': label, 'events': int(d[col].sum()), 'poverty_rr': fmt_rr(rr), 'rr': rr[0]})
    return pd.DataFrame(rows)


def leave_one_borough_out(d: pd.DataFrame, y: str = 'harm') -> pd.DataFrame:
    rows = []
    for name in sorted(d['county'].dropna().unique()):
        sub = d[d['county'] != name].copy()
        res = fit_poisson(sub, y, rhs_for(PRIMARY))
        rr = rr_per10(res)
        del res
        gc.collect()
        rows.append({'without': name, 'sites': len(sub), 'events': int(sub[y].sum()),
                     'poverty_rr': fmt_rr(rr), 'rr': rr[0]})
    return pd.DataFrame(rows)
