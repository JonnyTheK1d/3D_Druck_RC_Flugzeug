"""Vorschaubilder: Gesamtansichten, Explosionsdarstellung, Teile-Übersicht."""
from __future__ import annotations

import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from . import geom as g
from . import render, wires
from .params import *
from .parts import Part

COL = {
    "Rumpf": "#e4e7ec", "Flügel": "#3f7cc0", "Querruder": "#e8a33d", "Leitwerk": "#3f7cc0",
    "Antrieb": "#c0392b", "Fahrwerk": "#4a4f57", "Streben": "#9aa5b1", "Kleinteile": "#999999",
}


def color_of(p: Part) -> str:
    if p.group == "Leitwerk" and ("Hoehenruder" in p.name or "Seitenruder" in p.name):
        return COL["Querruder"]
    if p.name.startswith("G1_"):
        return "#202225"
    if p.name.startswith("G2_"):
        return "#c9ced6"
    return COL.get(p.group, "#888888")


def extras() -> list:
    out = [(wires.prop_solid(), "#2b2b2b"), (wires.motor_solid(), "#7d8590")]
    path = wires.main_gear_path()
    out.append((wires.wire_solid(path, MAIN_GEAR_X, 2.0), "#7d8590"))
    out.append((g.cyl((NOSE_GEAR_X, 0, 57.5), (NOSE_GEAR_X, 0, NOSE_WIRE_Z_TOP), 1.5, segs=16), "#7d8590"))
    return out


def assembly_items(parts: list[Part], explode=False, with_extras=True):
    items = []
    for p in parts:
        if p.group == "Kleinteile":
            continue
        for T in p.asm_Ts():
            m = g.apply(p.mesh, T)
            if explode:
                m = g.apply(m, g.translation(*explode_offset(p.name)))
            items.append((m, color_of(p)))
    if with_extras and not explode:
        items += extras()
    return items


def explode_offset(name: str):
    n = name
    side = -1.0 if "links" in n else 1.0
    if n.startswith("W0"):
        return (0, 0, 70)
    if n.startswith("W1"):
        return (0, side * 45, 70)
    if n.startswith("W2"):
        return (0, side * 90, 70)
    if n.startswith("W3"):
        return (0, side * 135, 70)
    if n.startswith("Q1"):
        return (45, side * 90, 70)
    if n.startswith("Q2"):
        return (45, side * 135, 70)
    if n.startswith("H1"):
        return (0, side * 40, 70) if "oben" in n else (0, side * 40, 40)
    if n.startswith("H2"):
        return (40, side * 45, 70) if "oben" in n else (40, side * 45, 40)
    if n.startswith("S1"):
        return (0, -40 if "oben" in n else 40, 0)
    if n.startswith("S2"):
        return (60, -40 if "oben" in n else 40, 0)
    if n.startswith("F"):
        idx = int(n[1]) - 1
        return (idx * 55 - 20, side * 55, 0)
    if n.startswith("P1"):
        return (-60, 0, 0)
    if n.startswith("P2") or n.startswith("P3"):
        return (-100, 0, 0)
    if n.startswith("G"):
        return (0, 0, -55)
    if n.startswith("Z"):
        return (0, side * 70, -30)
    return (0, 0, 0)


def make_images(parts: list[Part], outdir: str):
    os.makedirs(outdir, exist_ok=True)
    items = assembly_items(parts)
    for view, name, size in (("iso", "uebersicht.png", (1700, 1000)),
                             ("iso2", "uebersicht_hinten.png", (1700, 1000)),
                             ("side", "ansicht_seite.png", (1700, 720)),
                             ("top", "ansicht_oben.png", (1700, 1100)),
                             ("front", "ansicht_vorne.png", (1400, 800)),
                             ("bottom", "ansicht_unten.png", (1700, 1100))):
        render.render(items, os.path.join(outdir, name), view, size=size)
    ex = assembly_items(parts, explode=True, with_extras=False)
    render.render(ex, os.path.join(outdir, "explosion.png"), "iso", size=(2000, 1300))
    # Rumpf innen (rechte Hälften weggelassen -> Blick in die linken Halbschalen)
    inner = [(p.asm_mesh(), color_of(p)) for p in parts if p.group == "Rumpf" and "links" in p.name]
    render.render(inner, os.path.join(outdir, "rumpf_innen.png"), (np.array([0.35, 0.9, 0.45]), np.array([0, 0, 1.0])),
                  size=(1700, 800))


def contact_sheet(parts: list[Part], path: str, cols=6, tile=(330, 250)):
    """Alle Teile in Druckausrichtung (Ansicht schräg von oben) mit Beschriftung."""
    rows = int(np.ceil(len(parts) / cols))
    W, H = cols * tile[0], rows * tile[1]
    sheet = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(sheet)
    try:
        f = ImageFont.truetype("DejaVuSans.ttf", 14)
    except Exception:
        f = ImageFont.load_default()
    tmp = path + ".tmp.png"
    for i, p in enumerate(parts):
        m = p.print_mesh()
        render.render([(m, color_of(p))], tmp, (np.array([-0.55, -0.5, 0.67]), np.array([0, 0, 1.0])),
                      size=tile, ssaa=2, margin=0.14)
        im = Image.open(tmp)
        x, y = (i % cols) * tile[0], (i // cols) * tile[1]
        sheet.paste(im, (x, y))
        d.rectangle([x, y, x + tile[0] - 1, y + tile[1] - 1], outline=(215, 218, 224))
        s = p.print_size()
        label = f"{p.name}" + (f"  x{p.qty}" if p.qty > 1 else "")
        d.text((x + 8, y + 6), label, fill=(30, 30, 30), font=f)
        d.text((x + 8, y + tile[1] - 22), f"{s[0]:.0f} x {s[1]:.0f} x {s[2]:.0f} mm  {p.material}", fill=(90, 90, 90), font=f)
    os.remove(tmp)
    sheet.save(path)
