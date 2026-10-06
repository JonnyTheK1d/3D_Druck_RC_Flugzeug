"""Generischer hohler Auftriebsflächen-Abschnitt (Flügel, Leitwerk, Ruder).

Koordinaten im Abschnitts-Rahmen: x = Tiefe (Vorderkante bei x_le(y)), y = Spannweite,
z = Dicke (Sehne bei z = 0). Das Ergebnis liegt direkt in diesem Rahmen.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np

from . import airfoil as af
from . import geom as g
from .geom import CrossSection, Manifold
from .params import RIB_T, HINGE_GAP

CLIP = 0.93          # Hohlraum endet bei 93 % Tiefe, dahinter massive Hinterkante
MIN_PIECE_RATIO = 0.93
OV = 0.2             # Überstand von Verschlussplatten in den Spalt (mm)


@dataclass
class Surface:
    code: str                              # NACA-Profil
    chord: Callable[[float], float]        # Tiefe c(y)
    x_le0: float                           # Vorderkante bei y = 0
    sweep: float = 0.0                     # dx_le/dy (Pfeilung der Vorderkante)
    wall: float = 1.1
    breakpoints: tuple = ()                # Knicke der Tiefenverteilung
    rib_pitch: float = 35.0
    end_rib: float = 1.5
    hole_rim: float = 3.2                  # Mindeststeg um Rippenlöcher
    hole_x_frac: tuple = (0.50, 0.64, 0.78)  # Lochmitten (Tiefenbruchteil)
    hole_x_min: float = 0.0                # kein Loch vor dieser x-Position (mm hinter VK)
    flat_from: float | None = None         # gerader Unterseitenboden ab dieser Tiefe (Bruchteil)

    # -- Profil ------------------------------------------------------------ #
    def unit_outline(self) -> np.ndarray:
        if self.flat_from is None:
            return af.naca4(self.code)
        return af.naca4_flat(self.code, self.flat_from)[0]

    def tilt_deg(self) -> float:
        """Drehwinkel (um y), der die Bodenlinie waagerecht legt."""
        if self.flat_from is None:
            return 0.0
        return af.naca4_flat(self.code, self.flat_from)[1]

    def outline(self, c: float) -> np.ndarray:
        return self.unit_outline() * c

    def _surf_z(self, x_rel: float, c: float, upper: bool) -> float:
        pts = self.unit_outline()
        le = int(np.argmin(pts[:, 0]))
        # Oberseite liegt vor dem Nasenpunkt (HK -> Nase), Unterseite danach (Nase -> HK)
        part = pts[:le + 1][::-1] if upper else pts[le:]
        xs, zs = part[:, 0], part[:, 1]
        return float(np.interp(x_rel / c, xs, zs)) * c

    def thickness_abs(self, x_rel: float, c: float) -> float:
        return self._surf_z(x_rel, c, True) - self._surf_z(x_rel, c, False)

    def camber_abs(self, x_rel: float, c: float) -> float:
        """Höhe der Profilmitte (zwischen Ober- und Unterseite) an der Stelle x."""
        return 0.5 * (self._surf_z(x_rel, c, True) + self._surf_z(x_rel, c, False))

    def x_le(self, y):
        return self.x_le0 + self.sweep * y

    def cs_outer(self, c: float) -> CrossSection:
        return CrossSection([self.outline(c)])

    def cs_inner(self, c: float, wall: float | None = None, clip: float = CLIP) -> CrossSection:
        w = self.wall if wall is None else wall
        inner = self.cs_outer(c).offset(-w, g.m3.JoinType.Miter, 2.0, 16)
        cut = CrossSection.square((c * clip + 5, c)).translate((-5, -c / 2))
        return inner ^ cut

    # -- Rahmenwechsel -------------------------------------------------------#
    def _frame(self, m: Manifold, y0: float) -> Manifold:
        """Extrusionsrahmen (Spannweite = +Z) -> Abschnitts-Rahmen (Spannweite = +Y)."""
        return m.rotate((90, 0, 0)).mirror((0, 1, 0)).translate((0, y0, 0))

    def _shear(self, m: Manifold) -> Manifold:
        T = np.eye(4)
        T[0, 1] = self.sweep
        T[0, 3] = self.x_le0
        return g.apply(m, T)

    # -- Stationen ---------------------------------------------------------- #
    def stations(self, y0: float, y1: float) -> list[float]:
        pts = [y0] + [b for b in self.breakpoints if y0 < b < y1] + [y1]
        out = [pts[0]]
        for a, b in zip(pts[:-1], pts[1:]):
            ca, cb = self.chord(a), self.chord(b)
            r = min(ca, cb) / max(ca, cb)
            n = 1
            if r < MIN_PIECE_RATIO:
                n = int(np.ceil(np.log(r) / np.log(MIN_PIECE_RATIO)))
            out += [a + (b - a) * k / n for k in range(1, n + 1)]
        return out

    def prism(self, y0: float, y1: float, inner: bool, inset_ends=(0.0, 0.0), wall: float | None = None) -> Manifold:
        """Außen- bzw. Innenkörper zwischen y0 und y1 (stückweise linear verjüngt)."""
        ys = self.stations(y0, y1)
        pieces = []
        for a, b in zip(ys[:-1], ys[1:]):
            ca, cb = self.chord(a), self.chord(b)
            cs = self.cs_inner(ca, wall) if inner else self.cs_outer(ca)
            m = Manifold.extrude(cs, b - a, 0, 0.0, (cb / ca, cb / ca))
            pieces.append(self._frame(m, a))
        solid = g.union(pieces) if len(pieces) > 1 else pieces[0]
        solid = self._shear(solid)
        if inner:
            lo, hi = inset_ends
            solid = solid ^ g.box(-1e4, 1e4, y0 + lo, y1 - hi, -1e3, 1e3)
        return solid

    def rib(self, y: float, thick: float, holes: bool = True) -> Manifold:
        c = self.chord(y)
        cs = self.cs_outer(c).offset(-(self.wall - 0.35), g.m3.JoinType.Miter, 2.0, 16)
        cs = cs ^ CrossSection.square((c * CLIP + 0.6, c)).translate((-5, -c / 2))
        if holes:
            for xf in self.hole_x_frac:
                xc = xf * c
                if xc < self.hole_x_min:
                    continue
                zc = self.camber_abs(xc, c)
                r = self.thickness_abs(xc, c) / 2 - self.wall - self.hole_rim
                if r < 2.0:
                    continue
                cs = cs - CrossSection.circle(min(r, 14.0), 40).translate((xc, zc))
        m = Manifold.extrude(cs, thick)
        return self._shear(self._frame(m, y - thick / 2))


# --------------------------------------------------------------------------- #
# Randbogen
# --------------------------------------------------------------------------- #
def tip_cap(surf: Surface, y_start: float, length: float, inner_len: float, n_div=14, wall: float | None = None):
    """Abgerundeter Randbogen als elliptisch verjüngter Auslauf."""
    c0 = surf.chord(y_start)
    c_end = surf.chord(y_start + length)
    s_top = c_end / c0
    pts = surf.outline(c0)
    cx0, cz0 = pts[:, 0].mean(), 0.0

    def build(cs, h):
        m = Manifold.extrude(cs, h, n_div, 0.0, (s_top ** (h / length), s_top ** (h / length)))

        def fn(v):
            v = np.asarray(v, float).copy()
            u = np.clip(v[:, 2] / length, 0, 1)
            s = np.maximum(np.sqrt(np.maximum(1 - u ** 2, 0.0)), 0.14)
            lam = 1 + (s_top - 1) * u
            cx, cz = cx0 * lam, cz0 * lam
            v[:, 0] = cx + s * (v[:, 0] - cx)
            v[:, 1] = cz + s * (v[:, 1] - cz)
            return v
        return m.warp_batch(fn)

    outer = build(surf.cs_outer(c0), length)
    inner = build(surf.cs_inner(c0, wall), inner_len)
    return surf._shear(surf._frame(outer, y_start)), surf._shear(surf._frame(inner, y_start))


# --------------------------------------------------------------------------- #
# Abschnitt bauen
# --------------------------------------------------------------------------- #
def build_panel(surf: Surface, y0: float, y1: float, *, end0=True, end1=True, cap_len=0.0,
                spar=None, columns=(), name=""):
    """Baut einen Abschnitt zwischen y0 und y1 (+ optional Randbogen der Länge cap_len).

    spar: (x, z, bohr_d, hülsen_d) oder None; columns: Liste (x, y, r_aussen, r_innen) vertikaler Domen.
    Rückgabe: dict(solid, cav, outer, bore).
    """
    et = surf.end_rib
    outer = surf.prism(y0, y1, False)
    cav = surf.prism(y0, y1, True, (et if end0 else 0.0, et if (end1 and not cap_len) else 0.0))
    if cap_len:
        cap_out, cap_in = tip_cap(surf, y1, cap_len, 15.0)
        outer = g.union([outer, cap_out])
        cav = g.union([cav, cap_in])
    shell = outer - cav
    # leicht vergrößerter Hohlraum (0,15 mm in die Haut) -> Verschlussplatten überlappen die Haut statt bündig zu enden
    wg = surf.wall - 0.15
    cav_big = surf.prism(y0, y1, True, (et if end0 else 0.0, et if (end1 and not cap_len) else 0.0), wall=wg)
    if cap_len:
        cav_big = g.union([cav_big, tip_cap(surf, y1, cap_len, 15.0, wall=wg)[1]])

    ribs = []
    if end0:
        ribs.append(surf.rib(y0 + et / 2, et))
    if end1 and not cap_len:
        ribs.append(surf.rib(y1 - et / 2, et))
    L = y1 - y0
    n = max(1, int(round(L / surf.rib_pitch)))
    ribs += [surf.rib(y0 + L * k / n, RIB_T) for k in range(1, n)]
    solid = g.union([shell] + ribs)

    bore = None
    if spar is not None:
        sx, sz, bore_d, sleeve_d = spar
        y_end = y1 + (15.0 if cap_len else 0.0)
        sleeve = g.cyl((sx, y0, sz), (sx, y_end, sz), sleeve_d / 2) ^ outer
        solid = solid + sleeve
        bore = g.cyl((sx, y0 - 1, sz), (sx, (y1 + 10.0) if cap_len else y1 + 1, sz), bore_d / 2)

    holes = []
    for (cx, cy, ro, ri) in columns:
        solid = solid + (g.cyl((cx, cy, -25), (cx, cy, 40), ro) ^ outer)
        holes.append(g.cyl((cx, cy, -26), (cx, cy, 41), ri))
    solid = g.difference(solid, bore, *holes)
    return dict(solid=solid, cav=cav, cav_big=cav_big, outer=outer, bore=bore, holes=holes)


# --------------------------------------------------------------------------- #
# Steuerflächen-Schnitt (Rundnase + Hohlkehle)
# --------------------------------------------------------------------------- #
def hinge_geometry(surf: Surface, xh_fn, ya, yb, off=0.0):
    """Kegel entlang der Scharnierlinie (Achse in Profilmitte, Radius = halbe Dicke + 0,6)."""
    def pivot(y):
        c = surf.chord(y)
        rel = xh_fn(y) - surf.x_le(y)
        zp = surf.camber_abs(rel, c)
        r = surf.thickness_abs(rel, c) / 2 + 0.6
        return np.array([xh_fn(y), y, zp]), r
    p0, r0 = pivot(ya)
    p1, r1 = pivot(yb)
    return g.cyl(p0, p1, r0 + off, r1 + off, segs=48)


def pivot_axis(surf: Surface, xh_fn, ya, yb):
    def pivot(y):
        c = surf.chord(y)
        rel = xh_fn(y) - surf.x_le(y)
        return np.array([xh_fn(y), y, surf.camber_abs(rel, c)])
    return pivot(ya), pivot(yb)


def aft_prism(xh_fn, ya, yb, off=0.0, z=60.0):
    pts = [(xh_fn(ya) + off, ya), (xh_fn(yb) + off, yb), (3000.0, yb), (3000.0, ya)]
    return g.poly(pts, 2 * z, -z)


def fore_prism(xh_fn, ya, yb, depth=40.0, z=60.0):
    pts = [(xh_fn(ya) - depth, ya), (xh_fn(yb) - depth, yb), (xh_fn(yb), yb), (xh_fn(ya), ya)]
    return g.poly(pts, 2 * z, -z)


def y_slab(y0, y1):
    return g.box(-1e4, 1e4, y0, y1, -1e3, 1e3)


def control_surface(surf: Surface, solid: Manifold, cav: Manifold, outer: Manifold,
                    xh_fn, ya, yb, gap=HINGE_GAP, gap_a=True, gap_b=True,
                    plate_t=1.2, nose_fill=3.5, gap_a_len=None, gap_b_len=None, cav_big: Manifold | None = None):
    """Trennt aus `solid` eine Steuerfläche zwischen ya und yb ab -> (Festteil, Steuerfläche, Schnittkörper).

    gap_a_len / gap_b_len: Länge des freien Spalts am inneren / äußeren Ende (Standard = gap).
    """
    cav = cav if cav_big is None else cav_big
    ga = (gap if gap_a_len is None else gap_a_len) if gap_a else 0.0
    gb = (gap if gap_b_len is None else gap_b_len) if gap_b else 0.0

    # ---- Festteil: Aussparung = Hinterteil + Hohlkehle ---------------------- #
    cut = g.union([aft_prism(xh_fn, ya - 0.01, yb + 0.01),
                   hinge_geometry(surf, xh_fn, ya - 0.01, yb + 0.01, off=gap)]) ^ y_slab(ya, yb)
    fixed = solid - cut
    cove_ring = hinge_geometry(surf, xh_fn, ya, yb, off=gap + plate_t) - \
        hinge_geometry(surf, xh_fn, ya - 0.5, yb + 0.5, off=gap)
    plates = [cav ^ cove_ring ^ fore_prism(xh_fn, ya, yb, 40)]
    wide = g.union([aft_prism(xh_fn, ya - plate_t, yb + plate_t),
                    hinge_geometry(surf, xh_fn, ya - plate_t, yb + plate_t, off=gap)])
    plates.append(cav ^ wide ^ y_slab(ya - plate_t, ya + OV))          # ragt OV in den Spalt (keine bündigen Flächen)
    plates.append(cav ^ wide ^ y_slab(yb - OV, yb + plate_t))
    fixed = g.union([fixed] + plates)

    # ---- Steuerfläche -------------------------------------------------------- #
    ya2, yb2 = ya + ga, yb - gb
    region = g.union([aft_prism(xh_fn, ya2, yb2), hinge_geometry(surf, xh_fn, ya2, yb2, off=0.0)])
    ail = (solid ^ region) ^ y_slab(ya2, yb2)
    nose = (outer ^ hinge_geometry(surf, xh_fn, ya2, yb2, off=0.0)) ^ y_slab(ya2, yb2)
    nose = nose ^ g.union([fore_prism(xh_fn, ya2, yb2, 60), aft_prism(xh_fn, ya2, yb2)])
    nose = nose ^ (fore_prism(xh_fn, ya2, yb2, 60) + g.poly(
        [(xh_fn(ya2), ya2), (xh_fn(yb2), yb2), (xh_fn(yb2) + nose_fill, yb2), (xh_fn(ya2) + nose_fill, ya2)],
        120, -60))
    ail = g.union([ail, nose,
                   cav ^ region ^ y_slab(ya2 - OV, ya2 + plate_t),
                   cav ^ region ^ y_slab(yb2 - plate_t, yb2 + OV)])
    # größerer Ausschnitt für Flansche u. ä. (nicht bündig mit den Schnittflächen)
    cut_big = g.union([aft_prism(xh_fn, ya - 0.8, yb + 0.8, off=-0.8),
                       hinge_geometry(surf, xh_fn, ya - 0.8, yb + 0.8, off=gap + 0.8)])
    return fixed, ail, cut_big


# --------------------------------------------------------------------------- #
# Ruderhorn, Servoschacht
# --------------------------------------------------------------------------- #
def add_horn_slot(surf: Surface, solid: Manifold, outer: Manifold, xh_fn, y_h: float,
                  x_off: float = 6.0, length: float = 14.4, width: float = 2.0, height: float = 5.5):
    """Schlitzkasten in der Unterseite einer Steuerfläche für ein eingeklebtes Ruderhorn."""
    c = surf.chord(y_h)
    x0 = xh_fn(y_h) + x_off
    z_low = surf._surf_z(x0 - surf.x_le(y_h) + length / 2, c, False)
    wall = 1.3
    box = g.box(x0, x0 + length + 2 * wall, y_h - width / 2 - wall, y_h + width / 2 + wall,
                z_low - 1.0, z_low + height + 1.2) ^ outer
    slot = g.box(x0 + wall, x0 + wall + length, y_h - width / 2, y_h + width / 2, z_low - 3, z_low + height)
    return (solid + box) - slot


def ruderhorn(length=14.0, base=5.5, reach=13.0, hole=1.6) -> Manifold:
    """Ruderhorn: Fuß (steckt im Schlitz) + Arm mit Anlenkloch, liegend druckbar (Ebene XZ)."""
    t = 1.8
    foot = g.box(0, length, -t / 2, t / 2, 0, base)
    arm = g.poly([(2.5, 0), (length - 2.5, 0), (length - 5.5, -reach), (5.5, -reach)], t, -t / 2)
    arm = arm.rotate((90, 0, 0))          # Polygon-Ebene XY -> XZ, Extrusion -> -Y
    arm = g.apply(arm, g.translation(0, t / 2 - 0.0, 0)) if False else arm
    h = g.cyl((length / 2, -3, -reach + 4.0), (length / 2, 3, -reach + 4.0), hole / 2)
    return foot + arm - h


# --------------------------------------------------------------------------- #
# Teilung in Ober-/Unterschale (symmetrische Profile)
# --------------------------------------------------------------------------- #
def plan_ring(surf: Surface, ys: list[float], width=3.2, thick=1.0, z0=0.0) -> Manifold:
    """Klebeflansch entlang der Teilungsebene z = 0: Ring von `width` mm Breite im Hohlraum."""
    front = [(surf.x_le(y) + surf.wall - 0.3, y) for y in ys]
    rear = [(surf.x_le(y) + CLIP * surf.chord(y) + 0.3, y) for y in ys][::-1]
    pts = front + rear
    cs = CrossSection([g.ccw(pts)])
    ring = cs - cs.offset(-width, g.m3.JoinType.Miter, 2.0, 8)
    return Manifold.extrude(ring, thick).translate((0, 0, z0))


def split_halves(solid: Manifold, outer: Manifold, surf: Surface, y0: float, y1: float,
                 subtract=(), exclude: Manifold | None = None):
    """Teilt bei z = 0 in (oben, unten); jede Hälfte erhält einen Klebeflansch.

    exclude: Bereich (z. B. Ruderausschnitt), in dem kein Flansch entstehen darf.
    """
    ys = surf.stations(y0 + surf.end_rib, y1 - surf.end_rib)
    ring = plan_ring(surf, ys, thick=2.0, z0=-1.0) ^ outer
    if exclude is not None:
        ring = ring - exclude
    full = solid + ring                       # erst vereinigen, dann an z = 0 trennen (keine bündigen Flächen)
    upper = full ^ g.box(-1e4, 1e4, -1e4, 1e4, 0, 1e3)
    lower = full ^ g.box(-1e4, 1e4, -1e4, 1e4, -1e3, 0)
    return g.difference(upper, *subtract), g.difference(lower, *subtract)
