"""Geometrie-Hilfsfunktionen auf Basis von manifold3d (alle Maße in mm)."""
from __future__ import annotations

import numpy as np
import manifold3d as m3
import trimesh

Manifold = m3.Manifold
CrossSection = m3.CrossSection

SEGMENTS = 48  # Facetten pro Vollkreis für Zylinder u. ä.


# --------------------------------------------------------------------------- #
# Konvertierung
# --------------------------------------------------------------------------- #
def from_arrays(verts: np.ndarray, faces: np.ndarray) -> Manifold:
    """Dreiecksnetz -> Manifold. Dreht die Windung um, falls das Volumen < 0 ist."""
    verts = np.asarray(verts, dtype=np.float64)
    faces = np.asarray(faces, dtype=np.uint32)
    tri = verts[faces]
    vol = np.einsum("ij,ij->", tri[:, 0], np.cross(tri[:, 1], tri[:, 2])) / 6.0
    if vol < 0:
        faces = faces[:, ::-1].copy()
    mesh = m3.Mesh(vert_properties=verts.astype(np.float32), tri_verts=faces)
    out = Manifold(mesh)
    if out.status() != m3.Error.NoError:
        raise ValueError(f"Kein gültiges Manifold: {out.status()}")
    return out


def to_trimesh(m: Manifold) -> trimesh.Trimesh:
    mesh = m.to_mesh()
    return trimesh.Trimesh(
        vertices=np.asarray(mesh.vert_properties, dtype=np.float64)[:, :3],
        faces=np.asarray(mesh.tri_verts, dtype=np.int64),
        process=False,
    )


def union(parts):
    parts = [p for p in parts if p is not None]
    return Manifold.batch_boolean(parts, m3.OpType.Add)


def difference(a: Manifold, *cuts: Manifold) -> Manifold:
    for c in cuts:
        if c is not None:
            a = a - c
    return a


def intersect(a: Manifold, b: Manifold) -> Manifold:
    return a ^ b


# --------------------------------------------------------------------------- #
# Primitive
# --------------------------------------------------------------------------- #
def box(x0, x1, y0, y1, z0, z1) -> Manifold:
    lo = np.minimum([x0, y0, z0], [x1, y1, z1])
    hi = np.maximum([x0, y0, z0], [x1, y1, z1])
    return Manifold.cube(tuple(hi - lo), False).translate(tuple(lo))


def cyl(p0, p1, r, r1=None, segs=SEGMENTS) -> Manifold:
    """Zylinder/Kegelstumpf von p0 nach p1 (Radius r bei p0, r1 bei p1)."""
    p0 = np.asarray(p0, float)
    p1 = np.asarray(p1, float)
    d = p1 - p0
    h = float(np.linalg.norm(d))
    r1 = r if r1 is None else r1
    c = Manifold.cylinder(h, r, r1, segs, False)
    z = np.array([0, 0, 1.0])
    d = d / h
    axis = np.cross(z, d)
    s = np.linalg.norm(axis)
    if s < 1e-9:
        if d[2] < 0:
            c = c.rotate((180, 0, 0))
    else:
        ang = np.degrees(np.arctan2(s, np.dot(z, d)))
        R = rotation_matrix(axis / s, ang)
        c = c.transform(R[:3, :])
    return c.translate(tuple(p0))


def rotation_matrix(axis, angle_deg) -> np.ndarray:
    return trimesh.transformations.rotation_matrix(np.radians(angle_deg), axis)


def ccw(points) -> np.ndarray:
    """Polygon gegen den Uhrzeigersinn orientieren (CrossSection verlangt das)."""
    pts = np.asarray(points, float)
    x, y = pts[:, 0], pts[:, 1]
    area = 0.5 * np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y)
    return pts if area > 0 else pts[::-1].copy()


def poly(points, height, z0=0.0) -> Manifold:
    """Polygon (Nx2, XY) entlang +Z extrudieren, ab z0."""
    cs = CrossSection([ccw(points)])
    return Manifold.extrude(cs, height).translate((0, 0, z0))


def sphere(c, r, segs=SEGMENTS) -> Manifold:
    return Manifold.sphere(r, segs).translate(tuple(c))


def rounded_slot(x0, x1, y0, y1, r):
    """2D Langloch/Rechteck mit Radius r, als CrossSection."""
    r = min(r, (x1 - x0) / 2, (y1 - y0) / 2)
    hull = CrossSection.hull_points if hasattr(CrossSection, "hull_points") else None
    sq = CrossSection.square((x1 - x0 - 2 * r, y1 - y0 - 2 * r)).translate((x0 + r, y0 + r))
    return sq.offset(r, m3.JoinType.Round, 2.0, 24)


# --------------------------------------------------------------------------- #
# Lofts über Ringe
# --------------------------------------------------------------------------- #
def loft_rings(rings: np.ndarray, cap_start=True, cap_end=True) -> Manifold:
    """rings: (R, M, 3). Verbindet benachbarte Ringe, schließt die Enden mit Fächern."""
    rings = np.asarray(rings, float)
    R, M, _ = rings.shape
    verts = [rings.reshape(-1, 3)]
    faces = []
    idx = np.arange(R * M).reshape(R, M)
    for i in range(R - 1):
        for j in range(M):
            a, b = idx[i, j], idx[i, (j + 1) % M]
            c, d = idx[i + 1, j], idx[i + 1, (j + 1) % M]
            faces.append((a, b, c))
            faces.append((b, d, c))
    n = R * M
    if cap_start:
        verts.append(rings[0].mean(axis=0)[None])
        ci = n
        n += 1
        for j in range(M):
            faces.append((ci, idx[0, (j + 1) % M], idx[0, j]))
    if cap_end:
        verts.append(rings[-1].mean(axis=0)[None])
        ci = n
        n += 1
        for j in range(M):
            faces.append((ci, idx[-1, j], idx[-1, (j + 1) % M]))
    return from_arrays(np.vstack(verts), np.array(faces))


# --------------------------------------------------------------------------- #
# Transformationen
# --------------------------------------------------------------------------- #
def apply(m: Manifold, T: np.ndarray) -> Manifold:
    """4x4 Matrix anwenden (Spiegelungen werden von manifold korrekt behandelt)."""
    return m.transform(np.asarray(T, float)[:3, :])


def mirror_y(m: Manifold) -> Manifold:
    return m.mirror((0, 1, 0))


def translation(x=0, y=0, z=0) -> np.ndarray:
    T = np.eye(4)
    T[:3, 3] = (x, y, z)
    return T


def rot_y(deg, about=(0, 0, 0)) -> np.ndarray:
    R = rotation_matrix((0, 1, 0), deg)
    c = np.asarray(about, float)
    T = translation(*c) @ R @ translation(*(-c))
    return T


def rot_x(deg, about=(0, 0, 0)) -> np.ndarray:
    R = rotation_matrix((1, 0, 0), deg)
    c = np.asarray(about, float)
    return translation(*c) @ R @ translation(*(-c))


def rot_z(deg, about=(0, 0, 0)) -> np.ndarray:
    R = rotation_matrix((0, 0, 1), deg)
    c = np.asarray(about, float)
    return translation(*c) @ R @ translation(*(-c))


def bbox(m: Manifold):
    b = m.bounding_box()
    return np.array(b[:3]), np.array(b[3:])


def clean(m: Manifold, min_vol: float = 5.0) -> Manifold:
    """Entfernt Splitter-Komponenten (|Volumen| < min_vol mm³), z. B. aus deckungsgleichen Flächen.

    Arbeitet auf Netzebene, damit eingeschlossene Hohlräume (negative Schalen) erhalten bleiben.
    """
    tm = to_trimesh(m)
    comps = tm.split(only_watertight=False)
    if len(comps) <= 1:
        return m
    keep = [c for c in comps if abs(c.volume) >= min_vol or c.area > 200.0]
    if len(keep) == len(comps):
        return m
    verts, faces, off = [], [], 0
    for c in keep:
        verts.append(np.asarray(c.vertices))
        faces.append(np.asarray(c.faces) + off)
        off += len(c.vertices)
    mesh = m3.Mesh(vert_properties=np.vstack(verts).astype(np.float32),
                   tri_verts=np.vstack(faces).astype(np.uint32))
    out = Manifold(mesh)
    if out.status() != m3.Error.NoError:
        return m
    # Sicherheitsnetz: Bereinigung darf das Volumen nicht verändern
    if abs(out.volume() - m.volume()) > 0.002 * max(abs(m.volume()), 1.0):
        return m
    return out


def rot_from_to(a, b) -> np.ndarray:
    """4x4-Drehung, die Vektor a auf Vektor b dreht."""
    a = np.asarray(a, float) / np.linalg.norm(a)
    b = np.asarray(b, float) / np.linalg.norm(b)
    return trimesh.geometry.align_vectors(a, b)


def halfspace(point, normal, size=3000.0) -> Manifold:
    """Halbraum {p : (p - point) . normal <= 0} als großer Quader."""
    box_ = Manifold.cube((2 * size, 2 * size, size), False).translate((-size, -size, -size))   # z in [-size, 0]
    R = rot_from_to((0, 0, 1), normal)
    return apply(box_, translation(*point) @ R)


def clean_trimesh(tm: trimesh.Trimesh, min_vol: float = 5.0, min_area: float = 200.0) -> trimesh.Trimesh:
    """Entfernt Splitter-Komponenten (Doppelflächen mit Nullvolumen) aus einem Dreiecksnetz."""
    comps = tm.split(only_watertight=False)
    if len(comps) <= 1:
        return tm
    keep = [c for c in comps if abs(c.volume) >= min_vol or c.area > min_area]
    if len(keep) == len(comps):
        return tm
    verts, faces, off = [], [], 0
    for c in keep:
        verts.append(np.asarray(c.vertices))
        faces.append(np.asarray(c.faces) + off)
        off += len(c.vertices)
    return trimesh.Trimesh(np.vstack(verts), np.vstack(faces), process=False)


def solid_components(tm: trimesh.Trimesh):
    """(Festkörper-Komponenten, Hohlraum-Komponenten) eines Netzes; Splitter mit |V| < 1 mm³ werden ignoriert."""
    comps = tm.split(only_watertight=False)
    solids = [c for c in comps if c.volume > 1.0]
    voids = [c for c in comps if c.volume < -1.0]
    return solids, voids


def drop_slivers(m: Manifold, vmin: float = 1.0) -> Manifold:
    """Entfernt Splitter-Komponenten mit |V| < vmin (z. B. Null-Volumen-Flocken aus Booleschen Operationen)."""
    comps = m.decompose()
    if len(comps) <= 1 or all(abs(c.volume()) >= vmin for c in comps):
        return m
    out = Manifold.compose([c for c in comps if abs(c.volume()) >= vmin])
    return out if abs(out.volume() - m.volume()) <= 1e-3 * abs(m.volume()) + vmin else m


def drop_floating(m: Manifold) -> Manifold:
    """Behält nur den größten Festkörper (plus eingeschlossene Hohlräume); entfernt schwebende Reste."""
    m = drop_slivers(m)
    tm = to_trimesh(m)
    solids, voids = solid_components(tm)
    if len(solids) <= 1:
        return m
    main = max(solids, key=lambda c: c.volume)
    keep = [main] + voids
    verts, faces, off = [], [], 0
    for c in keep:
        verts.append(np.asarray(c.vertices))
        faces.append(np.asarray(c.faces) + off)
        off += len(c.vertices)
    out = Manifold(m3.Mesh(vert_properties=np.vstack(verts).astype(np.float32),
                           tri_verts=np.vstack(faces).astype(np.uint32)))
    removed = sum(c.volume for c in solids) - main.volume
    if out.status() != m3.Error.NoError or abs(out.volume() - (m.volume() - removed)) > 0.002 * abs(m.volume()):
        return m
    return out
