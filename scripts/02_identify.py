#!/usr/bin/env python3
"""
02_identify.py
Usage: python3 02_identify.py <inat_api_token>
"""

import json
import sys
import time
import subprocess
import tempfile
import os
import urllib.request
from pathlib import Path

ROOT      = Path(__file__).resolve().parent.parent
PHOTO_DIR = ROOT / "photos"
DATA_FILE = ROOT / "trees.json"
INAT_URL  = "https://api.inaturalist.org/v1/computervision/score_image"
MAX_BYTES = 2 * 1024 * 1024  # 2 MB


def resize_if_needed(photo_path):
    """Return image bytes, resized to max 1024px if over 2 MB."""
    data = photo_path.read_bytes()
    if len(data) <= MAX_BYTES:
        return data
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        subprocess.run(
            ["sips", "-Z", "1024", str(photo_path), "--out", tmp_path],
            capture_output=True, check=True,
        )
        return Path(tmp_path).read_bytes()
    finally:
        os.unlink(tmp_path)


def score_image(photo_path, token, lat=None, lng=None):
    boundary = "----iNatTreeBoundary7MA4YWxk"
    img_data = resize_if_needed(photo_path)

    body = b""
    body += f"--{boundary}\r\n".encode()
    body += f'Content-Disposition: form-data; name="image"; filename="{photo_path.name}"\r\n'.encode()
    body += b"Content-Type: image/jpeg\r\n\r\n"
    body += img_data + b"\r\n"

    if lat is not None:
        for name, val in [("lat", lat), ("lng", lng)]:
            body += f"--{boundary}\r\n".encode()
            body += f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode()
            body += str(val).encode() + b"\r\n"

    body += f"--{boundary}--\r\n".encode()

    req = urllib.request.Request(
        INAT_URL,
        data=body,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Authorization": f"Bearer {token}",
            "User-Agent": "trees-field-guide/1.0",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 02_identify.py <inat_api_token>")
        sys.exit(1)

    token = sys.argv[1]
    data  = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    photos = data["photos"]

    existing = {p.name for p in PHOTO_DIR.glob("*.jpeg")}
    photos = [p for p in photos if p["filename"] in existing]
    data["photos"] = photos

    total = len(photos)
    done  = 0

    for i, record in enumerate(photos, 1):
        if record.get("species_scientific"):
            print(f"  [{i:2d}/{total}] {record['filename']:30s} skip (already identified)")
            continue

        path = PHOTO_DIR / record["filename"]
        lat  = record.get("lat")
        lng  = record.get("lng")

        try:
            result  = score_image(path, token, lat, lng)
            results = result.get("results", [])
            if results:
                top   = results[0]
                taxon = top.get("taxon", {})
                record["species_scientific"] = taxon.get("name", "")
                record["species_common_en"]  = taxon.get("preferred_common_name", "")
                record["species_confidence"] = round(top.get("combined_score", 0), 4)
                print(f"  [{i:2d}/{total}] {record['filename']:30s} → {record['species_scientific']} "
                      f"({record['species_common_en']}) {record['species_confidence']:.2f}")
            else:
                print(f"  [{i:2d}/{total}] {record['filename']:30s} → no result")
            done += 1
        except Exception as e:
            print(f"  [{i:2d}/{total}] {record['filename']:30s} ERROR: {e}")

        DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        time.sleep(1.0)

    print(f"\nDone. {done}/{total} photos processed.")


if __name__ == "__main__":
    main()
