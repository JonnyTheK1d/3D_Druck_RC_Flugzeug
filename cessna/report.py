"""Dokumentationsdateien: Biegeschablone Fahrwerk, Druckliste (Markdown), Kennzahlen (JSON)."""
from __future__ import annotations

import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from . import wires
from .params import *
from .parts import Part


def gear_template(path_pdf: str, path_png: str):
    """Halbe Drahtform des Hauptfahrwerks im Maßstab 1:1 (A4 quer) + Bemaßung."""
    p = wires.main_gear_path()               # (y, z) links ... rechts
    half = p[p[:, 0] >= 0]                   # rechte Hälfte
    # Ursprung: Rumpfmitte (y = 0) -> Blatt
    fig = plt.figure(figsize=(297 / 25.4, 210 / 25.4))
    ax = fig.add_axes([0.04, 0.06, 0.92, 0.84])
    ax.set_aspect("equal")
    ax.plot(p[:, 0], p[:, 1], "-", color="#222", lw=GEAR_WIRE_MAIN * 72 / 25.4 * 0.5, solid_capstyle="round")
    ax.plot(p[:, 0], p[:, 1], "-", color="#888", lw=0.6)
    ax.axhline(0, color="#aaa", lw=0.8)
    ax.axvline(0, color="#aaa", lw=0.8, ls="--")
    names = ["Drahtende", "Achse außen", "Biegung 2", "Biegung 3", "Achse", "Drahtende"]
    # Maße der Teilstrecken (rechte Seite)
    pts = half
    for a, b in zip(pts[:-1], pts[1:]):
        L = np.linalg.norm(b - a)
        mid = (a + b) / 2
        ax.annotate(f"{L:.0f} mm", mid, xytext=(0, 14), textcoords="offset points", ha="center", fontsize=9, color="#c0392b")
    # Winkel
    d = np.diff(p, axis=0)
    ang = np.degrees(np.arctan2(d[:, 1], d[:, 0]))
    ax.annotate(f"Schenkel {abs(ang[2] - ang[1]):.0f}° zur Waagerechten", (pts[1] + (pts[2] - pts[1]) / 2),
                xytext=(10, -26), textcoords="offset points", fontsize=9, color="#1f5fa8")
    # Rad und Rumpfwand andeuten
    zc = WHEEL_D / 2
    for sy in (1,):
        ax.add_patch(plt.Rectangle((MAIN_GEAR_TRACK_HALF - WHEEL_W / 2, 0), WHEEL_W, WHEEL_D, fill=False, ec="#4a4f57", lw=1.2, ls=":"))
    ax.text(MAIN_GEAR_TRACK_HALF, WHEEL_D + 4, "Rad Ø55 (Lage)", ha="center", fontsize=8, color="#4a4f57")
    yw = float(__import__("cessna.fuselage", fromlist=["x"]).section(MAIN_GEAR_X)[0][0]) / 2
    ax.plot([yw, yw], [MAIN_WIRE_Z - 20, MAIN_WIRE_Z + 20], color="#2c7a4b", lw=2)
    ax.text(yw, MAIN_WIRE_Z + 24, "Rumpfwand", ha="center", fontsize=8, color="#2c7a4b")
    ax.set_xlim(-10, 195)
    ax.set_ylim(-5, 100)
    ax.set_xlabel("y [mm] ab Rumpfmitte")
    ax.set_ylabel("z [mm] über Boden")
    total = wires.polyline_length(p)
    ax.set_title(f"Hauptfahrwerk: Federstahldraht Ø{GEAR_WIRE_MAIN:.0f} mm - rechte Hälfte im Maßstab 1:1 (A4 quer ohne Skalierung drucken), "
                 f"Draht gesamt ca. {total + 10:.0f} mm, links spiegelbildlich", fontsize=9)
    ax.grid(True, color="#e5e5e5", lw=0.5)
    fig.savefig(path_pdf)
    fig.savefig(path_png, dpi=110)
    plt.close(fig)


def print_list_md(parts: list[Part], path: str):
    groups = {}
    for p in parts:
        groups.setdefault(p.group, []).append(p)
    lines = ["# Druckliste", "",
             "Alle STL-Dateien liegen bereits in **Druckausrichtung** vor (Teil liegt auf z = 0). Menge = Anzahl Drucke.",
             "Masse = Schätzung aus dem Modellvolumen (LW-PLA 0,55 g/cm³ als Hohlschale; Massivteile mit Füllfaktor).", ""]
    for gname, ps in groups.items():
        lines += [f"## {gname}", "", "| Teil | Menge | Material | Größe x·y·z [mm] | Masse [g] | Hinweis |",
                  "|---|---:|---|---|---:|---|"]
        for p in ps:
            s = p.print_size()
            n = len(p.asm_Ts())
            m = p.mass_g() / n if (n > 1 and p.qty > 1) else p.mass_g()
            lines.append(f"| `{p.name}` | {p.qty} | {p.material} | {s[0]:.0f} · {s[1]:.0f} · {s[2]:.0f} | {m:.1f} | {p.note} |")
        lines.append("")
    open(path, "w", encoding="utf-8").write("\n".join(lines))


def dump_numbers(parts, mass, np_, path):
    mac = np_["mac"]
    xle = np_["x_le_mac"]
    d = dict(
        teile=len(parts),
        druckteile_masse_g=round(mass["printed_mass"]),
        zukauf_masse_g=round(mass["bought_mass"]),
        gesamtmasse_g=round(mass["total_mass"]),
        schwerpunkt_x_mm=round(mass["cg_x"], 1),
        schwerpunkt_prozent_mac=round((mass["cg_x"] - xle) / mac * 100, 1),
        neutralpunkt_x_mm=round(np_["x_np"], 1),
        neutralpunkt_prozent_mac=round((np_["x_np"] - xle) / mac * 100, 1),
        stabilitaetsmass_prozent_mac=round((np_["x_np"] - mass["cg_x"]) / mac * 100, 1),
        fluegelflaeche_dm2=round(np_["S_w"] / 100 / 100, 2),
        flaechenbelastung_g_dm2=round(mass["total_mass"] / (np_["S_w"] / 100 / 100), 1),
        mac_mm=round(mac, 1),
        streckung=round(np_["AR_w"], 2),
        leitwerksvolumen=round(np_["vol_coeff"], 2),
        hauptfahrwerk_abstand_cg_mm=round(MAIN_GEAR_X - mass["cg_x"], 1),
        draht_hauptfahrwerk_mm=round(wires.summary()["gear_wire_len"] + 10),
    )
    json.dump(d, open(path, "w"), indent=2, ensure_ascii=False)
    return d


def _replace_block(path: str, key: str, text: str):
    s = open(path, encoding="utf-8").read()
    a, b = f"<!-- AUTO:{key} -->", f"<!-- /AUTO:{key} -->"
    i, j = s.index(a) + len(a), s.index(b)
    s = s[:i] + "\n" + text.rstrip("\n") + "\n" + s[j:]
    open(path, "w", encoding="utf-8").write(s)


def _de(x: float, nd: int = 1) -> str:
    return f"{x:.{nd}f}".replace(".", ",")


def sync_docs(root: str, parts: list[Part], mass: dict, np_: dict, nums: dict):
    """Schreibt Kennzahlen/Gewichte direkt aus dem Modell in README, Bauanleitung und Druckeinstellungen."""
    readme = os.path.join(root, "README.md")
    guide = os.path.join(root, "docs", "BAUANLEITUNG.md")
    pe = os.path.join(root, "docs", "DRUCKEINSTELLUNGEN.md")
    mac, xle = np_["mac"], np_["x_le_mac"]
    cg_rel = mass["cg_x"] - xle
    sizes = np.array([p.print_size() for p in parts])
    by_mat = {}
    for p in parts:
        by_mat[p.material] = by_mat.get(p.material, 0.0) + p.mass_g() * p.qty
    prints = sum(p.qty for p in parts)
    rows = [
        f"| Abfluggewicht (Schätzung) | **≈ {_de(nums['gesamtmasse_g'] / 1000)} kg** "
        f"({_de(nums['druckteile_masse_g'] / 1000, 2)} kg gedruckt + {_de(nums['zukauf_masse_g'] / 1000, 2)} kg Elektronik/Kohlefaser) |",
        f"| Flächenbelastung | ≈ {nums['flaechenbelastung_g_dm2']:.0f} g/dm², Überziehgeschwindigkeit ≈ 9 m/s |",
        f"| Schwerpunkt (Rechenwert) | {cg_rel:.0f} mm hinter der Flügelvorderkante ≈ **{nums['schwerpunkt_prozent_mac']:.0f} % MAC**, "
        f"Stabilitätsmaß ≈ {nums['stabilitaetsmass_prozent_mac']:.0f} % MAC |",
        f"| Druckteile | **{len(parts)} STL-Dateien / {prints} Drucke**, größte Grundfläche {max(sizes[:, 0].max(), sizes[:, 1].max()):.0f} × "
        f"{max(sizes[:, 0].max(), sizes[:, 1].max()):.0f} mm, höchstes Teil {sizes[:, 2].max():.0f} mm |",
        f"| Material | ca. {by_mat.get('LW-PLA', 0):.0f} g **LW-PLA**, {by_mat.get('PETG', 0):.0f} g PETG, {by_mat.get('PLA', 0):.0f} g PLA, "
        f"{by_mat.get('TPU', 0):.0f} g TPU (siehe `docs/DRUCKEINSTELLUNGEN.md`) |",
    ]
    _replace_block(readme, "eckdaten", "\n".join(rows))
    cg_rows = [
        "| Größe | Wert |", "|---|---|",
        f"| **Schwerpunkt** | **{cg_rel:.0f} mm hinter der Flügelvorderkante** (Rechenwert {mass['cg_x']:.0f} mm hinter der Haubenvorderkante); "
        f"zulässig: {0.24 * mac:.0f}–{0.35 * mac:.0f} mm = 24–35 % MAC |",
        f"| MAC | {mac:.0f} mm |",
        f"| Auswiegen | Flugzeug an den Punkten bei **x = {mass['cg_x']:.0f} mm** (am Rumpf von der Haubenvorderkante gemessen) unterstützen, Nase leicht unten |",
    ]
    _replace_block(guide, "schwerpunkt", "\n".join(cg_rows))
    mat_rows = ["| Material | Teile | Masse |", "|---|---|---:|",
                f"| **LW-PLA** (schäumend) | Flügel, Querruder, Rumpf (6 Segmente), Leitwerk | ca. {by_mat.get('LW-PLA', 0):.0f} g |",
                f"| **PETG** | Motorbock, Spinnerplatte, Fahrwerksklemmen, Bugfahrwerkslager, Gabel, Lenkhebel, Ruderhörner | ca. {by_mat.get('PETG', 0):.0f} g |",
                f"| **PLA** | Spinnerkegel, Radnaben, Streben | ca. {by_mat.get('PLA', 0):.0f} g |",
                f"| **TPU 95A** | 3 Reifen | ca. {by_mat.get('TPU', 0):.0f} g |"]
    _replace_block(pe, "material", "\n".join(mat_rows))
    from .linkage import doc_rows
    _replace_block(os.path.join(root, "docs", "FERNSTEUERUNG.md"), "anlenkung", "\n".join(doc_rows()))
