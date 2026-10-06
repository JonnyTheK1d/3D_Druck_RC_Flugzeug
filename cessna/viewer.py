"""Export für die 3D-Ansicht im Browser: GLB (ein Objekt pro Teil) + teile.json (Metadaten, Explosion, Scharniere)."""
from __future__ import annotations

import json
import os

import numpy as np
import trimesh

from . import geom as g
from . import surface as sf
from . import tail, wing
from .params import *
from .parts import Part
from .showcase import color_of, explode_offset

# Zusammenbau (x hinten, y rechts, z oben) -> glTF (y oben): x' = x, y' = z, z' = -y  (reine Drehung)
C = np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, -1, 0, 0], [0, 0, 0, 1.0]])


def _v(p):
    return (C[:3, :3] @ np.asarray(p, float)).tolist()


def hinge_axes() -> dict:
    """Scharnierachsen (Zusammenbau-Koordinaten) und Bewegungsart je Steuerflächen-Teil."""
    out = {}
    surf = wing.make_surface()
    Tw = wing.wing_asm_T()
    xh = lambda y: (1.0 - AIL_CHORD_FRAC) * wing.wing_chord(y)
    y2 = WING_CENTER_HALF + 2 * WING_PANEL_SPAN

    def tw(p):
        return (Tw @ np.append(p, 1))[:3]
    for name, kind, (ya, yb) in (("Q1_Querruder_innen", "quer", (AIL_Y0, y2)),
                                 ("Q2_Querruder_aussen", "quer", (y2, AIL_Y1)),
                                 ("K1_Landeklappe", "klappe", (FLAP_Y0, FLAP_Y1))):
        p0, p1 = (tw(p) for p in sf.pivot_axis(surf, xh, ya, yb))
        out[f"{name}_rechts"] = (kind, +1, p0, p1)
        m = np.array([1, -1, 1])
        out[f"{name}_links"] = (kind, -1, p0 * m, p1 * m)
    s = tail.stab_surface()
    xe = lambda y: s.x_le(y) + (1 - ELEV_FRAC) * tail.stab_chord(y)
    Ts = tail.stab_T()
    e0, e1 = ((Ts @ np.append(p, 1))[:3] for p in sf.pivot_axis(s, xe, ELEV_Y0, ELEV_END))
    for half in ("oben", "unten"):
        out[f"H2_Hoehenruder_rechts_{half}"] = ("hoehe", +1, e0, e1)
        out[f"H2_Hoehenruder_links_{half}"] = ("hoehe", -1, e0 * [1, -1, 1], e1 * [1, -1, 1])
    f = tail.fin_surface()
    (xa, _), (xb, _) = RUDDER_HINGE
    xhf = lambda y: xa + (xb - xa) * y / FIN_HEIGHT
    Tf = tail.fin_T()
    r0, r1 = ((Tf @ np.append(p, 1))[:3] for p in sf.pivot_axis(f, xhf, RUDDER_Y0, RUDDER_Y1))
    if r1[2] < r0[2]:
        r0, r1 = r1, r0
    for half in ("oben", "unten"):
        out[f"S2_Seitenruder_{half}"] = ("seite", +1, r0, r1)
    return out


def export_viewer(parts: list[Part], outdir: str, mass: dict, nums: dict, tol: float = 0.03) -> dict:
    os.makedirs(outdir, exist_ok=True)
    hinges = hinge_axes()
    scene = trimesh.Scene()
    meta = []
    allpts = []
    for p in parts:
        if p.group == "Kleinteile":
            continue
        Ts = p.asm_Ts()
        n = len(Ts)
        per_mass = p.mass_g() / n if (n > 1 and p.qty > 1) else p.mass_g()
        size = p.print_size()
        for k, T in enumerate(Ts):
            m = g.apply(p.mesh, C @ T).simplify(tol)
            tm = g.clean_trimesh(g.to_trimesh(m))
            node = p.name if n == 1 else f"{p.name}#{k + 1}"
            scene.add_geometry(tm, node_name=node, geom_name=node)
            allpts.append(tm.bounds)
            entry = dict(node=node, name=p.name, group=p.group, color=color_of(p), material=p.material,
                         qty=p.qty, mass=round(per_mass, 1), size=[round(float(v)) for v in size],
                         note=p.note, explode=_v(explode_offset(p.name)), tris=int(len(tm.faces)))
            if p.name in hinges:
                kind, sign, a0, a1 = hinges[p.name]
                entry["hinge"] = dict(kind=kind, sign=sign, p0=_v(a0), p1=_v(a1))
            meta.append(entry)
    path = os.path.join(outdir, "flugzeug.glb")
    scene.export(path)
    b = np.array(allpts)
    lo, hi = b[:, 0].min(axis=0), b[:, 1].max(axis=0)
    cg = _v((mass["cg_x"], 0.0, WING_Z_REF - 20.0))
    info = dict(parts=meta, bounds=[lo.tolist(), hi.tolist()], cg=cg, numbers=nums,
                span=2 * WING_SEMISPAN, length=FUSE_LEN + SPINNER_LEN + 4.0,
                stl_count=len(parts), prints=int(sum(p.qty for p in parts)))
    json.dump(info, open(os.path.join(outdir, "teile.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    return dict(glb=path, size_mb=os.path.getsize(path) / 1e6, tris=sum(e["tris"] for e in meta), objects=len(meta))


def write_index(outdir: str):
    """Eigenständige index.html (vollständiges HTML-Gerüst) aus seite.html erzeugen."""
    body = open(os.path.join(outdir, "seite.html"), encoding="utf-8").read()
    html = ('<!doctype html>\n<html lang="de">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            '<style>*,*::before,*::after{box-sizing:border-box}body{margin:0}[hidden]{display:none!important}</style>\n'
            '</head>\n<body>\n' + body + '\n</body>\n</html>\n')
    open(os.path.join(outdir, "index.html"), "w", encoding="utf-8").write(html)
