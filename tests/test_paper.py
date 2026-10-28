import json

import numpy as np

from nycped import paper
from test_diagnostics import simulate_sites


def test_paper_outputs_are_written_and_consistent(tmp_path):
    d, _, _ = simulate_sites(n_tracts=250, per=12, seed=5, truck_effect=0.3)
    rng = np.random.default_rng(0)
    d['killed'] = rng.poisson(0.05 * d['harm'] + 0.01)
    for yr in range(2019, 2024):
        d[f'y{yr}'] = rng.binomial(d['harm'], 0.2)
    d['y_early'] = d[['y2019', 'y2020', 'y2021']].sum(axis=1)
    d['y_late'] = d[['y2022', 'y2023']].sum(axis=1)
    nums = paper.build_outputs(d, tmp_path, (2019, 2020, 2021, 2022, 2023), draws=2, boot=20, perm=19)
    for name in ['table_main.tex', 'robustness.csv', 'robustness.pdf', 'numbers.json']:
        assert (tmp_path / name).exists()
    tex = (tmp_path / 'table_main.tex').read_text()
    assert tex.count('\\\\') >= 5 and 'D\\quad' in tex
    stored = json.loads((tmp_path / 'numbers.json').read_text())
    assert abs(stored['main']['D + borough (primary)']['harm_poisson'][0]
               - nums['main']['D + borough (primary)']['harm_poisson'][0]) < 1e-9
    assert abs(nums['main']['D + borough (primary)']['harm_poisson'][0] - np.exp(0.15)) < 0.15
