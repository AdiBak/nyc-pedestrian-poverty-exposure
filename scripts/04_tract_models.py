# Developed and run in Google Colab, as a cell of the project notebook.
# See README.md for the run order and for what each script needs.

# Merge crossing exposure onto the Milestone 5 tract table and refit the poverty models.
# Run in the TDSP Research Sandbox after the Milestone 1 and Milestone 5 cells.
# Uses these names from your session: tract_table, HEADLINE_YEARS, CONTROLS, tracts, smf, np, pd.

# %% E1. Merge exposure, check that the volumes are plausible, then fit the models
import warnings
import numpy as np
import pandas as pd

warnings.filterwarnings('ignore')

DRIVE_DIR = '/content/drive/MyDrive/TDSP/nyc_walks'
expo = pd.read_csv(f'{DRIVE_DIR}/tract_crossing_exposure_2018_2019_volumes.csv', dtype={'GEOID': str})

base = tract_table(HEADLINE_YEARS, 'local')
keep = ['GEOID', 'county', 'n_crossings', 'cross_vol_peak', 'mean_cross_vol',
        'wtd_speed_mph', 'wtd_street_width_ft']
m = base.merge(expo[keep], on='GEOID', how='inner')
print(f'tracts in the Milestone 5 table: {len(base)}, with crossing exposure: {len(m)}')

tr = tracts.to_crs(6538)
tr['area_km2'] = tr.geometry.area / 1e6
m = m.merge(tr[['GEOID', 'area_km2']], on='GEOID', how='left')
m['density'] = m['Total_Population'] / m['area_km2']
m['log_pop'] = np.log(m['Total_Population'])
m['log_cross'] = np.log(m['cross_vol_peak'])

# 1. Are the modeled volumes plausible? Compare them with density and ACS walking share.
print('\n1. Plausibility of the modeled volumes')
by = m.groupby('county').agg(
    tracts=('GEOID', 'size'),
    median_crossings=('n_crossings', 'median'),
    median_vol_per_crossing=('mean_cross_vol', 'median'),
    median_walk_share=('Walk_Share', 'median'),
    median_density=('density', 'median'))
print(by.round(1).to_string())
for col in ['density', 'Walk_Share', 'Poverty_Rate_Percent']:
    rho = m['mean_cross_vol'].corr(m[col], method='spearman')
    print(f'Spearman, volume per crossing vs {col}: {rho:.2f}')
rho = m['cross_vol_peak'].corr(m['Poverty_Rate_Percent'], method='spearman')
print(f'Spearman, total crossing volume vs poverty rate: {rho:.2f}')


# 2. Models. The exposure function lets each specification choose its own denominator.
def run(d, outcome, terms, expo_fn):
    rhs = ' + '.join(['Poverty_Rate_Percent'] + terms)
    model = smf.negativebinomial(f'{outcome} ~ {rhs}', data=d, exposure=expo_fn(d))
    groups = pd.factorize(d['ZCTA_cluster'])[0]
    return model.fit(disp=0, maxiter=500, cov_type='cluster', cov_kwds={'groups': groups})


def rr(fit, term='Poverty_Rate_Percent'):
    lo, hi = fit.conf_int().loc[term]
    return f'{np.exp(10 * fit.params[term]):.2f} ({np.exp(10 * lo):.2f} to {np.exp(10 * hi):.2f})'


def coef(fit, term):
    lo, hi = fit.conf_int().loc[term]
    return f'{fit.params[term]:.2f} ({lo:.2f} to {hi:.2f})'


pop_exp = lambda d: d['Total_Population'] * d['n_years']
cross_exp = lambda d: d['cross_vol_peak'] * d['n_years']
years_exp = lambda d: d['n_years']
no_si = m[m['county'] != 'Staten Island'].copy()
both = CONTROLS + ['log_pop', 'log_cross']

specs = [
    ('1 Residents as exposure, with controls (current)', m, CONTROLS, pop_exp),
    ('2 Residents as exposure, no controls', m, [], pop_exp),
    ('3 Crossing volume as exposure, with controls', m, CONTROLS, cross_exp),
    ('4 Crossing volume as exposure, no controls', m, [], cross_exp),
    ('5 Both as covariates, with controls', m, both, years_exp),
    ('6 Same as 5, plus borough effects', m, both + ['C(county)'], years_exp),
    ('7 Same as 5, Staten Island excluded', no_si, both, years_exp),
]

rows = []
for label, d, terms, expo_fn in specs:
    row = {'model': label, 'tracts': len(d)}
    for outcome, name in [('Ped_Injured', 'injuries'), ('Ped_Killed', 'deaths')]:
        try:
            fit = run(d, outcome, terms, expo_fn)
            row[f'{name}_poverty_RR_per_10'] = rr(fit)
            if 'log_cross' in terms:
                row[f'{name}_elasticity_pop'] = coef(fit, 'log_pop')
                row[f'{name}_elasticity_cross'] = coef(fit, 'log_cross')
        except Exception as e:
            row[f'{name}_poverty_RR_per_10'] = f'failed: {str(e)[:40]}'
    rows.append(row)

res = pd.DataFrame(rows)
pd.set_option('display.width', 250)
pd.set_option('display.max_colwidth', 60)
print('\n2. Poverty rate ratio per +10 points, 95% interval, clustered by ZIP area')
print(res[['model', 'tracts', 'injuries_poverty_RR_per_10', 'deaths_poverty_RR_per_10']].to_string(index=False))
print('\nElasticities in the models with both covariates (a value below 1 means risk per walker falls as volume rises)')
cols = [c for c in res.columns if 'elasticity' in c]
print(res.loc[res[cols[0]].notna(), ['model'] + cols].to_string(index=False))

res.to_csv(f'{DRIVE_DIR}/exposure_model_results.csv', index=False)
print('\nsaved to', f'{DRIVE_DIR}/exposure_model_results.csv')
