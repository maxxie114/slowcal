#!/usr/bin/env python3
"""
Download all datasets listed in src.utils.config.Config.DATASETS into data/raw/cache/

Usage: from repo root run `python scripts/download_all_datasets.py`
Requires network access. Honor SF_DATA_APP_TOKEN env var if present.
"""
import os
import time
import json
from pathlib import Path
import requests

# Ensure src is importable
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from utils.config import Config


OUT_DIR = Path("data/raw/cache")
OUT_DIR.mkdir(parents=True, exist_ok=True)

DATASETS = [v["id"] for v in Config.DATASETS.values()]
LIMIT = 50000
APP_TOKEN = os.getenv("SF_DATA_APP_TOKEN", "")


def download_dataset(dataset_id: str, out_path: Path):
    if out_path.exists() and out_path.stat().st_size > 0:
        print(f"Found existing file for {dataset_id}: {out_path} (skipping). Remove to re-download")
        return

    session = requests.Session()
    headers = {}
    if APP_TOKEN:
        headers["X-App-Token"] = APP_TOKEN

    all_rows = []
    offset = 0
    while True:
        params = {"$limit": LIMIT, "$offset": offset}
        try:
            resp = session.get(f"https://data.sfgov.org/resource/{dataset_id}.json", params=params, headers=headers, timeout=60)
            resp.raise_for_status()
            batch = resp.json()
        except Exception as e:
            print(f"Error fetching {dataset_id} offset={offset}: {e}")
            break

        if not batch:
            break

        all_rows.extend(batch)
        print(f"{dataset_id}: fetched {len(batch)} rows (offset {offset})")
        offset += LIMIT
        time.sleep(0.1)

    # write
    tmp = out_path.with_suffix('.tmp')
    with open(tmp, 'w') as f:
        json.dump(all_rows, f)
    tmp.replace(out_path)
    print(f"Saved {len(all_rows)} rows to {out_path}")


def main():
    print("Downloading datasets to:", OUT_DIR)
    for ds in DATASETS:
        out = OUT_DIR / f"{ds}_full.json"
        print("====", ds, "====")
        download_dataset(ds, out)


if __name__ == '__main__':
    main()
