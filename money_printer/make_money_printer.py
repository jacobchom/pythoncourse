"""Fake 'money printer' magic prop, v2. All parts 3D printed, no glue, no hardware.

How it works
  * FRONT slot and BACK slot are at the same height.
  * Paper pushed into the front slot hits a ramp and slides DOWN into a
    hidden pocket under the tray.
  * A real note lies on the tray. Turning the crank wheel spins a lead screw;
    a nut carriage on the screw drags a thin pusher bar along the tray,
    shoving the note out of the back slot.

Multi-note: notes are loaded end to end on the tray. Each print, crank until
the front note pops out (about 6.6 turns); the pusher shoves the whole row.

Run:  python3 make_money_printer.py [NOTES]      (default 3)
Writes print-ready STLs to ./print_<N>notes and world meshes to ./viewer.
All sizes in mm. Fits notes up to 166 x 77 (every UK note, US dollars).
"""
import sys
import os
import numpy as np
import trimesh
from manifold3d import Manifold, CrossSection

HERE = os.path.dirname(os.path.abspath(__file__))
PRINT = os.path.join(HERE, "print")
VIEW = os.path.join(HERE, "viewer")

# ---- key dimensions --------------------------------------------------------
NOTES = int(sys.argv[1]) if len(sys.argv) > 1 and __name__ == "__main__" else 3
NOTE_MAX_W = 77.0
P0 = 38.5                        # pusher start (rear edge of the last note)
W, H = 200.0, 36.0
D = P0 + NOTES * NOTE_MAX_W + 0.3 + 2.4   # deeper box: notes sit end to end
T = 2.4                          # wall
FLOOR = 2.0
CLR = 0.3                        # general print clearance
NOTE_X1 = 176.0                  # note area is x = T .. NOTE_X1
SLOT_X = (6.0, 172.0)            # both slots: 166 wide
SLOT_Z = (14.2, 17.0)            # both slots: SAME height
RAIL_TOP = 12.0
TRAY_T = 2.5
TRAY_TOP = RAIL_TOP + TRAY_T     # 14.5 (note and carriage slide on this)
RAMP_END_Y = 30.0                # paper ramp runs from front wall to here
FIN_GAP = 2.0                    # lid fins sit this far above the tray
BAR_H = 1.2                      # pusher bar height

SCREW_X, SCREW_Z = 188.0, 23.5   # lead-screw axis (runs along Y)
R_MAJ, R_MIN = 6.0, 4.5          # thread radii
STARTS, LEAD = 2, 12.0           # 2-start thread, 12 mm per turn
NUT_CLR = 0.4
JOURNAL_R = 4.0

P1 = D - T - 0.3                 # pusher end, against the back wall
TRAVEL = P1 - P0                 # NOTES x 77 mm in total
STEP = NOTE_MAX_W + T            # travel per print: clears the wall fully
SEG_MAX = 145.0                  # screw is printed in pieces no taller than this
CAR_LEN = 30.0
CAR_X = (SCREW_X - 9.3, SCREW_X + 9.3)


def box(x0, y0, z0, x1, y1, z1):
    return Manifold.cube([x1 - x0, y1 - y0, z1 - z0]).translate([x0, y0, z0])


def hull(pts):
    return Manifold.hull_points([list(map(float, p)) for p in pts])


def cyl_y(r, y0, y1, x, z, n=64):
    """Cylinder along +Y from y0 to y1."""
    return Manifold.cylinder(y1 - y0, r, r, n).rotate([-90, 0, 0]).translate([x, y0, z])


def ramp_z(y):
    return SLOT_Z[0] + (y - T) * (2.6 - SLOT_Z[0]) / (RAMP_END_Y - T)


def thread_section(offset=0.0, n=120):
    pts = []
    for i in range(n):
        th = 2 * np.pi * i / n
        t = (STARTS * th / (2 * np.pi)) % 1.0
        tri = 1 - 2 * abs(t - 0.5)                    # 0..1..0
        tri = min(1.0, tri * 1.25)                    # small flat crest
        r = R_MIN + (R_MAJ - R_MIN) * tri + offset
        pts.append([r * np.cos(th), r * np.sin(th)])
    return CrossSection([pts])


def threaded_rod(length, offset=0.0):
    cs = thread_section(offset)
    div = int(length / 0.5)
    m = Manifold.extrude(cs, length, div, -360.0 * length / LEAD)
    return m  # along +Z


# ---- base ------------------------------------------------------------------
def make_base():
    m = box(0, 0, 0, W, D, H) - box(T, T, FLOOR, W - T, D - T, H + 1)
    # slots, same height front and back
    m -= box(SLOT_X[0], -1, SLOT_Z[0], SLOT_X[1], T + 1, SLOT_Z[1])
    m -= box(SLOT_X[0], D - T - 1, SLOT_Z[0], SLOT_X[1], D + 1, SLOT_Z[1])
    # left rail + right block hold the tray (solid from floor, no overhangs)
    m += box(T, T, 0, T + 3, D - T, RAIL_TOP)
    m += box(NOTE_X1 - 3, T, 0, W - T, D - T, RAIL_TOP)
    # paper ramp: slot level down to the pocket floor
    m += hull([(x, y, z) for x in (T, NOTE_X1) for (y, z) in
               [(T, 0), (T, SLOT_Z[0]), (RAMP_END_Y, ramp_z(RAMP_END_Y)), (RAMP_END_Y, 0)]])
    # U-notches for the screw journals (front and back walls), open at top
    r = JOURNAL_R + CLR
    for y0, y1 in [(-1, T + 0.01), (D - T - 0.01, D + 1)]:
        m -= cyl_y(r, y0, y1, SCREW_X, SCREW_Z)
        m -= box(SCREW_X - r, y0, SCREW_Z, SCREW_X + r, y1, H + 1)
    # finger notch to lift the lid
    m -= box(W / 2 - 12, -1, H - 3, W / 2 + 12, T + 1, H + 1)
    return m


# ---- tray (hidden floor: note on top, paper pocket underneath) -------------
def make_tray():
    m = box(T + CLR, RAMP_END_Y + CLR, RAIL_TOP, W - T - CLR, D - T - CLR, TRAY_TOP)
    # strip beside the ramp so the carriage has a floor all the way forward
    m += box(NOTE_X1 + CLR, T + CLR, RAIL_TOP, W - T - CLR, RAMP_END_Y + 1, TRAY_TOP)
    m -= Manifold.cylinder(10, 7, 7, 48).translate([90, 42, RAIL_TOP - 1])   # lift hole
    return m


# ---- lead screw with crank wheel (one piece) -------------------------------
def make_screw():
    """Built along +Z from the wheel face, then laid along +Y in world."""
    parts = []
    z = 0.0
    wheel = Manifold.cylinder(5, 16, 16, 96)
    wheel -= Manifold.cylinder(7, 4.6, 4.6, 48).translate([9.8, 0, -1])     # finger hole
    for i in range(24):                                                      # grip ridges
        a = 2 * np.pi * i / 24
        wheel -= Manifold.cylinder(7, 1.0, 1.0, 16).translate([16.4 * np.cos(a), 16.4 * np.sin(a), -1])
    parts.append(wheel); z = 5
    parts.append(Manifold.cylinder(2.7, 6, 6, 64).translate([0, 0, z])); z += 2.7    # stop hub
    parts.append(Manifold.cylinder(T + 0.6, JOURNAL_R, JOURNAL_R, 64).translate([0, 0, z])); z += T + 0.6
    parts.append(Manifold.cylinder(2.7, 7.5, 7.5, 64).translate([0, 0, z])); z += 2.7  # inner collar
    thread_len = (D - T) - (T + 0.3 + 2.7)
    parts.append(threaded_rod(thread_len).translate([0, 0, z])); z += thread_len
    parts.append(Manifold.cylinder(T - 0.2, JOURNAL_R, JOURNAL_R, 64).translate([0, 0, z]))
    m = parts[0]
    for p in parts[1:]:
        m += p
    wheel_face_y = -(5 + 2.7 + 0.3)        # world Y of the wheel's outer face
    world = m.rotate([-90, 0, 0]).translate([SCREW_X, wheel_face_y, SCREW_Z])
    # split into printable pieces joined by keyed pegs (key keeps threads in line)
    total = z + T - 0.2
    n = int(np.ceil(total / SEG_MAX))
    cuts = [total * i / n for i in range(1, n)]
    pieces, lo = [], -1.0
    for zc in cuts + [total + 1]:
        pieces.append(m ^ box(-20, -20, lo, 20, 20, zc))
        lo = zc

    def key(r, k, h, zb):
        return (Manifold.cylinder(h, r, r, 48) + box(-k / 2, 0, 0, k / 2, r + 0.8, h)).translate([0, 0, zb])
    for i, zc in enumerate(cuts):
        pieces[i] += key(2.2, 1.6, 10, zc)
        pieces[i + 1] -= key(2.2 + 0.15, 1.6 + 0.3, 10.5, zc - 0.01)
    return pieces, world


# ---- carriage + pusher bar (one piece) -------------------------------------
def make_carriage(p=P0):
    nut_top = SCREW_Z + R_MAJ + NUT_CLR + 2.5
    car = box(CAR_X[0], p - CAR_LEN, TRAY_TOP + 0.1, CAR_X[1], p, nut_top)
    # start the nut thread in phase with the screw thread (starts at y = 5.4)
    pitch = LEAD / STARTS
    y0 = 5.4 + np.floor((p - CAR_LEN - 1 - 5.4) / pitch) * pitch
    nut = threaded_rod(p + 1 - y0, NUT_CLR).rotate([-90, 0, 0]).translate([SCREW_X, y0, SCREW_Z])
    car -= nut
    bar = box(SLOT_X[0] + 1, p - 8, TRAY_TOP + 0.1, CAR_X[0] + 1, p, TRAY_TOP + 0.1 + BAR_H)
    return car + bar


# ---- lid -------------------------------------------------------------------
def make_lid():
    m = box(0, 0, H, W, D, H + 3)
    for i in range(7):                                       # cosmetic grooves
        y = 30 + i * 9
        m -= box(30, y, H + 1.8, 150, y + 3, H + 4)
    # locating lip (left, front, back; right side is left open for the carriage)
    lip_z = H - 3.5
    m += box(T + CLR, T + CLR, lip_z, T + CLR + 1.6, D - T - CLR, H)
    m += box(T + CLR, T + CLR, lip_z, NOTE_X1, T + CLR + 1.6, H)
    m += box(T + CLR, D - T - CLR - 1.6, lip_z, NOTE_X1, D - T - CLR, H)
    # fins: steer paper DOWN the ramp, and hold the note flat on the tray
    for x in np.linspace(8, 169, 9):
        x0, x1 = x, x + 1.6
        y0, y1 = T + CLR + 0.2, RAMP_END_Y - 0.4
        m += hull([(xx, y, z) for xx in (x0, x1) for (y, z) in
                   [(y0, ramp_z(y0) + 3.2), (y1, ramp_z(y1) + 3.2), (y0, H), (y1, H)]])
        m += box(x0, RAMP_END_Y - 0.4, TRAY_TOP + FIN_GAP, x1, D - T - CLR, H)
    # tabs that drop into the wall notches and hold the screw down
    r = JOURNAL_R + CLR - 0.15
    tab_bot = SCREW_Z + JOURNAL_R + 0.3
    for y0, y1 in [(0.2, T), (D - T, D - 0.2)]:
        m += box(SCREW_X - r, y0, tab_bot, SCREW_X + r, y1, H)
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
    base, tray, lid = make_base(), make_tray(), make_lid()
    screw_pieces, screw_world = make_screw()
    car = make_carriage()

    checks = {
        "screw vs base": screw_world ^ base, "screw vs tray": screw_world ^ tray,
        "screw vs lid": screw_world ^ lid, "screw vs carriage": screw_world ^ car,
        "carriage vs base": car ^ base, "carriage vs lid": car ^ lid, "carriage vs tray": car ^ tray,
        "carriage(end) vs lid": make_carriage(P1) ^ lid,
        "carriage(end) vs base": make_carriage(P1) ^ base,
        "tray vs base": tray ^ base, "lid vs base": lid ^ base, "lid vs tray": lid ^ tray,
    }
    for k, v in checks.items():
        print(f"overlap {k:24s} {v.volume():8.2f} mm3")

    out = os.path.join(HERE, f"print_{NOTES}notes")
    items = [(base, "base.stl"), (on_bed(tray), "tray.stl"),
             (on_bed(lid.rotate([180, 0, 0])), "lid.stl"),
             (on_bed(car.rotate([-90, 0, 0])), "carriage_pusher.stl")]
    for i, p in enumerate(screw_pieces):
        items.append((on_bed(p), f"screw_part{i + 1}_of_{len(screw_pieces)}.stl"))
    for m, n in items:
        t = save(m, out, n)
        print(f"{n:24s} {np.round(t.extents,1)} watertight={t.is_watertight}")

    if NOTES == 3:
        for m, n in [(base, "base.stl"), (tray, "tray.stl"), (lid, "lid.stl"),
                     (screw_world, "screw.stl"), (car, "carriage.stl")]:
            save(m, VIEW, n)
    print(f"box {W:.0f} x {D:.1f} x {H+3:.0f}; travel {TRAVEL:.1f} mm = {TRAVEL/LEAD:.1f} turns; "
          f"{STEP/LEAD:.1f} turns per note; P0={P0} P1={P1}")
