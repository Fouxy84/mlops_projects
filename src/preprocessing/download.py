"""Download raw data from challengedata.ens.fr into data/raw/.

Authenticates against challengedata (CSRF + login), downloads the Rakuten
dataset files, and writes lineage.json for traceability. DVC versioning
(dvc add + dvc push) is performed by the calling Airflow DAG.
"""
import json
import os
import zipfile
from datetime import datetime

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://challengedata.ens.fr"
LOGIN_URL = f"{BASE_URL}/login/?next=/challenges/35"

FILES = {
    "X_train_update.csv": "/participants/challenges/35/download/x-train",
    "Y_train_CVw08PX.csv": "/participants/challenges/35/download/y-train",
    "X_test_update.csv": "/participants/challenges/35/download/x-test",
    "supplementary_files.zip": "/participants/challenges/35/download/supplementary-files",
}

DATA_RAW_DIR = os.getenv("DATA_RAW_DIR", "data/raw")


def login(session: requests.Session) -> None:
    resp = session.get(LOGIN_URL)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    csrf = soup.find("input", {"name": "csrfmiddlewaretoken"})
    if not csrf:
        raise ValueError("CSRF token not found on login page")

    payload = {
        "csrfmiddlewaretoken": csrf["value"],
        "username": os.getenv("CHALLENGEDATA_USERNAME"),
        "password": os.getenv("CHALLENGEDATA_PASSWORD"),
    }
    resp = session.post(LOGIN_URL, data=payload, headers={"Referer": LOGIN_URL})
    resp.raise_for_status()
    if "login" in resp.url:
        raise ValueError("Authentication failed - check CHALLENGEDATA_USERNAME / PASSWORD")


def _write_lineage(download_date: str, file_sizes: dict) -> None:
    meta = {
        "download_date": download_date,
        "downloaded_at": datetime.now().isoformat(),
        "local_path": DATA_RAW_DIR,
        "files": {fname: {"size_bytes": size} for fname, size in file_sizes.items()},
    }
    with open(os.path.join(DATA_RAW_DIR, "lineage.json"), "w") as f:
        json.dump(meta, f, indent=2)


def download_all(download_date: str | None = None) -> str:
    if not download_date:
        download_date = datetime.now().strftime("%Y-%m")

    if not os.getenv("CHALLENGEDATA_USERNAME") or not os.getenv("CHALLENGEDATA_PASSWORD"):
        raise ValueError("CHALLENGEDATA_USERNAME and CHALLENGEDATA_PASSWORD are required")

    os.makedirs(DATA_RAW_DIR, exist_ok=True)

    session = requests.Session()
    print("Authenticating on challengedata.ens.fr...")
    login(session)
    print(f"Connected. Target version: {download_date}")

    file_sizes: dict = {}
    for filename, path in FILES.items():
        print(f"Downloading {filename}...")
        dest = os.path.join(DATA_RAW_DIR, filename)
        with session.get(f"{BASE_URL}{path}", stream=True) as resp:
            resp.raise_for_status()
            size = 0
            with open(dest, "wb") as f:
                for chunk in resp.iter_content(chunk_size=1 << 20):
                    if chunk:
                        f.write(chunk)
                        size += len(chunk)
        file_sizes[filename] = size
        print(f"  -> {dest} ({size / 1_000_000:.1f} MB)")

        if filename.endswith(".zip"):
            print(f"Extracting {filename} into {DATA_RAW_DIR}/...")
            with zipfile.ZipFile(dest) as zf:
                zf.extractall(DATA_RAW_DIR)
            os.remove(dest)
            print(f"  -> extracted and removed {dest}")

    _write_lineage(download_date, file_sizes)
    print(f"Download complete. Version: {download_date}")
    return download_date


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Download Rakuten data into data/raw/")
    parser.add_argument("--download_date", default=os.getenv("DOWNLOAD_DATE"))
    args = parser.parse_args()
    download_all(download_date=args.download_date or None)
