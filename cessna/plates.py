"""Druckplatten: alle STL nach Material/Einstellung gruppiert und auf einem 220 × 220-mm-Bett angeordnet (3MF).

Jede Platte enthält nur Teile mit denselben Slicer-Einstellungen. 3MF (Kernformat) öffnen PrusaSlicer, Bambu Studio,
OrcaSlicer, Cura und Simplify3D; die Teile stehen bereits in Druckausrichtung an ihrem Platz.
"""
from __future__ import annotations

import os
import zipfile

import numpy as np
import trimesh

from .parts import Part

BED = (220.0, 220.0)
MARGIN = 4.0              # Abstand zum Bettrand
GAP = 8.0                 # Abstand zwischen Teilen (Platz für Brim)

# Profil: (Kurzname, Material, Einstellung, Reihenfolge)
PROFILES = {
    "fluegel":     ("LW-PLA_Fluegel", "LW-PLA", "Wand 1,1 mm, 0 % Füllung, Boden/Deckel 3 Schichten, Brim 3–5 mm", 1),
    "leitwerk":    ("LW-PLA_Leitwerk", "LW-PLA", "Wand 0,85 mm, 0 % Füllung, Boden/Deckel 3 Schichten, „dünne Wände“ an", 2),
    "rumpf":       ("LW-PLA_Rumpf", "LW-PLA", "Wand 1,2 mm, 0 % Füllung, Boden/Deckel 3 Schichten", 3),
    "verkleidung": ("LW-PLA_Verkleidung", "LW-PLA", "Wand 1,0 mm, 0 % Füllung", 4),
    "petg":        ("PETG", "PETG", "4 Wände, 40 % Füllung (Gyroid), 245 °C / Bett 80 °C", 5),
    "petg_massiv": ("PETG_massiv", "PETG", "100 % Füllung (Hebel und Ruderhörner müssen steif sein)", 6),
    "pla":         ("PLA", "PLA", "3 Wände, 20 % Füllung", 7),
    "tpu":         ("TPU", "TPU 95A", "2 Wände, 10 % Füllung, 15–25 mm/s, Rückzug aus", 8),
}


def profile_of(p: Part) -> str:
    if p.material == "LW-PLA":
        if p.group in ("Flügel", "Querruder"):
            return "fluegel"
        if p.group == "Leitwerk":
            return "leitwerk"
        if p.group == "Rumpf":
            return "rumpf"
        return "verkleidung"
    if p.material == "PETG":
        return "petg_massiv" if (p.name.startswith(("S4_", "G6_")) or p.name == "Ruderhorn") else "petg"
    if p.material == "PLA":
        return "pla"
    return "tpu"


# --------------------------------------------------------------------------- #
# Anordnung (MaxRects, Best Short Side Fit, mit 90°-Drehung)
# --------------------------------------------------------------------------- #
class _Bin:
    def __init__(self, w, h):
        self.free = [(0.0, 0.0, w, h)]
        self.items = []

    def find(self, w, h):
        best = None
        for (fx, fy, fw, fh) in self.free:
            for rot, (iw, ih) in ((False, (w, h)), (True, (h, w))):
                if iw <= fw + 1e-6 and ih <= fh + 1e-6:
                    score = (min(fw - iw, fh - ih), max(fw - iw, fh - ih))
                    if best is None or score < best[0]:
                        best = (score, fx, fy, iw, ih, rot)
        return best

    def place(self, x, y, w, h):
        new = []
        for (fx, fy, fw, fh) in self.free:
            if x >= fx + fw or x + w <= fx or y >= fy + fh or y + h <= fy:
                new.append((fx, fy, fw, fh))
                continue
            if x > fx:
                new.append((fx, fy, x - fx, fh))
            if x + w < fx + fw:
                new.append((x + w, fy, fx + fw - x - w, fh))
            if y > fy:
                new.append((fx, fy, fw, y - fy))
            if y + h < fy + fh:
                new.append((fx, y + h, fw, fy + fh - y - h))
        # enthaltene Rechtecke entfernen
        self.free = [a for i, a in enumerate(new)
                     if not any(i != j and a[0] >= b[0] - 1e-9 and a[1] >= b[1] - 1e-9 and
                                a[0] + a[2] <= b[0] + b[2] + 1e-9 and a[1] + a[3] <= b[1] + b[3] + 1e-9 and
                                (a != b or i > j) for j, b in enumerate(new))]


def pack(items: list[tuple[str, float, float]]) -> list[list[tuple[str, float, float, bool]]]:
    """items: (Schlüssel, Breite, Tiefe) -> Platten mit (Schlüssel, x, y, gedreht)."""
    W, H = BED[0] - 2 * MARGIN + GAP, BED[1] - 2 * MARGIN + GAP     # GAP wird je Teil angehängt
    bins: list[_Bin] = []
    for key, w, h in sorted(items, key=lambda t: (-t[1] * t[2], t[0])):
        placed = False
        for b in bins:
            f = b.find(w + GAP, h + GAP)
            if f:
                _, x, y, iw, ih, rot = f
                b.place(x, y, iw, ih)
                b.items.append((key, x, y, rot))
                placed = True
                break
        if not placed:
            b = _Bin(W, H)
            f = b.find(w + GAP, h + GAP)
            if f is None:
                raise ValueError(f"{key} passt nicht auf das Bett ({w:.0f} × {h:.0f} mm)")
            _, x, y, iw, ih, rot = f
            b.place(x, y, iw, ih)
            b.items.append((key, x, y, rot))
            bins.append(b)
    return [b.items for b in bins]


# --------------------------------------------------------------------------- #
# 3MF schreiben (Kernspezifikation, deterministisch)
# --------------------------------------------------------------------------- #
_CT = ('<?xml version="1.0" encoding="UTF-8"?>\n'
       '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
       '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
       '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>'
       '</Types>')
_RELS = ('<?xml version="1.0" encoding="UTF-8"?>\n'
         '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
         '<Relationship Target="/3D/3dmodel.model" Id="rel0" '
         'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def write_3mf(path: str, title: str, objects: list[tuple[str, trimesh.Trimesh]], items: list[tuple[int, np.ndarray]]):
    """objects: (Name, Netz); items: (Objekt-Index, 4×4-Lage auf dem Bett)."""
    out = ['<?xml version="1.0" encoding="UTF-8"?>\n<model unit="millimeter" xml:lang="de-DE" '
           'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">',
           f'<metadata name="Title">{_esc(title)}</metadata>',
           '<metadata name="Application">cessna (3D_Druck_RC_Flugzeug)</metadata>', '<resources>']
    for i, (name, tm) in enumerate(objects, start=1):
        out.append(f'<object id="{i}" type="model" name="{_esc(name)}"><mesh><vertices>')
        # exakt wie in der STL (float32), sonst verschmelzen eng benachbarte Punkte und das Netz wird undicht
        out.extend(f'<vertex x="{x:.9g}" y="{y:.9g}" z="{z:.9g}"/>' for x, y, z in np.asarray(tm.vertices, np.float32))
        out.append('</vertices><triangles>')
        out.extend(f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in np.asarray(tm.faces))
        out.append('</triangles></mesh></object>')
    out.append('</resources><build>')
    for oi, T in items:
        m = T[:3, :3].T.reshape(-1).tolist() + T[:3, 3].tolist()     # 3MF: Zeilenvektor-Konvention
        out.append(f'<item objectid="{oi + 1}" transform="{" ".join(f"{v:.6g}" for v in m)}"/>')
    out.append('</build></model>')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for name, data in (("[Content_Types].xml", _CT), ("_rels/.rels", _RELS),
                           ("3D/3dmodel.model", "\n".join(out))):
            zi = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(zi, data)


def _label(names: list[str]) -> str:
    """Kurzer, sprechender Dateiname für eine Platte, z. B. 'K1_Landeklappe_links+rechts' oder 'H1+H2_links_oben'."""
    if len(names) == 1:
        return names[0]
    toks = [n.split("_") for n in names]
    heads = list(dict.fromkeys(t[0] for t in toks))
    common = [w for w in ("links", "rechts", "oben", "unten", "innen", "aussen") if all(w in t for t in toks)]
    if len(heads) == 1:
        body = [w for w in toks[0][1:] if w not in ("links", "rechts", "oben", "unten", "innen", "aussen")]
        rest = sorted({w for t in toks for w in t if w in ("links", "rechts", "oben", "unten", "innen", "aussen")}
                      - set(common))
        return "_".join([heads[0]] + body + common + (["+".join(rest)] if rest else []))
    return "+".join(heads) + ("_" + "_".join(common) if common else "")


# --------------------------------------------------------------------------- #
# Platten erzeugen
# --------------------------------------------------------------------------- #
def make_plates(rows: list[tuple[Part, str]], outdir: str) -> list[dict]:
    """rows: (Teil, STL-Pfad) aus build.export_stl. Schreibt die 3MF-Platten und gibt die Plattenliste zurück."""
    for f in os.listdir(outdir) if os.path.isdir(outdir) else []:
        if f.endswith(".3mf"):
            os.remove(os.path.join(outdir, f))
    meshes, parts = {}, {}
    for p, path in rows:
        tm = trimesh.load(path, force="mesh")                         # Teile liegen schon auf z = 0
        lo = tm.bounds[0]
        tm.apply_translation([-lo[0], -lo[1], 0.0])                   # Fußabdruck beginnt bei (0, 0)
        tm.vertices = np.asarray(tm.vertices, np.float32).astype(float)
        assert tm.is_watertight, path
        meshes[p.name], parts[p.name] = tm, p
    by_prof: dict[str, list] = {}
    for name, p in parts.items():
        ext = meshes[name].extents
        for k in range(p.qty):
            by_prof.setdefault(profile_of(p), []).append((f"{name}#{k}", float(ext[0]), float(ext[1])))
    plates = []
    for prof in sorted(by_prof, key=lambda k: PROFILES[k][3]):
        packed = pack(by_prof[prof])
        # Probedruck W0 zuerst, sonst große Platten zuerst
        packed.sort(key=lambda its: not any(k.startswith("W0_") for k, *_ in its))
        for its in packed:
            plates.append((prof, its))
    out = []
    counters: dict[str, int] = {}
    for nr, (prof, its) in enumerate(plates, start=1):
        short, mat, setting, _ = PROFILES[prof]
        names = sorted({k.split("#")[0] for k, *_ in its}, key=lambda n: [k for k, *_ in its].index(n + "#0"))
        counters[prof] = counters.get(prof, 0) + 1
        label = _label(names)
        fname = f"{nr:02d}_{short}_{label}.3mf"
        objs = [(n, meshes[n]) for n in names]
        idx = {n: i for i, n in enumerate(names)}
        # Belegung zentrieren
        boxes = []
        for key, x, y, rot in its:
            e = meshes[key.split("#")[0]].extents
            w, h = (e[1], e[0]) if rot else (e[0], e[1])
            boxes.append((x, y, w, h))
        bx0 = min(b[0] for b in boxes)
        by0 = min(b[1] for b in boxes)
        bx1 = max(b[0] + b[2] for b in boxes)
        by1 = max(b[1] + b[3] for b in boxes)
        ox, oy = (BED[0] - (bx1 - bx0)) / 2 - bx0, (BED[1] - (by1 - by0)) / 2 - by0
        items = []
        for (key, x, y, rot), (_, _, w, h) in zip(its, boxes):
            n = key.split("#")[0]
            T = np.eye(4)
            if rot:                                                      # 90° um z, Fußabdruck bleibt ab (0, 0)
                T[:3, :3] = [[0, -1, 0], [1, 0, 0], [0, 0, 1]]
                T[0, 3] = meshes[n].extents[1]
            T[0, 3] += x + ox
            T[1, 3] += y + oy
            items.append((idx[n], T))
        write_3mf(os.path.join(outdir, fname), fname[:-4], objs, items)
        mass = sum(parts[k.split("#")[0]].mass_g() for k, *_ in its)          # mass_g gilt je Stück
        out.append(dict(_geom=[(meshes[names[i]], T) for i, T in items],
                        nr=nr, file=fname, profile=prof, material=mat, setting=setting,
                        parts=[k.split("#")[0] for k, *_ in its], mass=mass,
                        height=max(meshes[k.split("#")[0]].extents[2] for k, *_ in its),
                        bbox=(bx1 - bx0 - GAP, by1 - by0 - GAP)))
    return out


def plates_md(plates: list[dict], path: str):
    lines = ["# Druckplatten (3MF, fertig angeordnet)", "",
             "Alle druckbaren Teile, nach **Material und Slicer-Einstellung** auf Platten für ein **220 × 220-mm-Bett**",
             "verteilt (Ender 3, Prusa MK3/MK4, Bambu A1/P1/X1, Voron, …). Die Dateien liegen in `druckplatten/`.",
             "Die Teile stehen in Druckausrichtung und mit 8 mm Abstand (Platz für Brim). Größere Betten: einfach",
             "mehrere Platten im Slicer zusammenlegen oder „Anordnen“ drücken.", "",
             "**So geht's:** 3MF-Datei im Slicer öffnen (PrusaSlicer, Bambu Studio, OrcaSlicer, Cura) → Druckerprofil wählen →",
             "Einstellungen aus der Spalte „Einstellung“ setzen → slicen → G-Code/Druckauftrag an den Drucker.",
             "Fragt der Slicer, ob das Objekt aus mehreren Teilen besteht: **Nein** (jede Datei enthält einzelne Objekte).", "",
             "> Zuerst **Platte 01** (`W0_Mittelstueck`) drucken und wiegen: Soll ca. 57 g. Weicht das stark ab,",
             "> Fluss/Temperatur für LW-PLA nachstellen (siehe `docs/DRUCKEINSTELLUNGEN.md`), bevor du den Rest druckst.", "",
             "![Druckplatten](img/druckplatten.png)", "",
             "| Platte | Datei | Material | Einstellung | Teile | Masse | Höhe |", "|---:|---|---|---|---|---:|---:|"]
    for pl in plates:
        cnt: dict[str, int] = {}
        for n in pl["parts"]:
            cnt[n] = cnt.get(n, 0) + 1
        ps = ", ".join(f"`{n}`" + (f" ×{c}" if c > 1 else "") for n, c in cnt.items())
        lines.append(f"| {pl['nr']:02d} | `{pl['file']}` | {pl['material']} | {pl['setting']} | {ps} | "
                     f"{pl['mass']:.0f} g | {pl['height']:.0f} mm |")
    tot: dict[str, float] = {}
    for pl in plates:
        tot[pl["material"]] = tot.get(pl["material"], 0.0) + pl["mass"]
    lines += ["", f"**{len(plates)} Platten**, "
              + ", ".join(f"{m}: ca. {v:.0f} g" for m, v in tot.items()) + " (Filamentverbrauch etwas höher: Brim, Fehldrucke).",
              "", "Einzelteile als STL (gleiche Ausrichtung) liegen in `stl/`, die Teileliste in `docs/DRUCKLISTE.md`.", ""]
    open(path, "w", encoding="utf-8").write("\n".join(lines))


MAT_COL = {"LW-PLA": "#3f7cc0", "PETG": "#e8a33d", "PLA": "#c0392b", "TPU 95A": "#3b3f46"}


def overview_png(plates: list[dict], path: str, cols: int = 6):
    """Übersichtsbild aller Platten (Draufsicht, 220 × 220 mm)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    rows = -(-len(plates) // cols)
    fig, axs = plt.subplots(rows, cols, figsize=(cols * 2.6, rows * 2.85), dpi=110)
    for ax in np.asarray(axs).reshape(-1):
        ax.axis("off")
    for ax, pl in zip(np.asarray(axs).reshape(-1), plates):
        ax.add_patch(plt.Rectangle((0, 0), BED[0], BED[1], fc="#f3f5f8", ec="#9aa3ad", lw=0.8))
        for tm, T in pl["_geom"]:
            v = (np.c_[tm.vertices, np.ones(len(tm.vertices))] @ T.T)[:, :2]
            tri = v[tm.faces]
            ax.add_collection(PolyCollection(tri, facecolors=MAT_COL.get(pl["material"], "#888"), edgecolors="none"))
        ax.set_xlim(-4, BED[0] + 4)
        ax.set_ylim(-4, BED[1] + 4)
        ax.set_aspect("equal")
        ax.set_title(f"{pl['nr']:02d} · {pl['material']}\n{pl['file'][3:-4].split('_', 1)[-1][:28]}", fontsize=7.5)
    fig.suptitle("Druckplatten 220 × 220 mm (blau LW-PLA · orange PETG · rot PLA · grau TPU)", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.975))
    fig.savefig(path)
    plt.close(fig)
