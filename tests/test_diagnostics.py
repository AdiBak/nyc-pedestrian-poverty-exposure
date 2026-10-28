import numpy as np
import pandas as pd

from nycped import diagnostics as dg
from nycped import models as m
from nycped.config import NYC_COUNTIES


def simulate_sites(n_tracts=400, per=20, seed=1, beta_pov=0.015, truck_effect=0.0, pov_noise_se=0.0):
    rng = np.random.default_rng(seed)
    n = n_tracts * per
    tract = np.repeat(np.arange(n_tracts), per)
    pov_true = rng.uniform(0, 45, n_tracts)
    zip_of_tract = rng.integers(0, 40, n_tracts)
    county_of_tract = rng.choice(list(NYC_COUNTIES.values()), n_tracts)
    tx, ty = rng.uniform(0, 20000, n_tracts), rng.uniform(0, 20000, n_tracts)
    d = pd.DataFrame({
        'GEOID': [f'3600{t:07d}' for t in tract],
        'x': tx[tract] + rng.normal(0, 150, n), 'y': ty[tract] + rng.normal(0, 150, n),
        'ZCTA_cluster': zip_of_tract[tract], 'county': county_of_tract[tract],
        'log_vol': rng.normal(6, 1, n), 'width10': rng.normal(4, 0.8, n),
        'lanes': rng.integers(1, 5, n).astype(float), 'speed5': 5 + rng.normal(0, 0.1, n),
        'n_cross': rng.integers(1, 5, n).astype(float), 'any_truck': rng.integers(0, 2, n),
        'Walk_Share': rng.uniform(0, 30, n)[tract] * 0 + rng.uniform(0, 30, n_tracts)[tract],
        'Transit_Share': rng.uniform(0, 60, n_tracts)[tract], 'Commercial_Share': rng.uniform(0, 40, n_tracts)[tract],
    })
    mu = np.exp(-6 + beta_pov * pov_true[tract] + 0.8 * d['log_vol'] + 0.2 * d['width10'] + 0.05 * d['lanes']
                + truck_effect * d['any_truck'])
    d['harm'] = rng.poisson(mu)
    pov_obs = pov_true + rng.normal(0, pov_noise_se, n_tracts) if pov_noise_se else pov_true
    d['Poverty_Rate_Percent'] = pov_obs[tract]
    return m.prepare_frame(d), pov_true, pov_noise_se


def test_knn_weights_rows_sum_to_one():
    rng = np.random.default_rng(0)
    W = dg.knn_weights(rng.uniform(0, 100, (200, 2)), k=6)
    assert np.allclose(np.asarray(W.sum(axis=1)).ravel(), 1.0)


def test_morans_i_separates_pattern_from_noise():
    rng = np.random.default_rng(1)
    xy = rng.uniform(0, 100, (1500, 2))
    smooth = np.sin(xy[:, 0] / 12) + np.cos(xy[:, 1] / 15) + rng.normal(0, 0.2, 1500)
    pattern = dg.morans_i(xy, smooth, n_perm=99)
    noise = dg.morans_i(xy, rng.normal(size=1500), n_perm=99)
    assert pattern['I'] > 0.5 and pattern['p_value'] <= 0.02
    assert abs(noise['I']) < 0.06 and noise['p_value'] > 0.02


def test_residuals_from_a_correct_model_are_not_spatially_clustered():
    d, _, _ = simulate_sites(seed=2)
    out = dg.residual_autocorrelation(d, n_perm=49)
    assert abs(out['sites']['I']) < 0.05


def test_clustering_sensitivity_returns_five_rows_with_similar_estimates():
    d, _, _ = simulate_sites(seed=3)
    cs = dg.clustering_sensitivity(d)
    assert len(cs) == 5
    assert cs['rr'].max() - cs['rr'].min() < 1e-6 or cs['rr'].nunique() == 1


def test_block_bootstrap_and_zip_fixed_effects_run():
    d, _, _ = simulate_sites(n_tracts=250, per=12, seed=4)
    bb = dg.block_bootstrap(d, dg.grid_cells(d, 2000), n_boot=60)
    assert bb['lo'] < bb['point'] < bb['hi']
    rr, lo, hi = dg.zip_fixed_effects(d)
    assert lo < rr < hi


def test_truck_route_check_recovers_the_truck_effect():
    d, _, _ = simulate_sites(seed=5, truck_effect=0.3)
    out = dg.truck_route_check(d)
    assert abs(float(out.loc[out['model'] == 'plus truck route flag', 'truck_route_rr'].iloc[0]) - np.exp(0.3)) < 0.08
    assert len(out) == 4


def test_poverty_error_simex_moves_toward_the_truth():
    d, pov_true, se = simulate_sites(n_tracts=500, per=20, seed=6, beta_pov=0.02, pov_noise_se=6.0)
    moe = pd.DataFrame({'GEOID': d.drop_duplicates('GEOID')['GEOID'], 'poverty_moe': 1.645 * se})
    out = dg.poverty_error_simex(d, moe, n_rep=8)
    truth = float(np.exp(0.2))
    assert out['naive_rr'] < truth
    assert abs(out['simex_quadratic_rr'] - truth) < abs(out['naive_rr'] - truth)
    assert 0.5 < out['reliability'] < 0.95


def test_lean_fixed_effects_matches_statsmodels():
    import statsmodels.api as sm
    import statsmodels.formula.api as smf
    d, _, _ = simulate_sites(n_tracts=120, per=10, seed=7)
    d = d.assign(zip_code=d['ZCTA_cluster'])
    rhs = 'Poverty_Rate_Percent + log_vol + width10 + lanes + speed5 + n_cross_z + Walk_Share_z + C(zip_code) - 1'
    groups = pd.factorize(d['zip_code'])[0]
    dense = smf.glm(f'harm ~ {rhs}', data=d, family=sm.families.Poisson()).fit(
        cov_type='cluster', cov_kwds={'groups': groups, 'use_correction': False})
    cols = ['Poverty_Rate_Percent', 'log_vol', 'width10', 'lanes', 'speed5', 'n_cross_z', 'Walk_Share_z']
    lean = m.poisson_fixed_effects(d[cols].values, d['harm'].values.astype(float), groups, small_sample=False)
    assert abs(lean['beta'][0] - dense.params['Poverty_Rate_Percent']) < 1e-6
    assert abs(lean['se'][0] / dense.bse['Poverty_Rate_Percent'] - 1) < 0.02
