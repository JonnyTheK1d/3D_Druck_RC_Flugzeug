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
    out["S4_Seitenruderhebel"] = ("seite", +1, r0, r1)
    out["Z_Ruderwelle"] = ("seite", +1, r0, r1)
    # Bugradlenkung: senkrechte Achse durch den Bugfahrwerksdraht
    n0, n1 = np.array([NOSE_GEAR_X, 0.0, 0.0]), np.array([NOSE_GEAR_X, 0.0, 200.0])
    for node in ("G6_Lenkhebel", "G7_Bugradgabel", "G1_Reifen#3", "G2_Radnabe#3", "G9_Radverkleidung_Bug_rechts",
                 "G9_Radverkleidung_Bug_links", "Z_Bugfahrwerksdraht", "Z_Bugradachse"):
        out[node] = ("bugrad", +1, n0, n1)
    return out


# --------------------------------------------------------------------------- #
# Zukaufteile (nur Darstellung): Draht, Holm, Antrieb, Elektronik, Servos, Ruderhörner
# --------------------------------------------------------------------------- #
COL_BOUGHT = {"draht": "#a3abb5", "cfk": "#2a2c30", "motor": "#7d8590", "prop": "#2b2b2b", "servo": "#2f4a7a",
              "akku": "#d9a21b", "regler": "#5b6b8c", "rx": "#2e7d4f", "horn": "#f4f5f7"}


def _frame(center, bx, bz):
    bx = np.asarray(bx, float) / np.linalg.norm(bx)
    bz = np.asarray(bz, float) / np.linalg.norm(bz)
    T = np.eye(4)
    T[:3, 0], T[:3, 1], T[:3, 2], T[:3, 3] = bx, np.cross(bz, bx), bz, center
    return T


def servo_mesh(sv: dict):
    """9-g-Servo: Gehäuse, Befestigungslaschen, Abtriebsdom (lokal z = Abtriebsseite)."""
    from .linkage import SHAFT_OFF
    S = SERVO_9G
    L, W, H = S["L"], S["W"], S["H"]
    m = g.box(-L / 2, L / 2, -W / 2, W / 2, -H / 2, H / 2)
    zf = H / 2 - S["flange_off"]
    m = m + g.box(-S["flange_L"] / 2, S["flange_L"] / 2, -W / 2, W / 2, zf, zf + S["flange_T"])
    m = m + g.cyl((SHAFT_OFF, 0, H / 2 - 0.1), (SHAFT_OFF, 0, H / 2 + 3.0), 2.6, segs=20)
    return g.apply(m, _frame(sv["center"], sv["body_x"], sv["axis"]))


def bought_items() -> list[dict]:
    from . import linkage, wires
    from .linkage import LABEL
    out = []

    def add(node, name, group, col, mesh, note, explode=(0, 0, 0), mass=0.0):
        out.append(dict(node=node, name=name, group=group, color=COL_BOUGHT[col], mesh=mesh, note=note,
                        explode=explode, mass=mass))

    # Fahrwerksdrähte
    zc = WHEEL_D / 2
    add("Z_Hauptfahrwerksdraht", "Hauptfahrwerksdraht", "Zukauf", "draht",
        wires.wire_solid(wires.main_gear_path(), MAIN_GEAR_X, 2.0),
        "Federstahl Ø4 mm, nach Biegeschablone (fahrwerk_biegeschablone.pdf); Achsenden tragen die Räder",
        explode_offset("G3"), 30.0)
    add("Z_Bugfahrwerksdraht", "Bugfahrwerksdraht", "Zukauf", "draht",
        g.cyl((NOSE_GEAR_X, 0, 57.5), (NOSE_GEAR_X, 0, NOSE_WIRE_Z_TOP + 1.0), 1.5, segs=16),
        "Federstahl Ø3 mm; steckt in G7, läuft durch das Lager G5, oben klemmt der Lenkhebel G6",
        explode_offset("G5"), 4.0)
    add("Z_Bugradachse", "Bugradachse", "Zukauf", "draht",
        g.cyl((NOSE_GEAR_X, -21.0, zc), (NOSE_GEAR_X, 21.0, zc), 1.5, segs=16),
        "Stahlstab Ø3 mm, 42 mm, durch Gabel und Verkleidung", explode_offset("G7"), 2.0)
    a, b = tail.rudder_wire_line()
    add("Z_Ruderwelle", "Ruderwelle Seitenruder", "Zukauf", "draht", g.cyl(a, b, 1.0, segs=16),
        f"Federstahl Ø2 mm, {np.linalg.norm(b - a):.0f} mm: im Seitenruder eingeklebt, in der Flosse gelagert, "
        "unten klemmt der Hebel S4", (60.0, 0.0, 0.0), 2.5)
    add("Z_Holm", "CFK-Holm", "Zukauf", "cfk", wires.spar_tubes(),
        "2 × CFK-Rohr 10/8 mm + Verbinder 8 mm im Mittelstück", explode_offset("W0"), 75.0)
    add("Z_Motor", "Motor", "Zukauf", "motor", wires.motor_solid(), "Außenläufer 2826/2830, ca. 1000 kV",
        explode_offset("P1"), 75.0)
    add("Z_Luftschraube", "Luftschraube", "Zukauf", "prop", wires.prop_solid(), "10×6\" (APC-E o. ä.)",
        explode_offset("P2"), 14.0)
    # Elektronik
    add("Z_Akku", "Akku", "Elektronik", "akku", g.box(170.0, 285.0, -17.5, 17.5, 80.5, 106.5),
        "LiPo 3S 2200 mAh (115 × 35 × 26 mm), mit Klett auf dem Rumpfboden; verschieben zum Schwerpunkt-Einstellen",
        mass=190.0)
    add("Z_Regler", "Regler", "Elektronik", "regler", g.box(68.0, 118.0, -13.0, 13.0, 100.0, 110.0),
        "Brushless-Regler 30 A mit BEC, unter dem Motorbock (Kühlluft vom Lufteinlass)", explode_offset("P1"), 30.0)
    add("Z_Empfaenger", "Empfänger", "Elektronik", "rx", g.box(222.0, 262.0, 52.0, 62.0, 112.0, 136.0),
        "Empfänger ≥ 6 Kanäle, mit Klett an die rechte Seitenwand; Antennen 90° zueinander", mass=8.0)
    hosts = {"quer": "W2", "klappe": "W1", "hoehe": "F4", "seite": "F4", "bugrad": "F2"}
    for d in linkage.linkages():
        side = "links" if d["side"] < 0 or d["kind"] == "bugrad" else "rechts"
        nm = d["name"].replace(" ", "_")
        add(f"Z_Servo_{nm}", f"Servo {d['name']}", "Elektronik", "servo", servo_mesh(d["servo"]),
            f"9-g-Servo; Hebel-Loch {d['arm_r']:.0f} mm; Gestänge: {d['rod']}",
            explode_offset(f"{hosts[d['kind']]}_x_{side}"), 9.0)
    horn = sf.ruderhorn()
    for k, (node, T) in enumerate(linkage.horn_transforms()):
        add(f"Z_Ruderhorn#{k + 1}", "Ruderhorn", "Elektronik", "horn", g.apply(horn, T),
            "gedruckt (PETG), in den Schlitz der Steuerfläche geklebt", explode_offset(node), 0.5)
        out[-1]["hinge_of"] = node
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
            key = node if node in hinges else p.name
            if key in hinges:
                kind, sign, a0, a1 = hinges[key]
                entry["hinge"] = dict(kind=kind, sign=sign, p0=_v(a0), p1=_v(a1))
            meta.append(entry)
    for b in bought_items():
        m = g.apply(b["mesh"], C).simplify(tol)
        tm = g.clean_trimesh(g.to_trimesh(m))
        scene.add_geometry(tm, node_name=b["node"], geom_name=b["node"])
        lo_, hi_ = b["mesh"].bounding_box()[:3], b["mesh"].bounding_box()[3:]
        entry = dict(node=b["node"], name=b["name"], group=b["group"], color=b["color"], material="Zukauf",
                     qty=1, mass=b["mass"], size=[round(float(v)) for v in np.subtract(hi_, lo_)], note=b["note"],
                     explode=_v(b["explode"]), tris=int(len(tm.faces)), bought=True)
        key = b.get("hinge_of", b["node"])
        if key in hinges:
            kind, sign, a0, a1 = hinges[key]
            entry["hinge"] = dict(kind=kind, sign=sign, p0=_v(a0), p1=_v(a1))
        meta.append(entry)
    path = os.path.join(outdir, "flugzeug.glb")
    scene.export(path)
    # Base64-Textfassung (Web-Hosting, das nur Text-/Bildtypen ausliefert)
    import base64
    open(os.path.join(outdir, "flugzeug.glb.txt"), "w").write(base64.b64encode(open(path, "rb").read()).decode("ascii"))
    b = np.array(allpts)
    lo, hi = b[:, 0].min(axis=0), b[:, 1].max(axis=0)
    cg = _v((mass["cg_x"], 0.0, WING_Z_REF - 20.0))
    info = dict(parts=meta, bounds=[lo.tolist(), hi.tolist()], cg=cg, numbers=nums,
                span=2 * WING_SEMISPAN, length=FUSE_LEN + SPINNER_LEN + 4.0,
                stl_count=len(parts), prints=int(sum(p.qty for p in parts)), linkages=linkage_json())
    json.dump(info, open(os.path.join(outdir, "teile.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    return dict(glb=path, size_mb=os.path.getsize(path) / 1e6, tris=sum(e["tris"] for e in meta), objects=len(meta))


def linkage_json() -> list[dict]:
    """Anlenkungen für die Animation im Browser (glTF-Koordinaten)."""
    from . import linkage
    out = []
    for d in linkage.linkages():
        sv = d["servo"]
        out.append(dict(name=d["name"], kind=d["kind"], surface=d["surface"],
                        servo="Z_Servo_" + d["name"].replace(" ", "_"),
                        pivot=_v(sv["arm_pivot"]), axis=_v(sv["axis"]), dir=_v(sv["arm_dir"]), r=d["arm_r"],
                        rest=d["rest_phi"], horn=_v(d["horn"]), via=[_v(p) for p in d.get("via", [])],
                        rod_len=round(d["rod_len"], 1), max_deflection=round(d["max_deflection"], 1)))
    return out


def write_index(outdir: str):
    """Eigenständige index.html (vollständiges HTML-Gerüst) aus seite.html erzeugen."""
    body = open(os.path.join(outdir, "seite.html"), encoding="utf-8").read()
    html = ('<!doctype html>\n<html lang="de">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            '<style>*,*::before,*::after{box-sizing:border-box}body{margin:0}[hidden]{display:none!important}</style>\n'
            '</head>\n<body>\n' + body + '\n</body>\n</html>\n')
    open(os.path.join(outdir, "index.html"), "w", encoding="utf-8").write(html)
