"""Rumpf: Rundrechteck-Querschnitte, Schale mit konstanter Wand, in Segmente und Hälften geteilt."""
from __future__ import annotations

import numpy as np
from scipy.interpolate import PchipInterpolator

from . import geom as g
from . import tail as tail_mod
from . import wing as wing_mod
from .geom import CrossSection, Manifold
from .params import *
from .parts import Part

T = WALL_FUSE
M = 72                                     # Punkte pro Querschnitt (durch 4 teilbar -> Symmetrie)
TH = np.linspace(0, 2 * np.pi, M, endpoint=False)

_tx = FUSE_TABLE[:, 0]
_W = lambda x: np.interp(x, FUSE_WIDTH_NODES[:, 0], FUSE_WIDTH_NODES[:, 1])   # Seitenwände eben
_ZB = PchipInterpolator(_tx, FUSE_TABLE[:, 2])
_ZT = PchipInterpolator(_tx, FUSE_TABLE[:, 3])
_RC = PchipInterpolator(_tx, FUSE_TABLE[:, 4])


# --------------------------------------------------------------------------- #
# Querschnitte
# --------------------------------------------------------------------------- #
def section(x):
    x = np.atleast_1d(np.asarray(x, float))
    w, zb, zt, rc = _W(x), _ZB(x), _ZT(x), _RC(x)
    rc = np.minimum(rc, 0.499 * np.minimum(w, zt - zb))
    return w, zb, zt, rc


def ring_yz(x, inset=0.0) -> np.ndarray:
    """Querschnittspunkte (S, M, 2) = (y, z) als Rundrechteck, um `inset` verkleinert."""
    w, zb, zt, rc = section(x)
    a = np.maximum(w / 2 - inset, 0.3)
    b = np.maximum((zt - zb) / 2 - inset, 0.3)
    r = np.clip(rc - inset, 0.25, np.minimum(a, b) - 0.01)
    zc = (zt + zb) / 2
    d0, d1 = np.cos(TH)[None, :], np.sin(TH)[None, :]
    lo = np.zeros((len(a), M))
    hi = np.full((len(a), M), float((a + b).max() + 10))
    ia, ib = (a - r)[:, None], (b - r)[:, None]
    for _ in range(34):
        t = (lo + hi) / 2
        qx = np.maximum(np.abs(t * d0) - ia, 0)
        qz = np.maximum(np.abs(t * d1) - ib, 0)
        out = (np.hypot(qx, qz) - r[:, None]) > 0
        hi = np.where(out, t, hi)
        lo = np.where(out, lo, t)
    t = (lo + hi) / 2
    return np.stack([t * d0, zc[:, None] + t * d1], axis=-1)


def grid(x0, x1, step=5.0):
    xs = set(np.arange(0, FUSE_LEN + 0.01, step)) | set(_tx) | {x0, x1}
    xs = np.array(sorted(v for v in xs if x0 - 1e-9 <= v <= x1 + 1e-9))
    return xs


def body(x0, x1, inset=0.0) -> Manifold:
    xs = grid(x0, x1)
    yz = ring_yz(xs, inset)
    rings = np.concatenate([xs[:, None, None] * np.ones((1, M, 1)), yz], axis=-1)
    return g.loft_rings(rings)


def poly_yz(x, inset=0.0) -> np.ndarray:
    return ring_yz([x], inset)[0]


def slab_x(cs: CrossSection, x0: float, thick: float) -> Manifold:
    """Querschnitt (Rahmen: X=y, Y=z) entlang x von x0 bis x0+thick extrudieren."""
    m = Manifold.extrude(cs, thick)
    Tm = np.array([[0, 0, 1, x0], [1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1.0]])
    return g.apply(m, Tm)


def ring_frame(x, thick=FRAME_T, width=FRAME_W, in0=T - 0.1):
    """Ringspant bei x: Band zwischen Innenfläche und Innenfläche + width (voll bei engen Querschnitten)."""
    w, zb, zt, rc = section(x)
    h_in = float(zt[0] - zb[0]) - 2 * T
    wd = min(width, 0.5 * min(float(w[0]) - 2 * T, h_in) - 1.8)
    outer = CrossSection([g.ccw(poly_yz(x, in0))])
    if wd < 0.8:
        return slab_x(outer, x, thick)
    inner = CrossSection([g.ccw(poly_yz(x, T + wd))])
    return slab_x(outer - inner, x, thick)


def ref_frame_pt(x, ang_deg, inset):
    """Punkt auf dem um `inset` verkleinerten Querschnitt in Richtung ang_deg (0 = +y, 90 = +z)."""
    pts = ring_yz([x], inset)[0]
    i = int(round(ang_deg / 360.0 * M)) % M
    return pts[i]


# --------------------------------------------------------------------------- #
# Aufbau des gesamten Rumpfes
# --------------------------------------------------------------------------- #
def wing_clear() -> Manifold:
    s = wing_mod.make_surface()
    sol = s.prism(-WING_CENTER_HALF - 1.0, WING_CENTER_HALF + 1.0, False)
    sol = g.apply(sol, wing_mod.wing_asm_T())
    return sol + sol.translate((0, 0, -0.25))


def roof_hole() -> Manifold:
    """Dachöffnung unter dem Flügelmittelstück; seitlich bleibt ein schmaler Rand für die Auflage."""
    xs = np.linspace(*CABIN_OPEN_X, 20)
    w, zb, zt, rc = section(xs)
    half = float((w / 2 - rc).min()) - 1.5
    return g.box(CABIN_OPEN_X[0], CABIN_OPEN_X[1], -half, half, 120.0, 320.0)


def build_core() -> Manifold:
    outer = body(0.0, FUSE_LEN, 0.0)
    inner = body(2.4, FUSE_LEN - 5.0, T)
    hole = roof_hole()
    a_max = 0.5 * float(section(np.linspace(*CABIN_OPEN_X, 20))[0].max())
    shell = outer - (inner + hole)

    parts = [shell]

    # ---- Spanten ------------------------------------------------------------ #
    for x in FRAME_X:
        parts.append(ring_frame(x))

    # ---- Spantenbalken für die Flügelschrauben ------------------------------- #
    Tw = wing_mod.wing_asm_T()
    beam_holes = []
    for bx in WING_BOLT_X:
        xb = WING_LE_X + bx
        beam = g.box(xb - 5.0, xb + 5.0, -(a_max - T + 0.5), a_max - T + 0.5, 205.0, 250.0) ^ outer
        parts.append(beam)
        for sy in (-1, 1):
            p_top = (Tw @ np.array([bx, sy * WING_BOLT_Y, 40.0, 1.0]))[:3]
            p_bot = (Tw @ np.array([bx, sy * WING_BOLT_Y, -30.0, 1.0]))[:3]
            beam_holes.append(g.cyl(p_bot, p_top, 1.25, segs=24))

    # ---- Klebeflansch an der Teilungsebene y = 0 ---------------------------- #
    xs = grid(0.0, FUSE_LEN, 5.0)
    w, zb, zt, rc = section(xs)
    wb = np.clip(0.5 * (zt - zb) - T - 1.0, 0.0, FRAME_W)
    for top in (True, False):
        # Streifen in zusammenhängende Abschnitte zerlegen
        runs, cur = [], []
        for i, x in enumerate(xs):
            skip = (top and CABIN_OPEN_X[0] - 6 <= x <= CABIN_OPEN_X[1] + 6) or \
                   (not top and any(a <= x <= b for a, b in FLANGE_GAPS_BOTTOM))
            if skip:
                if len(cur) > 1:
                    runs.append(cur)
                cur = []
            else:
                cur.append(i)
        if len(cur) > 1:
            runs.append(cur)
        for run in runs:
            if top:
                hi = [(xs[i], zt[i] - T + 0.3) for i in run]
                lo = [(xs[i], zt[i] - T - wb[i]) for i in run]
            else:
                hi = [(xs[i], zb[i] + T + wb[i]) for i in run]
                lo = [(xs[i], zb[i] + T - 0.3) for i in run]
            polyxy = hi + lo[::-1]
            m = Manifold.extrude(CrossSection([g.ccw(polyxy)]), 2 * FLANGE_T)       # Rahmen (x, z) -> Extrusion = y
            Tm = g.rot_x(90)                                                         # (x,y,z) -> (x,-z,y)
            m = g.apply(m, Tm).translate((0, FLANGE_T, 0))
            parts.append(m ^ outer)

    whole = g.union(parts)
    whole = g.difference(whole, *beam_holes)

    # ---- Sättel: Flügel, Höhenleitwerk, Seitenflosse -------------------------- #
    fin_o = tail_mod.fin_outer_asm()
    fin_clear = fin_o + fin_o.translate((0, 0.25, 0)) + fin_o.translate((0, -0.25, 0))
    stab_o = tail_mod.stab_outer_asm()
    stab_clear = stab_o + stab_o.translate((0, 0, -0.25))
    whole = g.difference(whole, wing_clear(), stab_clear, fin_clear)
    return whole


_POST_CUT = None


def post_cut() -> Manifold:
    """Schnittkörper, die auch auf die Steckmuffen wirken (Flügel-/Leitwerkssättel, offenes Dach)."""
    global _POST_CUT
    if _POST_CUT is None:
        hole = roof_hole()
        fin_o = tail_mod.fin_outer_asm()
        stab_o = tail_mod.stab_outer_asm()
        _POST_CUT = g.union([hole, wing_clear(), stab_o, stab_o.translate((0, 0, -0.25)),
                             fin_o, fin_o.translate((0, 0.25, 0)), fin_o.translate((0, -0.25, 0))])
    return _POST_CUT


FLANGE_T = 1.2
# unten kein Klebeflansch, wo Fahrwerksblöcke die Naht von innen überbrücken
FLANGE_GAPS_BOTTOM = ((FIREWALL_X + FIREWALL_T - 1.0, NOSE_GEAR_X + 17.0), (MAIN_GEAR_X - 17.0, MAIN_GEAR_X + 17.0))


# --------------------------------------------------------------------------- #
# Fenster-Gravuren
# --------------------------------------------------------------------------- #
def window_grooves() -> Manifold:
    layer = body(0.0, FUSE_LEN, 0.0) - body(0.0, FUSE_LEN, 0.4)          # 0,4 mm Außenhaut
    cuts = []
    for poly in WINDOW_SIDE:
        cs = CrossSection([g.ccw(poly)])
        band = cs.offset(0.4, g.m3.JoinType.Miter, 2.0, 8) - cs.offset(-0.4, g.m3.JoinType.Miter, 2.0, 8)
        pr = Manifold.extrude(band, 140.0)                                # Rahmen (x, z) -> Extrusion = y
        pr = g.apply(pr, g.rot_x(90))                                     # (x,y,z) -> (x,-z,y)
        for sgn in (1, -1):
            m = pr.translate((0, 66.0 + 140.0, 0)) if sgn > 0 else g.mirror_y(pr.translate((0, 66.0 + 140.0, 0)))
            cuts.append(m)
    for poly in WINDOW_TOP:
        cs = CrossSection([g.ccw(poly)])
        band = cs.offset(0.4, g.m3.JoinType.Miter, 2.0, 8) - cs.offset(-0.4, g.m3.JoinType.Miter, 2.0, 8)
        cuts.append(Manifold.extrude(band, 120.0).translate((0, 0, 150.0)))   # z 150 .. 270
    return g.union(cuts) ^ layer


# --------------------------------------------------------------------------- #
# Zusatzteile je Segment
# --------------------------------------------------------------------------- #
def firewall() -> Manifold:
    fw = slab_x(CrossSection([g.ccw(poly_yz(FIREWALL_X, T - 0.1))]), FIREWALL_X, FIREWALL_T)
    holes = [g.cyl((FIREWALL_X - 1, 0, MOTOR_AXIS_Z), (FIREWALL_X + FIREWALL_T + 1, 0, MOTOR_AXIS_Z), 13.0)]
    for sy in (-1, 1):
        for sz in (-1, 1):
            holes.append(g.cyl((FIREWALL_X - 1, sy * 15.0, MOTOR_AXIS_Z + sz * 15.0),
                               (FIREWALL_X + FIREWALL_T + 1, sy * 15.0, MOTOR_AXIS_Z + sz * 15.0), 1.6))
    for ang in HOOD_SCREW_ANGLES:
        y, z = ref_frame_pt(FIREWALL_X - 6.0, ang, T + 2.2)
        holes.append(g.cyl((FIREWALL_X - 1, y, z), (FIREWALL_X + FIREWALL_T + 1, y, z), 1.5, segs=16))
    return g.difference(fw, *holes)


HOOD_SCREW_ANGLES = (45, 135, 225, 315)


def cowl_extras(cowl: Manifold) -> Manifold:
    """Schraubdome (hinten), Spinner-Öffnung und Lufteinlässe in der Motorhaube."""
    for ang in HOOD_SCREW_ANGLES:
        y, z = ref_frame_pt(FIREWALL_X - 6.0, ang, T + 2.2)
        boss = g.cyl((FIREWALL_X - 15.0, y, z), (FIREWALL_X, y, z), 3.7, segs=24)
        cowl = cowl + boss
        cowl = cowl - g.cyl((FIREWALL_X - 14.0, y, z), (FIREWALL_X + 1.0, y, z), 1.15, segs=16)
    cut = [g.cyl((-1, 0, MOTOR_AXIS_Z), (6, 0, MOTOR_AXIS_Z), 21.0, segs=64)]
    for sy in (-1, 1):
        rs = g.rounded_slot(-12.0, 12.0, -7.0, 7.0, 6.0)
        cut.append(slab_x(rs.translate((sy * 38.0, MOTOR_AXIS_Z - 22.0)), -1.0, 6.0))
    return g.difference(cowl, *cut)


# --------------------------------------------------------------------------- #
# Servoböden, Gestängekanäle, Durchführungen
# --------------------------------------------------------------------------- #
SERVO = SERVO_9G
TAIL_SERVO_X = 538.0                 # Mitte der Heckservos
TAIL_SERVO_Z = 100.0                 # Höhe des Servobodens
NOSE_SERVO_X = 190.0
NOSE_SERVO_Z = 100.0
SERVO_INSET = 10.0                   # Servomitte innen von der Seitenwand (Wand verjüngt sich nach hinten)
ARM_Z = 2.4 + SERVO_9G["flange_off"] + 1.0   # Höhe der Servohebelebene über dem Servoboden
SHAFT_OFF = SERVO_9G["L"] / 2 - 5.9  # Abtriebswelle sitzt nahe einem Servoende (hier: hinten)
TAIL_ARM_R = 10.0                    # Lochabstand am Servohebel der Heckservos (Kanal ist darauf ausgelegt)
TAIL_ROD_EXIT_X, TAIL_ROD_EXIT_Y, TAIL_ROD_EXIT_Z = 850.0, 16.0, 160.0   # Knick des Höhenruder-Bowdenzugs (links); Austritt schräg nach außen


def inner_half_width(x: float, z: float | None = None) -> float:
    pts = ring_yz([x], T)[0]
    if z is None:
        return float(pts[:, 0].max())
    # y bei Höhe z (rechte Seite)
    r = pts[pts[:, 0] > 0]
    order = np.argsort(r[:, 1])
    return float(np.interp(z, r[order, 1], r[order, 0]))


def servo_shelf(sgn: int, x_c: float, z_s: float, depth: float = 26.0) -> tuple[Manifold, tuple]:
    """Servoboden an der Seitenwand (sgn=+1 rechts, -1 links). Servo hängt mit Flansch im Boden, Abtrieb oben."""
    yw = inner_half_width(x_c, z_s)
    y0, y1 = yw + 0.8, yw - depth
    ylo, yhi = (min(sgn * y0, sgn * y1), max(sgn * y0, sgn * y1))
    plate = g.box(x_c - 18.0, x_c + 18.0, ylo, yhi, z_s, z_s + 2.4) ^ body(x_c - 22.0, x_c + 22.0, 0.3)
    y_c = sgn * (yw - SERVO_INSET)
    cut = g.box(x_c - SERVO["L"] / 2 - 0.15, x_c + SERVO["L"] / 2 + 0.15,
                y_c - SERVO["W"] / 2 - 0.15, y_c + SERVO["W"] / 2 + 0.15, z_s - 1, z_s + 4)
    for sx in (-1, 1):
        cut = cut + g.cyl((x_c + sx * 14.0, y_c, z_s + 0.5), (x_c + sx * 14.0, y_c, z_s - 3.5), 0.95, segs=16)
        cut = cut + g.cyl((x_c + sx * 14.0, y_c, z_s - 3.5), (x_c + sx * 14.0, y_c, z_s + 3.0), 0.95, segs=16)
    # vertikale Pilotlöcher in der Platte
    holes = [g.cyl((x_c + sx * 14.0, y_c, z_s - 1), (x_c + sx * 14.0, y_c, z_s + 3.5), 0.95, segs=16) for sx in (-1, 1)]
    plate = plate - cut
    # Ausschnitt nicht über die Flanschlöcher legen
    for h in holes:
        plate = plate - h
    return plate, (x_c, y_c, z_s + ARM_Z)


def rod_tunnel(start, end, r=1.9, out_to=None) -> Manifold:
    """Kanal für das Gestänge (durch die Spanten); mit out_to zusätzlich ein Austrittsloch durch die
    Rumpfwand, ausgerichtet auf das außen liegende Gestängestück end -> out_to."""
    start, end = np.asarray(start, float), np.asarray(end, float)
    d = (end - start) / np.linalg.norm(end - start)
    if out_to is None:
        return g.cyl(start - 3 * d, end - 6 * d, r, segs=20)
    do = (np.asarray(out_to, float) - end) / np.linalg.norm(np.asarray(out_to, float) - end)
    return g.cyl(start - 3 * d, end, r, segs=20) + g.sphere(end, r, 20) + \
        g.cyl(end - 2 * do, end + 32 * do, r + 0.1, segs=20)


def service_opening() -> Manifold:
    """Wartungsöffnung links im Heck: Madenschraube des Seitenruderhebels und Gabelkopf erreichbar."""
    c = tail_mod.rudder_axis_at(RUDDER_LEVER_Z + 4.0)
    caps = [g.cyl((c[0] + dx, -40.0, c[2]), (c[0] + dx, -6.0, c[2]), 6.0, segs=32) for dx in (-2.0, 10.0)]
    return g.union(caps + [g.box(c[0] - 2.0, c[0] + 10.0, -40.0, -6.0, c[2] - 6.0, c[2] + 6.0)])


def tail_rod_lines(sgn: int):
    """Gestängelinien: Höhenruder (links) Servohebel -> Austritt Heckwand,
    Seitenruder (rechts) Servohebel -> Seitenruderhebel im Heck (Gestänge bleibt innen)."""
    yw = inner_half_width(TAIL_SERVO_X, TAIL_SERVO_Z)
    start = np.array([TAIL_SERVO_X + SHAFT_OFF, sgn * (yw - SERVO_INSET - TAIL_ARM_R), TAIL_SERVO_Z + ARM_Z])
    if sgn > 0:
        return start, tail_mod.rudder_lever_hole()
    end = np.array([TAIL_ROD_EXIT_X, sgn * TAIL_ROD_EXIT_Y, TAIL_ROD_EXIT_Z])
    return start, end


def check_rod_clear(start, end, margin=2.2, step=10.0) -> float:
    """Kleinster Abstand des Gestänges zur Innenwand entlang der Linie (negativ = Kollision)."""
    worst = 1e9
    L = np.linalg.norm(end - start)
    for t in np.arange(0, L - 20, step):
        p = start + (end - start) * (t / L)
        x = float(p[0])
        if x < FUSE_LEN - 20:
            pts = ring_yz([x], T + margin)[0]
            ang = np.arctan2(p[2] - float(section(x)[1][0] + section(x)[2][0]) / 2, p[1])
            # Punkt im Querschnitt? (Rundrechteck -> über SDF prüfen)
            w, zb, zt, rc = section(x)
            a, b = w[0] / 2 - T - margin, (zt[0] - zb[0]) / 2 - T - margin
            r = max(rc[0] - T - margin, 0.5)
            qy = max(abs(p[1]) - (a - r), 0.0)
            qz = max(abs(p[2] - (zt[0] + zb[0]) / 2) - (b - r), 0.0)
            sd = np.hypot(qy, qz) - r
            worst = min(worst, -sd)
    return worst


# --------------------------------------------------------------------------- #
# Segmente und Hälften
# --------------------------------------------------------------------------- #
def lip(x1: float) -> Manifold:
    """Steckmuffe: ragt vom Segmentende x1 aus LIP_LEN weit in das nächste Segment.

    Innerhalb des eigenen Segments (5 mm vor x1) ist der Ring verdickt und mit der Schale verschmolzen,
    danach springt er um das Spiel CLEAR nach innen und gleitet in das Folgesegment.
    """
    free = body(x1, x1 + LIP_LEN, T + CLEAR) - body(x1 - 0.5, x1 + LIP_LEN + 0.5, 2 * T + CLEAR)
    root = body(x1 - 6.0, x1 + 0.01, T - 0.3) - body(x1 - 6.5, x1 + 0.5, 2 * T + CLEAR)
    notch = g.box(x1 - 8, x1 + LIP_LEN + 1, -1.5, 1.5, -10, 500)       # Platz für den Klebeflansch
    return (free + root) - post_cut() - notch


def wall_taper_deg(x0: float, x1: float) -> float:
    """Neigung der Seitenwand (halbe Breite über x) in Grad, als Ausgleichsgerade über [x0, x1]."""
    xs = np.linspace(x0, x1, 40)
    a = section(xs)[0] / 2
    m = np.polyfit(xs, a, 1)[0]
    return float(np.degrees(np.arctan(m)))


def gear_cuts() -> Manifold:
    """Drahtdurchführungen des Hauptfahrwerks (beide Wände) und Bohrung für das Bugfahrwerk."""
    holes = [g.cyl((MAIN_GEAR_X, -90, MAIN_WIRE_Z), (MAIN_GEAR_X, 90, MAIN_WIRE_Z), 2.9, segs=24)]
    zb = float(section(NOSE_GEAR_X)[1][0])
    holes.append(g.cyl((NOSE_GEAR_X, 0, zb - 3), (NOSE_GEAR_X, 0, zb + 8), 2.6, segs=24))
    return g.union(holes)


def build_fuselage() -> list[Part]:
    core = build_core()
    core = core - gear_cuts() - window_grooves()
    parts: list[Part] = []
    # Gestängekanäle (Höhenruder links, Seitenruder rechts)
    tunnels = {}
    for sgn in (-1, 1):
        s0, e0 = tail_rod_lines(sgn)
        tunnels[sgn] = rod_tunnel(s0, e0, out_to=tail_mod.elevator_horn_hole() if sgn < 0 else None)
    for (x0, x1, name) in FUSE_SEGMENTS:
        seg = core ^ g.box(x0, x1, -300, 300, -10, 500)
        if name.startswith("F1"):
            seg = cowl_extras(seg)
        elif name.startswith("F2"):
            seg = seg + firewall()
        if x1 < FUSE_LEN - 1 and not name.startswith("F1"):
            seg = seg + lip(x1)
        right = seg ^ g.box(x0 - 1, x1 + LIP_LEN + 1, 0, 300, -10, 500)
        left = g.mirror_y(right)
        # seitenabhängige Einbauten
        extras = {+1: [], -1: []}
        if name.startswith("F4"):
            for sgn in (+1, -1):
                shelf, _ = servo_shelf(sgn, TAIL_SERVO_X, TAIL_SERVO_Z)
                extras[sgn].append(shelf)
        if name.startswith("F2"):
            shelf, _ = servo_shelf(-1, NOSE_SERVO_X, NOSE_SERVO_Z)
            extras[-1].append(shelf)
        half = {+1: right, -1: left}
        for sgn in (+1, -1):
            h = half[sgn]
            for e in extras[sgn]:
                h = h + (e ^ g.box(x0 - 1, x1 + LIP_LEN + 1, -300, 300, -10, 500))
            if x1 > 400:
                h = h - tunnels[sgn]
            if name.startswith("F6") and sgn < 0:
                h = h - service_opening()
            half[sgn] = h
        right, left = half[+1], half[-1]
        note = "mit Steckmuffe nach hinten" if (x1 < FUSE_LEN - 1 and not name.startswith("F1")) else ""
        phi = wall_taper_deg(x0, x1)      # Verjüngung der Seitenwand -> Wand liegt waagerecht auf dem Bett
        parts.append(Part(f"{name}_rechts", "Rumpf", right, np.eye(4), g.rot_x(-90) @ g.rot_z(-phi), note=note))
        parts.append(Part(f"{name}_links", "Rumpf", left, np.eye(4), g.rot_x(90) @ g.rot_z(phi), note=note))
    return parts


# --------------------------------------------------------------------------- #
# Rückenflosse (separates, flach gedrucktes Teil)
# --------------------------------------------------------------------------- #
def dorsal_fin() -> Part:
    def fin_le(z):
        return FIN_ROOT_LE + (FIN_TIP_LE - FIN_ROOT_LE) / FIN_HEIGHT * (z - FIN_BASE_Z)
    x0 = DORSAL_X0
    zt0 = float(section(x0)[2][0])
    x_top = fin_le(DORSAL_TOP) + 3.0
    zb_end = float(section(x_top)[2][0])
    xs = np.linspace(x0, x_top, 30)
    bottom = [(x, float(section(x)[2][0]) - 5.0) for x in xs]
    u = np.linspace(0.0, 1.0, 30)
    top = [(x_top + (x0 - x_top) * ui, zt0 + (DORSAL_TOP - zt0) * (1.0 - ui) ** 2.2) for ui in u]
    pts = bottom + top
    m = Manifold.extrude(CrossSection([g.ccw(pts)]), DORSAL_T)          # Ebene (x, z), Dicke -> y
    m = g.apply(m, g.rot_x(90)).translate((0, DORSAL_T / 2, 0))
    # unten an die Rumpfrundung angepasst, vorn an die Flossenvorderkante (0,3 mm Spalt)
    fin_o = tail_mod.fin_outer_asm()
    fin_c = g.union([fin_o, fin_o.translate((-0.3, 0, 0)), fin_o.translate((0, 0.3, 0)), fin_o.translate((0, -0.3, 0))])
    m = m - body(x0 - 5, x_top + 5, -0.2) - fin_c
    m = g.drop_floating(m)
    return Part("S3_Rueckenflosse", "Leitwerk", m, np.eye(4), g.rot_x(90), material="LW-PLA",
                note="flach drucken; auf den Rumpfrücken (F5) und an die Vorderkante der Seitenflosse kleben")
