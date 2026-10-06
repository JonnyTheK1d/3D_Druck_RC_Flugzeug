"""Kleiner Z-Buffer-Renderer (orthografisch, numba) für Vorschaubilder ohne GPU."""
from __future__ import annotations

import numpy as np
from numba import njit
from PIL import Image

from . import geom as g

VIEWS = {
    # Blickrichtung (vom Objekt zur Kamera) und "oben"-Vektor
    "iso":    (np.array([-0.78, -0.55, 0.45]), np.array([0, 0, 1.0])),
    "iso2":   (np.array([0.78, 0.55, 0.45]), np.array([0, 0, 1.0])),
    "iso3":   (np.array([-0.55, 0.78, 0.40]), np.array([0, 0, 1.0])),
    "side":   (np.array([0, -1.0, 0]), np.array([0, 0, 1.0])),
    "top":    (np.array([0, 0, 1.0]), np.array([-1.0, 0, 0])),
    "front":  (np.array([-1.0, 0, 0]), np.array([0, 0, 1.0])),
    "bottom": (np.array([0, 0, -1.0]), np.array([-1.0, 0, 0])),
}


@njit(cache=True)
def _raster(px, depth, shade, rgb, W, H, img, zbuf):
    n = px.shape[0]
    for t in range(n):
        x0, y0 = px[t, 0, 0], px[t, 0, 1]
        x1, y1 = px[t, 1, 0], px[t, 1, 1]
        x2, y2 = px[t, 2, 0], px[t, 2, 1]
        minx = max(int(np.floor(min(x0, min(x1, x2)))), 0)
        maxx = min(int(np.ceil(max(x0, max(x1, x2)))), W - 1)
        miny = max(int(np.floor(min(y0, min(y1, y2)))), 0)
        maxy = min(int(np.ceil(max(y0, max(y1, y2)))), H - 1)
        den = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
        if abs(den) < 1e-12:
            continue
        for yy in range(miny, maxy + 1):
            for xx in range(minx, maxx + 1):
                cx, cy = xx + 0.5, yy + 0.5
                l0 = ((y1 - y2) * (cx - x2) + (x2 - x1) * (cy - y2)) / den
                l1 = ((y2 - y0) * (cx - x2) + (x0 - x2) * (cy - y2)) / den
                l2 = 1.0 - l0 - l1
                if l0 < -1e-4 or l1 < -1e-4 or l2 < -1e-4:
                    continue
                z = l0 * depth[t, 0] + l1 * depth[t, 1] + l2 * depth[t, 2]
                if z > zbuf[yy, xx]:
                    zbuf[yy, xx] = z
                    s = shade[t]
                    img[yy, xx, 0] = min(rgb[t, 0] * s, 255.0)
                    img[yy, xx, 1] = min(rgb[t, 1] * s, 255.0)
                    img[yy, xx, 2] = min(rgb[t, 2] * s, 255.0)


def _hex(c):
    c = c.lstrip("#")
    return np.array([int(c[i:i + 2], 16) for i in (0, 2, 4)], float)


def _basis(view, up):
    w = view / np.linalg.norm(view)
    u = np.cross(up, w)
    u /= np.linalg.norm(u)
    v = np.cross(w, u)
    return u, v, w


def render(items, path, view="iso", size=(1400, 900), title=None, ssaa=2,
           bg=(255, 255, 255), margin=0.05, light=(0.45, -0.35, 0.85), smooth=True):
    """items: Liste von (Manifold | trimesh, '#rrggbb'). Schreibt PNG."""
    vdir, up = VIEWS[view] if isinstance(view, str) else view
    u, v, w = _basis(vdir, up)
    Lg = np.asarray(light, float)
    Lg /= np.linalg.norm(Lg)
    # Licht in Weltkoordinaten relativ zur Kamera: Kopflicht + Seitenlicht
    key = (-u * 0.55 + v * 0.65 + w * 0.65)
    key /= np.linalg.norm(key)
    tris, cols, nrm = [], [], []
    for obj, color in items:
        tm = g.to_trimesh(obj) if hasattr(obj, "to_mesh") else obj
        V = np.asarray(tm.vertices, float)
        F = np.asarray(tm.faces)
        T = V[F]
        n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
        ln = np.linalg.norm(n, axis=1)
        ln[ln == 0] = 1
        n = n / ln[:, None]
        tris.append(T)
        nrm.append(n)
        cols.append(np.tile(_hex(color), (len(T), 1)))
    T = np.concatenate(tris)
    n = np.concatenate(nrm)
    rgb = np.concatenate(cols)
    P = np.stack([T @ u, T @ v], axis=-1)
    D = T @ w
    lo, hi = P.reshape(-1, 2).min(0), P.reshape(-1, 2).max(0)
    W0, H0 = size
    W, H = W0 * ssaa, H0 * ssaa
    scale = min(W / (hi[0] - lo[0]), H / (hi[1] - lo[1])) * (1 - 2 * margin)
    off = np.array([W, H]) / 2 - (lo + hi) / 2 * scale
    px = P * scale + off
    px[..., 1] = H - px[..., 1]
    facing = n @ w
    keep = facing > -0.05
    shade = 0.30 + 0.70 * (0.45 * np.clip(n @ key, 0, 1) + 0.55 * np.clip(facing, 0, 1) ** 0.8)
    img = np.empty((H, W, 3), np.float64)
    img[:] = np.array(bg, float)
    zbuf = np.full((H, W), -1e18)
    _raster(np.ascontiguousarray(px[keep]), np.ascontiguousarray(D[keep]),
            np.ascontiguousarray(shade[keep]), np.ascontiguousarray(rgb[keep]), W, H, img, zbuf)
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    if ssaa > 1:
        im = im.resize((W0, H0), Image.LANCZOS)
    if title:
        from PIL import ImageDraw, ImageFont
        d = ImageDraw.Draw(im)
        try:
            f = ImageFont.truetype("DejaVuSans.ttf", 24)
        except Exception:
            f = ImageFont.load_default()
        d.text((20, 14), title, fill=(40, 40, 40), font=f)
    im.save(path)
