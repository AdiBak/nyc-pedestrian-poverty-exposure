# Developed and run in Google Colab, as a cell of the project notebook.
# See README.md for the run order and for what each script needs.

# Step 1 of the crossing exposure build: get the NYC street centerlines and look at road types.
# The NYC Walks file has no segment type field, so we will infer crosswalks as the segments
# that cross a street centerline. For that we need to know which centerline types are real roadbeds.

# %% C1. Download the Centerline dataset (NYC Open Data, id inkn-q76z) and inspect it
import os
import geopandas as gpd
from google.colab import drive

drive.mount('/content/drive')
DRIVE_DIR = '/content/drive/MyDrive/TDSP/nyc_walks'
os.makedirs(DRIVE_DIR, exist_ok=True)

URL = 'https://data.cityofnewyork.us/resource/inkn-q76z.geojson?$limit=300000'
cl = gpd.read_file(URL)
print('rows:', len(cl), '| crs:', cl.crs)
print('columns:', list(cl.columns))

# Print the value counts of any column that looks like a road or segment type
hints = ('rw_type', 'rwtype', 'feature', 'segment', 'status', 'trafdir', 'traf_dir', 'roadway')
for c in cl.columns:
    if any(h in c.lower() for h in hints):
        print(f'\n{c}')
        print(cl[c].value_counts(dropna=False).head(15).to_string())

print('\nFirst three rows')
print(cl.drop(columns='geometry').head(3).T.to_string())

cl.to_file(f'{DRIVE_DIR}/centerline_inkn-q76z.geojson', driver='GeoJSON')
print('\nsaved to', f'{DRIVE_DIR}/centerline_inkn-q76z.geojson')
