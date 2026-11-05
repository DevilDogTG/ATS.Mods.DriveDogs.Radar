# DriveDogs: Radar (ATS)

American Truck Simulator mod: every **fining speed camera** of the base game and all SCS map DLCs blinks a
red police-style strobe, and every **police speed trap**'s parked patrol car flashes its lightbar, so you see
them before they see you. No sounds, no truck parts, tiny package.

The ATS twin of the ETS2 DriveDogs Radar mod, with the same strobe. ATS has far fewer of them than ETS2:

| | Models | Placed on the map (ATS 1.62.1.1) |
|---|---|---|
| Speed cameras (`speedcam.11` hookup) | `pole_sc`, `speedcamera_pole`, `speedcamera_stand` | 5, all `speedcamera_pole` |
| Police speed traps (`police_sc`) | `police_sc` | 16 |

- Cameras: only the models' `.pmg` files are overridden (strobe locators added); base models, collisions and
  materials are reused.
- Traps: `police_sc.pmg` points its parked police car at the base game's `police.always.parked.physics.hooter`
  variant (lightbar forced on) in place of `...driver`. The car and the speed check are unchanged.
- The Iowa camera prop (`ia_speedcamera`) is decoration with no hookup: it never fines you, so it gets no strobe.

Want a "camera ahead" warning on a dashboard, phone or LEDs? Detection lives in the
**DevDogs.TruckSimulator** SimHub plugin, which can use the same camera database (`data/camera_db.csv`; rows
carry a `kind` of `camera` or `trap`).

## Install
Copy `drivedog_radar_v<version>.scs` into `Documents\American Truck Simulator\mod` and enable it in the Mod
Manager. Optional for multiplayer (`mp_mod_optional`).

## Build (after a game update)
Requires Python 3 + Pillow, `scs_packer` on `PATH`, and the extracted ATS game reference
(`<reference root>/base/<X.Y>`, resolved through the `scs-mod-developer` profile helpers;
`GAME_VERSION` in `tools/scs_common.py`). The tools refuse to run unless `pack.config.json` says `"game": "ats"`.

```bash
python tools/scan_cameras.py        # data/cameras.json  - camera and trap models
python tools/extract_camera_db.py   # data/camera_db.csv + .meta.json - placed cameras and traps (game version)
python tools/generate_cover.py      # src/cover.jpg (version badge from VERSION)
python tools/build_mod.py --version "$(cat VERSION)"   # lint + output/drivedog_radar_v<version>.scs
```

Strobe positions come from `data/placement_overrides.json` (hand-placed) or a pole heuristic. The camera DB
is copied into the SimHub plugin repo only for the **same game version** (`data/camera_db.meta.json`).

## History
Ported from the ETS2 DriveDogs Radar 1.0.0 tools; the ETS2 repo's `docs/POC-PLAN.md` records the proof of
concept, including why an in-cab indicator was not possible as a mod.
