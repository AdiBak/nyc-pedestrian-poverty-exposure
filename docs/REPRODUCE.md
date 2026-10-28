# Reproduce the results in five steps

Needs Python 3.11 or newer, about 1 GB of free memory, 300 MB of disk and an internet connection. The full run takes a few minutes. The steps below were run end to end on 28 October 2026 and reproduced the published numbers.

## 1. Get the code

```
git clone https://github.com/AdiBak/nyc-pedestrian-poverty-exposure.git
cd nyc-pedestrian-poverty-exposure
pip install -e ".[test]"
pytest          # optional, about 10 seconds, no data needed
```

For the exact library versions of the verified run, see `requirements-lock.txt`.

## 2. Get the two processed inputs

Download `tract_table.csv` and `ped_harm_crashes.csv` from the Zenodo data deposit, [ZENODO_DATA_DOI], into an empty folder. Point the package at it.

```
export NYCPED_DATA_DIR=/path/to/that/folder
shasum -a 256 "$NYCPED_DATA_DIR"/tract_table.csv "$NYCPED_DATA_DIR"/ped_harm_crashes.csv
```

The checksums should be

```
16632c5696a001e00acb16f6a3396c9547db6fe31d5baf9b97169c3022d3a208  tract_table.csv
bdfb46ee5da7c1b68a36c1fb7e8a1bfa98fabed41692eb456188831e6fdc76f5  ped_harm_crashes.csv
```

## 3. Download the public sources

```
python -m nycped fetch
```

This downloads about 280 MB, the NYC Walks supplementary network (60 MB), the NYC street centerlines (218 MB) and the Census tract boundaries (2 MB). It writes `MANIFEST.json` with the checksum of each file. The published run used these.

| File | SHA-256 |
|---|---|
| `supp_data_1_network.zip` | `84d83d7d23760d33d77d9e8fec81e0ab9f24150f3899befc6d888eb9442149c7` |
| `ny_tracts2020.zip` | `8f1e3b60c51b71ed6193247ff58dc7814b5d227254b4b33878dacea8022033ec` |
| `centerline_inkn-q76z.geojson` | `b27f370ad5d19a72fd108407341e448c9a9747bd4136ad00c0af2a6d552218d0` |

NYC updates the centerline dataset over time. If your checksum differs, the street attributes may differ slightly and the results may move a little. Step 5 tells you whether they still agree with the published run.

## 4. Build the site table

```
python -m nycped sites --crashes "$NYCPED_DATA_DIR/ped_harm_crashes.csv" --tract-table "$NYCPED_DATA_DIR/tract_table.csv"
```

Expected output

```
crosswalk segments: 110603 | sites: 41937
sites in the model: 38477 | crashes assigned: 81.9% | saved to .../site_dataset.csv
```

## 5. Check the results

```
python -m nycped verify --sites "$NYCPED_DATA_DIR/site_dataset.csv"
```

All six checks should print PASS.

```
PASS  n_sites: got 38477.0000, expected 38477 (tolerance 0)
PASS  harm_poverty_rr_primary: got 1.1612, expected 1.16 (tolerance 0.01)
PASS  deaths_poverty_rr_primary: got 1.2880, expected 1.29 (tolerance 0.02)
PASS  volume_elasticity_primary: got 0.7915, expected 0.79 (tolerance 0.02)
PASS  severity_rr: got 1.1101, expected 1.11 (tolerance 0.02)
PASS  frequency_rr: got 1.1612, expected 1.16 (tolerance 0.01)
```

Then run the rest of the analysis.

```
python -m nycped models --sites "$NYCPED_DATA_DIR/site_dataset.csv" --bootstrap 500
python -m nycped robustness --sites "$NYCPED_DATA_DIR/site_dataset.csv"
python -m nycped scale --sites "$NYCPED_DATA_DIR/site_dataset.csv"
```

The numbers are in `docs/research_log.md`.

## If something differs

- **Different site counts.** Check the centerline checksum in step 3. A newer centerline file is the most likely cause.
- **Different model estimates with the same site table.** Check the library versions against `requirements-lock.txt`.
- **A command fails.** Open an issue with the full output.

## Where the two processed inputs come from

`tract_table.csv` and `ped_harm_crashes.csv` were built once from the NYC crash data, the ACS and PLUTO in the original Colab notebook, using `scripts/00_export_processed_inputs.py`. `docs/DATA_RELEASE.md` describes how they were made and what each column means.
