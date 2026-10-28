# Run in the Colab session that holds the Milestone 5 setup (needs crashes, tract_table and HEADLINE_YEARS).
# It writes the two small processed inputs that the nycped package reads, so the package does not
# depend on the notebook session or on the Census API.
#   tract_table.csv         one row per tract with poverty, commuting, land use and the ZIP cluster
#   ped_harm_crashes.csv    pedestrian harm crashes, 2019 to 2023, highway crashes dropped

# %% Export processed inputs
import pandas as pd

OUT = '/content/drive/MyDrive/TDSP/nyc_walks'

tm = tract_table(HEADLINE_YEARS, 'local')
tm.to_csv(f'{OUT}/tract_table.csv', index=False)

c = crashes[crashes['YEAR'].isin(HEADLINE_YEARS) & ~crashes['is_highway']].copy()
c['ped_inj'] = c['NUMBER OF PEDESTRIANS INJURED'].fillna(0)
c['ped_kill'] = c['NUMBER OF PEDESTRIANS KILLED'].fillna(0)
c = c[(c['ped_inj'] + c['ped_kill']) > 0]
c = c[c['LATITUDE'].between(40.4, 41.0) & c['LONGITUDE'].between(-74.3, -73.6)]
export = c[['YEAR', 'LATITUDE', 'LONGITUDE', 'ped_inj', 'ped_kill']].rename(
    columns={'YEAR': 'year', 'LATITUDE': 'lat', 'LONGITUDE': 'lon'})
export.to_csv(f'{OUT}/ped_harm_crashes.csv', index=False)

print('tract table:', tm.shape, '| tracts:', tm['GEOID'].nunique())
print('pedestrian harm crashes:', len(export), '| deaths among them:', int(export['ped_kill'].sum()))
print('expected from the published run: 37,815 crashes and 469 deaths')
