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
