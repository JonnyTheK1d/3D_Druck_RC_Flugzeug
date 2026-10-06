"""Antrieb: Motorbock (Standrohr) und Spinner."""
from __future__ import annotations

import numpy as np

from . import geom as g
from .geom import CrossSection, Manifold
from .params import *
from .parts import Part


def motor_mount() -> Part:
    """Standrohr mit Motorflansch vorne (x = MOTOR_SEAT_X) und Brandschott-Flansch hinten (x = 125)."""
    x_f0, x_f1 = MOTOR_SEAT_X, MOTOR_SEAT_X + 4.0           # Motorflansch
    x_r0, x_r1 = FIREWALL_X - 4.0, FIREWALL_X               # hinterer Flansch
    z0 = MOTOR_AXIS_Z
    ax = lambda xa, xb, r, r1=None, y=0.0, z=0.0, segs=64: g.cyl((xa, y, z0 + z), (xb, y, z0 + z), r, r1, segs)
    body = ax(x_f0, x_f1, 23.0) + ax(x_f1 - 0.01, x_r0 + 0.01, 20.0) + ax(x_r0, x_r1, 26.0)
    # Innenraum (Kabeldurchgang) und Lüftungsschlitze
    body = body - ax(x_f1 - 0.01, x_r1 + 1, 18.0) - ax(x_f0 - 1, x_f1 + 1, 6.5)
    for ang in np.arange(0, 360, 60) + 30:
        c, s = np.cos(np.radians(ang)), np.sin(np.radians(ang))
        slot = g.box(x_f1 + 14, x_f1 + 44, 16.0, 24.0, -5.0, 5.0)
        slot = g.apply(slot, g.rot_x(ang)).translate((0, 0, z0))
        body = body - slot
    # Motorbefestigung: 16/19-mm-Kreuz (M3), Motor sitzt vor dem Flansch
    for d in (16.0, 19.0):
        for sy in (-1, 1):
            for sz in (-1, 1):
                body = body - ax(x_f0 - 1, x_f1 + 1, 1.7, y=sy * d / 2, z=sz * d / 2, segs=16)
    # hinten: M3 auf 30-mm-Quadrat (wie Brandschott)
    for sy in (-1, 1):
        for sz in (-1, 1):
            body = body - ax(x_r0 - 1, x_r1 + 1, 1.7, y=sy * 15.0, z=sz * 15.0, segs=16)
    # Druckausrichtung: Achse nach oben, hinterer Flansch unten
    R = g.rot_y(-90)
    return Part("P1_Motorbock", "Antrieb", body, np.eye(4), R, material="PETG", infill=0.45,
                note="Motor vorn mit 4x M3 anschrauben, hinten mit 4x M3 an den Brandschott; Hitze -> PETG")


def spinner_profile(L=SPINNER_LEN, R=SPINNER_D / 2, n=36):
    s = np.linspace(0, L, n)
    r = R * np.sqrt(np.maximum(1 - (s / L) ** 2.2, 0.0)) ** 0.9
    return s, r


def revolve_profile(s, r, wall=None):
    """Rotationskörper um die x-Achse (hier: s = Achsrichtung nach vorn = -x)."""
    pts = [(0.0, 0.0)] + list(zip(r, s)) + [(0.0, s[-1])]
    # CrossSection: x = Radius, y = Achsabstand -> revolve um die Y-Achse
    cs = CrossSection([g.ccw([(0.0, s[0])] + [(ri, si) for si, ri in zip(s, r)] + [(0.0, s[-1])])])
    m = Manifold.revolve(cs, 96)                      # Achse = Z
    return m


def spinner() -> list[Part]:
    L, R = SPINNER_LEN, SPINNER_D / 2
    s, r = spinner_profile(L, R)
    r[-1] = max(r[-1], 0.5)
    outer = revolve_profile(s, r)
    # Hohlraum: Profil um die Wand nach innen versetzt
    wall = 1.2
    inner_cs = CrossSection([g.ccw([(0.0, -1.0), (R - wall, -1.0)] + [(max(ri - wall, 0.0), si) for si, ri in zip(s, r) if si < L - 4]
                                    + [(0.0, L - 4.5)])])
    inner = Manifold.revolve(inner_cs, 96)
    cone = outer - inner
    # Blattaussparungen (2 Blätter, 12 mm breit, 14 mm tief vom hinteren Rand)
    for ang in (0, 90):
        slot = g.box(-R - 2, R + 2, -7.0, 7.0, -1.0, 14.0)
        cone = cone - g.apply(slot, g.rot_z(ang))
    # vier Schraubdome innen, nahe dem Rand (M2.5 Blechschrauben)
    for ang in (45, 135, 225, 315):
        c, sn = np.cos(np.radians(ang)), np.sin(np.radians(ang))
        px, py = (R - wall - 3.0) * c, (R - wall - 3.0) * sn
        boss = g.cyl((px, py, 0.0), (px, py, 10.0), 3.2, segs=24) ^ outer
        cone = cone + boss - g.cyl((px, py, -1.0), (px, py, 9.0), 1.1, segs=16)
    # Rückplatte
    plate = g.cyl((0, 0, 0), (0, 0, 3.0), R, segs=96)
    plate = plate - g.cyl((0, 0, -1), (0, 0, 4), 4.2, segs=48)
    for ang in (45, 135, 225, 315):
        c, sn = np.cos(np.radians(ang)), np.sin(np.radians(ang))
        px, py = (R - wall - 3.0) * c, (R - wall - 3.0) * sn
        plate = plate - g.cyl((px, py, -1), (px, py, 4), 1.4, segs=16)
    for ang in (0, 90, 180, 270):               # Aussparungen für die Blattwurzeln
        pass
    # Zusammenbau: Achse Z -> -X (Spitze nach vorn), Rückplatte bei x = -1
    T = g.translation(-4.0, 0, MOTOR_AXIS_Z) @ g.rot_y(-90)           # Kegelrand bei x = -4, Spitze bei x = -49
    cone_part = Part("P2_Spinner", "Antrieb", cone, T, np.eye(4), material="PLA", infill=1.0,
                     note="offene Seite nach unten drucken; 4x M2.5x10 Blechschrauben in die Domen")
    plate_part = Part("P3_Spinnerplatte", "Antrieb", plate, g.translation(-1.0, 0, MOTOR_AXIS_Z) @ g.rot_y(-90),
                      np.eye(4), material="PETG", note="mit Mitnehmer/Propelleradapter verschrauben")
    return [cone_part, plate_part]
