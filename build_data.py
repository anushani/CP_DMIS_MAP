#!/usr/bin/env python3
"""
Build the web-map data files from (1) DS boundaries and (2) the DMIS Excel export.

Usage:
    python build_data.py --boundaries DMIS_DS_Demo.gpkg --excel DMIS_DS_Summary.xlsx

Needs:  pip install geopandas pyogrio pandas openpyxl     and     npm i -g mapshaper
Boundary layer must have: DS_CODE, D_CODE, DS_NAME, D_NAME  (DS_CODE repeats between
districts, so the unique key is  D_CODE-DS_CODE).
Excel must have a 'Projects' sheet with: project_code, project_name, institute,
source_of_funds, allocation_rs, financial_progress_rs, financial_progress_pct,
physical_progress_category, start_date, end_date, location_status, DS_CODE, D_CODE,
district_name.
"""
import argparse, json, subprocess, tempfile, os, datetime
import pandas as pd, geopandas as gpd

ap = argparse.ArgumentParser()
ap.add_argument("--boundaries", required=True)
ap.add_argument("--layer", default="DMIS_DS_Summary")
ap.add_argument("--excel", required=True)
ap.add_argument("--out", default="data")
ap.add_argument("--simplify", default="12%", help="mapshaper simplify level")
a = ap.parse_args()
os.makedirs(a.out, exist_ok=True)

CATS = ["0-10", "11-24", "25-49", "50-74", "75-99", "100"]

# ---------- boundaries ----------
g = gpd.read_file(a.boundaries, layer=a.layer).to_crs(4326)
g = g[["DS_CODE", "D_CODE", "DS_NAME", "D_NAME", "geometry"]].copy()
g["DS_CODE"] = g.DS_CODE.astype(int); g["D_CODE"] = g.D_CODE.astype(int)
g["key"] = g.D_CODE.astype(str) + "-" + g.DS_CODE.astype(str)
g = g.rename(columns={"DS_NAME": "name", "D_NAME": "district"})[["key", "name", "district", "geometry"]]

with tempfile.TemporaryDirectory() as t:
    raw = os.path.join(t, "ds.geojson"); g.to_file(raw, driver="GeoJSON")
    run = lambda *c: subprocess.run(c, check=True)
    run("mapshaper", raw, "-simplify", a.simplify, "keep-shapes", "-o",
        os.path.join(a.out, "ds.geojson"), "format=geojson", "precision=0.00001")
    run("mapshaper", os.path.join(a.out, "ds.geojson"), "-dissolve", "district",
        "-o", os.path.join(a.out, "district.geojson"), "format=geojson", "precision=0.00001")

# ---------- projects ----------
p = pd.read_excel(a.excel, sheet_name="Projects")
for c in ("allocation_rs", "financial_progress_rs", "financial_progress_pct"):
    p[c] = pd.to_numeric(p[c], errors="coerce").fillna(0)
p["cat"] = p.physical_progress_category.astype(str)
ok = p.location_status.eq("DS_IDENTIFIED") & p.DS_CODE.notna() & p.D_CODE.notna()
p["key"] = None
p.loc[ok, "key"] = p.loc[ok, "D_CODE"].astype(int).astype(str) + "-" + p.loc[ok, "DS_CODE"].astype(int).astype(str)
valid = set(g.key)
bad = set(p.key.dropna()) - valid
if bad: print("WARNING: project keys with no polygon:", bad)

stats, projects = {}, {}
for k, d in p[ok].groupby("key"):
    al, fi = d.allocation_rs.sum(), d.financial_progress_rs.sum()
    stats[k] = dict(
        count=int(len(d)), alloc=round(al, 2), fin=round(fi, 2),
        wpct=round(100 * fi / al, 2) if al else 0,          # money-weighted financial progress
        avgpct=round(d.financial_progress_pct.mean(), 2),   # simple average of project %
        cats={c: int((d.cat == c).sum()) for c in CATS},
        completed=int((d.cat == "100").sum()),
    )
    d = d.sort_values("allocation_rs", ascending=False)
    projects[k] = [[r.project_code, r.project_name, r.institute, r.source_of_funds,
                    float(r.allocation_rs), float(r.financial_progress_rs),
                    float(r.financial_progress_pct), r.cat,
                    str(r.start_date)[:10], str(r.end_date)[:10]] for r in d.itertuples()]

# projects that cannot be drawn on a DS polygon, grouped by district
unloc = {}
for dist, d in p[~ok].groupby("district_name"):
    unloc[dist] = dict(
        count=int(len(d)), alloc=round(d.allocation_rs.sum(), 2),
        multi_ds=int(d.location_status.eq("MULTIPLE_DS").sum()))
meta = dict(
    generated=datetime.date.today().isoformat(),
    data_date=str(p.demo_loaded_date.max())[:10] if 'demo_loaded_date' in p else None,
    total_projects=int(len(p)), mapped_projects=int(ok.sum()),
    total_alloc=round(p.allocation_rs.sum(), 2), mapped_alloc=round(p[ok].allocation_rs.sum(), 2),
    unlocated=unloc)
json.dump(dict(meta=meta, ds=stats), open(f"{a.out}/stats.json", "w"), ensure_ascii=False, separators=(",", ":"))
json.dump(projects, open(f"{a.out}/projects.json", "w"), ensure_ascii=False, separators=(",", ":"))
print(f"DS polygons: {len(g)} | with data: {len(stats)} | mapped projects: {ok.sum()}/{len(p)}")
print("DS polygons without projects:", sorted(valid - set(stats)))
for f in os.listdir(a.out): print(f, os.path.getsize(os.path.join(a.out, f)) // 1024, "KB")
