#!/usr/bin/env python3
"""Extract world positions of every speed camera and police trap placed on the map -> data/camera_db.csv.

Sign and model items live in the sector `.base` and `.aux` files of map/usa. Instead of parsing every item
type, we look for the token of each `sign_model` / `model_def` unit from data/cameras.json and validate the
fixed item header in front of it (same layout for both item types):

  u32 type (36 = sign, 5 = model) | u64 uid | f32 kdop_min[5] | f32 kdop_max[5] | u32 flags | u8 view_dist | u64 model

kdop_min/max[0..2] are the item's world-space AABB (x, y, z), so its centre is the camera position in
the same coordinate system the telemetry SDK reports (`truck.world.placement`). The type check matters:
short unit tokens (`model.225`, `model.226`) also match `sign.225`/`sign.226` and random bytes.

usage: python tools/extract_camera_db.py [--base ...] [--cameras data/cameras.json]
"""
import argparse
import csv
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(__file__))
from scs_common import GAME, default_base, token  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ITEM_TYPES = {"sign": 36, "model": 5}   # unit prefix -> map item type
MAP = "usa"
COLUMNS = ["uid", "x", "y", "z", "kind", "unit", "model", "sector"]
# offsets relative to the model token
TYPE_AT, UID_AT, KDOP_AT = -57, -53, -45


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=None, help="default: <host reference root>/base/<GAME_VERSION>")
    ap.add_argument("--cameras", default=os.path.join(ROOT, "data", "cameras.json"))
    ap.add_argument("--out", default=os.path.join(ROOT, "data", "camera_db.csv"))
    args = ap.parse_args()
    args.base = args.base or default_base()

    with open(args.cameras) as fh:
        cameras = json.load(fh)["cameras"]
    units = {}
    for cam in cameras:
        for unit in cam["units"]:
            prefix, name = unit.split(".", 1)
            units[struct.pack("<Q", token(name))] = (ITEM_TYPES[prefix], unit, cam)

    sector_dir = os.path.join(args.base, "map", MAP)
    rows, seen, rejected = [], set(), 0
    for f in sorted(os.listdir(sector_dir)):
        if not f.endswith((".base", ".aux")):
            continue
        with open(os.path.join(sector_dir, f), "rb") as fh:
            data = fh.read()
        for packed, (item_type, unit, cam) in units.items():
            i = data.find(packed)
            while i >= 0:
                ok = i + TYPE_AT >= 0 and struct.unpack_from("<I", data, i + TYPE_AT)[0] == item_type
                if ok:
                    uid = struct.unpack_from("<Q", data, i + UID_AT)[0]
                    kmin = struct.unpack_from("<5f", data, i + KDOP_AT)
                    kmax = struct.unpack_from("<5f", data, i + KDOP_AT + 20)
                    if uid not in seen:
                        seen.add(uid)
                        c = [(kmin[k] + kmax[k]) / 2 for k in range(3)]
                        rows.append([f"{uid:016x}", round(c[0], 2), round(c[1], 2), round(c[2], 2), cam["kind"],
                                     unit, cam["model"].split("/")[-1], f.rsplit(".", 1)[0]])
                else:
                    rejected += 1
                i = data.find(packed, i + 1)

    rows.sort(key=lambda r: (r[7], r[0]))
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(COLUMNS)
        w.writerows(rows)
    # The DB is copied into other repos (DevDogs.TruckSimulator SimHub plugin) - always state which
    # game and game version it was extracted from, so a copy can be matched to the game it serves.
    kinds = [r[4] for r in rows]
    meta = {"game": GAME, "game_version": os.path.basename(args.base.rstrip("/\\")),
            "cameras": kinds.count("camera"), "traps": kinds.count("trap"),
            "source": "DriveDogs Radar (ATS) tools/extract_camera_db.py",
            "columns": COLUMNS,
            "kinds": {"camera": "fixed speed camera (fines on its own)",
                      "trap": "parked police car with a speed check (police_car hookup)"},
            "coordinates": "world space, metres - same as SCS telemetry truck.world.placement"}
    with open(os.path.splitext(args.out)[0] + ".meta.json", "w", newline="\n") as fh:
        json.dump(meta, fh, indent=1)
    print(f"{kinds.count('camera')} cameras + {kinds.count('trap')} traps placed on the map "
          f"({rejected} token hits rejected) -> {args.out}")


if __name__ == "__main__":
    main()
