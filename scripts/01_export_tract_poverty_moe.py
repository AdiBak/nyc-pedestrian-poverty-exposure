# Run in a Colab session. Pulls the ACS tract poverty rate and its margin of error for New York City.
# Needs your Census access saved in Colab Secrets as CENSUS_API_KEY, with notebook access switched on.
# Writes tract_poverty_moe.csv to the data folder, for: python -m nycped checks --poverty-moe

# %% Export tract poverty margins of error
import numpy as np
import pandas as pd
import requests
from google.colab import userdata

OUT = '/content/drive/MyDrive/TDSP/nyc_walks'
ACCESS = userdata.get('CENSUS_API_KEY')
BASE = 'https://api.census.gov/data/2023/acs/acs5/subject'

frames = []
for county in ['005', '047', '061', '081', '085']:
    r = requests.get(BASE, params={'get': 'S1701_C03_001E,S1701_C03_001M', 'for': 'tract:*',
                                   'in': ['state:36', f'county:{county}'], 'key': ACCESS}, timeout=60)
    if r.status_code != 200:  # do not print the request, it carries your access string
        raise RuntimeError(f'Census API returned status {r.status_code} for county {county}: {r.text[:200]}')
    rows = r.json()
    frames.append(pd.DataFrame(rows[1:], columns=rows[0]))

df = pd.concat(frames, ignore_index=True)
df['GEOID'] = df['state'] + df['county'] + df['tract']
for c in ['S1701_C03_001E', 'S1701_C03_001M']:
    df[c] = pd.to_numeric(df[c], errors='coerce')
    df.loc[df[c] <= -1e8, c] = np.nan  # the ACS codes missing values as large negative numbers
out = df.rename(columns={'S1701_C03_001E': 'poverty_estimate', 'S1701_C03_001M': 'poverty_moe'})[
    ['GEOID', 'poverty_estimate', 'poverty_moe']]
out.to_csv(f'{OUT}/tract_poverty_moe.csv', index=False)

# Check against the tract table the analysis used
tt = pd.read_csv(f'{OUT}/tract_table.csv', dtype={'GEOID': str})
m = tt.merge(out, on='GEOID', how='left')
print('tracts pulled:', len(out), '| analysis tracts with a margin of error:', int(m['poverty_moe'].notna().sum()), 'of', len(tt))
same = int((np.abs(m['poverty_estimate'] - m['Poverty_Rate_Percent']) < 1e-6).sum())
print('estimate equals the analysis poverty rate for', same, 'tracts')
print(m['poverty_moe'].describe().round(2).to_string())
