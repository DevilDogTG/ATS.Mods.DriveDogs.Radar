#!/usr/bin/env python3
"""Find every speed enforcement model the map can place -> data/cameras.json.

Two kinds (ATS 1.61):
  camera  the .pmg carries a `speed_camera` hookup (`speedcam.11` / `speedcam.r`, unit/hookup/speed_camera.sii);
          `speedcam.toll` is not speed enforcement and is skipped. ATS: pole_sc, speedcamera_pole,
          speedcamera_stand.
  trap    a parked police speed trap: a `police.always.parked.physics.driver` parked car plus a `police_car.*`
          speed check (unit/hookup/police_car.sii). ATS: police_sc.

Candidates are the models of the `sign_model` units in def/world/sign*.sii and the `model_def` units in
def/world/model*.sii: ATS places its cameras as model items (ETS2 places them as sign items), and the map
refers to either by that unit's token (see extract_camera_db.py). A full scan of all 15,386 model_def/sign
models and 1,783 prefab models in 1.61.3.1 found no other carrier, so the model_defs are cut to the paths
that could hold one.

usage: python tools/scan_cameras.py [--base <reference root>/base/<version>]
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
from scs_common import Pmg, default_base, megapack  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UNIT = re.compile(r"^\s*(sign_model|model_def)\s*:\s*([\w.]+)\s*\{(.*?)^\s*\}", re.M | re.S)
MODEL_DESC = re.compile(r'model_desc\s*:\s*"/?([^"]+)\.pmd"')
MODEL_DEF_PATHS = re.compile(r"sign/|street|camera|police|weigh")
TRAP_CAR = "police.always.parked.physics.driver"


def units_by_model(base):
    """{model path without extension: [sign_model / model_def unit names]} from def/world/{sign,model}*.sii."""
    by_model = {}
    world = os.path.join(base, "def", "world")
    for f in sorted(os.listdir(world)):
        if not (f.startswith(("sign", "model")) and f.endswith(".sii")):
            continue
        with open(os.path.join(world, f), encoding="utf-8", errors="ignore") as fh:
            text = fh.read()
        for cls, unit, body in UNIT.findall(text):
            m = MODEL_DESC.search(body)
            if m and (cls == "sign_model" or MODEL_DEF_PATHS.search(m.group(1))):
                by_model.setdefault(m.group(1), []).append(unit)
    return by_model


def kind_of(hooks):
    if any(h.startswith("speedcam.") and h != "speedcam.toll" for h in hooks):
        return "camera"
    if TRAP_CAR in hooks and any(h.startswith("police_car.") for h in hooks):
        return "trap"
    return None


def find_camera_models(base, by_model):
    mp = megapack()
    rels = [m + ".pmg" for m in sorted(by_model) if mp.ref_exists(Path(base), m + ".pmg")]
    paths = mp.ref_fetch(Path(base), rels)   # one extractor run per archive; no-op when on disk
    found = {}
    for rel, path in zip(rels, paths):
        with open(path, "rb") as fh:
            data = fh.read()
        if b"speedcam." not in data and TRAP_CAR.encode() not in data:
            continue
        pmg = Pmg(data)
        locs = [l for l in pmg.locators() if l[4]]
        kind = kind_of({l[4] for l in locs})
        if not kind:
            continue
        model = rel[:-4]
        found[model] = {
            "model": model,
            "kind": kind,
            "hookups": [{"name": l[0], "hookup": l[4], "pos": [round(v, 3) for v in l[1]],
                         "quat": [round(v, 4) for v in l[3]]} for l in locs],
            "bbox_min": [round(v, 3) for v in pmg.bbox_min],
            "bbox_max": [round(v, 3) for v in pmg.bbox_max],
            "units": sorted(by_model[model]),
        }
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=None, help="default: <host reference root>/base/<GAME_VERSION>")
    ap.add_argument("--out", default=os.path.join(ROOT, "data", "cameras.json"))
    args = ap.parse_args()
    base = args.base or default_base()

    by_model = units_by_model(base)
    cameras = find_camera_models(base, by_model)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", newline="\n") as fh:
        json.dump({"base": os.path.basename(base.rstrip("/\\")),
                   "cameras": [cameras[k] for k in sorted(cameras)]}, fh, indent=1)
    kinds = [c["kind"] for c in cameras.values()]
    print(f"{kinds.count('camera')} camera + {kinds.count('trap')} trap models "
          f"(of {len(by_model)} candidates) -> {args.out}")


if __name__ == "__main__":
    main()
