"""NACA-4-Ziffern-Profile als geschlossene Konturen (Einheitssehne)."""
from __future__ import annotations

import numpy as np

TE_THICKNESS = 0.0021   # relative Hinterkantendicke (Standardformel ohne Schließung)


def naca4(code: str, n: int = 56) -> np.ndarray:
    """Liefert Kontur (M,2) mit x in [0,1]: Oberseite HK->VK, dann Unterseite VK->HK.

    Ohne doppelten Punkt an der Nase; Hinterkante bleibt leicht geöffnet.
    """
    m = int(code[0]) / 100.0
    p = int(code[1]) / 10.0
    t = int(code[2:]) / 100.0
    beta = np.linspace(0, np.pi, n)
    x = 0.5 * (1 - np.cos(beta))                     # Cosinus-Verteilung
    yt = 5 * t * (0.2969 * np.sqrt(x) - 0.1260 * x - 0.3516 * x**2
                  + 0.2843 * x**3 - 0.1015 * x**4)
    if m == 0 or p == 0:
        yc = np.zeros_like(x)
        dyc = np.zeros_like(x)
    else:
        yc = np.where(x < p, m / p**2 * (2 * p * x - x**2),
                      m / (1 - p) ** 2 * ((1 - 2 * p) + 2 * p * x - x**2))
        dyc = np.where(x < p, 2 * m / p**2 * (p - x), 2 * m / (1 - p) ** 2 * (p - x))
    th = np.arctan(dyc)
    xu, yu = x - yt * np.sin(th), yc + yt * np.cos(th)
    xl, yl = x + yt * np.sin(th), yc - yt * np.cos(th)
    upper = np.column_stack([xu, yu])[::-1]           # HK -> VK
    lower = np.column_stack([xl, yl])[1:]             # VK -> HK (Nase nicht doppelt)
    return np.vstack([upper, lower])


def camber(code: str, x: np.ndarray) -> np.ndarray:
    m = int(code[0]) / 100.0
    p = int(code[1]) / 10.0
    if m == 0 or p == 0:
        return np.zeros_like(x)
    return np.where(x < p, m / p**2 * (2 * p * x - x**2),
                    m / (1 - p) ** 2 * ((1 - 2 * p) + 2 * p * x - x**2))


def thickness(code: str, x: np.ndarray) -> np.ndarray:
    """Volle relative Dicke an der Stelle x."""
    t = int(code[2:]) / 100.0
    return 2 * 5 * t * (0.2969 * np.sqrt(x) - 0.1260 * x - 0.3516 * x**2
                        + 0.2843 * x**3 - 0.1015 * x**4)


def naca4_flat(code: str, x_flat: float = 0.35, n: int = 56):
    """NACA-4-Ziffern-Profil mit geradem Unterseitenboden hinter x_flat (druckfreundlich).

    Rückgabe: (Kontur (M,2), Neigung der Bodenlinie in Grad). Die Bodenlinie verläuft
    vom Unterseitenpunkt bei x_flat zum unteren Hinterkantenpunkt.
    """
    pts = naca4(code, n)
    half = len(pts) // 2
    upper, lower = pts[:half], pts[half:]            # lower: Nase -> HK
    xs, zs = lower[:, 0], lower[:, 1]
    zf = np.interp(x_flat, xs, zs)
    te = lower[-1]
    keep = lower[xs <= x_flat]
    k = (te[1] - zf) / (te[0] - x_flat)
    new_lower = np.vstack([keep, [x_flat, zf], te[None]])
    # doppelte Punkte entfernen
    d = np.linalg.norm(np.diff(new_lower, axis=0), axis=1)
    new_lower = new_lower[np.concatenate([[True], d > 1e-6])]
    out = np.vstack([upper, new_lower])
    return out, float(np.degrees(np.arctan(k)))
