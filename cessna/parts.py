"""Bauteil-Container und Druckausrichtung."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from . import geom as g
from .params import BED, BED_MARGIN, DENSITY


@dataclass
class Part:
    name: str
    group: str
    mesh: g.Manifold                 # im lokalen Rahmen
    asm_T: np.ndarray = field(default_factory=lambda: np.eye(4))     # lokal -> Zusammenbau
    print_R: np.ndarray = field(default_factory=lambda: np.eye(4))   # lokal -> Druckrichtung (nur Drehung)
    qty: int = 1
    material: str = "LW-PLA"
    note: str = ""
    cg_override: tuple | None = None
    infill: float = 1.0              # Massefaktor bei Teilfüllung (Massivteile aus PETG/PLA)
    instances: list | None = None     # weitere Einbaulagen (lokal -> Zusammenbau), falls qty > 1

    def __post_init__(self):
        self.mesh = g.clean(self.mesh)

    # -- abgeleitet -------------------------------------------------------- #
    def print_mesh(self) -> g.Manifold:
        m = g.apply(self.mesh, self.print_R)
        lo, hi = g.bbox(m)
        # mittig auf dem Druckbett, Unterseite auf z = 0
        T = g.translation(-lo[0], -lo[1], -lo[2])
        return g.apply(m, T)

    def print_size(self):
        lo, hi = g.bbox(g.apply(self.mesh, self.print_R))
        return hi - lo

    def fits(self, bed=BED) -> bool:
        s = self.print_size()
        return bool(s[0] <= bed[0] - BED_MARGIN and s[1] <= bed[1] - BED_MARGIN and s[2] <= bed[2])

    def volume(self) -> float:
        return self.mesh.volume()

    def mass_g(self) -> float:
        return self.volume() / 1000.0 * DENSITY[self.material] * self.infill

    def asm_Ts(self):
        return self.instances if self.instances else [self.asm_T]

    def asm_mesh(self) -> g.Manifold:
        ms = [g.apply(self.mesh, T) for T in self.asm_Ts()]
        return g.union(ms) if len(ms) > 1 else ms[0]

    def asm_centroid(self) -> np.ndarray:
        """Volumenschwerpunkt im Zusammenbau (grob über Netz)."""
        tm = g.to_trimesh(self.asm_mesh())
        try:
            return np.asarray(tm.center_mass)
        except Exception:
            return np.asarray(tm.centroid)
