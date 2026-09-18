"""M3BW interactive product — single source of semantic truth.

Mirrors the seismograph project's semantic_map.py: both the GLB exporter
(node extras) and the manifest builder (explode vectors, inspect layouts,
camera presets) consume this module so they can never disagree.

Logical structure:

    DEVICE_ROOT
    ├── SYS_TOP              lid + screws + antenna puck/boss + coax
    ├── SYS_ACQUISITION      main PCB (HERO) + on-board GEO_* dressing
    ├── SYS_POWER            two Li-ion packs + leads
    ├── SYS_SENSOR           ADI MEMS accelerometer (lone chip part)
    ├── SYS_FIELD_PLATFORM   body shell + base + magnet feet + wall ports
    └── SYS_TRANSMISSION     semantic only — radio chain FX, no moving parts
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Functional systems. explode = per-system vector in Blender coords (cm);
# converted Z-up -> Y-up at manifest write time.
# ---------------------------------------------------------------------------

SYSTEMS: dict[str, dict[str, object]] = {
    "SYS_TOP": {
        "displayName": "Top Assembly",
        "oneLiner": "Lid, screws and the 4G antenna puck.",
        "order": 0,
        "parts": ("PRT_LID", "PRT_COAX"),
        "explode": [0.0, 0.0, 9.0],
    },
    "SYS_ACQUISITION": {
        "displayName": "Acquisition System",
        "oneLiner": "Main PCB: STM32 host, Air724 modem and analog front-end.",
        "order": 1,
        "parts": ("PRT_PCB",),
        "explode": [0.0, 0.0, 5.0],
    },
    "SYS_POWER": {
        "displayName": "Power System",
        "oneLiner": "Two Li-ion packs feeding the board through JST leads.",
        "order": 2,
        "parts": ("PRT_BATL", "PRT_BATR"),
        "explode": [0.0, 0.0, 2.5],
    },
    "SYS_SENSOR": {
        "displayName": "Sensing System",
        "oneLiner": "ADI MEMS accelerometer — the vibration pickup on the board.",
        "order": 3,
        "parts": ("PRT_ADXL",),
        # same vector as ACQUISITION: the chip rides the board in the explode
        "explode": [0.0, 0.0, 5.0],
    },
    "SYS_FIELD_PLATFORM": {
        "displayName": "Field Platform",
        "oneLiner": "Housing, base plate, mounting magnets and wall ports.",
        "order": 4,
        "parts": ("PRT_BODY", "PRT_BASE", "PRT_MAG_01", "PRT_MAG_02",
                  "PRT_MAG_03", "PRT_MAG_04", "PRT_BULKHEAD", "PRT_USB"),
        "explode": [0.0, 0.0, -1.2],
    },
    "SYS_TRANSMISSION": {
        "displayName": "Transmission",
        "oneLiner": "Air724 modem -> coax -> puck antenna -> cloud.",
        "order": 5,
        "parts": (),
        "explode": [0.0, 0.0, 0.0],
    },
}

# ---------------------------------------------------------------------------
# Physical parts. members = exact object names or name prefixes; every object
# not claimed by another part falls back to PRT_PCB (board + all on-board
# components). anchor = Empty position (cm, Blender coords).
# ---------------------------------------------------------------------------

PARTS: dict[str, dict[str, object]] = {
    "PRT_LID": {
        "semanticId": "CMP_LID_ASSEMBLY", "displayName": "Lid & Antenna Assembly",
        "role": "SECONDARY", "systemId": "SYS_TOP", "anchor": (0, 0, 5.2),
        "members": ("Lid_Plate", "Lid_Screw_", "Antenna_", "Puck_Antenna"),
    },
    "PRT_COAX": {
        "semanticId": "CMP_COAX_FEED", "displayName": "Antenna Coax Feed",
        "role": "SUPPORT", "systemId": "SYS_TOP", "anchor": (0.6, -1.6, 3.6),
        "members": ("Coax_ANT",),
    },
    "PRT_PCB": {
        "semanticId": "CMP_MAIN_PCB", "displayName": "Acquisition Main Board",
        "role": "HERO", "systemId": "SYS_ACQUISITION", "anchor": (0, 0, 1.6),
        "members": (),      # catch-all: every unclaimed object
        "inspect": (0, 0, 3.8),
    },
    "PRT_ADXL": {
        "semanticId": "CMP_ADXL_SENSOR", "displayName": "ADI MEMS Accelerometer",
        "role": "HERO", "systemId": "SYS_SENSOR", "anchor": (1.85, -3.2, 1.62),
        "members": ("U3_ADXL",),
        "inspect": (0, 0, 4.2),
    },
    "PRT_BATL": {
        "semanticId": "CMP_BATTERY_L", "displayName": "Battery Pack L",
        "role": "PRIMARY", "systemId": "SYS_POWER", "anchor": (-3.3, 0, 2.7),
        "members": ("Battery_L", "Wire_BatL"),
        "inspect": (-4.2, 0, 3.0),
    },
    "PRT_BATR": {
        "semanticId": "CMP_BATTERY_R", "displayName": "Battery Pack R",
        "role": "PRIMARY", "systemId": "SYS_POWER", "anchor": (3.3, 0, 2.7),
        "members": ("Battery_R", "Wire_BatR"),
        "inspect": (4.2, 0, 3.0),
    },
    "PRT_BODY": {
        "semanticId": "CMP_BODY_SHELL", "displayName": "Body Shell",
        "role": "SECONDARY", "systemId": "SYS_FIELD_PLATFORM",
        "anchor": (0, 0, 2.6), "members": ("Body_Shell",),
        "inspectable": False,
    },
    "PRT_BASE": {
        "semanticId": "CMP_BASE_PLATE", "displayName": "Base Plate",
        "role": "SECONDARY", "systemId": "SYS_FIELD_PLATFORM",
        "anchor": (0, 0, 0.34), "members": ("Base_Plate",),
        "inspectable": False,
    },
    "PRT_MAG_01": {
        "semanticId": "CMP_MAGNET_01", "displayName": "Magnet Foot 01",
        "role": "SUPPORT", "systemId": "SYS_FIELD_PLATFORM",
        "anchor": (4.5, 2.5, -0.25), "members": ("Magnet_Foot_01",),
        "inspectable": False, "explodeOffset": (0, 0, -1.5),
    },
    "PRT_MAG_02": {
        "semanticId": "CMP_MAGNET_02", "displayName": "Magnet Foot 02",
        "role": "SUPPORT", "systemId": "SYS_FIELD_PLATFORM",
        "anchor": (-4.5, 2.5, -0.25), "members": ("Magnet_Foot_02",),
        "inspectable": False, "explodeOffset": (0, 0, -1.5),
    },
    "PRT_MAG_03": {
        "semanticId": "CMP_MAGNET_03", "displayName": "Magnet Foot 03",
        "role": "SUPPORT", "systemId": "SYS_FIELD_PLATFORM",
        "anchor": (4.5, -2.5, -0.25), "members": ("Magnet_Foot_03",),
        "inspectable": False, "explodeOffset": (0, 0, -1.5),
    },
    "PRT_MAG_04": {
        "semanticId": "CMP_MAGNET_04", "displayName": "Magnet Foot 04",
        "role": "SUPPORT", "systemId": "SYS_FIELD_PLATFORM",
        "anchor": (-4.5, -2.5, -0.25), "members": ("Magnet_Foot_04",),
        "inspectable": False, "explodeOffset": (0, 0, -1.5),
    },
    "PRT_BULKHEAD": {
        "semanticId": "CMP_BULKHEAD", "displayName": "Bulkhead Connector",
        "role": "SUPPORT", "systemId": "SYS_FIELD_PLATFORM",
        "anchor": (0, -4.2, 3.2),
        "members": ("Bulkhead_", "Harness_wire_"),
        "inspectable": False, "explodeOffset": (0, -2.2, 0),
    },
    "PRT_USB": {
        "semanticId": "CMP_USB_PORT", "displayName": "USB-C Service Port",
        "role": "SUPPORT", "systemId": "SYS_FIELD_PLATFORM",
        "anchor": (1.0, 4.2, 3.2), "members": ("USB_",),
        "inspectable": False, "explodeOffset": (0, 2.2, 0),
    },
}

# ---------------------------------------------------------------------------
# Tagged children (entities that live inside a part's subtree — they fade and
# raycast individually but never move on their own).
# ---------------------------------------------------------------------------

CHILD_TAGS: dict[str, dict[str, object]] = {
    "RADIO_MOD": {
        "semanticId": "CMP_RADIO_MODULE", "displayName": "Air724 4G Modem",
        "type": "component", "role": "PRIMARY", "systemId": "SYS_ACQUISITION",
        "sourcePart": "PRT_PCB", "members": ("U2_AIR724",),
    },
    "RADIO_ANT": {
        "semanticId": "CMP_RADIO_ANTENNA", "displayName": "4G Puck Antenna",
        "type": "component", "role": "PRIMARY", "systemId": "SYS_TRANSMISSION",
        "sourcePart": "PRT_LID", "members": ("Puck_Antenna",),
    },
    "GEO_STM32": {
        "semanticId": "GEO_STM32", "displayName": "STM32 Host MCU",
        "type": "geometry", "role": "SUPPORT", "systemId": "SYS_ACQUISITION",
        "sourcePart": "PRT_PCB", "members": ("U1_STM32",),
    },
    "GEO_ANT_SMA": {
        "semanticId": "GEO_ANT_SMA", "displayName": "4G Antenna SMA",
        "type": "geometry", "role": "SUPPORT", "systemId": "SYS_ACQUISITION",
        "sourcePart": "PRT_PCB", "members": ("J3_ANT",),
    },
    "GEO_GNSS_SMA": {
        "semanticId": "GEO_GNSS_SMA", "displayName": "GNSS Antenna SMA",
        "type": "geometry", "role": "SUPPORT", "systemId": "SYS_ACQUISITION",
        "sourcePart": "PRT_PCB", "members": ("J6_ANT_GNSS",),
    },
    "GEO_USB_JST": {
        "semanticId": "GEO_USB_JST", "displayName": "USB Data JST",
        "type": "geometry", "role": "SUPPORT", "systemId": "SYS_ACQUISITION",
        "sourcePart": "PRT_PCB", "members": ("J1", "J1_p"),
    },
    "GEO_BULK_JST": {
        "semanticId": "GEO_BULK_JST", "displayName": "Bulkhead Harness JST",
        "type": "geometry", "role": "SUPPORT", "systemId": "SYS_ACQUISITION",
        "sourcePart": "PRT_PCB", "members": ("JB_BULK",),
    },
}

# ---------------------------------------------------------------------------
# Camera presets — Blender coords (cm); yup() converts at manifest write.
# ---------------------------------------------------------------------------

CAMERA_PRESETS: dict[str, dict[str, object]] = {
    "overviewHero":       {"position": (30, -30, 24),  "target": (0, 0, 3),   "lens_mm": 55},
    "architectureHero":   {"position": (42, -42, 31),  "target": (0, 0, 5),   "lens_mm": 55},
    "SYS_SENSOR": {
        "context": {"position": (23, -22, 17),   "target": (0, 0, 3),   "lens_mm": 55},
        "inspect": {"position": (1.6, -3.0, 5.6), "target": (0, 0, 4.2), "lens_mm": 55},
    },
    "SYS_ACQUISITION": {
        "context": {"position": (24, -23, 17),   "target": (0, 0, 3),   "lens_mm": 55},
        "inspect": {"position": (7, -12, 10.5),  "target": (0, 0, 3.8), "lens_mm": 55},
    },
    "SYS_POWER": {
        "context": {"position": (24, -21, 15),   "target": (0, 0, 3),   "lens_mm": 55},
        "inspect": {"position": (11, -24, 13),   "target": (0, 0, 3.1), "lens_mm": 55},
    },
    "SYS_TRANSMISSION": {
        "context": {"position": (31, -20, 23),   "target": (0, 0, 4.5), "lens_mm": 55},
    },
}


def part_of(name: str) -> str | None:
    """Resolve an object name to its part id (PRT_PCB is the catch-all)."""
    for pid, spec in PARTS.items():
        for m in spec["members"]:  # type: ignore[index]
            if name == m or name.startswith(m):
                return pid
    return None


def child_tag_of(name: str) -> str | None:
    for tid, spec in CHILD_TAGS.items():
        for m in spec["members"]:  # type: ignore[index]
            if name == m or name.startswith(m):
                return tid
    return None


def validate() -> None:
    seen: set[str] = set()
    for sys_id, spec in SYSTEMS.items():
        for pid in spec["parts"]:  # type: ignore[index]
            if pid in seen:
                raise ValueError(f"{pid} assigned to two systems")
            seen.add(pid)
            if PARTS[pid]["systemId"] != sys_id:
                raise ValueError(f"{pid} systemId disagrees with SYSTEMS[{sys_id}]")
    missing = seen - set(PARTS)
    if missing:
        raise ValueError(f"unknown parts in systems: {missing}")
