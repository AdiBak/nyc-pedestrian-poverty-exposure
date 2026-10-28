"""Command line interface. Run with python -m nycped <command>."""
from __future__ import annotations

import argparse
import json
from importlib import resources

import pandas as pd

from . import crashes as cr
from . import exposure as ex
from . import models as m
from . import robustness as rb
from . import scale as sc
from . import sitedata
from .config import Settings
from .io import fetch_all


def _load_sites(path) -> pd.DataFrame:
    return m.prepare_frame(pd.read_csv(path, dtype={'GEOID': str}))


def cmd_fetch(args, s: Settings):
    manifest = fetch_all(s, force=args.force)
    for name, e in manifest.entries.items():
        print(f"{name}: {e['bytes'] / 1e6:.1f} MB, sha256 {e['sha256'][:12]}, from {e['url'][:60]}")


def cmd_sites(args, s: Settings):
    """Build the site table from the NYC Walks file, centerlines, the crash export and the tract table."""
    geojson = ex.extract_walks_geojson(s.path('supp_data_1_network.zip'), s.path('cache'))
    seg = ex.read_walks(geojson)
    streets = ex.read_streets(s.path('centerline_inkn-q76z.geojson'), s.street_types)
    cross = ex.infer_crosswalks(seg, streets)
    sites = ex.build_sites(cross, s.site_eps_m)
    print(f'crosswalk segments: {len(cross)} | sites: {len(sites)}')
    tracts = ex.read_nyc_tracts(s.path('ny_tracts2020.zip'))
    tract_table = pd.read_csv(args.tract_table, dtype={'GEOID': str})
    sites = ex.attach_tracts(sites, tracts, tract_table)
    pts = cr.load_ped_harm_crashes(args.crashes)
    assigned, share = cr.assign_to_sites(pts, ex.site_points(sites), s.crash_radius_m)
    counts = cr.site_counts(assigned, s.years)
    d = sitedata.make_site_dataset(sites, counts, s.years)
    out = s.path('site_dataset.csv')
    d.to_csv(out, index=False)
    print(f'sites in the model: {len(d)} | crashes assigned: {share:.1%} | saved to {out}')


def cmd_models(args, s: Settings):
    d = _load_sites(args.sites)
    print('Poverty rate ratio per +10 points, harm crashes')
    print(m.ladder(d, 'harm').drop(columns='rr').to_string(index=False))
    print('\nPoverty rate ratio per +10 points, deaths')
    print(m.ladder(d, 'killed').drop(columns='rr').to_string(index=False))
    fs = m.frequency_severity(d)
    print('\nFrequency and severity, model D')
    for k in ['frequency', 'severity', 'total']:
        print(f'  {k}: {m.fmt_rr(fs[k])}')
    if args.bootstrap:
        b = m.cluster_bootstrap(d, 'killed', n_boot=args.bootstrap)
        print(f"\nCluster bootstrap, deaths: {b['point']:.2f} ({b['lo']:.2f} to {b['hi']:.2f}), {b['n_clusters']} clusters")


def cmd_robustness(args, s: Settings):
    d = _load_sites(args.sites)
    print('Measurement error (SIMEX)')
    print(rb.simex(d, seed=s.seed).round(3).to_string(index=False))
    if 'y_early' in d.columns:
        print('\nBy period, harm crashes')
        print(rb.by_period(d, s.years, 'harm').drop(columns='rr').to_string(index=False))
        print('\nBy period, deaths')
        print(rb.by_period(d, s.years, 'killed').drop(columns='rr').to_string(index=False))
    print('\nLeave one borough out, harm crashes')
    print(rb.leave_one_borough_out(d, 'harm').drop(columns='rr').to_string(index=False))


def cmd_scale(args, s: Settings):
    d = _load_sites(args.sites)
    t = sc.tract_frame(d)
    print(sc.real_scales(t).round(3).to_string(index=False))
    tracts = ex.read_nyc_tracts(s.path('ny_tracts2020.zip'))
    nbrs = sc.adjacency(tracts, list(t['GEOID']), dict(zip(t['GEOID'], t['county'])))
    print('\nRandom contiguous zonings')
    print(sc.random_zonings(t, nbrs, n_draws=args.draws, seed=11).round(3).to_string(index=False))


def cmd_verify(args, s: Settings) -> int:
    """Compare a fresh fit on a site table with the stored expected values."""
    expected = json.loads(resources.files('nycped').joinpath('expected_results.json').read_text())['checks']
    d = _load_sites(args.sites)
    fs = m.frequency_severity(d)
    p = m.fit_poisson(d, 'harm', m.rhs_for(m.PRIMARY))
    actual = {
        'n_sites': len(d),
        'harm_poverty_rr_primary': m.rr_per10(p)[0],
        'deaths_poverty_rr_primary': fs['total'][0],
        'volume_elasticity_primary': float(p.params['log_vol']),
        'severity_rr': fs['severity'][0],
        'frequency_rr': fs['frequency'][0],
    }
    failed = 0
    for name, spec in expected.items():
        ok = abs(actual[name] - spec['value']) <= spec['tol']
        failed += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {name}: got {actual[name]:.4f}, expected {spec['value']} (tolerance {spec['tol']})")
    print('\nAll checks passed.' if not failed else f'\n{failed} check(s) failed.')
    return 1 if failed else 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog='nycped', description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('fetch', help='download the public data sources and write MANIFEST.json')
    p.add_argument('--force', action='store_true')
    p = sub.add_parser('sites', help='build the site table')
    p.add_argument('--crashes', required=True, help='ped_harm_crashes.csv')
    p.add_argument('--tract-table', required=True, help='tract_table.csv')
    for name, helptext in [('models', 'primary models and the frequency and severity split'),
                           ('robustness', 'measurement error, periods and leave one borough out'),
                           ('scale', 'scale and zone effects'),
                           ('verify', 'check a site table against the stored expected values')]:
        p = sub.add_parser(name, help=helptext)
        p.add_argument('--sites', required=True, help='site table CSV')
        if name == 'models':
            p.add_argument('--bootstrap', type=int, default=0, help='cluster bootstrap resamples for deaths')
        if name == 'scale':
            p.add_argument('--draws', type=int, default=100)
    args = parser.parse_args(argv)
    s = Settings()
    handler = {'fetch': cmd_fetch, 'sites': cmd_sites, 'models': cmd_models, 'robustness': cmd_robustness,
               'scale': cmd_scale, 'verify': cmd_verify}[args.command]
    result = handler(args, s)
    return int(result or 0)


if __name__ == '__main__':
    raise SystemExit(main())
