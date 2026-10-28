# Developed and run in Google Colab, as a cell of the project notebook.
# See README.md for the run order and for what each script needs.

# Robust refit of the crossing site models, reading the table saved by the previous cell.
# Poisson with cluster robust standard errors is the primary estimator. It stays consistent under
# overdispersion, and the negative binomial GLM with a moment based alpha is a cross check.
# Run in the Colab sandbox or any session with Drive mounted. Needs statsmodels.

# %% G1. Site level models, robust estimators
import warnings
import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from google.colab import drive

warnings.filterwarnings('ignore')
drive.mount('/content/drive')
DRIVE_DIR = '/content/drive/MyDrive/TDSP/nyc_walks'
df = pd.read_csv(f'{DRIVE_DIR}/crossing_sites_model_data.csv', dtype={'GEOID': str})
print(df.shape)

for c in ['Walk_Share', 'Transit_Share', 'Commercial_Share', 'n_cross']:
    df[c + '_z'] = (df[c] - df[c].mean()) / df[c].std()
groups = pd.factorize(df['ZCTA_cluster'])[0]

design = 'log_vol + width10 + lanes + speed5'
ctrl = ' + n_cross_z + Walk_Share_z + Transit_Share_z + Commercial_Share_z'
specs = {
    'A volume only': 'log_vol',
    'B + street design': design,
    'C + crosswalks per site, tract controls': design + ctrl,
    'D + borough effects': design + ctrl + ' + C(county)',
}


def rr(res, term='Poverty_Rate_Percent'):
    lo, hi = res.conf_int().loc[term]
    return f"{np.exp(10 * res.params[term]):.2f} ({np.exp(10 * lo):.2f} to {np.exp(10 * hi):.2f})"


def fit_pois(f, data, groups_, y='harm_crashes'):
    model = smf.glm(f'{y} ~ Poverty_Rate_Percent + {f}', data=data, family=sm.families.Poisson())
    return model.fit(cov_type='cluster', cov_kwds={'groups': groups_})


def fit_nbglm(pres, f, data, groups_, y='harm_crashes'):
    mu = np.asarray(pres.mu)
    yy = data[y].values
    ystar = ((yy - mu) ** 2 - yy) / mu
    alpha = max(float((mu * ystar).sum() / (mu * mu).sum()), 1e-6)
    model = smf.glm(f'{y} ~ Poverty_Rate_Percent + {f}', data=data,
                    family=sm.families.NegativeBinomial(alpha=alpha))
    return model.fit(cov_type='cluster', cov_kwds={'groups': groups_}), alpha


rows, pfits = [], {}
for k, f in specs.items():
    p = fit_pois(f, df, groups)
    pfits[k] = p
    nbres, alpha = fit_nbglm(p, f, df, groups)
    rows.append({'model': k, 'Poisson_robust_RR': rr(p), 'NB_RR': rr(nbres),
                 'alpha_hat': round(alpha, 2), 'vol_elasticity': round(p.params['log_vol'], 2)})
print('\nPoverty rate ratio per +10 points, cluster robust by ZIP area')
print(pd.DataFrame(rows).to_string(index=False))

pD = pfits['D + borough effects']
ci = pD.conf_int()
tab = pd.DataFrame({'RR': np.exp(pD.params), 'lo': np.exp(ci[0]), 'hi': np.exp(ci[1]), 'p': pD.pvalues}).round(3)
print('\nModel D rate ratios per unit. _z terms are per 1 SD, width10 per 10 ft, speed5 per 5 mph.')
print(tab.drop(index='Intercept').to_string())
print('log_vol elasticity:', round(pD.params['log_vol'], 2))

lnA = pfits['A volume only'].params['Poverty_Rate_Percent']
print('\nHow much of the poverty gap each block of controls absorbs')
for k in specs:
    b = pfits[k].params['Poverty_Rate_Percent']
    print(f"  {k}: log RR per +10 = {10 * b:.3f} ({100 * (1 - b / lnA):.0f}% smaller than A)")

# Robustness
cut = df['harm_crashes'].quantile(0.99)
sub = df[df['harm_crashes'] <= cut].copy()
g2 = pd.factorize(sub['ZCTA_cluster'])[0]
fD = specs['D + borough effects']
print(f'\nRobustness for model D (top 1% cutoff is {cut:.0f} crashes)')
print('  drop top 1% of sites:', rr(fit_pois(fD, sub, g2)), '| sites:', len(sub))
print('  pedestrians injured:', rr(fit_pois(fD, df, groups, y='ped_injured')))
print('  pedestrians killed:', rr(fit_pois(fD, df, groups, y='ped_killed')),
      '| deaths in sample:', int(df['ped_killed'].sum()))

# Does the poverty gap change with volume or street width?
dd = df.copy()
dd['vol_c'] = dd['log_vol'] - dd['log_vol'].mean()
dd['wid_c'] = dd['width10'] - dd['width10'].mean()
fi = fD + ' + Poverty_Rate_Percent:vol_c + Poverty_Rate_Percent:wid_c'
pi = smf.glm(f'harm_crashes ~ Poverty_Rate_Percent + {fi}', data=dd,
             family=sm.families.Poisson()).fit(cov_type='cluster', cov_kwds={'groups': groups})
for t in ['Poverty_Rate_Percent:vol_c', 'Poverty_Rate_Percent:wid_c']:
    lo, hi = pi.conf_int().loc[t]
    print(f'  interaction {t}: coef {pi.params[t]:.4f} ({lo:.4f} to {hi:.4f}), p = {pi.pvalues[t]:.3f}')
