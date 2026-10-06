"""Fernsteuerung: Servos, Servohebel, Gestänge und Ruderhörner aus der Modellgeometrie.

Alle Punkte im Zusammenbau-Rahmen (x hinten, y rechts, z oben, mm). Für jede Funktion wird geprüft,
welcher Servohebel-Lochabstand den gewünschten Ruderausschlag ergibt.
"""
from __future__ import annotations

import numpy as np

from . import fuselage as fu
from . import surface as sf
from . import tail, wing
from .params import *

SV = SERVO_9G
SHAFT_OFF = fu.SHAFT_OFF
SERVO_TRAVEL = 35.0                    # genutzter Servoweg ± (Grad)
STD_ARM_HOLES = (8.0, 10.0, 12.0, 14.0, 16.0, 18.0)   # übliche Lochabstände an Servohebeln
TAIL_ARM_R = fu.TAIL_ARM_R

# Sollausschläge (Grad) – siehe docs/FERNSTEUERUNG.md
TARGET = {"quer": 15.0, "klappe": 35.0, "hoehe": 15.0, "seite": 20.0, "bugrad": 30.0}
LABEL = {"quer": "Querruder", "klappe": "Landeklappe", "hoehe": "Höhenruder", "seite": "Seitenruder", "bugrad": "Bugrad"}


def _tp(T, p):
    return (T @ np.append(np.asarray(p, float), 1.0))[:3]


def _td(T, d):
    return T[:3, :3] @ np.asarray(d, float)


def _mirror(v):
    return np.asarray(v, float) * np.array([1.0, -1.0, 1.0])


def _line_dist(p, a, b):
    d = (b - a) / np.linalg.norm(b - a)
    v = p - a
    return float(np.linalg.norm(v - d * (v @ d)))


def horn_transforms() -> list[tuple[str, np.ndarray]]:
    """(Steuerflächen-Knoten, Einbaulage des Ruderhorns im Zusammenbau) für alle 5 Hörner."""
    out = []
    surf = wing.make_surface()
    Tw = wing.wing_asm_T()
    xh = lambda y: (1.0 - AIL_CHORD_FRAC) * wing.wing_chord(y)
    M = np.diag([1.0, -1.0, 1.0, 1.0])
    for node, y_h in (("Q1_Querruder_innen", AIL_SERVO_Y + 22.0), ("K1_Landeklappe", FLAP_SERVO_Y + 22.0)):
        T, _ = sf.horn_place(surf, xh, y_h)
        out.append((f"{node}_rechts", Tw @ T))
        out.append((f"{node}_links", M @ Tw @ T @ M))     # gespiegelt (Horn bleibt mittig im Schlitz)
    s = tail.stab_surface()
    xe = lambda y: s.x_le(y) + (1 - ELEV_FRAC) * tail.stab_chord(y)
    T, _ = sf.horn_place(s, xe, ELEV_HORN_Y, x_off=3.0)
    out.append(("H2_Hoehenruder_links_unten", tail.elevator_horn_T()))
    return out


def _wing_servo(y_s, side):
    """Flügelservo im Schacht: Flansch an der Unterseite (folgt deren Neigung), Abtrieb nach unten,
    Hebel zeigt nach außen (Richtung Horn)."""
    surf = wing.make_surface()
    Tw = wing.wing_asm_T()
    c = surf.chord(y_s)
    z_low = surf._surf_z(AIL_SERVO_X, c, False)
    a = np.arctan2(surf._surf_z(AIL_SERVO_X + 10, c, False) - surf._surf_z(AIL_SERVO_X - 10, c, False), 20.0)
    bx = np.array([np.cos(a), 0.0, np.sin(a)])
    ax = np.array([np.sin(a), 0.0, -np.cos(a)])          # Abtriebsseite (nach unten)
    p0 = np.array([AIL_SERVO_X, y_s, z_low])
    center = p0 + ax * (SV["flange_off"] - SV["H"] / 2)
    shaft = p0 + ax * SV["flange_off"] + bx * SHAFT_OFF
    res = dict(center=_tp(Tw, center), shaft=_tp(Tw, shaft), arm_pivot=_tp(Tw, shaft + ax * 2.5),
               axis=_td(Tw, ax), arm_dir=_td(Tw, (0, 1, 0)), body_x=_td(Tw, bx), body_z=_td(Tw, -ax))
    if side < 0:
        res = {k: _mirror(v) for k, v in res.items()}
    return res


def _wing_horn_hole(y_h, side):
    surf = wing.make_surface()
    xh = lambda y: (1.0 - AIL_CHORD_FRAC) * wing.wing_chord(y)
    _, hole = sf.horn_place(surf, xh, y_h)
    p = _tp(wing.wing_asm_T(), hole)
    return p if side > 0 else _mirror(p)


def _shelf_servo(sgn, x_c, z_s, arm_dir, shaft_fwd=False):
    """Servo im Servoboden an der Seitenwand; Abtrieb oben, Welle hinten (oder vorn bei shaft_fwd)."""
    yw = fu.inner_half_width(x_c, z_s)
    y_c = sgn * (yw - fu.SERVO_INSET)
    top = z_s + 2.4 + SV["flange_off"]                 # Abtriebsseite (oben)
    bx = np.array([-1.0 if shaft_fwd else 1.0, 0, 0])
    center = np.array([x_c, y_c, top - SV["H"] / 2])
    shaft = np.array([x_c + bx[0] * SHAFT_OFF, y_c, top])
    return dict(center=center, shaft=shaft, arm_pivot=np.array([shaft[0], y_c, z_s + fu.ARM_Z]), axis=np.array([0, 0, 1.0]),
                arm_dir=np.asarray(arm_dir, float), body_x=bx, body_z=np.array([0, 0, 1.0]))


def _rot(p, a, b, ang):
    """Punkt p um die Achse a->b um ang (Grad) drehen (Rodrigues)."""
    k = (b - a) / np.linalg.norm(b - a)
    v = p - a
    t = np.radians(ang)
    return a + v * np.cos(t) + np.cross(k, v) * np.sin(t) + k * (k @ v) * (1 - np.cos(t))


def arm_end(d, phi):
    sv = d["servo"]
    return _rot(sv["arm_pivot"] + sv["arm_dir"] * d["arm_r"], sv["arm_pivot"], sv["arm_pivot"] + sv["axis"], phi)


def _rod_len(d, phi, delta):
    a, b = d["hinge"]
    pts = [arm_end(d, phi)] + d.get("via", []) + [_rot(d["horn"], a, b, delta)]
    return sum(float(np.linalg.norm(q - p)) for p, q in zip(pts[:-1], pts[1:]))


def solve_delta(d, phi, L0, rng=70.0):
    """Ruderausschlag (Grad, um die Scharnierachse) bei Servowinkel phi; Gestängelänge bleibt L0."""
    ds = np.linspace(-rng, rng, 281)
    f = np.array([_rod_len(d, phi, x) - L0 for x in ds])
    roots = [ds[i] - f[i] * (ds[i + 1] - ds[i]) / (f[i + 1] - f[i])
             for i in range(len(ds) - 1) if f[i] == 0 or f[i] * f[i + 1] < 0]
    if not roots:
        return float("nan")
    return float(min(roots, key=abs))


def simulate(d) -> dict:
    """Kinematik: Servo ±SERVO_TRAVEL (Klappe: Endlage -> andere Endlage) -> Ruderausschläge."""
    if d["kind"] == "klappe":
        best = None
        for phi0 in (-SERVO_TRAVEL, SERVO_TRAVEL):        # Ruhelage = eine Servo-Endlage (Klappe eingefahren)
            L0 = _rod_len(d, phi0, 0.0)
            dl = solve_delta(d, -phi0, L0)
            down = dl * d["hinge_sign"] > 0
            if down and (best is None or abs(dl) > abs(best[1])):
                best = (phi0, dl)
        phi0, dl = best
        return dict(rest_phi=phi0, max_deflection=abs(dl), deflections=(0.0, abs(dl)),
                    arm_end=arm_end(d, phi0))
    L0 = _rod_len(d, 0.0, 0.0)
    lo, hi = solve_delta(d, -SERVO_TRAVEL, L0), solve_delta(d, SERVO_TRAVEL, L0)
    m = min(abs(lo), abs(hi)) if not (np.isnan(lo) or np.isnan(hi)) else 0.0
    return dict(rest_phi=0.0, max_deflection=m, deflections=(abs(lo), abs(hi)), arm_end=arm_end(d, 0.0))


def linkages() -> list[dict]:
    out = []
    hinges = {}
    from .viewer import hinge_axes                      # Scharnierachsen (Zusammenbau)
    signs = {}
    for k, (kind, sign, a, b) in hinge_axes().items():
        hinges[k] = (np.asarray(a, float), np.asarray(b, float))
        signs[k] = sign

    def finish(d, surface_node, target):
        a, b = hinges[surface_node] if surface_node in hinges else d.pop("_axis")
        d.update(surface=surface_node, hinge=(a, b), horn_arm=_line_dist(d["horn"], a, b), target=target)
        servo = d["servo"]
        if d["kind"] == "klappe":
            r_req = d["horn_arm"] * np.sin(np.radians(target)) / (2 * np.sin(np.radians(SERVO_TRAVEL)))
        else:
            r_req = d["horn_arm"] * np.sin(np.radians(target)) / np.sin(np.radians(SERVO_TRAVEL))
        holes = [d["arm_r_fixed"]] if d.get("arm_r_fixed") else list(STD_ARM_HOLES)
        for r in holes:                                  # kleinstes Loch, das den Sollausschlag erreicht
            d["arm_r"] = r
            d.update(simulate(d))
            if d["max_deflection"] >= target:
                break
        pts = [d["arm_end"]] + d.get("via", []) + [d["horn"]]
        seg = [float(np.linalg.norm(q - p)) for p, q in zip(pts[:-1], pts[1:])]
        d.update(arm_r_req=r_req, rod_points=pts, rod_segments=seg, rod_len=sum(seg))
        out.append(d)

    for side, sname in ((1, "rechts"), (-1, "links")):
        for kind, y_s, node in (("quer", AIL_SERVO_Y, "Q1_Querruder_innen"), ("klappe", FLAP_SERVO_Y, "K1_Landeklappe")):
            servo = _wing_servo(y_s, side)
            horn = _wing_horn_hole(y_s + 22.0, side)
            where = f"Flügel {'W2' if kind == 'quer' else 'W1'} {sname}, y = {side * y_s:+.0f} mm, Abtrieb unten"
            finish(dict(name=f"{LABEL[kind]} {sname}", kind=kind, side=side, servo=servo, horn=horn, where=where,
                        hinge_sign=signs[f"{node}_{sname}"],
                        rod="Stahldraht Ø1,5 mm mit Z-Bügel am Servo und Gabelkopf am Horn"),
                   f"{node}_{sname}", TARGET[kind])

    # Höhenruder (links): Servo im Rumpf (F4), CFK-Stab im Kanal, Austritt links am Heck, Z-Bügel zum Horn
    servo = _shelf_servo(-1, fu.TAIL_SERVO_X, fu.TAIL_SERVO_Z, (0, 1, 0))
    exit_p = np.array([fu.TAIL_ROD_EXIT_X, -fu.TAIL_ROD_EXIT_Y, fu.TAIL_ROD_EXIT_Z])
    finish(dict(name=LABEL["hoehe"], kind="hoehe", side=-1, servo=servo, horn=tail.elevator_horn_hole(), via=[exit_p],
                where=f"Rumpf F4 links, x = {fu.TAIL_SERVO_X:.0f} mm, Abtrieb oben",
                arm_r_fixed=TAIL_ARM_R,
                rod="Bowdenzug: Außenrohr Ø3/2 mm im Kanal bis ins Austrittsloch, Stahlseele Ø1,2 mm; "
                    "Z-Bügel am Servo, Gabelkopf am Horn"),
           "H2_Hoehenruder_links_unten", TARGET["hoehe"])
    # Seitenruder (rechts): Gestänge bleibt im Rumpf und greift am Seitenruderhebel (S4) auf der Ruderwelle an
    servo = _shelf_servo(+1, fu.TAIL_SERVO_X, fu.TAIL_SERVO_Z, (0, -1, 0))
    finish(dict(name=LABEL["seite"], kind="seite", side=1, servo=servo, horn=tail.rudder_lever_hole(),
                where=f"Rumpf F4 rechts, x = {fu.TAIL_SERVO_X:.0f} mm, Abtrieb oben",
                arm_r_fixed=TAIL_ARM_R,
                rod="CFK-Stab Ø2 mm im Kanal, Enden Stahldraht Ø1,5 mm (Z-Bügel am Servo, Gabelkopf am Hebel)"),
           "S2_Seitenruder_unten", TARGET["seite"])

    # Bugrad: Servo links im Bug (Welle vorn), Hebel zeigt nach vorn, Gestänge fast quer zum Lenkhebel G6
    servo = _shelf_servo(-1, fu.NOSE_SERVO_X, fu.NOSE_SERVO_Z, (-1, 0, 0), shaft_fwd=True)
    hole = np.array([NOSE_GEAR_X + 14.0, 0.0, NOSE_WIRE_Z_TOP - 8.0 + 0.6 + 2.5])
    finish(dict(name=LABEL["bugrad"], kind="bugrad", side=0, servo=servo, horn=hole,
                where=f"Rumpf F2 links, x = {fu.NOSE_SERVO_X:.0f} mm, Abtrieb oben (Welle vorn)",
                _axis=(np.array([NOSE_GEAR_X, 0, 0.0]), np.array([NOSE_GEAR_X, 0, 200.0])),
                rod="Stahldraht Ø1,2 mm mit Z-Bügeln"),
           "G6_Lenkhebel", TARGET["bugrad"])
    return out


def surface_depth(kind: str) -> float | None:
    """Rudertiefe (Scharnier -> Hinterkante) an der Anlenkstelle, für Ausschläge in mm."""
    if kind == "quer":
        return AIL_CHORD_FRAC * wing.wing_chord(AIL_SERVO_Y + 22.0)
    if kind == "klappe":
        return AIL_CHORD_FRAC * wing.wing_chord(FLAP_SERVO_Y + 22.0)
    if kind == "hoehe":
        return ELEV_FRAC * tail.stab_chord(ELEV_HORN_Y)
    if kind == "seite":
        f = tail.fin_surface()
        (xa, _), (xb, _) = RUDDER_HINGE
        y = RUDDER_Y0 + 10.0
        return f.x_le(y) + tail.fin_chord(y) - (xa + (xb - xa) * y / FIN_HEIGHT)
    return None


def doc_rows() -> list[str]:
    """Tabelle für docs/FERNSTEUERUNG.md (AUTO:anlenkung)."""
    def de(v, d=0):
        return f"{v:.{d}f}".replace(".", ",")
    rows = ["| Funktion | Servo | Hebel-Loch | Ruderhebel | Gestänge (Z-Bügel → Loch) | max. Ausschlag (±35° Servo) | Soll | ≈ an der Hinterkante | Servoweg-Anteil für Soll |",
            "|---|---|---:|---:|---|---:|---:|---:|---:|"]
    for d in linkages():
        segs = " + ".join(de(x) for x in d["rod_segments"])
        depth = surface_depth(d["kind"])
        mm = f"{de(depth * np.sin(np.radians(d['target'])))} mm" if depth else "–"
        if d["kind"] == "klappe":
            mx, travel = f"0 … {de(d['max_deflection'])}°", "100 % (Endlage → Endlage)"
        else:
            mx = f"± {de(d['max_deflection'])}°"
            travel = f"≈ {min(100, 5 * round(20 * d['target'] / d['max_deflection'])):.0f} %"
        rows.append(f"| **{d['name']}** | {d['where']} | {de(d['arm_r'])} mm | {de(d['horn_arm'])} mm | "
                    f"**{segs} mm**: {d['rod']} | {mx} | {de(d['target'])}° | {mm} | {travel} |")
    return rows
