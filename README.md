# Capital Flow Atlas

## RD (Real Data) — Mark 1

This phase is a data spike using the public World Bank Projects & Operations API. It does not change the current dashboard UI.

Run a fresh download:

```powershell
python scripts/fetch_worldbank.py
```

Rebuild the normalized sample and audit from the saved raw response:

```powershell
python scripts/fetch_worldbank.py --use-cache
```

Outputs:

- `data/raw/worldbank-projects.json`: source project records and retrieval metadata
- `data/raw/worldbank-countries.json`: source country coordinates used for map points
- `data/projects.json`: normalized, map-ready candidates
- `data/rd-mark-1-metadata.json`: filters and quality counts
- `reports/rd-mark-1-audit.md`: readable quality audit and limitations
