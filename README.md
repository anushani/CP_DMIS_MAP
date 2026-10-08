# DMIS Central Province – project map (free, static)

Leaflet + GeoJSON. No server, no database, no paid service.

## Files
- `index.html` – the map (open via a web server, see below)
- `data/ds.geojson`, `data/district.geojson` – boundaries (simplified)
- `data/stats.json` – numbers per DS division (what the colours use)
- `data/projects.json` – project list per DS division (side panel)
- `lib/leaflet/` – Leaflet 1.9.4 (bundled, works offline)
- `build_data.py` – rebuilds the `data/` files from your Excel + boundaries

## Test on your computer
Browsers block `fetch` from `file://`, so double-clicking index.html shows an error. Run:
    cd dmis-map
    python -m http.server 8000
then open http://localhost:8000

## Publish free (GitHub Pages)
1. Create a free GitHub account → New repository `dmis-map` (Public).
2. Upload everything in this folder.
3. Settings → Pages → Branch: main, folder: / (root) → Save.
4. Your map: https://YOUR-NAME.github.io/dmis-map/
(Alternatives: Netlify Drop, Cloudflare Pages – drag the folder in.)
Only publish data DMIS already shows publicly. Project names/amounts are in projects.json.

## Update when DMIS data changes
1. Export a new Excel with the same sheet/column names (sheet `Projects`).
2. One-time setup: `pip install geopandas pyogrio pandas openpyxl` and `npm i -g mapshaper`
3. `python build_data.py --boundaries DMIS_DS_Demo.gpkg --excel NEW_EXPORT.xlsx`
4. Replace the `data/` folder in GitHub (upload). Done.

## Going live later (no map code change)
Make your own API return the same JSON shape as `data/stats.json`
({"meta":{...},"ds":{"21-27":{count,alloc,fin,wpct,avgpct,cats,completed}}}),
then set `CONFIG.stats` to its URL and `CONFIG.refreshSeconds` to 60 in index.html.
DS key = D_CODE-DS_CODE (DS_CODE alone repeats between districts).

## Known limits
- 2,007 of 6,283 projects have no single DS (provincial/district-wide, or several DS), so they are not drawn; the panel reports them.
- DS level only. DMIS has no GN field; a GN map needs GN data in the export.
