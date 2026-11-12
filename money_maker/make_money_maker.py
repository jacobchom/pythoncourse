"""Two-roller 'money maker' magic prop. Everything printed except one strip
of thin black cloth/ribbon (~160 x 550 mm).

How it works
  The cloth is wound S-shaped between the rollers: one end clipped into the
  TOP roller, the other into the BOTTOM roller. A real note is wound up inside
  the cloth on the bottom roller. Turn the top knob: the cloth winds onto the
  top roller, swallowing the blank paper you feed in from the front, while the
  note unwinds from the bottom roller and slides out the back.

Run: python3 make_money_maker.py  -> ./print (bed-ready STLs) and ./viewer.
Axes: X along the rollers, Y = paper direction (front is -Y), Z up. mm.
"""
import os
import numpy as np
import trimesh
from manifold3d import Manifold, CrossSection

HERE = os.path.dirname(os.path.abspath(__file__))

BODY = 170.0          # roller body length (fits notes up to 166 long)
INNER = BODY + 2.0    # gap between the side plates
PT = 6.0              # side plate thickness
R = 15.0              # roller radius
AX = 4.0              # axle radius
CLR = 0.3
ZB = 32.0             # bottom roller centre
ZA = ZB + 2 * R + 2.5 # top roller centre (2.5 mm gap for cloth build-up)
NIP = (ZB + R + ZA - R) / 2
TRAY_T = 2.0


def box(x0, y0, z0, x1, y1, z1):
    return Manifold.cube([x1 - x0, y1 - y0, z1 - z0]).translate([x0, y0, z0])


def cyl_x(r, x0, x1, y, z, n=96):
    return Manifold.cylinder(x1 - x0, r, r, n).rotate([0, 90, 0]).translate([x0, y, z])


def yz_prism(pts, x0, x1):
    """Polygon in the YZ plane, extruded along X."""
    m = Manifold.extrude(CrossSection([pts]), x1 - x0)          # (y, z, x)
    return m.warp_batch(lambda v: np.stack([v[:, 2] + x0, v[:, 0], v[:, 1]], axis=1))


def hexagon(r, h):
    return Manifold.cylinder(h, r, r, 6)


# ---- side plate (print 2; same part for left and right) ---------------------
PLATE = [(-30, 0), (30, 0), (30, 20), (24, 28), (24, 72), (30, 80), (30, 98),
         (-30, 98), (-30, 80), (-24, 72), (-24, 28), (-30, 20)]
BARS = [(-17, 9), (17, 9), (0, 91)]                 # (y, z) centres, 10x10 bars
TAB_Y = (-22.0, -18.0)                              # tray tab slot, front side


def make_plate():
    """Built as the LEFT plate: inner face at x=0, outer at x=-PT."""
    m = yz_prism(PLATE, -PT, 0)
    # raised rim around the outer face for a machined look
    inner = [(y * 0.82, 10 + (z - 10) * 0.86) for y, z in PLATE]
    m += yz_prism(PLATE, -PT - 1.2, -PT) - yz_prism(inner, -PT - 2, -PT + 0.1)
    for zc in (ZB, ZA):
        m += cyl_x(9, -PT - 2.2, -PT, 0, zc)                        # bearing boss
        m -= cyl_x(AX + CLR, -PT - 3, 1, 0, zc, 48)                 # axle hole
    for y, z in [(-25, 7), (25, 7), (-25, 91), (25, 91), (-19, 48), (19, 48)]:
        m += hexagon(2.8, 1.6).rotate([0, -90, 0]).translate([-PT - 1.2, y, z])  # bolt heads
    for y, z in BARS:                                               # bar sockets
        m -= box(-5.2, y - 3.15, z - 3.15, 0.1, y + 3.15, z + 3.15)
    for s in (-1, 1):                                               # tray tab slots
        y0, y1 = sorted((s * TAB_Y[0], s * TAB_Y[1]))
        m -= box(-4.2, y0 - 0.2, NIP - TRAY_T - 0.25, 0.1, y1 + 0.2, NIP + 0.25)
    return m


# ---- bars (print 3) -----------------------------------------------------------
def make_bar(y, z):
    m = box(0, y - 5, z - 5, INNER, y + 5, z + 5)
    m += box(-5, y - 3, z - 3, 0, y + 3, z + 3) + box(INNER, y - 3, z - 3, INNER + 5, y + 3, z + 3)
    return m


# ---- rollers (print 2) --------------------------------------------------------
KEY_W, KEY_D = 2.2, 7.0


def make_roller(zc):
    m = cyl_x(R, 1, 1 + BODY, 0, zc)
    m += cyl_x(AX, -PT, 1, 0, zc, 48)                        # left axle
    shaft = cyl_x(AX, 1 + BODY, INNER + PT + 15.5, 0, zc, 48)  # right axle + knob shaft
    shaft -= box(INNER + PT + 2, -10, zc + AX - 1, INNER + PT + 19, 10, zc + 10)   # D flat
    m += shaft
    # cloth clamp slot along the top of the roller
    m -= box(5, -KEY_W / 2, zc + R - KEY_D, BODY - 3, KEY_W / 2, zc + R + 1)
    return m


def make_key():
    """Wedge strip that pinches the cloth into the roller slot (print 2)."""
    pts = [(-0.85, 0), (0.85, 0), (1.15, KEY_D - 0.4), (-1.15, KEY_D - 0.4)]
    return yz_prism(pts, 5.5, BODY - 3.5)


# ---- knobs (print 2) ----------------------------------------------------------
def make_knob():
    m = Manifold.cylinder(16, 11, 11, 96)
    m += Manifold.cylinder(3, 11, 9, 96).translate([0, 0, 16])          # chamfered cap
    for i in range(20):
        a = 2 * np.pi * i / 20
        m -= Manifold.cylinder(18, 1.1, 1.1, 16).translate([11.6 * np.cos(a), 11.6 * np.sin(a), -1])
    hole = Manifold.cylinder(14, AX + 0.15, AX + 0.15, 48).translate([0, 0, -1])
    hole -= box(-10, AX - 1 + 0.1, -2, 10, 10, 20)                       # matching D
    return m - hole


# ---- paper trays (print 2; front and back are the same part) ----------------
def make_tray(front=True):
    y_tip, y_end = 17.0, 75.0
    m = box(0.3, y_tip, NIP - TRAY_T, INNER - 0.3, y_end, NIP)
    m += box(-3.9, 18.0, NIP - TRAY_T, 0.3, 22.0, NIP)
    m += box(INNER - 0.3, 18.0, NIP - TRAY_T, INNER + 3.9, 22.0, NIP)
    m += box(INNER / 2 - 25, y_end - 6, NIP - TRAY_T - 1.5, INNER / 2 + 25, y_end, NIP)  # stiff lip
    for x0 in (6, INNER - 12):                                           # legs
        m += box(x0, y_end - 6, 0, x0 + 6, y_end, NIP - TRAY_T)
    if front:
        m = m.mirror([0, 1, 0])
    return m


def save(m, folder, name):
    os.makedirs(folder, exist_ok=True)
    mesh = m.to_mesh()
    t = trimesh.Trimesh(vertices=mesh.vert_properties[:, :3], faces=mesh.tri_verts)
    t.export(os.path.join(folder, name))
    return t


def on_bed(m):
    b = m.bounding_box()
    return m.translate([-b[0], -b[1], -b[2]])


if __name__ == "__main__":
    left = make_plate()
    right = left.mirror([1, 0, 0]).translate([INNER, 0, 0])
    bars = [make_bar(y, z) for y, z in BARS]
    rb, ra = make_roller(ZB), make_roller(ZA)
    keys = [make_key().translate([0, 0, zc + R - KEY_D + 0.4]) for zc in (ZB, ZA)]
    knob = make_knob()
    knobs = [knob.rotate([0, 0, 90]).rotate([0, 90, 0]).translate([INNER + PT + 3, 0, zc]) for zc in (ZB, ZA)]
    tf, tb = make_tray(True), make_tray(False)

    frame = left + right
    for b in bars:
        frame += b
    pairs = {"roller B vs frame": rb ^ frame, "roller A vs frame": ra ^ frame,
             "rollers": ra ^ rb, "trays vs frame": (tf + tb) ^ frame,
             "trays vs rollers": (tf + tb) ^ (ra + rb), "knobs vs frame": (knobs[0] + knobs[1]) ^ frame,
             "knobs vs rollers": knobs[0] ^ rb, "key vs roller": keys[0] ^ rb, "knob vs knob": knobs[0] ^ knobs[1]}
    for k, v in pairs.items():
        print(f"overlap {k:20s} {v.volume():8.2f}")

    P = os.path.join(HERE, "print")
    to_stand = lambda m: on_bed(m.rotate([0, -90, 0]))     # roller axis vertical
    for m, n in [(on_bed(left.rotate([0, 90, 0])), "side_plate_x2.stl"),
                 (on_bed(bars[0]), "bar_x3.stl"),
                 (to_stand(rb), "roller_x2.stl"),
                 (on_bed(make_key().rotate([0, 90, 0])), "cloth_clip_x2.stl"),
                 (on_bed(knob), "knob_x2.stl"),
                 (on_bed(tb.mirror([0, 0, 1])), "paper_tray_x2.stl")]:
        t = save(m, P, n)
        print(f"{n:22s} {np.round(t.extents, 1)} watertight={t.is_watertight}")

    V = os.path.join(HERE, "viewer")
    for m, n in [(frame, "frame.stl"), (rb + knobs[0], "roller.stl"),
                 (tf + tb, "trays.stl")]:
        save(m, V, n)
    print(f"ZB={ZB} ZA={ZA} NIP={NIP}  overall {INNER + 2*PT + 22:.0f} x 150 x 98")
