"""Tests: Geometrie, Druckbarkeit, Funktion und Auslegung des Modells."""
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cessna import build, checks, geom as g  # noqa: E402
from cessna.params import *  # noqa: E402,F401


@pytest.fixture(scope="module")
def parts():
    return build.build_all()


def test_parts_valid_and_fit_bed(parts):
    assert len(parts) >= 45
    assert build.check_parts(parts) == []


def test_no_overlaps_in_assembly(parts):
    assert build.overlap_report(parts) == []


def test_control_surfaces_move_freely(parts):
    bad = [(n, a, v) for n, a, v in checks.hinge_clearance(parts) if v > 1.0]
    assert bad == []


def test_spar_inside_airfoil():
    for label, (top, bot) in checks.spar_fit().items():
        assert top > 0.2 and bot > 0.2, (label, top, bot)


def test_center_of_gravity(parts):
    mass = build.mass_and_cg(parts)
    np_ = build.neutral_point()
    mac, xle = np_["mac"], np_["x_le_mac"]
    cg = (mass["cg_x"] - xle) / mac
    sm = (np_["x_np"] - mass["cg_x"]) / mac
    assert 0.22 <= cg <= 0.34, cg
    assert sm >= 0.08, sm
    assert MAIN_GEAR_X - mass["cg_x"] >= 15.0                      # Kippsicherheit nach hinten
    assert 1200 <= mass["total_mass"] <= 2100


def test_stl_export_is_watertight(parts, tmp_path):
    rows = build.export_stl(parts, str(tmp_path))
    assert len(rows) == len(parts)
    assert build.verify_exports(rows) == []


def test_wall_taper_planar():
    """Jede Rumpf-Seitenwand ist eben (Voraussetzung für flaches Aufliegen beim Druck)."""
    from cessna import fuselage as f
    for (x0, x1, _) in FUSE_SEGMENTS:
        xs = np.linspace(x0, x1, 25)
        a = f.section(xs)[0] / 2
        k, b = np.polyfit(xs, a, 1)
        assert np.abs(a - (k * xs + b)).max() < 0.05


def test_print_orientation_flat_bottom(parts):
    """Flügel, Querruder und Leitwerk liegen mit einer ebenen Fläche auf dem Bett (keine schwebende Unterseite)."""
    for p in parts:
        if p.group not in ("Flügel", "Querruder", "Leitwerk") or p.name.startswith("S4_"):
            continue
        tm = g.to_trimesh(p.print_mesh())
        main = max(tm.split(only_watertight=False), key=lambda c: c.volume)
        n, a = main.face_normals, main.area_faces
        z = main.triangles[:, :, 2].max(axis=1)
        down = n[:, 2] < -0.995
        a03 = a[down & (z < 0.3)].sum()
        a15 = a[down & (z < 1.5)].sum()
        assert a03 > 500.0, (p.name, a03)                  # mind. 5 cm² Auflage
        assert a03 >= 0.75 * a15, (p.name, a03, a15)       # Unterseite nicht schräg (Randbogen krümmt sich natürlich)


def test_linkages_reach_target_throws():
    """Jede Anlenkung erreicht mit ±35° Servoweg mindestens den Sollausschlag (Kinematik mit fester Gestängelänge)."""
    from cessna import linkage
    links = linkage.linkages()
    assert len(links) == 7
    for d in links:
        assert d["max_deflection"] >= d["target"], (d["name"], d["max_deflection"], d["target"])
        assert d["arm_r"] in linkage.STD_ARM_HOLES, d["name"]
        assert 40.0 < d["rod_len"] < 400.0, (d["name"], d["rod_len"])


def test_rod_tunnels_clear_of_fuselage_wall():
    """Gestängekanäle zu den Heckrudern halten Abstand zur Rumpfinnenwand (Rohr Ø3 passt durch)."""
    from cessna import fuselage as f
    for sgn in (-1, 1):
        a, b = f.tail_rod_lines(sgn)
        assert f.check_rod_clear(a, b, margin=0.0) > 2.0, sgn


def test_bought_parts_do_not_collide(parts):
    """Servos, Akku, Regler, Empfänger, Drähte und Ruderhörner haben Platz zwischen den Druckteilen."""
    from cessna import viewer
    for b in viewer.bought_items():
        bb = b["mesh"].bounding_box()
        for p in parts:
            if p.group == "Kleinteile":
                continue
            for T in p.asm_Ts():
                m = g.apply(p.mesh, T)
                pb = m.bounding_box()
                if any(bb[i] > pb[i + 3] or pb[i] > bb[i + 3] for i in range(3)):
                    continue
                assert (m ^ b["mesh"]).volume() < 2.0, (b["node"], p.name)


def test_print_plates_complete(parts, tmp_path):
    """Die 3MF-Druckplatten enthalten jedes Teil in der richtigen Stückzahl, dicht und innerhalb des 220er-Betts."""
    import trimesh
    from cessna import plates
    rows = build.export_stl(parts, str(tmp_path / "stl"))
    pl = plates.make_plates(rows, str(tmp_path / "plates"))
    count = {}
    for p in pl:
        for n in p["parts"]:
            count[n] = count.get(n, 0) + 1
        assert len({plates.profile_of(q) for q in parts if q.name in p["parts"]}) == 1, p["file"]
        sc = trimesh.load(str(tmp_path / "plates" / p["file"]))
        for gm in sc.dump():
            assert gm.is_watertight, p["file"]
            lo, hi = gm.bounds
            assert lo[0] >= plates.MARGIN - 0.1 and lo[1] >= plates.MARGIN - 0.1, p["file"]
            assert hi[0] <= plates.BED[0] - plates.MARGIN + 0.1 and hi[1] <= plates.BED[1] - plates.MARGIN + 0.1, p["file"]
            assert abs(lo[2]) < 1e-3, p["file"]
    assert count == {q.name: q.qty for q in parts}
