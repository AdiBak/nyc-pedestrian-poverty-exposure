"""Check the two processed inputs against the published checksums and zip them with the deposit README.

Usage: python scripts/make_deposit_bundle.py DIR_WITH_CSVS OUTPUT.zip
"""
from __future__ import annotations

import hashlib
import sys
import zipfile
from pathlib import Path

EXPECTED = {
    'tract_table.csv': '16632c5696a001e00acb16f6a3396c9547db6fe31d5baf9b97169c3022d3a208',
    'ped_harm_crashes.csv': 'bdfb46ee5da7c1b68a36c1fb7e8a1bfa98fabed41692eb456188831e6fdc76f5',
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def main(src: str, out: str) -> int:
    src_dir = Path(src)
    ok = True
    for name, want in EXPECTED.items():
        p = src_dir / name
        if not p.exists():
            print(f'MISSING {name}')
            ok = False
            continue
        got = sha256(p)
        print(f"{'PASS' if got == want else 'FAIL'}  {name}  {got}")
        ok = ok and got == want
    if not ok:
        print('Not building the bundle. Fix the files above first.')
        return 1
    readme = Path(__file__).resolve().parents[1] / 'deposit' / 'README.md'
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        for name in EXPECTED:
            z.write(src_dir / name, name)
        z.write(readme, 'README.md')
    print(f'wrote {out}')
    return 0


if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    sys.exit(main(sys.argv[1], sys.argv[2]))
