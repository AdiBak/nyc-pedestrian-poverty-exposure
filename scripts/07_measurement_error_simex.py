# Developed and run in Google Colab, as a cell of the project notebook.
# See README.md for the run order and for what each script needs.

# Measurement error sensitivity for the site level model (SIMEX).
# Question: how much could error in the modeled pedestrian volumes move the poverty estimate?
# Needs only crossing_sites_model_data.csv on Drive. Run it in any session with Drive mounted.
#
# Method. Treat observed log volume as true log volume plus classical noise. For an assumed
# reliability (share of variance that is real signal), add extra noise at several multiples of the
# estimated error variance, refit, and extrapolate the coefficients back to zero error.
# Classical error is a worst case. Model predictions often behave more like Berkson error, which
# does not bias the volume coefficient, so read the results as a plausible range, not a correction.

# %% H1. SIMEX sensitivity
import time
import numpy as np
import pandas as pd
import patsy
from google.colab import drive

drive.mount('/content/drive')
DRIVE_DIR = '/content/drive/MyDrive/TDSP/nyc_walks'
df = pd.read_csv(f'{DRIVE_DIR}/crossing_sites_model_data.csv', dtype={'GEOID': str})
for c in ['Walk_Share', 'Transit_Share', 'Commercial_Share', 'n_cross']:
    df[c + '_z'] = (df[c] - df[c].mean()) / df[c].std()

formula = ('harm_crashes ~ Poverty_Rate_Percent + log_vol + width10 + lanes + speed5'
           ' + n_cross_z + Walk_Share_z + Transit_Share_z + Commercial_Share_z + C(county)')
yS, XS = patsy.dmatrices(formula, df, return_type='dataframe')
yv = yS.iloc[:, 0].values.astype(float)
Xv = XS.values.astype(float)
names = list(XS.columns)
i_pov, i_vol = names.index('Poverty_Rate_Percent'), names.index('log_vol')
var_obs = df['log_vol'].var()
t0 = time.time()


def pois_irls(Xm, beta0, iters=30, tol=1e-9):
    beta = beta0.copy()
    for _ in range(iters):
        eta = Xm @ beta
        mu = np.exp(np.clip(eta, -20, 20))
        z = eta + (yv - mu) / mu
        XtW = Xm.T * mu
        new = np.linalg.solve(XtW @ Xm, XtW @ z)
        done = np.max(np.abs(new - beta)) < tol
        beta = new
        if done:
            break
    return beta


b0 = pois_irls(Xv, np.zeros(Xv.shape[1]), iters=80)
b0 = pois_irls(Xv, b0)
naive = (b0[i_pov], b0[i_vol])
print(f'corr(log volume, poverty) across sites: {df["log_vol"].corr(df["Poverty_Rate_Percent"]):.3f}')
print(f'naive fit: poverty RR per +10 = {np.exp(10 * naive[0]):.3f}, volume elasticity = {naive[1]:.2f}')

rng = np.random.default_rng(2026)
LAMS, B = [0.5, 1.0, 1.5, 2.0], 12
rows = []
for rel in [0.95, 0.9, 0.8, 0.7]:
    s2 = (1 - rel) * var_obs
    pts = {0.0: naive}
    for lam in LAMS:
        acc = []
        for _ in range(B):
            Xs = Xv.copy()
            Xs[:, i_vol] = Xv[:, i_vol] + rng.normal(0, np.sqrt(lam * s2), len(Xv))
            bs = pois_irls(Xs, b0)
            acc.append((bs[i_pov], bs[i_vol]))
        pts[lam] = tuple(np.mean(acc, axis=0))
    L = np.array(sorted(pts))
    pov = np.array([pts[k][0] for k in L])
    vol = np.array([pts[k][1] for k in L])
    rows.append({
        'assumed reliability': rel,
        'poverty RR naive': round(np.exp(10 * naive[0]), 3),
        'poverty RR SIMEX quadratic': round(np.exp(10 * np.polyval(np.polyfit(L, pov, 2), -1.0)), 3),
        'poverty RR SIMEX linear': round(np.exp(10 * np.polyval(np.polyfit(L, pov, 1), -1.0)), 3),
        'elasticity naive': round(naive[1], 2),
        'elasticity SIMEX quadratic': round(np.polyval(np.polyfit(L, vol, 2), -1.0), 2),
    })
    print(f'reliability {rel} done after {time.time() - t0:.0f} s')

print('\nPoverty rate ratio per +10 points and volume elasticity after correcting for assumed error')
print(pd.DataFrame(rows).to_string(index=False))
