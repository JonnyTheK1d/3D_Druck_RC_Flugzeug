"""Fahrwerk: Räder, Drahtklemmen, Bugfahrwerkslager, Lenkhebel, Streben."""
from __future__ import annotations

import numpy as np

from . import fuselage as fu
from . import geom as g
from . import wing as wing_mod
from .geom import CrossSection, Manifold
from .params import *
from .parts import Part


# --------------------------------------------------------------------------- #
# Räder
# --------------------------------------------------------------------------- #
def tire(D=WHEEL_D, W=WHEEL_W, rim_d=38.0) -> Manifold:
    ri, ro = rim_d / 2, D / 2
    cs = g.rounded_slot(ri, ro, -W / 2, W / 2, 5.0)
    m = Manifold.revolve(cs, 96)               # Achse = Z, Mitte bei z = 0
    return m.translate((0, 0, 0))


def hub(D=WHEEL_D, W=WHEEL_W, rim_d=38.0, bore=4.2) -> Manifold:
    ri = rim_d / 2
    pts = [(0, -8), (6.5, -8), (6.5, -2.5), (ri - 3.5, -2.5), (ri - 3.5, -8), (ri, -8), (ri, 8),
           (ri - 3.5, 8), (ri - 3.5, 2.5), (6.5, 2.5), (6.5, 8), (0, 8)]
    m = Manifold.revolve(CrossSection([g.ccw(pts)]), 96)
    m = m - g.cyl((0, 0, -9), (0, 0, 9), bore / 2, segs=32)
    # Leichtbau-Löcher im Steg
    for k in range(6):
        a = np.radians(60 * k)
        c = (np.cos(a) * (ri - 3.5 + 6.5) / 2, np.sin(a) * (ri - 3.5 + 6.5) / 2)
        m = m - g.cyl((c[0], c[1], -3), (c[0], c[1], 3), 3.0, segs=24)
    return m


def wheels() -> list[Part]:
    parts = []
    # Rad: Achse = Z, Druck liegend auf der Seite (Achse nach oben)
    zc = WHEEL_D / 2
    place = [g.translation(MAIN_GEAR_X, MAIN_GEAR_TRACK_HALF, zc) @ g.rot_x(90),
             g.translation(MAIN_GEAR_X, -MAIN_GEAR_TRACK_HALF, zc) @ g.rot_x(90),
             g.translation(NOSE_GEAR_X, 0, zc) @ g.rot_x(90)]
    parts.append(Part("G1_Reifen", "Fahrwerk", tire(), place[0], np.eye(4), qty=3, material="TPU", infill=0.45,
                      instances=place, note="TPU 95A, 2 Hauptreifen + 1 Bugreifen (1-2 mm Wand reicht)"))
    parts.append(Part("G2_Radnabe", "Fahrwerk", hub(), place[0], np.eye(4), qty=3, material="PLA", infill=0.5,
                      instances=place, note="Reifen aufkleben (Sekundenkleber); Achsbohrung 4,2 mm (Haupt), Bugrad auf 3 mm aufbohren"))
    return parts


# --------------------------------------------------------------------------- #
# Hauptfahrwerk: Klemmblock für 4-mm-Draht
# --------------------------------------------------------------------------- #
def main_gear_clamp() -> list[Part]:
    L, Wd = 30.0, 52.0
    x0, x1 = MAIN_GEAR_X - L / 2, MAIN_GEAR_X + L / 2
    zf = 66.0 + WALL_FUSE                       # Rumpfboden innen
    zw = MAIN_WIRE_Z
    lower = g.box(x0, x1, -Wd / 2, Wd / 2, zf - 0.5, zw)
    upper = g.box(x0, x1, -Wd / 2, Wd / 2, zw, zw + 6.0)
    # conform lower block to curved floor
    lower = lower ^ fu.body(0, FUSE_LEN, T_IN)
    groove = g.cyl((MAIN_GEAR_X, -Wd, zw), (MAIN_GEAR_X, Wd, zw), GEAR_WIRE_MAIN / 2 + 0.1, segs=32)
    lower, upper = lower - groove, upper - groove
    for sx in (-1, 1):
        for sy in (-1, 1):
            c = (MAIN_GEAR_X + sx * 9.0, sy * 19.0)
            lower = lower - g.cyl((c[0], c[1], zf - 1), (c[0], c[1], zw - 1.0), 1.25, segs=16)
            upper = upper - g.cyl((c[0], c[1], zw - 1), (c[0], c[1], zw + 7), 1.7, segs=16)
            upper = upper - g.cyl((c[0], c[1], zw + 3.0), (c[0], c[1], zw + 7), 3.1, segs=24)
    return [Part("G3_Hauptfahrwerk_Klemme_unten", "Fahrwerk", lower, np.eye(4), np.eye(4), material="PETG",
                 infill=0.6, note="auf den Rumpfboden kleben; Draht 4 mm Federstahl"),
            Part("G4_Hauptfahrwerk_Klemme_oben", "Fahrwerk", upper, np.eye(4), g.rot_x(180), material="PETG",
                 infill=0.6, note="2x M3x12 Blechschrauben in die Bohrungen des unteren Blocks")]


T_IN = fu.T


# --------------------------------------------------------------------------- #
# Bugfahrwerkslager
# --------------------------------------------------------------------------- #
def nose_gear_block() -> Part:
    x0, x1 = FIREWALL_X + FIREWALL_T + 0.3, NOSE_GEAR_X + 14.0
    blk = g.box(x0, x1, -13.0, 13.0, 55.0, NOSE_WIRE_Z_TOP - 8.0)
    blk = blk ^ fu.body(0, FUSE_LEN, T_IN)                  # an den Rumpfboden angepasst
    bore = g.cyl((NOSE_GEAR_X, 0, 40.0), (NOSE_GEAR_X, 0, NOSE_WIRE_Z_TOP), 1.75, segs=24)
    # Ausschnitt oben für Servo-Gestänge frei lassen, Verbindung zum Brandschott klebt
    blk = blk - bore
    for sy in (-1, 1):
        blk = blk - g.cyl((x0 - 1, sy * 8.0, 95.0), (x0 + 5, sy * 8.0, 95.0), 1.2, segs=16)
    return Part("G5_Bugfahrwerkslager", "Fahrwerk", blk, np.eye(4), np.eye(4), material="PETG", infill=0.6,
                note="auf Rumpfboden und Brandschott kleben; 3-mm-Federstahl, Messingrohr 4/3 optional")


def nose_fork() -> Part:
    """Bugradgabel: Brücke mit Drahtbohrung oben, zwei Arme mit Achsbohrung (Rad dazwischen)."""
    zc = WHEEL_D / 2
    gap = WHEEL_W + 1.5
    arm_t = 5.0
    cx = NOSE_GEAR_X
    z_top = 72.0
    z_bot = zc - 7.0
    bridge = g.box(cx - 8.0, cx + 8.0, -(gap / 2 + arm_t), gap / 2 + arm_t, z_top - 14.0, z_top)
    arms = []
    for sy in (-1, 1):
        ya, yb = sorted((sy * gap / 2, sy * (gap / 2 + arm_t)))
        arms.append(g.box(cx - 7.0, cx + 7.0, ya, yb, z_bot, z_top - 13.0))
    fork = g.union([bridge] + arms)
    fork = fork - g.cyl((cx, 0, z_top - 15.0), (cx, 0, z_top + 1.0), 1.65, segs=24)      # 3-mm-Draht von oben
    fork = fork - g.cyl((cx, -gap, zc), (cx, gap, zc), 1.65, segs=24)                      # Achse Ø3
    return Part("G7_Bugradgabel", "Fahrwerk", fork, np.eye(4), g.rot_x(180), material="PETG", infill=0.8,
                note="Bruecke liegt auf dem Druckbett; 3-mm-Draht einkleben, Achse 3-mm-Stab (Stellringe)")


def steering_collar() -> Part:
    r, h = 5.0, 9.0
    place = g.translation(NOSE_GEAR_X, 0, NOSE_WIRE_Z_TOP - 8.0 + 0.6)      # sitzt direkt auf dem Lager
    body = g.cyl((0, 0, 0), (0, 0, h), r, segs=40)
    arm = g.box(0, 17.0, -3.0, 3.0, 1.0, 6.0)
    body = body + arm
    body = body - g.cyl((0, 0, -1), (0, 0, h + 1), 1.6, segs=24)                  # Drahtbohrung 3,2
    body = body - g.cyl((-6, 0, h / 2), (r + 1, 0, h / 2), 1.25, segs=16)          # Madenschraube
    body = body - g.cyl((14, -4, 3.5), (14, 4, 3.5), 0.8, segs=16)                 # Anlenkloch
    return Part("G6_Lenkhebel", "Fahrwerk", body, place, np.eye(4), material="PETG", infill=1.0,
                note="M3-Madenschraube klemmt auf dem 3-mm-Bugfahrwerksdraht")


# --------------------------------------------------------------------------- #
# Streben (kosmetisch + leichte Entlastung)
# --------------------------------------------------------------------------- #
def struts() -> list[Part]:
    T = wing_mod.wing_asm_T()
    surf = wing_mod.make_surface()
    xw = STRUT_X
    c = surf.chord(STRUT_Y)
    # Punkte auf der Flügelunterseite (lokal) -> Zusammenbau
    def low(xr):
        return (T @ np.array([xr, STRUT_Y, surf._surf_z(xr, c, False), 1.0]))[:3]
    p_a, p_b = low(xw - 12), low(xw + 12)
    p_w = low(xw)
    p_f = np.array([WING_LE_X + xw - 18.0, STRUT_Y_FUSE, STRUT_Z_FUSE])
    out = []
    ax = p_w - p_f
    L = np.linalg.norm(ax)
    e1 = ax / L
    # Ellipsenquerschnitt: Sehne ~ globale x-Richtung, Dicke senkrecht dazu
    e2 = np.array([1.0, 0, 0]) - e1 * e1[0]
    e2 /= np.linalg.norm(e2)
    e3 = np.cross(e1, e2)
    chord, thick = 13.0, 6.0
    th = np.linspace(0, 2 * np.pi, 48, endpoint=False)
    # Stromlinienprofil: NACA-0040-artig (Ellipse mit spitzem Heck)
    prof = np.column_stack([chord / 2 * np.cos(th), thick / 2 * np.sin(th)])
    prof[:, 0] += 0.0
    cs = CrossSection([g.ccw(prof)])
    body = Manifold.extrude(cs, L + 40.0)                    # Achse = Z
    # lokal: z = Achse, x = e2, y = e3
    Rm = np.eye(4)
    Rm[:3, 0], Rm[:3, 1], Rm[:3, 2] = e2, e3, e1
    body = g.apply(body, g.translation(*(p_f - 20 * e1)) @ Rm)
    # Schnittebenen: oben parallel zur Flügelunterseite, unten Rumpfseitenwand (y = 75)
    n_top = np.cross(p_b - p_a, np.array([0, 1.0, 0]))
    n_top = n_top / np.linalg.norm(n_top)
    if n_top[2] < 0:
        n_top = -n_top
    top_hs = g.halfspace(p_w, n_top)                          # alles unterhalb der Flügelunterseite
    bot_hs = g.halfspace(np.array([0, STRUT_Y_FUSE, 0]), np.array([0, -1.0, 0]))
    bot_keep = g.box(-1e4, 1e4, STRUT_Y_FUSE, 1e4, -1e4, 1e4)
    body = (body ^ top_hs) ^ bot_keep
    asm_right = Part("Z1_Strebe_rechts", "Streben", body, np.eye(4), np.eye(4), material="PLA", infill=0.5,
                     note="kosmetisch; mit Epoxy an Rumpfseite und Flügelunterseite kleben")
    # Druckausrichtung: Achse -> x, Sehne -> y (flach liegen)
    P = np.eye(4)
    P[:3, 0], P[:3, 1], P[:3, 2] = e1, e2, e3
    asm_right.print_R = g.rot_z(45) @ np.linalg.inv(P)
    left = Part("Z1_Strebe_links", "Streben", g.mirror_y(body), np.eye(4), np.eye(4), material="PLA", infill=0.5,
                note=asm_right.note)
    # Drehung für linke Seite: gespiegelte Achse
    e1l, e2l = e1 * np.array([1, -1, 1]), e2 * np.array([1, -1, 1])
    e3l = np.cross(e1l, e2l)
    Pl = np.eye(4)
    Pl[:3, 0], Pl[:3, 1], Pl[:3, 2] = e1l, e2l, e3l
    left.print_R = g.rot_z(45) @ np.linalg.inv(Pl)
    return [asm_right, left]


def build_gear() -> list[Part]:
    return wheels() + main_gear_clamp() + [nose_gear_block(), steering_collar(), nose_fork()] + struts()
