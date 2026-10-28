import numpy as np
import pandas as pd

from nycped import models as m
from nycped import robustness as rb
from nycped.config import NYC_COUNTIES


def simulate(n=8000, seed=1, beta_pov=0.015):
    rng = np.random.default_rng(seed)
    d = pd.DataFrame({
        'Poverty_Rate_Percent': rng.uniform(0, 50, n),
        'log_vol': rng.normal(6, 1, n),
        'width10': rng.normal(4, 0.8, n),
        'lanes': rng.integers(1, 5, n).astype(float),
        'speed5': 5 + rng.normal(0, 0.1, n),
        'n_cross': rng.integers(1, 5, n).astype(float),
        'Walk_Share': rng.uniform(0, 30, n),
        'Transit_Share': rng.uniform(0, 60, n),
        'Commercial_Share': rng.uniform(0, 40, n),
        'county': rng.choice(list(NYC_COUNTIES.values()), n),
        'ZCTA_cluster': rng.integers(0, 60, n),
    })
    mu = np.exp(-6 + beta_pov * d['Poverty_Rate_Percent'] + 0.8 * d['log_vol'] + 0.2 * d['width10'] + 0.05 * d['lanes'])
    d['harm'] = rng.poisson(mu)
    d['killed'] = rng.poisson(mu * 0.05)
    return m.prepare_frame(d)


def test_poisson_recovers_the_poverty_effect():
    d = simulate()
    rr, lo, hi = m.rr_per10(m.fit_poisson(d, 'harm', m.rhs_for(m.PRIMARY)))
    assert abs(rr - np.exp(0.15)) < 0.03
    assert lo < np.exp(0.15) < hi


def test_negative_binomial_agrees_with_poisson_on_poisson_data():
    d = simulate()
    p = m.rr_per10(m.fit_poisson(d, 'harm', m.rhs_for(m.PRIMARY)))[0]
    nb, alpha = m.fit_nb_glm(d, 'harm', m.rhs_for(m.PRIMARY))
    assert abs(m.rr_per10(nb)[0] - p) < 0.02
    assert alpha < 0.2


def test_ladder_has_four_models():
    d = simulate(n=3000)
    lad = m.ladder(d, 'harm')
    assert list(lad['model']) == list(m.SPECS)
    assert (lad['rr'] > 1.0).all()


def test_frequency_and_severity_multiply_to_the_total():
    d = simulate(n=12000, seed=3)
    fs = m.frequency_severity(d)
    assert abs(fs['frequency'][0] * fs['severity'][0] - fs['total'][0]) < 0.06


def test_cluster_bootstrap_interval_contains_the_estimate():
    d = simulate(n=4000, seed=2)
    b = m.cluster_bootstrap(d, 'harm', n_boot=80, seed=1)
    assert b['lo'] < b['point'] < b['hi']
    assert b['n_ok'] > 70


def test_irls_matches_statsmodels():
    d = simulate(n=3000, seed=4)
    y, X, names = m.design_matrix(d, 'harm', m.rhs_for('B + street design'))
    beta = m.irls_poisson(X, y, iters=80)
    res = m.fit_poisson(d, 'harm', m.rhs_for('B + street design'))
    assert abs(beta[names.index(m.POVERTY)] - res.params[m.POVERTY]) < 1e-5


def test_simex_moves_the_volume_elasticity_toward_the_truth():
    rng = np.random.default_rng(5)
    d = simulate(n=20000, seed=5)
    truth = d['log_vol'].copy()
    mu = np.exp(-6 + 0.015 * d['Poverty_Rate_Percent'] + 0.8 * truth + 0.2 * d['width10'] + 0.05 * d['lanes'])
    d['harm'] = rng.poisson(mu)
    var_true = truth.var()
    noise_var = var_true * 0.25  # reliability 0.8
    d['log_vol'] = truth + rng.normal(0, np.sqrt(noise_var), len(d))
    out = rb.simex(d, 'harm', reliabilities=(0.8,), n_rep=6)
    naive, corrected = out['elasticity_naive'].iloc[0], out['elasticity_simex_quadratic'].iloc[0]
    assert naive < 0.8
    assert abs(corrected - 0.8) < abs(naive - 0.8)


def test_leave_one_borough_out_covers_each_borough():
    d = simulate(n=4000, seed=6)
    out = rb.leave_one_borough_out(d, 'harm')
    assert sorted(out['without']) == sorted(NYC_COUNTIES.values())
