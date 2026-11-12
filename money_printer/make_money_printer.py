"""Fake 'money printer' magic prop. Generates printable STLs.

How it works: blank paper pushed into the FRONT slot drops into a hidden
lower pocket. A real note pre-loaded on a hidden tray sits under a rubber-
banded roller; turning the crank feeds the note out of the BACK slot.

Run:  python3 make_money_printer.py   -> writes STLs next to this file.
All sizes in mm. Sized for notes up to 156 x 77 (all UK notes, US $).
"""
import os
import numpy as np
import trimesh
from manifold3d import Manifold, CrossSection

OUT = os.path.dirname(os.path.abspath(__file__))

# ---- main dimensions -------------------------------------------------------
W, D, H = 180.0, 100.0, 32.0      # base outer size (X wide, Y deep, Z tall)
T = 2.4                           # wall thickness
FLOOR = 2.0
SLOT_W = 166.0                    # slot width (note long edge goes first)
ENTRY_Z = (3.0, 7.0)              # front slot: paper goes in, drops to pocket
RAIL_TOP = 12.0                   # tray rests on side rails at this height
TRAY_T = 2.5
TRAY_TOP = RAIL_TOP + TRAY_T      # 14.5
EXIT_Z = (TRAY_TOP - 0.5, TRAY_TOP + 3.5)  # back slot: note comes out
ROLL_R = 8.0                      # roller radius
ROLL_Y = D - 12.0                 # roller axis Y (near the exit)
ROLL_Z = TRAY_TOP + ROLL_R        # roller just touches tray; bands add grip
ROD_D = 6.0                       # 6 mm wooden dowel / steel rod as axle
CLR = 0.3                         # print clearance


def box(x0, y0, z0, x1, y1, z1):
    return Manifold.cube([x1 - x0, y1 - y0, z1 - z0]).translate([x0, y0, z0])


def cyl_x(r, x0, x1, y, z, n=64):
    """Cylinder along X."""
    return (Manifold.cylinder(x1 - x0, r, r, n)
            .rotate([0, 90, 0]).translate([x0, y, z]))


# ---- base ------------------------------------------------------------------
def make_base():
    m = box(0, 0, 0, W, D, H) - box(T, T, FLOOR, W - T, D - T, H + 1)
    sx0 = (W - SLOT_W) / 2
    # front entry slot (into lower pocket)
    m -= box(sx0, -1, ENTRY_Z[0], sx0 + SLOT_W, T + 1, ENTRY_Z[1])
    # back exit slot (level with tray top)
    m -= box(sx0, D - T - 1, EXIT_Z[0], sx0 + SLOT_W, D + 1, EXIT_Z[1])
    # side rails the tray sits on (solid from floor: no overhangs)
    m += box(T, T, 0, T + 3, D - T, RAIL_TOP)
    m += box(W - T - 3, T, 0, W - T, D - T, RAIL_TOP)
    # U-notches in side walls for the axle, open at the top
    r = ROD_D / 2 + CLR
    for x0, x1 in [(-1, T + 3.5), (W - T - 3.5, W + 1)]:
        m -= cyl_x(r, x0, x1, ROLL_Y, ROLL_Z)
        m -= box(x0, ROLL_Y - r, ROLL_Z, x1, ROLL_Y + r, H + 1)
    # finger notch on top edge of front wall to lift lid
    m -= box(W / 2 - 10, -1, H - 3, W / 2 + 10, T + 1, H + 1)
    return m


# ---- hidden tray (sits on rails, separates pocket from note) ---------------
def make_tray():
    x0, x1 = T + CLR, W - T - CLR
    y0, y1 = T + CLR, D - T - CLR
    m = box(x0, y0, 0, x1, y1, TRAY_T)
    # little thumb hole at the front to lift it out
    m -= Manifold.cylinder(TRAY_T + 2, 7, 7, 48).translate([W / 2, y0 + 10, -1])
    return m


# ---- lid --------------------------------------------------------------------
def make_lid():
    LT = 3.0
    m = box(0, 0, 0, W, D, LT)
    # locating lip that drops inside the walls
    lip = box(T + CLR, T + CLR, -4, W - T - CLR, D - T - CLR, 0)
    lip -= box(T + CLR + 1.6, T + CLR + 1.6, -5, W - T - CLR - 1.6, D - T - CLR - 1.6, 1)
    # gap in lip where the roller lives
    lip -= box(0, ROLL_Y - ROLL_R - 3, -5, W, D, 1)
    m += lip
    # tabs that fill the axle notches and hold the axle down
    r = ROD_D / 2 + CLR - 0.15
    tab_bottom = ROLL_Z + ROD_D / 2 + 0.3 - H   # relative to lid underside
    for x0, x1 in [(0.2, T + 3.3), (W - T - 3.3, W - 0.2)]:
        m += box(x0, ROLL_Y - r, tab_bottom, x1, ROLL_Y + r, 0)
    # decorative vent slots on top (looks like a machine)
    for i in range(6):
        y = 20 + i * 8
        m -= box(40, y, 1.2, W - 40, y + 3, LT + 1)
    return m


# ---- roller halves (slide onto the 6 mm rod, glue in place) -----------------
def make_roller_half():
    L = (W - 2 * T - 2 * 3 - 2 * 1.0) / 2 - 0.5   # fits between rails
    m = Manifold.cylinder(L, ROLL_R, ROLL_R, 96)
    m -= Manifold.cylinder(L + 2, ROD_D / 2 + 0.15, ROD_D / 2 + 0.15, 48).translate([0, 0, -1])
    # grooves for rubber bands (bands give grip on the note)
    for z in np.linspace(12, L - 12, 3):
        ring = (Manifold.cylinder(4, ROLL_R + 1, ROLL_R + 1, 96)
                - Manifold.cylinder(4, ROLL_R - 1.0, ROLL_R - 1.0, 96))
        m -= ring.translate([0, 0, z - 2])
    return m, L


# ---- crank ------------------------------------------------------------------
def make_crank():
    hub_r, arm_l, th = 7.0, 35.0, 6.0
    m = Manifold.cylinder(th + 4, hub_r, hub_r, 64)
    m += box(0, -5, 0, arm_l, 5, th)
    m += Manifold.cylinder(th, 6, 6, 64).translate([arm_l, 0, 0])
    m -= Manifold.cylinder(th + 6, ROD_D / 2 + 0.1, ROD_D / 2 + 0.1, 48).translate([0, 0, -1])
    # handle peg
    m += Manifold.cylinder(18, 4, 4, 48).translate([arm_l, 0, th])
    return m


def save(m, name):
    mesh = m.to_mesh()
    t = trimesh.Trimesh(vertices=mesh.vert_properties[:, :3], faces=mesh.tri_verts)
    path = os.path.join(OUT, name)
    t.export(path)
    print(f"{name}: {t.bounds[1] - t.bounds[0]} mm, watertight={t.is_watertight}")
    return t


if __name__ == "__main__":
    base = make_base()
    tray = make_tray()
    lid = make_lid()
    roller, RL = make_roller_half()
    crank = make_crank()

    save(base, "base.stl")
    save(tray, "tray.stl")
    save(lid.rotate([180, 0, 0]), "lid.stl")            # print top-down
    save(roller, "roller_half_x2.stl")                  # print 2, standing up
    save(crank, "crank.stl")

    # assembled preview (lid lifted 25 mm so you can see inside)
    asm = base + tray.translate([0, 0, RAIL_TOP])
    gap = (W - 2 * RL) / 2
    for i in range(2):
        asm += roller.rotate([0, 90, 0]).translate([gap + i * (RL + 0.5) - 0.25 * 0, ROLL_Y, ROLL_Z])
    asm += cyl_x(ROD_D / 2, -3, W + 14, ROLL_Y, ROLL_Z, 32)  # the rod
    asm += crank.rotate([0, 90, 0]).translate([W + 4, ROLL_Y, ROLL_Z])
    asm += lid.translate([0, 0, H + 25])
    save(asm, "preview_assembled.stl")
