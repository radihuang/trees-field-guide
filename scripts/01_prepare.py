#!/usr/bin/env python3
"""
01_prepare.py
Read EXIF, apply manual GPS, detect near-duplicates, reverse-geocode.
Output: trees.json (no species data yet)
"""

import csv
import json
import math
import re
import subprocess
import time
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PHOTO_DIR = ROOT / "photos"
OUTPUT = ROOT / "trees.json"

MANUAL_GPS = {
    "IMG_0133.jpeg": (36.6983, 137.8601),  # Hakuba, Nagano, Japan
    "IMG_1132.jpeg": (36.6983, 137.8601),  # Hakuba, Nagano, Japan
    "IMG_6137.jpeg": (24.1330, 121.2830),  # Hehuanshan, Taiwan
}
NO_GPS = {"IMG_7464.jpeg"}

DUPE_SECONDS = 300    # 5 minutes
DUPE_METERS  = 200


def dms_to_decimal(s):
    if not s:
        return None
    m = re.match(r'(\d+) deg (\d+)\' ([\d.]+)" ([NSEW])', s.strip())
    if not m:
        return None
    d, mn, sec, direction = m.groups()
    v = float(d) + float(mn) / 60 + float(sec) / 3600
    return -v if direction in ("S", "W") else v


def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = (math.sin(math.radians(lat2 - lat1) / 2) ** 2
         + math.cos(p1) * math.cos(p2)
         * math.sin(math.radians(lon2 - lon1) / 2) ** 2)
    return 2 * R * math.asin(math.sqrt(a))


def reverse_geocode(lat, lng):
    url = (f"https://nominatim.openstreetmap.org/reverse"
           f"?lat={lat}&lon={lng}&format=json&accept-language=en")
    req = urllib.request.Request(url, headers={"User-Agent": "trees-field-guide/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        addr = data.get("address", {})
        parts = []
        for key in ("suburb", "town", "city", "county", "state", "country"):
            if addr.get(key) and addr[key] not in parts:
                parts.append(addr[key])
            if len(parts) == 2:
                break
        return ", ".join(parts) or data.get("display_name", "")
    except Exception as e:
        return f"[geocode error: {e}]"


def read_exif():
    result = subprocess.run(
        ["exiftool", "-csv", "-FileName", "-DateTimeOriginal",
         "-GPSLatitude", "-GPSLongitude", str(PHOTO_DIR)],
        capture_output=True, text=True
    )
    rows = list(csv.DictReader(result.stdout.splitlines()))
    return rows


def main():
    print("Reading EXIF …")
    rows = read_exif()

    records = []
    for row in rows:
        fname = Path(row["SourceFile"]).name
        if not fname.lower().endswith((".jpeg", ".jpg")):
            continue

        dt_str = row.get("DateTimeOriginal", "")
        try:
            dt = datetime.strptime(dt_str, "%Y:%m:%d %H:%M:%S")
            date_iso  = dt.strftime("%Y-%m-%d")
            timestamp = dt.timestamp()
        except ValueError:
            date_iso  = ""
            timestamp = 0.0

        if fname in MANUAL_GPS:
            lat, lng = MANUAL_GPS[fname]
        elif fname in NO_GPS:
            lat, lng = None, None
        else:
            lat = dms_to_decimal(row.get("GPSLatitude"))
            lng = dms_to_decimal(row.get("GPSLongitude"))

        records.append({
            "id":                  fname.rsplit(".", 1)[0],
            "filename":            fname,
            "date":                date_iso,
            "timestamp":           timestamp,
            "lat":                 lat,
            "lng":                 lng,
            "location_en":         "",
            "species_scientific":  "",
            "species_common_en":   "",
            "species_common_zh":   "",
            "species_confidence":  0.0,
            "personal_note":       "",
        })

    records.sort(key=lambda x: x["timestamp"])

    # ── near-duplicate detection ──────────────────────────────────────────────
    print(f"\nScanning {len(records)} photos for near-duplicates …")
    used   = set()
    groups = []

    for i, a in enumerate(records):
        if i in used:
            continue
        group = [i]
        for j in range(i + 1, len(records)):
            b = records[j]
            if j in used:
                continue
            if abs(a["timestamp"] - b["timestamp"]) > DUPE_SECONDS:
                continue
            if a["lat"] and b["lat"]:
                if haversine(a["lat"], a["lng"], b["lat"], b["lng"]) <= DUPE_METERS:
                    group.append(j)
                    used.add(j)
            elif a["lat"] is None and b["lat"] is None:
                group.append(j)
                used.add(j)
        if len(group) > 1:
            groups.append(group)
        used.add(i)

    if groups:
        print(f"\nFound {len(groups)} potential duplicate group(s):\n")
        for k, g in enumerate(groups, 1):
            print(f"  Group {k}:")
            for idx in g:
                r = records[idx]
                print(f"    {r['filename']}  {r['date']}")
    else:
        print("No near-duplicates found.")

    # ── reverse geocode ───────────────────────────────────────────────────────
    with_gps = [r for r in records if r["lat"]]
    print(f"\nReverse geocoding {len(with_gps)} photos …")
    cache = {}
    for i, r in enumerate(records):
        if not r["lat"]:
            continue
        key = (round(r["lat"], 3), round(r["lng"], 3))
        if key not in cache:
            loc = reverse_geocode(r["lat"], r["lng"])
            cache[key] = loc
            print(f"  [{i+1:3d}] {r['filename']:30s} → {loc}")
            time.sleep(1.1)
        r["location_en"] = cache[key]

    # ── save ─────────────────────────────────────────────────────────────────
    data = {"photos": records}
    OUTPUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSaved {len(records)} records → {OUTPUT}")
    print("Next: review duplicates, then run scripts/02_identify.py")


if __name__ == "__main__":
    main()
