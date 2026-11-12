"""Two-roller 'money maker' magic prop, minimalist gadget version.

A closed rounded black case with a thin slit front and back. Inside, two
rollers and a strip of black cloth do the trick. Everything is printed except
the cloth (~160 x 550 mm thin black fabric or ribbon).

How it works
  The cloth runs S-shaped between the rollers: one end clipped into the TOP
  roller, the other into the BOTTOM roller. A real note is wound up inside the
  cloth on the bottom roller. Turn the big knob: the cloth winds onto the top
  roller, swallowing the blank paper fed into the front slit, while the note
  unwinds from the bottom roller and slides out of the back slit.

Run: python3 make_money_maker.py  -> ./print (bed-ready STLs) and ./viewer.
Axes: X along the rollers, Y = paper direction (front is -Y), Z up. mm.
"""
import os
import numpy as np
import trimesh
from manifold3d import Manifold, CrossSection

HERE = os.path.dirname(os.path.abspath(__file__))

BODY = 170.0          # roller body length (fits notes up to 166 long)
INNER = BODY + 2.0    # space between the end caps
PT = 8.0              # end cap thickness
R = 15.0              # roller radius
AX = 4.0              # axle radius
CLR = 0.3
WALL = 3.0
HW, HT, RAD = 25.0, 77.0, 12.0   # case half-width, height, corner radius
ZB = 22.0                        # bottom roller centre
ZA = ZB + 2 * R + 2.5            # top roller centre (2.5 mm gap for the cloth)
NIP = (ZB + R + ZA - R) / 2      # 38.25
SLIT = (NIP - 1.5, NIP + 1.5)    # 3 mm slit front and back
LEDGE_TIP = 16.5                 # guide ledges reach in this far (|y|)


def box(x0, y0, z0, x1, y1, z1):
    return Manifold.cube([x1 - x0, y1 - y0, z1 - z0]).translate([x0, y0, z0])


def cyl_x(r, x0, x1, y, z, n=96):
    return Manifold.cylinder(x1 - x0, r, r, n).rotate([0, 90, 0]).translate([x0, y, z])


def rrect(y0, z0, y1, z1, r, n=16):
    pts = []
    for cy, cz, a0 in [(y1 - r, z0 + r, -90), (y1 - r, z1 - r, 0), (y0 + r, z1 - r, 90), (y0 + r, z0 + r, 180)]:
        for i in range(n + 1):
            a = np.radians(a0 + 90 * i / n)
            pts.append((cy + r * np.cos(a), cz + r * np.sin(a)))
    return pts


def yz_prism(pts, x0, x1):
    """Polygon(s) in the YZ plane, extruded along X from x0 to x1."""
    polys = pts if isinstance(pts[0][0], (list, tuple)) else [pts]
    m = Manifold.extrude(CrossSection([list(map(list, p)) for p in polys]), x1 - x0)
    return m.warp_batch(lambda v: np.stack([v[:, 2] + x0, v[:, 0], v[:, 1]], axis=1))


OUTER = rrect(-HW, 0, HW, HT, RAD)
INNERP = rrect(-HW + WALL, WALL, HW - WALL, HT - WALL, RAD - WALL)


def profile_solid(x0, x1):
    return yz_prism(OUTER, x0, x1) - yz_prism(INNERP, x0 - 1, x1 + 1)


# ---- shells: base (U) and cover (upside-down U); the slit is the gap between
BASE_TABS = [(0, WALL / 2), (-HW + WALL / 2, 16), (HW - WALL / 2, 16)]
COVER_TABS = [(0, HT - WALL / 2), (-HW + WALL / 2, 60), (HW - WALL / 2, 60)]


def tab(y, z, x0, x1, grow=0.0):
    hy, hz = (4 + grow, 1.5 + grow) if abs(y) < 1 else (1.5 + grow, 4 + grow)
    return box(x0, y - hy, z - hz, x1, y + hy, z + hz)


def make_base():
    m = profile_solid(0, INNER) ^ box(-1, -HW - 1, -1, INNER + 1, HW + 1, SLIT[0])
    for s in (-1, 1):   # 45-degree guide ledges: lead the paper into the nip
        w = HW - WALL
        m += yz_prism([(s * w, SLIT[0]), (s * LEDGE_TIP, SLIT[0]), (s * w, SLIT[0] - (w - LEDGE_TIP))][::s], 0, INNER)
    for y, z in BASE_TABS:
        m += tab(y, z, -5, 0) + tab(y, z, INNER, INNER + 5)
    return m


def make_cover():
    m = profile_solid(0, INNER) ^ box(-1, -HW - 1, SLIT[1], INNER + 1, HW + 1, HT + 1)
    for s in (-1, 1):
        w = HW - WALL
        m += yz_prism([(s * w, SLIT[1]), (s * w, SLIT[1] + (w - LEDGE_TIP)), (s * LEDGE_TIP, SLIT[1])][::s], 0, INNER)
    for y, z in COVER_TABS:
        m += tab(y, z, -5, 0) + tab(y, z, INNER, INNER + 5)
    # recessed accent line on top, for a contrasting inlay
    m -= box(INNER / 2 - 30, -1.6, HT - 1.0, INNER / 2 + 30, 1.6, HT + 1)
    return m


def make_inlay():
    return box(INNER / 2 - 29.8, -1.4, HT - 1.0, INNER / 2 + 29.8, 1.4, HT + 0.2)


# ---- end caps (print 2; same part both ends) ---------------------------------
def make_cap():
    """Left cap: inner face at x=0, outer face at x=-PT, 1 mm chamfered edges."""
    small = rrect(-HW + 1, 1, HW - 1, HT - 1, RAD - 1)
    m = Manifold.hull(yz_prism(small, -PT, 0) + yz_prism(OUTER, -PT + 1, -1))
    for zc in (ZB, ZA):
        m -= cyl_x(AX + CLR, -PT - 1, 1, 0, zc, 48)
    for y, z in BASE_TABS + COVER_TABS:
        m -= tab(y, z, -5.2, 0.1, grow=0.15)
    return m


# ---- rollers ------------------------------------------------------------------
KEY_W, KEY_D = 2.2, 7.0
KNOB_X = INNER + PT + 1.0          # knobs start 1 mm outside the cap


def make_roller(zc, shaft_len):
    m = cyl_x(R, 1, 1 + BODY, 0, zc)
    m += cyl_x(AX, -PT, 1, 0, zc, 48)
    shaft = cyl_x(AX, 1 + BODY, KNOB_X + shaft_len, 0, zc, 48)
    shaft -= box(KNOB_X - 1, -10, zc + AX - 1, KNOB_X + shaft_len + 1, 10, zc + 10)   # D flat
    m += shaft
    m -= box(5, -KEY_W / 2, zc + R - KEY_D, BODY - 3, KEY_W / 2, zc + R + 1)          # cloth slot
    return m


def make_key():
    pts = [(-0.85, 0), (0.85, 0), (1.15, KEY_D - 0.4), (-1.15, KEY_D - 0.4)]
    return yz_prism(pts, 5.5, BODY - 3.5)


def d_hole(depth):
    h = Manifold.cylinder(depth + 1, AX + 0.15, AX + 0.15, 48).translate([0, 0, -1])
    return h - box(-10, AX - 1 + 0.1, -2, 10, 10, depth + 2)


def chamfered_disc(r, h, c):
    return Manifold.hull(Manifold.cylinder(h, r - c, r - c, 96) + Manifold.cylinder(h - 2 * c, r, r, 96).translate([0, 0, c]))


def make_knob_main():
    """Big knob for the top roller: fine knurl band, plain chamfered face."""
    m = chamfered_disc(13, 14, 1.0)
    for i in range(48):
        a = 2 * np.pi * i / 48
        m -= Manifold.cylinder(9, 0.55, 0.55, 12).translate([13.2 * np.cos(a), 13.2 * np.sin(a), 2.5])
    m -= Manifold.cylinder(1, 1.6, 1.6, 24).translate([8.5, 0, 13.2])     # index dot
    return m - d_hole(12)


def make_knob_load():
    """Low disc for the bottom roller, turned only when loading: coin slot."""
    m = chamfered_disc(8, 5, 0.8)
    m -= box(-6, -0.7, 3.8, 6, 0.7, 6)
    return m - d_hole(4.2)


def save(m, folder, name):
    os.makedirs(folder, exist_ok=True)
    mesh = m.to_mesh()
    t = trimesh.Trimesh(vertices=mesh.vert_properties[:, :3], faces=mesh.tri_verts)
    t.export(os.path.join(folder, name))
    return t


def on_bed(m):
    b = m.bounding_box()
    return m.translate([-b[0], -b[1], -b[2]])


def to_axis(knob, zc):
    """Knob (built along +Z, D flat at +Y) placed on a roller shaft."""
    return knob.rotate([0, 0, 90]).rotate([0, 90, 0]).translate([KNOB_X, 0, zc])


if __name__ == "__main__":
    capL = make_cap()
    capR = capL.mirror([1, 0, 0]).translate([INNER, 0, 0])
    base, cover, inlay = make_base(), make_cover(), make_inlay()
    ra, rb = make_roller(ZA, 11.5), make_roller(ZB, 4.0)
    kA, kB = to_axis(make_knob_main(), ZA), to_axis(make_knob_load(), ZB)
    keys = [make_key().translate([0, 0, zc + R - KEY_D + 0.4]) for zc in (ZB, ZA)]
    case = capL + capR + base + cover

    checks = {"rollers vs case": (ra + rb) ^ case, "rollers": ra ^ rb,
              "knobs vs case": (kA + kB) ^ case, "knob A vs roller": kA ^ ra, "knob B vs roller": kB ^ rb,
              "knobs": kA ^ kB, "base vs cover": base ^ cover, "inlay vs cover": inlay ^ cover,
              "caps vs shells": (capL + capR) ^ (base + cover), "key vs roller (press fit)": keys[0] ^ rb}
    for k, v in checks.items():
        print(f"overlap {k:26s} {v.volume():8.2f}")

    P = os.path.join(HERE, "print")
    stand = lambda m: on_bed(m.rotate([0, -90, 0]))
    for m, n in [(on_bed(capL.rotate([0, -90, 0])), "end_cap_x2.stl"),
                 (on_bed(base), "base_shell.stl"),
                 (on_bed(cover.mirror([0, 0, 1])), "top_shell.stl"),
                 (on_bed(inlay), "accent_inlay.stl"),
                 (stand(ra), "roller_top.stl"), (stand(rb), "roller_bottom.stl"),
                 (on_bed(make_knob_main()), "knob_main.stl"),
                 (on_bed(make_knob_load()), "knob_loading.stl"),
                 (on_bed(make_key().rotate([0, 90, 0])), "cloth_clip_x2.stl")]:
        t = save(m, P, n)
        print(f"{n:20s} {np.round(t.extents, 1)} watertight={t.is_watertight}")

    V = os.path.join(HERE, "viewer")
    for m, n in [(capL + capR, "caps.stl"), (base + cover, "shell.stl"), (inlay, "inlay.stl"),
                 (ra + kA, "rollerA.stl"), (rb + kB, "rollerB.stl")]:
        save(m, V, n)
    print(f"ZB={ZB} ZA={ZA} NIP={NIP} case {INNER + 2*PT:.0f} x {2*HW:.0f} x {HT:.0f}")
