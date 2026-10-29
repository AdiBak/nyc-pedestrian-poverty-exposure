"""Write the paper's tables, numbers and robustness figure from a site table.

Every number in the paper comes out of this module, so the text can be traced to code.
Outputs go to one folder: numbers.json, table_main.tex, table_scale.tex, robustness.csv, robustness.pdf.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from . import diagnostics as dg
from . import models as m
from . import robustness as rb
from . import scale as sc


def _ci(t) -> str:
    return f'{t[0]:.2f} ({t[1]:.2f} to {t[2]:.2f})'


def main_table(d: pd.DataFrame) -> tuple[str, dict]:
    """Models A to D for harm crashes (Poisson and negative binomial) and deaths (Poisson)."""
    rows, nums = [], {}
    for spec in m.SPECS:
        rhs = m.rhs_for(spec)
        hp = m.rr_per10(m.fit_poisson(d, 'harm', rhs))
        hn = m.rr_per10(m.fit_nb_glm(d, 'harm', rhs)[0])
        cells = [_ci(hp), _ci(hn)]
        nums[spec] = {'harm_poisson': hp, 'harm_negbin': hn}
        if 'killed' in d:
            dp = m.rr_per10(m.fit_poisson(d, 'killed', rhs))
            cells.append(_ci(dp))
            nums[spec]['deaths_poisson'] = dp
        letter, rest = spec.split(' ', 1)
        rows.append(f'{letter}\\quad {rest} & ' + ' & '.join(cells) + ' \\\\')
    body = '\n'.join(rows)
    tex = ('\\begin{tabular}{lccc}\n\\toprule\nModel & Harm, Poisson & Harm, neg.\\ binomial & Deaths, Poisson \\\\\n'
           f'\\midrule\n{body}\n\\bottomrule\n\\end{{tabular}}\n')
    return tex, nums


def coefficient_numbers(d: pd.DataFrame) -> dict:
    res = m.fit_poisson(d, 'harm', m.rhs_for(m.PRIMARY))
    ci = res.conf_int()
    keep = ['width10', 'lanes', 'speed5', 'n_cross_z', 'Walk_Share_z', 'Transit_Share_z', 'Commercial_Share_z']
    out = {k: [float(np.exp(res.params[k])), float(np.exp(ci.loc[k, 0])), float(np.exp(ci.loc[k, 1]))] for k in keep}
    out['volume_elasticity'] = float(res.params['log_vol'])
    out['sites'] = int(len(d))
    out['harm_crashes'] = int(d['harm'].sum())
    if 'killed' in d:
        out['deaths'] = int(d['killed'].sum())
    return out


def scale_table(t: pd.DataFrame, nbrs: dict, draws: int) -> tuple[str, dict]:
    real = sc.real_scales(t)
    zon = sc.random_zonings(t, nbrs, n_draws=draws, seed=11)
    cols = [('harm', 'residents only'), ('harm', 'residents + volume + design'),
            ('killed', 'residents only'), ('killed', 'residents + volume + design')]
    rows = []
    for scale_name, label in [('tracts', f'Tracts ({int(real[real.scale == "tracts"].zones.iloc[0]):,})'),
                              ('ZIP areas', f'ZIP areas ({int(real[real.scale == "ZIP areas"].zones.iloc[0])})')]:
        cells = []
        for y, form in cols:
            r = real[(real.scale == scale_name) & (real.outcome == y) & (real.model == form)].iloc[0]
            cells.append(_ci((r.rr, r.lo, r.hi)))
        rows.append(f'{label} & ' + ' & '.join(cells) + ' \\\\')
    for k, g in zon.groupby('target_tracts'):
        size = len(t) / g['zones'].iloc[0]
        cells = []
        for y, form in cols:
            cells.append(f"{g[(g.outcome == y) & (g.model == form)]['median'].iloc[0]:.2f}")
        rows.append(f'Random, about {size:.0f} tracts & ' + ' & '.join(cells) + ' \\\\')
    body = '\n'.join(rows)
    tex = ('\\begin{tabular}{lcccc}\n\\toprule\n & \\multicolumn{2}{c}{Harm crashes} & \\multicolumn{2}{c}{Deaths} \\\\\n'
           '\\cmidrule(lr){2-3}\\cmidrule(lr){4-5}\n'
           'Scale & Residents only & With exposure & Residents only & With exposure \\\\\n'
           f'\\midrule\n{body}\n\\bottomrule\n\\end{{tabular}}\n')
    return tex, {'real': real.to_dict('records'), 'random': zon.to_dict('records')}


def robustness_rows(d: pd.DataFrame, years, definitions: dict | None, boot: int, perm: int) -> list[dict]:
    """Rows of (group, label, rr, lo, hi). lo and hi are None when the check reports no interval."""
    rows = []

    def add(group, label, t):
        rows.append({'group': group, 'label': label, 'rr': t[0], 'lo': t[1] if len(t) > 1 else None,
                     'hi': t[2] if len(t) > 1 else None})

    rhs = m.rhs_for(m.PRIMARY)
    add('Estimator and sample', 'Primary (Poisson model D)', m.rr_per10(m.fit_poisson(d, 'harm', rhs)))
    add('Estimator and sample', 'Negative binomial GLM', m.rr_per10(m.fit_nb_glm(d, 'harm', rhs)[0]))
    sub = d[d['harm'] <= d['harm'].quantile(0.99)]
    add('Estimator and sample', 'Drop top 1% of sites', m.rr_per10(m.fit_poisson(sub, 'harm', rhs)))
    if 'injured' in d:
        add('Estimator and sample', 'Outcome: pedestrians injured', m.rr_per10(m.fit_poisson(d, 'injured', rhs)))
    cs = dg.clustering_sensitivity(d)
    r = cs[cs.clustering == 'tract'].iloc[0]
    add('Inference', 'Cluster by tract', (r.rr, r.lo, r.hi))
    bb = dg.block_bootstrap(d, dg.grid_cells(d, 2000), n_boot=boot)
    add('Inference', 'Block bootstrap (2 km)', (bb['point'], bb['lo'], bb['hi']))
    add('Confounding', 'ZIP area fixed effects', dg.zip_fixed_effects(d))
    if 'any_truck' in d:
        tr = dg.truck_route_check(d)
        for label, name in [('plus truck route flag', 'Plus truck route flag'),
                            ('sites on no truck route', 'Sites off truck routes'),
                            ('sites on a truck route', 'Sites on truck routes')]:
            n = tr[tr.model == label].iloc[0]
            add('Confounding', name, (n.rr, n.lo, n.hi))
    for label, t in (definitions or {}).items():
        add('Definitions', label, (t,))
    if 'y_early' in d:
        bp = rb.by_period(d, years, 'harm')
        for _, r in bp.iloc[:2].iterrows():
            add('Time', r.period, (r.rr,))
    lb = rb.leave_one_borough_out(d, 'harm')
    for _, r in lb.iterrows():
        add('Borough left out', f'Without {r.without}', (r.rr,))
    return rows


def draw_robustness(rows: list[dict], path: Path) -> None:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(3.4, 4.3))
    y, last, ticks, labels = len(rows), None, [], []
    for r in rows:
        y -= 1
        if last is not None and r['group'] != last:
            y -= 0.6
        last = r['group']
        if r['lo'] is not None and not pd.isna(r['lo']):
            ax.plot([r['lo'], r['hi']], [y, y], color='0.25', lw=1.6)
            ax.plot(r['rr'], y, 'o', color='0.1', ms=5)
        else:
            ax.plot(r['rr'], y, 'o', mfc='white', mec='0.1', ms=5)
        ticks.append(y)
        labels.append(r['label'])
    ax.axvline(rows[0]['rr'], color='0.6', ls=':', lw=1)
    ax.axvline(1.0, color='0.3', lw=0.8)
    ax.set_yticks(ticks)
    ax.set_yticklabels(labels, fontsize=6.5)
    ax.set_xlabel('Rate ratio per 10 points of poverty', fontsize=8)
    ax.tick_params(axis='x', labelsize=7)
    for side in ('top', 'right'):
        ax.spines[side].set_visible(False)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def observed_over_expected(d: pd.DataFrame, terms: str, n_bins: int = 10, n_boot: int = 300, seed: int = 3) -> pd.DataFrame:
    """Observed over expected harm crashes by poverty decile.

    The expected count comes from a Poisson model that holds the given terms fixed and leaves poverty out.
    A ratio above 1 means the decile has more harm than those terms predict. The ratio is scaled so the
    lowest decile equals 1. Intervals come from resampling ZIP area clusters.
    """
    res = m.fit_poisson(d, 'harm', terms)
    dd = pd.DataFrame({'cl': pd.factorize(d[m.CLUSTER])[0], 'bin': pd.qcut(d[m.POVERTY], n_bins, labels=False, duplicates='drop'),
                       'y': d['harm'].values, 'mu': np.asarray(res.mu), 'pov': d[m.POVERTY].values})
    n_cl, n_b = dd['cl'].max() + 1, dd['bin'].max() + 1
    Y = np.zeros((n_cl, n_b))
    M = np.zeros((n_cl, n_b))
    np.add.at(Y, (dd['cl'].values, dd['bin'].values), dd['y'].values)
    np.add.at(M, (dd['cl'].values, dd['bin'].values), dd['mu'].values)
    oe = Y.sum(0) / M.sum(0)
    rng = np.random.default_rng(seed)
    boots = []
    for _ in range(n_boot):
        w = np.bincount(rng.integers(0, n_cl, n_cl), minlength=n_cl)
        boots.append((w @ Y) / (w @ M))
    boots = np.array(boots)
    base = oe[0]
    base_b = boots[:, 0:1]
    out = pd.DataFrame({'decile': np.arange(1, n_b + 1), 'mean_poverty': dd.groupby('bin')['pov'].mean().values,
                        'ratio': oe / base, 'lo': np.percentile(boots / base_b, 2.5, axis=0),
                        'hi': np.percentile(boots / base_b, 97.5, axis=0)})
    return out


def draw_gradient(curves: dict, path: Path) -> None:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(3.4, 2.9))
    marks = ['o', 's']
    for i, (label, g) in enumerate(curves.items()):
        off = (i - 0.5) * 0.12
        ax.errorbar(g['mean_poverty'] + off, g['ratio'], yerr=[g['ratio'] - g['lo'], g['hi'] - g['ratio']],
                    fmt=marks[i % 2] + '-', ms=3.5, lw=1, capsize=1.5, label=label)
    ax.axhline(1.0, color='0.6', lw=0.8)
    ax.set_xlabel('Tract poverty rate, mean within decile of sites (%)', fontsize=8)
    ax.set_ylabel('Observed over expected harm,\nlowest decile = 1', fontsize=8)
    ax.tick_params(labelsize=7)
    ax.legend(fontsize=7, frameon=False)
    for side in ('top', 'right'):
        ax.spines[side].set_visible(False)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def draw_ladder(main: dict, path: Path) -> None:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    specs = list(main)
    fig, ax = plt.subplots(figsize=(3.4, 2.6))
    for key, label, off, mk in [('harm_poisson', 'Harm crashes', 0.12, 'o'), ('deaths_poisson', 'Deaths', -0.12, 's')]:
        if key not in main[specs[0]]:
            continue
        for i, sp in enumerate(specs):
            rr, lo, hi = main[sp][key]
            ax.plot([lo, hi], [-i + off] * 2, color='0.3', lw=1.3)
            ax.plot(rr, -i + off, mk, color='0.1' if mk == 'o' else '0.5', ms=4, label=label if i == 0 else None)
    ax.axvline(1.0, color='0.6', lw=0.8)
    ax.set_yticks([-i for i in range(len(specs))])
    ax.set_yticklabels([sp.split(' ', 1)[0] + '  ' + sp.split(' ', 1)[1] for sp in specs], fontsize=7)
    ax.set_xlabel('Rate ratio per 10 points of poverty', fontsize=8)
    ax.tick_params(axis='x', labelsize=7)
    ax.legend(fontsize=7, frameon=False, loc='lower center', bbox_to_anchor=(0.5, 1.0), ncol=2)
    for side in ('top', 'right'):
        ax.spines[side].set_visible(False)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def build_outputs(d: pd.DataFrame, out_dir, years, *, nbrs=None, tract_frame=None, poverty_moe=None, definitions=None,
                  draws: int = 100, boot: int = 300, perm: int = 199, seed: int = 2026) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    numbers = {'coefficients': coefficient_numbers(d)}
    tex, nums = main_table(d)
    (out / 'table_main.tex').write_text(tex)
    numbers['main'] = nums
    draw_ladder(nums, out / 'ladder.pdf')
    curves = {'Street design and volume': observed_over_expected(d, m.DESIGN),
              'Plus tract context and borough': observed_over_expected(d, m.DESIGN + m.CONTROLS + ' + C(county)')}
    draw_gradient(curves, out / 'gradient.pdf')
    numbers['gradient'] = {k: v.to_dict('records') for k, v in curves.items()}
    if 'killed' in d:
        fs = m.frequency_severity(d)
        numbers['frequency_severity'] = {k: v for k, v in fs.items()}
    if nbrs is not None and tract_frame is not None:
        tex, nums = scale_table(tract_frame, nbrs, draws)
        (out / 'table_scale.tex').write_text(tex)
        numbers['scale'] = nums
    numbers['autocorrelation'] = dg.residual_autocorrelation(d, n_perm=perm)
    if poverty_moe is not None:
        numbers['acs_error'] = dg.poverty_error_simex(d, poverty_moe, seed=seed)
    rows = robustness_rows(d, years, definitions, boot, perm)
    pd.DataFrame(rows).to_csv(out / 'robustness.csv', index=False)
    draw_robustness(rows, out / 'robustness.pdf')
    (out / 'numbers.json').write_text(json.dumps(numbers, indent=1, default=float))
    return numbers
