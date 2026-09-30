# Web samples

These files are pinned copies for exercising different report shapes. They are test data, not part of the skill's MIT-licensed implementation.

| File | Why it is useful | Source and license | Pinned commit | SHA-256 |
| --- | --- | --- | --- | --- |
| `titanic.csv` | Mixed numeric, categorical, text, and substantially incomplete fields | [MLCommons Croissant Titanic](https://github.com/mlcommons/croissant/tree/main/datasets/1.0/titanic), [AFL-3.0 metadata](https://github.com/mlcommons/croissant/blob/main/datasets/1.0/titanic/metadata.json) | `6896ea2c65ef530580d359525fb446b222aa2fe9` | `C617DB2C7470716250F6F001BE51304C76BCC8815527AB8BAE734BDCA0735737` |
| `seattle-weather.csv` | Time series, numeric distributions, and a categorical weather field | [Vega Datasets](https://github.com/vega/vega-datasets/blob/main/data/seattle-weather.csv), derived from NOAA and identified as a U.S. Government dataset in the repository metadata | `ede9366badecc625cd6bcea5c4aaa055870c6ca6` | `0845078A290B48E3149AB8639966824110A251DB4E06FC144C06EBB534AF23BE` |
| `global-temp.csv` | Long numeric time series with multiple measures and useful outlier checks | [Vega Datasets](https://github.com/vega/vega-datasets/blob/main/data/global-temp.csv), derived from NASA GISS and identified as a U.S. Government dataset in the repository metadata | `ede9366badecc625cd6bcea5c4aaa055870c6ca6` | `5933DCB6D5E7FC5C0C241B956B802DE2B02DA12D0914D06031030579A0F1443B` |
| `quality-lab.csv` | Small intentionally inconsistent file for exercising every report view | Original TriunaLabs test fixture, MIT with the skill | This repository | Generated locally |

The Vega repository states that each dataset retains its original license; see its `datapackage.json` for the per-file source and license records. Verify upstream terms again before redistributing these datasets beyond testing.

Generate reports from the installed skill directory:

```sh
python scripts/analyze_csv.py samples/titanic.csv --format html --output titanic.profile.html
python scripts/analyze_csv.py samples/seattle-weather.csv --format markdown --output seattle-weather.profile.md
```
