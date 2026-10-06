"""Baut alle Teile, prüft sie, exportiert STL/Stückliste und Vorschaubilder.

Aufruf:  python -m cessna.build [--no-render] [--only GRUPPE]
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import time

import numpy as np

from . import fuselage, gear, geom as g, power, tail, wing
from .params import *
from .parts import Part

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STL_DIR = os.path.join(ROOT, "stl")
DOC_DIR = os.path.join(ROOT, "docs")


def build_all() -> list[Part]:
    parts: list[Part] = []
    parts += wing.build_wing()
    parts += tail.build_tail()
    parts += fuselage.build_fuselage()
    parts.append(fuselage.dorsal_fin())
    parts.append(power.motor_mount())
    parts += power.spinner()
    parts += gear.build_gear()
    return parts


# --------------------------------------------------------------------------- #
# Prüfungen
# --------------------------------------------------------------------------- #
def check_parts(parts: list[Part]) -> list[str]:
    problems = []
    names = set()
    for p in parts:
        if p.name in names:
            problems.append(f"{p.name}: doppelter Name")
        names.add(p.name)
        if p.mesh.status() != g.m3.Error.NoError:
            problems.append(f"{p.name}: kein gültiges Manifold ({p.mesh.status()})")
            continue
        if p.volume() <= 1.0:
            problems.append(f"{p.name}: Volumen ~ 0")
        if not p.fits():
            problems.append(f"{p.name}: passt nicht auf das Druckbett {p.print_size().round(1)} > {BED}")
        solids, _ = g.solid_components(g.to_trimesh(p.mesh))
        if len(solids) != 1:
            problems.append(f"{p.name}: {len(solids)} getrennte Festkörper (erwartet 1): {[round(c.volume) for c in solids]} mm³")
        tm = g.to_trimesh(p.print_mesh())
        if tm.vertices.min(axis=0)[2] < -1e-3:
            problems.append(f"{p.name}: Teil ragt unter die Druckbettebene")
    return problems


def overlap_report(parts: list[Part], min_vol=3.0, ignore=()) -> list[tuple]:
    """Paarweise Überschneidungsvolumina im Zusammenbau (mm³)."""
    meshes = [(p, p.asm_mesh()) for p in parts if p.group != "Kleinteile"]
    bbs = [g.bbox(m) for _, m in meshes]
    out = []
    for i in range(len(meshes)):
        for j in range(i + 1, len(meshes)):
            lo = np.maximum(bbs[i][0], bbs[j][0])
            hi = np.minimum(bbs[i][1], bbs[j][1])
            if np.any(lo >= hi):
                continue
            a, b = meshes[i][0].name, meshes[j][0].name
            if (a, b) in ignore or (b, a) in ignore:
                continue
            v = (meshes[i][1] ^ meshes[j][1]).volume()
            if v > min_vol:
                out.append((a, b, round(v, 1)))
    return sorted(out, key=lambda t: -t[2])


# --------------------------------------------------------------------------- #
# Masse und Schwerpunkt
# --------------------------------------------------------------------------- #
def mass_and_cg(parts: list[Part]):
    rows = []
    M = 0.0
    Mx = 0.0
    for p in parts:
        mass = p.mass_g()
        n = len(p.asm_Ts())
        per = mass / n * p.qty if n == 1 else mass * p.qty / n
        for T in p.asm_Ts():
            m = g.apply(p.mesh, T)
            tm = g.to_trimesh(m)
            vol = tm.volume
            c = tm.center_mass if abs(vol) > 1e-6 else tm.centroid
            rows.append((p.name, mass * p.qty / n if n > 1 else mass, float(c[0]), float(c[2])))
    printed = sum(r[1] for r in rows)
    mx = sum(r[1] * r[2] for r in rows)
    bought = sum(m for m, _ in BOUGHT_PARTS.values())
    bx = sum(m * x for m, x in BOUGHT_PARTS.values())
    return dict(rows=rows, printed_mass=printed, printed_cg=mx / printed, bought_mass=bought,
                total_mass=printed + bought, cg_x=(mx + bx) / (printed + bought))


def neutral_point():
    """Neutralpunkt (grobe Abschätzung nach Standard-Methode: Flügel + Leitwerk + Rumpf-Korrektur)."""
    # Flügelfläche aus Planform
    ys = np.linspace(0, WING_SEMISPAN, 400)
    c = np.array([wing.wing_chord(y) for y in ys])
    S_w = 2 * np.trapezoid(c, ys)
    mac = 2 * np.trapezoid(c ** 2, ys) / S_w
    y_mac = 2 * np.trapezoid(c * ys, ys) / S_w
    x_le_mac = WING_LE_X                       # gerade Vorderkante
    St_c = (STAB_ROOT_CHORD + STAB_TIP_CHORD) / 2
    S_t = 2 * STAB_HALFSPAN * St_c
    AR_w = (2 * WING_SEMISPAN) ** 2 / S_w
    AR_t = (2 * STAB_HALFSPAN) ** 2 / S_t
    a_w = 2 * np.pi * AR_w / (2 + np.sqrt(4 + AR_w ** 2))
    a_t = 2 * np.pi * AR_t / (2 + np.sqrt(4 + AR_t ** 2))
    deps = 2 * a_w / (np.pi * AR_w)            # downwash-Gradient
    eta = 0.9
    x_ac_w = x_le_mac + 0.25 * mac
    x_ac_t = STAB_LE_X + 0.25 * St_c
    num = a_w * x_ac_w + eta * a_t * (S_t / S_w) * (1 - deps) * x_ac_t
    den = a_w + eta * a_t * (S_t / S_w) * (1 - deps)
    x_np = num / den
    return dict(S_w=S_w, mac=mac, y_mac=y_mac, S_t=S_t, AR_w=AR_w, x_np=x_np,
                x_le_mac=x_le_mac, vol_coeff=S_t * (x_ac_t - x_ac_w) / (S_w * mac))


# --------------------------------------------------------------------------- #
# Export
# --------------------------------------------------------------------------- #
def stl_ok(tm) -> bool:
    """Netz nach STL-Rundung (float32) prüfen: nach dem Verschmelzen nur wasserdichte, konsistente Komponenten."""
    import trimesh
    chk = trimesh.Trimesh(np.asarray(tm.vertices, np.float32).astype(np.float64), np.asarray(tm.faces), process=True)
    chk.merge_vertices()
    comps = chk.split(only_watertight=False)
    return len(comps) <= 3 and all(c.is_watertight and c.is_winding_consistent for c in comps)


def to_f32(tm):
    """Wie im STL: auf float32 runden, gleiche Eckpunkte verschmelzen, Splitter-Komponenten entfernen."""
    import trimesh
    t = trimesh.Trimesh(np.asarray(tm.vertices, np.float32).astype(np.float64), np.asarray(tm.faces), process=True)
    t.merge_vertices()
    t = g.clean_trimesh(t)
    t.remove_unreferenced_vertices()
    return t


def export_mesh(m: g.Manifold):
    """Netz für den STL-Export.

    Stufen (die erste, deren STL nach der float32-Rundung wasserdicht ist, gewinnt):
    1. Vereinfachen (kollabiert Nulldreiecke an T-Stößen) mit steigender Toleranz,
    2. mikroskopische Verschiebung in x/y (ändert, welche Eckpunkte beim float32-Runden zusammenfallen),
    3. Aufweiten um wenige Mikrometer (schließt Haarspalte zwischen sich fast berührenden Flächen).
    """
    first = None

    def attempt(mm):
        nonlocal first
        tm = to_f32(g.clean_trimesh(g.to_trimesh(mm)))
        first = tm if first is None else first
        return tm if stl_ok(tm) else None

    for tol in (1e-4, 3e-4, 1e-3, 3e-3, 1e-2, 3e-2):
        ms = m.simplify(tol)
        tm = attempt(ms)
        if tm is not None:
            return tm
    base = m.simplify(1e-3)
    for dx, dy in ((0.00137, 0.00291), (0.00311, 0.00073), (0.00219, 0.00417), (0.00053, 0.00377),
                   (0.00439, 0.00161), (0.00277, 0.00523)):
        tm = attempt(base.translate((dx, dy, 0.0)))
        if tm is not None:
            return tm
    kern = lambda r: g.Manifold.sphere(r, 8)
    for r in (0.004, 0.006, 0.010):
        tm = attempt(m.minkowski_sum(kern(r)).simplify(1e-3).translate((0.0, 0.0, r)))   # Boden wieder auf z = 0
        if tm is not None:
            return tm
    return first


def export_stl(parts: list[Part], outdir=STL_DIR):
    import trimesh
    os.makedirs(outdir, exist_ok=True)
    rows = []
    for p in parts:
        d = os.path.join(outdir, p.group.replace(" ", "_").replace("ü", "ue").replace("ä", "ae").replace("ö", "oe"))
        os.makedirs(d, exist_ok=True)
        path = os.path.join(d, f"{p.name}.stl")
        tm = export_mesh(p.print_mesh())
        tm.export(path)
        rows.append((p, path))
    return rows


def write_bom(parts: list[Part], path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["Teil", "Gruppe", "Anzahl", "Material", "Druckgroesse x [mm]", "y [mm]", "z [mm]",
                    "Masse je Teil [g]", "Hinweis"])
        for p in parts:
            s = p.print_size()
            w.writerow([p.name, p.group, p.qty, p.material, round(s[0], 1), round(s[1], 1), round(s[2], 1),
                        round(p.mass_g() / (len(p.asm_Ts()) if len(p.asm_Ts()) > 1 else 1) if p.qty == 1 else
                              p.mass_g() / len(p.asm_Ts()), 1), p.note])


def verify_exports(rows):
    """Lädt jede STL erneut und prüft Wasserdichtigkeit, Volumen und Bettgröße."""
    import trimesh
    bad = []
    for p, path in rows:
        tm = trimesh.load(path, process=True)      # Eckpunkte verschmelzen (STL speichert sie je Dreieck)
        tm.merge_vertices()
        comps = tm.split(only_watertight=False)
        wt = all(c.is_watertight for c in comps)
        vol = sum(c.volume for c in comps)
        lo, hi = tm.bounds
        if not wt:
            bad.append(f"{p.name}: STL nicht wasserdicht ({len(comps)} Komponenten)")
        solids = [c for c in comps if c.volume > 1.0]
        if len(solids) != 1:
            bad.append(f"{p.name}: {len(solids)} getrennte Festkörper (erwartet 1) – Teile {[round(c.volume) for c in solids]} mm³")
        if len(comps) > 3:
            bad.append(f"{p.name}: {len(comps)} lose Komponenten")
        if vol <= 0:
            bad.append(f"{p.name}: Volumen <= 0 ({vol:.1f})")
        if abs(lo[2]) > 1e-3:
            bad.append(f"{p.name}: Unterseite nicht auf z=0 ({lo[2]:.3f})")
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-images", action="store_true")
    ap.add_argument("--no-export", action="store_true")
    ap.add_argument("--overlaps", action="store_true")
    args = ap.parse_args()
    from . import report, showcase
    t0 = time.time()
    parts = build_all()
    print(f"{len(parts)} Teile gebaut in {time.time() - t0:.1f} s")
    problems = check_parts(parts)
    for pr in problems:
        print("PROBLEM:", pr)
    if args.overlaps:
        ov = overlap_report(parts)
        for row in ov:
            print("ÜBERSCHNEIDUNG", row)
        if not ov:
            print("Keine Überschneidungen im Zusammenbau.")
    mass = mass_and_cg(parts)
    np_ = neutral_point()
    os.makedirs(DOC_DIR, exist_ok=True)
    nums = report.dump_numbers(parts, mass, np_, os.path.join(DOC_DIR, "kennzahlen.json"))
    print(json.dumps(nums, indent=1, ensure_ascii=False))
    if not args.no_export:
        rows = export_stl(parts)
        bad = verify_exports(rows)
        for b in bad:
            print("STL-PROBLEM:", b)
        write_bom(parts, os.path.join(DOC_DIR, "stueckliste.csv"))
        report.print_list_md(parts, os.path.join(DOC_DIR, "DRUCKLISTE.md"))
        report.gear_template(os.path.join(DOC_DIR, "fahrwerk_biegeschablone.pdf"),
                             os.path.join(DOC_DIR, "img", "fahrwerk_biegeschablone.png")) if os.makedirs(os.path.join(DOC_DIR, "img"), exist_ok=True) is None else None
        total = sum(os.path.getsize(path) for _, path in rows)
        print(f"STL exportiert: {len(rows)} Dateien, {total / 1e6:.1f} MB")
        from . import plates
        pl = plates.make_plates(rows, os.path.join(ROOT, "druckplatten"))
        plates.plates_md(pl, os.path.join(DOC_DIR, "DRUCKPLATTEN.md"))
        plates.overview_png(pl, os.path.join(DOC_DIR, "img", "druckplatten.png"))
        print(f"Druckplatten (3MF): {len(pl)} Platten in druckplatten/")
    report.sync_docs(ROOT, parts, mass, np_, nums)
    from . import viewer
    vinfo = viewer.export_viewer(parts, os.path.join(DOC_DIR, "viewer"), mass, nums)
    viewer.write_index(os.path.join(DOC_DIR, "viewer"))
    print(f"3D-Ansicht: {vinfo['objects']} Objekte, {vinfo['tris']} Dreiecke, {vinfo['size_mb']:.1f} MB")
    if not args.no_images:
        showcase.make_images(parts, os.path.join(DOC_DIR, "img"))
        showcase.contact_sheet(parts, os.path.join(DOC_DIR, "img", "teileuebersicht.png"))
    print(f"fertig in {time.time() - t0:.1f} s")
    return parts


if __name__ == "__main__":
    main()
