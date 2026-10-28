# Developed and run in Google Colab, as a cell of the project notebook.
# See README.md for the run order and for what each script needs.

# NYC Walks supplementary files, downloaded straight into Google Drive
# Source: Sevtsuk et al. (2026), Nature Cities, Supplementary Data 1 and its metadata.
# Run this in its own Colab session. Do not load any .pckl file in a session with Drive mounted.
import os, hashlib, zipfile, requests
from google.colab import drive

drive.mount('/content/drive')

OUT = '/content/drive/MyDrive/TDSP/nyc_walks'
os.makedirs(OUT, exist_ok=True)

BASE = ('https://media.springernature.com/original/springer-static/esm/'
        'art%3A10.1038%2Fs44284-025-00383-y/MediaObjects/')

FILES = {
    'supp_data_1_network.zip': '44284_2025_383_MOESM3_ESM.zip',
    'supp_data_1_metadata.txt': '44284_2025_383_MOESM4_ESM.txt',
}

# Supplementary Data 2 holds pickled model files. Leave this off unless you need them.
GET_MODELS = False
if GET_MODELS:
    FILES['supp_data_2_models.zip'] = '44284_2025_383_MOESM5_ESM.zip'

for name, remote in FILES.items():
    path = os.path.join(OUT, name)
    r = requests.get(BASE + remote, stream=True, timeout=120,
                     headers={'User-Agent': 'Mozilla/5.0'})
    r.raise_for_status()
    sha = hashlib.sha256()
    with open(path, 'wb') as f:
        for chunk in r.iter_content(1 << 20):
            f.write(chunk)
            sha.update(chunk)
    print(f'{name}: {os.path.getsize(path) / 1e6:.1f} MB, sha256 {sha.hexdigest()[:16]}')

# Look inside the ZIP files without extracting or loading anything
for name in FILES:
    if name.endswith('.zip'):
        with zipfile.ZipFile(os.path.join(OUT, name)) as z:
            print(f'\n{name}, first bad file: {z.testzip()}')
            for info in z.infolist()[:40]:
                print(f'  {info.file_size / 1e6:8.1f} MB  {info.filename}')

# The metadata file says what each column means and may state the license
meta = open(os.path.join(OUT, 'supp_data_1_metadata.txt'), encoding='utf-8', errors='replace').read()
print('\n--- metadata (first 6,000 characters) ---')
print(meta[:6000])
