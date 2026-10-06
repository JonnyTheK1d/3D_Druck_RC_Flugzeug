"""Tragfläche: Mittelstück + 3 Außenabschnitte je Seite + Querruder."""
from __future__ import annotations

import numpy as np

from . import airfoil as af
from . import geom as g
from .geom import CrossSection, Manifold
from .params import *
from .parts import Part
from .surface import (CLIP, Surface, build_panel, control_surface, add_horn_slot, ruderhorn)


# --------------------------------------------------------------------------- #
# Tiefenverteilung
# --------------------------------------------------------------------------- #
def wing_chord(y: float) -> float:
    y = abs(y)
    if y <= WING_TAPER_START:
        return WING_ROOT_CHORD
    f = (y - WING_TAPER_START) / (WING_SEMISPAN - WING_TAPER_START)
    return WING_ROOT_CHORD + (WING_TIP_CHORD - WING_ROOT_CHORD) * f


def make_surface() -> Surface:
    return Surface(code=WING_AIRFOIL, chord=wing_chord, x_le0=0.0, sweep=0.0,
                   wall=WALL_WING, breakpoints=(WING_TAPER_START,),
                   rib_pitch=35.0, hole_x_min=SPAR_X + 10.0, flat_from=WING_FLAT_FROM)


SPAR = (SPAR_X, SPAR_Z, SPAR_BORE, SPAR_SLEEVE_OD)
CABLE_SLOT_X, CABLE_SLOT_W, CABLE_SLOT_L = 105.0, 12.0, 24.0     # Langloch: Lage x, Breite (x), Länge (y)
BOLT_COLUMNS = tuple((bx, sy * WING_BOLT_Y, 4.6, 1.75) for bx in WING_BOLT_X for sy in (-1, 1))


# --------------------------------------------------------------------------- #
# Servoschacht und Hornschlitz
# --------------------------------------------------------------------------- #
def add_servo_box(surf: Surface, solid: Manifold, outer: Manifold, y_s: float, x_s: float):
    """Rechteckiger Schacht in der Unterseite für ein 9-g-Servo (Abtrieb nach unten)."""
    sv = SERVO_9G
    c = surf.chord(y_s)
    z_low = surf._surf_z(x_s, c, False)
    wall = 1.3
    ix0, ix1 = x_s - sv["L"] / 2 - 0.3, x_s + sv["L"] / 2 + 0.3
    iy0, iy1 = y_s - sv["W"] / 2 - 0.3, y_s + sv["W"] / 2 + 0.3
    h_up = sv["H"] - sv["flange_off"] + 1.0          # Körperhöhe über dem Flansch
    outer_box = g.box(ix0 - wall, ix1 + wall, iy0 - wall, iy1 + wall, z_low - 2.0, z_low + h_up + 1.0) ^ outer
    inner_box = g.box(ix0, ix1, iy0, iy1, z_low - 5.0, z_low + h_up)
    notch = g.box(ix0 + 4, ix0 + 10, iy0 - wall - 1, iy0 + 0.5, z_low + h_up - 6, z_low + h_up - 0.5)  # Kabelkerbe
    solid = (solid + outer_box) - inner_box - notch
    return solid


# --------------------------------------------------------------------------- #
# Gesamter Flügel
# --------------------------------------------------------------------------- #
def wing_asm_T() -> np.ndarray:
    return g.translation(WING_LE_X, 0, WING_Z_REF) @ g.rot_y(WING_INCIDENCE, about=(50.0, 0, 0))


def tilt_R(surf: Surface, y0: float | None = None, y1: float | None = None, mirror: bool = False) -> np.ndarray:
    """Drehung, die die ebene Profilunterseite (Bodenebene) waagerecht auf das Druckbett legt.

    Bei verjüngtem Flügel ist die Unterseite auch spanweise geneigt; sie ist dann eine Ebene
    z = a*x + b*y + c, die hier per Ausgleichsrechnung bestimmt wird.
    """
    if y0 is None:
        return g.rot_y(surf.tilt_deg())
    pts = []
    for y in np.linspace(y0 + 3.0, y1 - 3.0, 7):
        c = surf.chord(y)
        for xr in (0.45, 0.6, 0.8, 0.95):
            pts.append((xr * c, y, surf._surf_z(xr * c, c, False)))
    P = np.array(pts)
    A = np.c_[P[:, 0], P[:, 1], np.ones(len(P))]
    a, b, _ = np.linalg.lstsq(A, P[:, 2], rcond=None)[0]
    n_out = np.array([a, -b if mirror else b, -1.0])           # nach unten zeigende Normale der Bodenebene
    return g.rot_from_to(n_out, (0.0, 0.0, -1.0))


def mirrored(part: Part, name: str, print_R: np.ndarray | None = None) -> Part:
    return Part(name, part.group, g.mirror_y(part.mesh), part.asm_T, part.print_R if print_R is None else print_R,
                part.qty, part.material, part.note)


def build_wing() -> list[Part]:
    surf = make_surface()
    T = wing_asm_T()
    R = tilt_R(surf)
    parts: list[Part] = []

    def xh_fn(y):
        return (1.0 - AIL_CHORD_FRAC) * wing_chord(y)

    # ---- Mittelstück --------------------------------------------------------- #
    p = build_panel(surf, -WING_CENTER_HALF, WING_CENTER_HALF, spar=SPAR, columns=BOLT_COLUMNS)
    # Kabelaustritt (Servostecker) in der Unterseite zur Kabine hin, zwischen den Rippen bei y = ±16
    c0 = surf.chord(0.0)
    z_low = surf._surf_z(CABLE_SLOT_X, c0, False)
    slot = g.apply(Manifold.extrude(g.rounded_slot(-CABLE_SLOT_W / 2, CABLE_SLOT_W / 2, -CABLE_SLOT_L / 2, CABLE_SLOT_L / 2, 3.0), 6.0),
                   g.translation(CABLE_SLOT_X, 0, z_low - 2.0))
    w0 = p["solid"] - slot
    parts.append(Part("W0_Mittelstueck", "Flügel", w0, T, R, note="4 Schraubendome für M3, Kabelaustritt unten"))

    y1, y2, y3 = (WING_CENTER_HALF + WING_PANEL_SPAN * k for k in (1, 2, 3))   # 282.5 / 485 / 687.5

    # ---- Abschnitt 1 --------------------------------------------------------- #
    p = build_panel(surf, WING_CENTER_HALF, y1, spar=SPAR)
    R1 = tilt_R(surf, WING_CENTER_HALF, y1)
    w1 = Part("W1_rechts", "Flügel", p["solid"], T, R1)
    parts += [w1, mirrored(w1, "W1_links", tilt_R(surf, WING_CENTER_HALF, y1, True))]

    # ---- Abschnitt 2: Servoschacht + Querruder A ---------------------------- #
    p = build_panel(surf, y1, y2, spar=SPAR)
    solid = add_servo_box(surf, p["solid"], p["outer"], AIL_SERVO_Y, AIL_SERVO_X)
    fixed, ail_a, _ = control_surface(surf, solid, p["cav"], p["outer"], xh_fn, AIL_Y0, y2,
                                   gap_a=True, gap_b=False, cav_big=p["cav_big"])
    ail_a = add_horn_slot(surf, ail_a, p["outer"], xh_fn, AIL_SERVO_Y + 22.0)
    R2, R2m = tilt_R(surf, y1, y2), tilt_R(surf, y1, y2, True)
    w2 = Part("W2_rechts", "Flügel", fixed, T, R2, note="mit Servoschacht für 9-g-Servo (Querruder)")
    qa = Part("Q1_Querruder_innen_rechts", "Querruder", ail_a, T, tilt_R(surf, AIL_Y0, y2),
              note="Horn-Schlitz an der Unterseite; mit Q2 zu einem Ruder verkleben")
    parts += [w2, mirrored(w2, "W2_links", R2m), qa, mirrored(qa, "Q1_Querruder_innen_links", tilt_R(surf, AIL_Y0, y2, True))]

    # ---- Abschnitt 3: Randbogen + Querruder B ------------------------------- #
    y_cap0 = y3 - 30.0
    p = build_panel(surf, y2, y_cap0, end1=False, cap_len=30.0, spar=SPAR)
    fixed, ail_b, _ = control_surface(surf, p["solid"], p["cav"], p["outer"], xh_fn, y2, AIL_Y1,
                                   gap_a=False, gap_b=True, cav_big=p["cav_big"])
    R3, R3m = tilt_R(surf, y2, y_cap0), tilt_R(surf, y2, y_cap0, True)
    w3 = Part("W3_rechts", "Flügel", fixed, T, R3, note="mit abgerundetem Randbogen")
    qb = Part("Q2_Querruder_aussen_rechts", "Querruder", ail_b, T, tilt_R(surf, y2, AIL_Y1))
    parts += [w3, mirrored(w3, "W3_links", R3m), qb, mirrored(qb, "Q2_Querruder_aussen_links", tilt_R(surf, y2, AIL_Y1, True))]
    return parts
