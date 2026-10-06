"""Geometrische Funktionsprüfungen: Ruderfreigang (virtuelles Ausschlagen um die Scharnierachse)."""
from __future__ import annotations

import numpy as np

from . import fuselage, geom as g, tail, wing
from . import surface as sf
from .params import *
from .parts import Part


def _rot_about_axis(m, p0, p1, deg):
    d = np.asarray(p1, float) - np.asarray(p0, float)
    d /= np.linalg.norm(d)
    R = g.rotation_matrix(d, deg)
    T = g.translation(*p0) @ R @ g.translation(*(-np.asarray(p0, float)))
    return g.apply(m, T)


def hinge_clearance(parts: list[Part], angles=(-30, -25, 25, 30)) -> list[tuple]:
    """Gibt (Ruder, Winkel, Überschneidung mm³) zurück; 0 = frei beweglich."""
    P = {p.name: p for p in parts}
    out = []

    # --- Querruder (rechts) --------------------------------------------------- #
    surf = wing.make_surface()
    xh = lambda y: (1.0 - AIL_CHORD_FRAC) * wing.wing_chord(y)
    y2 = WING_CENTER_HALF + 2 * WING_PANEL_SPAN
    wing_T = wing.wing_asm_T()
    for fixed, ail, (ya, yb) in (("W2_rechts", "Q1_Querruder_innen_rechts", (AIL_Y0, y2)),
                                 ("W3_rechts", "Q2_Querruder_aussen_rechts", (y2, AIL_Y1))):
        p0, p1 = sf.pivot_axis(surf, xh, ya, yb)
        F, A = P[fixed].mesh, P[ail].mesh
        for a in angles:
            out.append((ail, a, (F ^ _rot_about_axis(A, p0, p1, a)).volume()))

    # --- Landeklappe (rechts): 0 .. FLAP_DOWN_MAX nach unten (beide Drehrichtungen geprüft) --- #
    p0, p1 = sf.pivot_axis(surf, xh, FLAP_Y0, FLAP_Y1)
    F, A = P["W1_rechts"].mesh, P["K1_Landeklappe_rechts"].mesh
    for a in (-FLAP_DOWN_MAX, -15, 15, FLAP_DOWN_MAX):
        out.append(("K1_Landeklappe_rechts", a, (F ^ _rot_about_axis(A, p0, p1, a)).volume()))

    # --- Höhenruder (rechts) ---------------------------------------------------- #
    s = tail.stab_surface()
    xe = lambda y: s.x_le(y) + (1 - ELEV_FRAC) * tail.stab_chord(y)
    q0, q1 = sf.pivot_axis(s, xe, ELEV_Y0, ELEV_END)
    Ts = tail.stab_T()
    q0, q1 = (Ts @ np.append(q0, 1))[:3], (Ts @ np.append(q1, 1))[:3]
    asm = lambda n: P[n].asm_mesh()
    elev = g.union([asm("H2_Hoehenruder_rechts_oben"), asm("H2_Hoehenruder_rechts_unten")])
    fixed = g.union([asm(n) for n in P if n.startswith(("H1_Hoehenflosse_rechts", "S1_", "S2_"))])
    for a in angles:
        out.append(("H2_Hoehenruder_rechts", a, (fixed ^ _rot_about_axis(elev, q0, q1, a)).volume()))

    # --- Seitenruder --------------------------------------------------------------- #
    f = tail.fin_surface()
    (xa, _), (xb, _) = RUDDER_HINGE
    xhf = lambda y: xa + (xb - xa) * y / FIN_HEIGHT
    r0, r1 = sf.pivot_axis(f, xhf, RUDDER_Y0, RUDDER_Y1)
    Tf = tail.fin_T()
    r0, r1 = (Tf @ np.append(r0, 1))[:3], (Tf @ np.append(r1, 1))[:3]
    rud = g.union([asm("S2_Seitenruder_oben"), asm("S2_Seitenruder_unten")])
    fixed2 = g.union([asm(n) for n in P if n.startswith(("S1_", "H1_", "H2_"))])
    for a in angles:
        out.append(("S2_Seitenruder", a, (fixed2 ^ _rot_about_axis(rud, r0, r1, a)).volume()))
    return out


def spar_fit() -> dict:
    """Prüft, dass die Holmhülse an Wurzel und Spitze innerhalb des Profils liegt (Restwand in mm)."""
    surf = wing.make_surface()
    res = {}
    for y, label in ((0.0, "Wurzel"), (WING_SEMISPAN - 30.0, "Randbogen-Beginn")):
        c = surf.chord(y)
        zu = surf._surf_z(SPAR_X, c, True)
        zl = surf._surf_z(SPAR_X, c, False)
        top = zu - (SPAR_Z + SPAR_SLEEVE_OD / 2)
        bot = (SPAR_Z - SPAR_SLEEVE_OD / 2) - zl
        res[label] = (round(top, 2), round(bot, 2))
    return res
