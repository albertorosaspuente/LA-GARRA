"""
Scene Graph
===================
SceneNode con jerarquía, matrices local/global y dos tipos de pivote:

  pivot      : (px, py) en coords LOCALES del mundo (Y↑)
               Punto de articulación matemático.  el renderer transforma
               este punto con M_global para obtener la posición en pantalla.

  pivot_img  : (px_img, py_img) en coords del PNG original (Y↓ Pygame).
               Indica qué pixel del PNG se alinea con `pivot` en pantalla.
               Se inicializa a (0,0) y se asigna desde main.py con los
               valores calibrados.
"""

import numpy as np
from math_engine import MathEngine


class SceneNode:
    def __init__(self, name: str, pivot=(0.0, 0.0),
                 color=(200, 200, 200), size=(60, 60)):
        self.name = name

        # jerarquía
        self.parent: "SceneNode | None" = None
        self.children: list["SceneNode"] = []

        # pivote matemático (espacio local, Y↑)
        self.pivot = np.array(pivot, dtype=float)

        # pivote de imagen PNG (espacio Pygame, Y↓) — calibrado por el DT
        self.pivot_img: tuple[float, float] = (0.0, 0.0)

        # visual debug
        self.color = color
        self.size  = size

        # parámetros de transformación local
        self._tx   = 0.0;  self._ty    = 0.0
        self._angle = 0.0
        self._sx   = 1.0;  self._sy    = 1.0
        self._shx  = 0.0;  self._shy   = 0.0

        # matrices
        self.local_matrix  = MathEngine.get_identity()
        self.global_matrix = MathEngine.get_identity()

        # sprite (pygame.Surface asignado desde main)
        self.sprite = None

        self._rebuild_local_matrix()

    # ── setters de transformación ──────────────────────────────────── #

    def set_translation(self, tx: float, ty: float):
        self._tx, self._ty = tx, ty
        self._rebuild_local_matrix()

    def set_rotation(self, angle_degrees: float):
        self._angle = angle_degrees
        self._rebuild_local_matrix()

    def set_scale(self, sx: float, sy: float):
        self._sx, self._sy = sx, sy
        self._rebuild_local_matrix()

    def set_shear(self, shx: float, shy: float):
        self._shx, self._shy = shx, shy
        self._rebuild_local_matrix()

    @property
    def translation(self): return (self._tx, self._ty)
    @property
    def rotation(self):    return self._angle
    @property
    def scale(self):       return (self._sx, self._sy)

    # ── jerarquía ─────────────────────────────────────────────────── #

    def add_child(self, child: "SceneNode"):
        if child.parent is not None:
            child.parent.remove_child(child)
        child.parent = self
        self.children.append(child)

    def remove_child(self, child: "SceneNode"):
        if child in self.children:
            self.children.remove(child)
            child.parent = None

    # ── matrices ──────────────────────────────────────────────────── #

    def _rebuild_local_matrix(self):
        T     = MathEngine.get_translation_matrix(self._tx, self._ty)
        R     = MathEngine.get_rotation_matrix(self._angle)
        S     = MathEngine.get_scale_matrix(self._sx, self._sy)
        Shear = MathEngine.get_shear_matrix(self._shx, self._shy)
        self.local_matrix = MathEngine.compose_matrices(T, R, S, Shear)

    def update(self):
        if self.parent is None:
            self.global_matrix = self.local_matrix.copy()
        else:
            self.global_matrix = np.dot(
                self.parent.global_matrix,
                self.local_matrix
            )
        for child in self.children:
            child.update()

    # ── utilidades ────────────────────────────────────────────────── #

    def get_world_position(self) -> np.ndarray:
        local_point = np.array([self.pivot[0], self.pivot[1], 1.0])
        return (self.global_matrix @ local_point)[:2]

    def get_inverse_matrix(self) -> np.ndarray:
        return MathEngine.get_inverse(self.global_matrix)

    def verify_inverse(self) -> np.ndarray:
        return self.global_matrix @ self.get_inverse_matrix()

    def get_decomposed(self) -> dict:
        m  = self.global_matrix
        tx = m[0, 2];  ty = m[1, 2]
        sx = float(np.linalg.norm(m[:2, 0]))
        sy = float(np.linalg.norm(m[:2, 1]))
        angle_rad = float(np.arctan2(m[1, 0], m[0, 0]))
        return {"tx": tx, "ty": ty, "sx": sx, "sy": sy,
                "angle_deg": float(np.degrees(angle_rad))}

    def __repr__(self):
        return (f"<SceneNode '{self.name}' "
                f"pos=({self._tx:.1f},{self._ty:.1f}) "
                f"rot={self._angle:.1f}°>")


class WorldNode(SceneNode):
    """Nodo raíz — siempre identidad."""
    def __init__(self):
        super().__init__(name="World", color=(0, 0, 0), size=(0, 0))

    def _rebuild_local_matrix(self):
        self.local_matrix = MathEngine.get_identity()