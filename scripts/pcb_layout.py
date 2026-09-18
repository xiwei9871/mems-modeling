"""Shared PCB layout table for the M3BW mainboard (LKRL_DL_MB-Unifsd-M3BW_A0).

Board-local coords, units = cm. Origin at board center. The bulkhead
connector sits on the -y wall (photo-up in the reference close-up);
+x is photo-left in that photo. Positions eyeballed against
references/raw/Weixin Image_20260917173228_30_238.jpg using the
STM32 QFP100 body (1.4 cm) as scale. Estimated - not fabrication data.
"""

BOARD = {"x": 5.2, "y": 7.4, "t": 0.16, "corner_r": 0.08}
BOARD_TOP_Z = 1.51  # board bottom 1.35 on standoffs

MOUNT_HOLES = [(-2.35, -3.4), (2.35, -3.4), (-2.35, 3.4), (2.35, 3.4),
               (0.5, -0.15)]  # 4 corners + mid-board screw seen in photo
MOUNT_HOLE_R = 0.16

# id, type, center (x,y), size (w,d,h) or params; dir = long axis for jst
COMPONENTS = [
    {"id": "U1_STM32",  "type": "qfp",     "pos": (0.0, -1.5),    "size": (1.42, 1.42, 0.14), "pins": 25},
    {"id": "U2_AIR724", "type": "module",  "pos": (-0.85, 0.9),   "size": (2.4, 2.1, 0.24), "label": True},
    {"id": "U8",        "type": "ic",      "pos": (-1.75, -1.3),  "size": (0.9, 0.6, 0.12)},
    {"id": "U3_ADXL",   "type": "sensor",  "pos": (1.85, -3.2),   "size": (1.20, 1.20, 0.42)},
    {"id": "U5",        "type": "ic",      "pos": (1.3, -2.5),    "size": (0.45, 0.3, 0.1)},

    {"id": "J3_ANT",    "type": "sma",     "pos": (2.1, -2.0)},
    {"id": "J6_ANT_GNSS", "type": "sma",   "pos": (-1.5, 2.3)},
    {"id": "J1",        "type": "jst",     "pos": (2.3, -0.55),   "pins": 4, "dir": "y"},
    {"id": "J2",        "type": "jst",     "pos": (2.3, 0.9),     "pins": 2, "dir": "y"},
    {"id": "J4",        "type": "jst",     "pos": (2.3, 2.3),     "pins": 4, "dir": "y"},
    {"id": "J7_BATL",   "type": "jst",     "pos": (-2.3, -2.4),   "pins": 2, "dir": "x"},
    {"id": "JB_BULK",   "type": "jst_sm",  "pos": (0.4, -3.0),    "pins": 4, "dir": "x"},
    {"id": "L1",        "type": "inductor","pos": (1.2, 1.2),     "size": (0.7, 0.7, 0.35)},
    {"id": "L2",        "type": "inductor","pos": (0.3, 2.5),     "size": (0.7, 0.7, 0.35)},
    {"id": "Q1",        "type": "sot223",  "pos": (-1.9, -0.55),  "size": (0.66, 0.36, 0.16)},
    {"id": "Q2",        "type": "sot223",  "pos": (-1.3, -3.0),   "size": (0.66, 0.36, 0.16)},
    {"id": "XT1",       "type": "xtal",    "pos": (1.3, -0.9),    "size": (0.5, 0.32, 0.1)},
]

# passive sprinkle zones: rects (x0,y0,x1,y1) filled with small 0805/0603 boxes
PASSIVE_ZONES = [
    (-2.4, -3.3, -0.7, -1.8, 10),   # -x,-y corner field (photo upper-right)
    (0.9, -3.4, 2.2, -2.4, 8),      # +x,-y around Y1/J3
    (-2.3, -0.2, -0.9, 0.6, 7),     # around U8
    (-0.5, -1.1, 0.9, -0.2, 6),     # around STM32
    (-1.9, 1.6, -0.3, 3.3, 10),     # -x,+y field below module
    (0.7, 1.8, 2.3, 3.3, 8),        # +x,+y field near L1/L2
]
PASSIVE_SEED = 20260917
