"""Nicht gedruckte Komponenten (Draht, Rohre, Luftschraube): Maße für die Anleitung + Darstellung."""
from __future__ import annotations

import numpy as np

from . import geom as g
from .geom import CrossSection, Manifold
from .params import *

WIRE_EXIT_OUT = 6.0          # Biegung liegt 6 mm außerhalb der Rumpfwand


def main_gear_path():
    """Hauptfahrwerksdraht als Polylinie (y, z); symmetrisch zur Rumpfmitte."""
    from . import fuselage as fu
    yw = float(fu.section(MAIN_GEAR_X)[0][0]) / 2        # Rumpfwand
    zc = WHEEL_D / 2
    ye = yw + WIRE_EXIT_OUT
    y_ax = MAIN_GEAR_TRACK_HALF - WHEEL_W / 2 - 3.0       # Beginn der Achse (innen am Rad)
    y_end = MAIN_GEAR_TRACK_HALF + WHEEL_W / 2 + 6.0      # Drahtende hinter dem Rad
    left = [(-y_end, zc), (-y_ax, zc), (-ye, MAIN_WIRE_Z), (ye, MAIN_WIRE_Z), (y_ax, zc), (y_end, zc)]
    return np.array(left)


def polyline_length(pts) -> float:
    pts = np.asarray(pts, float)
    return float(np.linalg.norm(np.diff(pts, axis=0), axis=1).sum())


def wire_solid(path_yz, x, r) -> Manifold:
    segs = []
    for a, b in zip(path_yz[:-1], path_yz[1:]):
        segs.append(g.cyl((x, a[0], a[1]), (x, b[0], b[1]), r, segs=16))
        segs.append(g.sphere((x, b[0], b[1]), r, 16))
    return g.union(segs)


def prop_solid(dia_in=PROP_DIA_IN, x=-9.0) -> Manifold:
    """Zweiblatt-Luftschraube (nur Darstellung)."""
    R = dia_in * 25.4 / 2
    blades = []
    for k in (0, 1):
        pts = [(5.0, -4.0), (R * 0.35, -9.0), (R * 0.65, -11.0), (R * 0.92, -7.0), (R, -2.5),
               (R, 2.0), (R * 0.9, 5.0), (R * 0.6, 4.0), (R * 0.3, 2.5), (5.0, 3.0)]
        b = Manifold.extrude(CrossSection([g.ccw(pts)]), 2.2)                  # Blatt in XY, Dicke z
        b = b.translate((0, 0, -1.1))
        b = g.apply(b, g.rot_x(-22))                                             # Anstellwinkel
        if k:
            b = b.rotate((0, 0, 180))
        blades.append(b)
    hub = g.cyl((0, 0, -4.5), (0, 0, 4.5), 7.0, segs=32)
    prop = g.union(blades + [hub])
    # Propeller-Ebene = YZ, Achse = x
    return g.apply(prop, g.translation(x, 0, MOTOR_AXIS_Z) @ g.rot_y(90))


def motor_solid() -> Manifold:
    x0 = MOTOR_SEAT_X - MOTOR_LEN
    m = g.cyl((x0, 0, MOTOR_AXIS_Z), (MOTOR_SEAT_X, 0, MOTOR_AXIS_Z), MOTOR_D / 2, segs=48)
    m = m + g.cyl((x0 - 14.0, 0, MOTOR_AXIS_Z), (x0, 0, MOTOR_AXIS_Z), 2.0, segs=16)
    return m


def spar_tubes() -> Manifold:
    """CFK-Holm (zwei Rohre 10/8 + Verbinder) - nur Darstellung."""
    sx, sz = WING_LE_X + SPAR_X, WING_Z_REF + SPAR_Z
    return g.cyl((sx, -WING_SEMISPAN + 30, sz), (sx, WING_SEMISPAN - 30, sz), SPAR_OD / 2, segs=24)


def summary() -> dict:
    p = main_gear_path()
    return dict(
        gear_wire_len=polyline_length(p),
        nose_wire_len=NOSE_WIRE_Z_TOP + 1.0 - 57.5,
        spar_tube_len=660.0,
        joiner_len=200.0,
    )
