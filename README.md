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

## RD (Real Data) — Mark 2

The dashboard now loads `data/projects.json` automatically. Records without a valid recipient coordinate remain in the source totals but are not drawn on the map; the interface shows the mapped/total record count so this data limitation stays visible.

The detail drawer discloses the amount field, sector-classification method, representative-country coordinate method, and original World Bank source link. If the real-data files cannot load, the embedded demonstration records remain available as a clearly labelled fallback.
