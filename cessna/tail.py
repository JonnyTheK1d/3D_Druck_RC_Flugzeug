"""Leitwerk: Höhenflosse + Höhenruder, Seitenflosse + Seitenruder (Ober-/Unterschalen)."""
from __future__ import annotations

import numpy as np

from . import geom as g
from .geom import Manifold
from .params import *
from .parts import Part
from .surface import (Surface, build_panel, control_surface, add_horn_slot, horn_slot_cut, ruderhorn,
                      split_halves, aft_prism, hinge_geometry, plan_ring, CLIP, y_slab)

STAB_SPAR = (STAB_SPAR_X, 0.0, 4.4, 7.4)


def stab_chord(y):
    return STAB_ROOT_CHORD + (STAB_TIP_CHORD - STAB_ROOT_CHORD) * abs(y) / STAB_HALFSPAN


def stab_surface() -> Surface:
    return Surface(STAB_AIRFOIL, stab_chord, x_le0=STAB_LE_X, wall=0.85, rib_pitch=45.0,
                   hole_x_min=1e9, end_rib=1.2)


def fin_chord(y):
    root = FIN_ROOT_TE - FIN_ROOT_LE
    tip = FIN_TIP_TE - FIN_TIP_LE
    return root + (tip - root) * y / FIN_HEIGHT


def fin_surface() -> Surface:
    return Surface(FIN_AIRFOIL, fin_chord, x_le0=FIN_ROOT_LE,
                   sweep=(FIN_TIP_LE - FIN_ROOT_LE) / FIN_HEIGHT, wall=0.85, rib_pitch=45.0,
                   hole_x_min=1e9, end_rib=1.2)


def stab_T():
    return g.translation(0, 0, STAB_Z)


def fin_T():
    return g.translation(0, 0, FIN_BASE_Z) @ g.rot_x(90)


# --------------------------------------------------------------------------- #
# Hüllkörper für Sättel im Rumpf
# --------------------------------------------------------------------------- #
def stab_outer_asm() -> Manifold:
    s = stab_surface()
    half = g.union([s.prism(0, STAB_HALFSPAN - STAB_CAP, False),
                    tip_outer(s, STAB_HALFSPAN - STAB_CAP, STAB_CAP)])
    full = half + g.mirror_y(half)
    return g.apply(full, stab_T())


def tip_outer(surf, y0, cap):
    from .surface import tip_cap
    return tip_cap(surf, y0, cap, 1.0)[0]


def fin_outer_asm() -> Manifold:
    s = fin_surface()
    sol = g.union([s.prism(0, FIN_HEIGHT - FIN_CAP, False), tip_outer(s, FIN_HEIGHT - FIN_CAP, FIN_CAP)])
    return g.apply(sol, fin_T())


# --------------------------------------------------------------------------- #
# Teile
# --------------------------------------------------------------------------- #
FLIP = g.rot_x(180)


def _upper_lower(name, group, upper, lower, T, note="", material="LW-PLA"):
    return [Part(f"{name}_oben", group, upper, T, np.eye(4), note=note, material=material),
            Part(f"{name}_unten", group, lower, T, FLIP, note=note, material=material)]


def build_tail() -> list[Part]:
    parts: list[Part] = []

    # ---- Höhenleitwerk (rechte Hälfte, links gespiegelt) -------------------- #
    s = stab_surface()
    y1 = STAB_HALFSPAN - STAB_CAP
    p = build_panel(s, 0.0, y1, end0=True, end1=False, cap_len=STAB_CAP, spar=STAB_SPAR)

    def xh_fn(y):
        return s.x_le(y) + (1 - ELEV_FRAC) * stab_chord(y)

    fin_o = fin_outer_asm()
    inv = np.linalg.inv(stab_T())
    fin_loc = g.apply(fin_o, inv)
    fin_gap_stab = fin_loc + fin_loc.translate((0, 0.25, 0)) + fin_loc.translate((0, -0.25, 0))
    fin_gap_elev = fin_loc + fin_loc.translate((0, 1.0, 0)) + fin_loc.translate((0, -1.0, 0))
    fin_excl = fin_loc + fin_loc.translate((0, 0.8, 0)) + fin_loc.translate((0, -0.8, 0))      # Flansch-Ausschluss (nicht bündig)
    solid0 = p["solid"] - fin_gap_stab
    fixed, elev, cut_e = control_surface(s, solid0, p["cav"], p["outer"], xh_fn, 0.0, ELEV_END,
                                         gap_a=True, gap_a_len=ELEV_Y0, gap_b=True, cav_big=p["cav_big"])
    fixed = fixed - fin_gap_stab
    elev = elev - fin_gap_elev
    # Anlenkloch für 2-mm-Verbindungsstab in der massiven Nase des Höhenruders
    p0, p1 = pivot_pts(s, xh_fn, ELEV_Y0, ELEV_END)
    elev = elev - g.cyl(p0 + [0, -1, 0], p1 + [0, 1, 0], 1.1, segs=24)
    elev = add_horn_slot(s, elev, p["outer"], xh_fn, ELEV_HORN_Y, x_off=3.0, length=14.4)
    holes = [p["bore"]]
    up, lo = split_halves(fixed, p["outer"], s, 0.0, y1 + STAB_CAP, subtract=holes, exclude=cut_e + fin_excl)
    for side, mir in (("rechts", False), ("links", True)):
        U, L = (g.mirror_y(up), g.mirror_y(lo)) if mir else (up, lo)
        parts += _upper_lower(f"H1_Hoehenflosse_{side}", "Leitwerk", U, L, stab_T(),
                              note="CFK-Stab Ø4 als Holm durch beide Hälften")
    # Höhenruder
    ye_up, ye_lo = split_halves_ctrl(s, elev, p["outer"], xh_fn, ELEV_Y0, ELEV_END - HINGE_GAP, gap_a=False)
    slot = horn_slot_cut(s, xh_fn, ELEV_HORN_Y, x_off=3.0)          # Flanschring nicht in den Hornschlitz
    ye_up, ye_lo = ye_up - slot, ye_lo - slot
    for side, mir in (("rechts", False), ("links", True)):
        U, L = (g.mirror_y(ye_up), g.mirror_y(ye_lo)) if mir else (ye_up, ye_lo)
        parts += _upper_lower(f"H2_Hoehenruder_{side}", "Leitwerk", U, L, stab_T(),
                              note="2-mm-CFK-Stab verbindet beide Hälften; Horn nur an einer Seite")

    # ---- Seitenleitwerk ------------------------------------------------------ #
    f = fin_surface()
    yf1 = FIN_HEIGHT - FIN_CAP
    pf = build_panel(f, 0.0, yf1, end0=True, end1=False, cap_len=FIN_CAP, spar=None)
    (xa, za), (xb, zb) = RUDDER_HINGE

    def xhf(y):
        return xa + (xb - xa) * y / FIN_HEIGHT

    fixed_f, rud, cut_r = control_surface(f, pf["solid"], pf["cav"], pf["outer"], xhf, RUDDER_Y0, RUDDER_Y1,
                                          gap_a=True, gap_b=True, cav_big=pf["cav_big"])
    # Ruderwelle: Ø2-Federstahl in der Scharnierachse, im Ruder eingeklebt, in der Flosse gelagert;
    # unten im Rumpf sitzt der Seitenruderhebel (S4). Die Bohrungen liegen in der Teilungsebene -> Halbrinnen.
    def axis_cyl(ya, yb, r):
        return g.cyl((xhf(ya), ya, 0.0), (xhf(yb), yb, 0.0), r, segs=24)
    boss_f = (axis_cyl(-2.0, RUDDER_Y0 + 1.0, 2.5) ^ pf["outer"] ^ y_slab(-1.0, RUDDER_Y0 - 0.05)) - cut_r
    fixed_f = fixed_f + boss_f
    wire_bore = axis_cyl(-30.0, RUDDER_Y0 + 2.0, 1.2)                 # Lagerbohrung (auch durch den Klebeflansch)
    boss_r = axis_cyl(RUDDER_Y0, RUDDER_WIRE_TOP + 2.0, 2.5) ^ pf["outer"] ^ cut_r ^ y_slab(RUDDER_Y0 + HINGE_GAP, 200.0)
    rud = (rud + boss_r) - axis_cyl(RUDDER_Y0 - 5.0, RUDDER_WIRE_TOP, 1.05)
    f_up, f_lo = split_halves(fixed_f, pf["outer"], f, 0.0, yf1 + FIN_CAP, subtract=[wire_bore], exclude=cut_r)
    # Querbohrung für den 2-mm-Verbindungsstab der Höhenruder (liegt auf deren Scharnierachse, geht durch die Flosse)
    x_e = s.x_le(0.0) + (1 - ELEV_FRAC) * stab_chord(0.0)
    y_e = STAB_Z - FIN_BASE_Z                                  # Höhe der Achse über der Flossenfußebene
    cross = g.cyl((x_e, y_e, -30.0), (x_e, y_e, 30.0), 1.25, segs=24)
    f_up, f_lo = f_up - cross, f_lo - cross
    r_up, r_lo = split_halves_ctrl(f, rud, pf["outer"], xhf, RUDDER_Y0 + HINGE_GAP, RUDDER_Y1 - HINGE_GAP)
    parts += _upper_lower("S1_Seitenflosse", "Leitwerk", f_up, f_lo, fin_T(),
                          note="unterste 15 mm stecken im Heck (Schlitz im Rumpf)")
    parts += _upper_lower("S2_Seitenruder", "Leitwerk", r_up, r_lo, fin_T())
    # Seitenflosse/-ruder: obere = linke Seite, untere = rechte Seite
    for i, nm in enumerate(("links", "rechts")):
        pass
    parts.append(rudder_lever())
    # ---- Hörner --------------------------------------------------------------- #
    horn = ruderhorn()
    parts.append(Part("Ruderhorn", "Kleinteile", horn, np.eye(4), g.rot_x(90), qty=5, material="PETG",
                      note="je 1x Querruder links/rechts, Landeklappe links/rechts, Höhenruder (links unten)"))
    return parts


# --------------------------------------------------------------------------- #
# Seitenruder-Anlenkung: Ruderwelle + Hebel im Rumpfheck
# --------------------------------------------------------------------------- #
def elevator_horn_T() -> np.ndarray:
    """Einbaulage des Höhenruderhorns (links unten) im Zusammenbau."""
    from .surface import horn_place
    s = stab_surface()
    xe = lambda y: s.x_le(y) + (1 - ELEV_FRAC) * stab_chord(y)
    T, _ = horn_place(s, xe, ELEV_HORN_Y, x_off=3.0)
    M = np.diag([1.0, -1.0, 1.0, 1.0])
    return M @ stab_T() @ T @ M


def elevator_horn_hole() -> np.ndarray:
    from .surface import HORN_REACH, HORN_HOLE_UP
    return (elevator_horn_T() @ np.array([7.0, 0.0, -HORN_REACH + HORN_HOLE_UP, 1.0]))[:3]


def rudder_axis():
    """Scharnierachse des Seitenruders im Zusammenbau: (Punkt bei Fußhöhe, Richtung nach oben)."""
    (xa, _), (xb, _) = RUDDER_HINGE
    a = np.array([xa, 0.0, FIN_BASE_Z])
    b = np.array([xb, 0.0, FIN_BASE_Z + FIN_HEIGHT])
    return a, (b - a) / np.linalg.norm(b - a)


def rudder_axis_at(z: float) -> np.ndarray:
    a, u = rudder_axis()
    return a + u * (z - a[2]) / u[2]


def rudder_lever_T() -> np.ndarray:
    """Hebel lokal (z = Wellenachse, x = Hebelarm) -> Zusammenbau; Arm zeigt nach rechts (+y)."""
    _, u = rudder_axis()
    ex = np.array([0.0, 1.0, 0.0])
    T = np.eye(4)
    T[:3, 0], T[:3, 1], T[:3, 2] = ex, np.cross(u, ex), u
    T[:3, 3] = rudder_axis_at(RUDDER_LEVER_Z)
    return T


def rudder_lever_hole() -> np.ndarray:
    return (rudder_lever_T() @ np.array([RUDDER_LEVER_R, 0.0, 2.5, 1.0]))[:3]


def rudder_wire_line():
    """Ruderwelle (Zusammenbau): von der Hebel-Unterkante bis ins Seitenruder."""
    return rudder_axis_at(RUDDER_LEVER_Z - 1.0), rudder_axis_at(FIN_BASE_Z + RUDDER_WIRE_TOP - 1.0)


def rudder_lever() -> Part:
    r, h = 5.0, 8.0
    body = g.cyl((0, 0, 0), (0, 0, h), r, segs=40) + g.box(0, RUDDER_LEVER_R + 3.5, -3.0, 3.0, 0.0, 5.0)   # liegt flach auf
    body = body - g.cyl((0, 0, -1), (0, 0, h + 1), 1.1, segs=24)                       # Ø2-Welle
    body = body - g.cyl((-r - 1, 0, h / 2), (0, 0, h / 2), 1.25, segs=16)              # M3-Madenschraube (nach links)
    body = body - g.cyl((RUDDER_LEVER_R, 0, 0), (RUDDER_LEVER_R, 0, h), 0.8, segs=16)  # Anlenkloch Ø1,6
    return Part("S4_Seitenruderhebel", "Leitwerk", body, rudder_lever_T(), np.eye(4), material="PETG", infill=1.0,
                note="klemmt mit M3-Madenschraube auf der Ø2-Ruderwelle; Zugang durch die Wartungsöffnung links im Heck")


def pivot_pts(surf, xh_fn, ya, yb):
    from .surface import pivot_axis
    return pivot_axis(surf, xh_fn, ya, yb)


def split_halves_ctrl(surf, ctrl, outer, xh_fn, ya, yb, gap_a=True):
    """Ober-/Unterschale einer Steuerfläche (Flansch nur hinter der Scharnierlinie)."""
    ys = [ya + 2.0, yb - 2.0]
    front = [(xh_fn(y) + 3.0, y) for y in ys]
    rear = [(surf.x_le(y) + CLIP * surf.chord(y) - 0.2, y) for y in ys][::-1]
    cs = g.CrossSection([g.ccw(front + rear)])
    ring = cs - cs.offset(-3.0, g.m3.JoinType.Miter, 2.0, 8)
    up_ring = g.Manifold.extrude(ring, 1.0) ^ outer
    dn_ring = g.Manifold.extrude(ring, 1.0).translate((0, 0, -1.0)) ^ outer
    upper = (ctrl ^ g.box(-1e4, 1e4, -1e4, 1e4, 0, 1e3)) + up_ring
    lower = (ctrl ^ g.box(-1e4, 1e4, -1e4, 1e4, -1e3, 0)) + dn_ring
    return g.drop_floating(upper), g.drop_floating(lower)
