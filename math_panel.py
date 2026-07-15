"""
Paso 5 — Panel Matemáticoooo
===============================================
Muestra en tiempo real las matrices del nodo seleccionado:
  - Matriz local
  - Matriz global
  - Matriz inversa
  - Verificación M·M⁻¹ ≈ I
  - Posición del pivote (antes y después de la transformación)
  - Descomposición (tx, ty, sx, sy, ángulo)
"""

import numpy as np
import pygame
from scene_graph import SceneNode
from math_engine import MathEngine


# Colores del panel
BG_COLOR     = (18, 18, 28)
TITLE_COLOR  = (130, 200, 255)
LABEL_COLOR  = (160, 160, 200)
VALUE_COLOR  = (220, 240, 200)
MATRIX_COLOR = (180, 255, 180)
WARN_COLOR   = (255, 180, 80)
SEP_COLOR    = (50, 55, 75)
ACCENT       = (80, 140, 255)


class MathPanel:
    """
    Panel matemático derecho (480×720 px).

    Parámetros
    ----------
    surface      : superficie de la ventana completa
    panel_rect   : pygame.Rect que define el área del panel dentro de la ventana
    """

    def __init__(self, surface: pygame.Surface, panel_rect: pygame.Rect):
        self.surface    = surface
        self.rect       = panel_rect
        self.selected: SceneNode | None = None

        pygame.font.init()
        self._font_title  = pygame.font.SysFont("monospace", 13, bold=True)
        self._font_label  = pygame.font.SysFont("monospace", 11, bold=True)
        self._font_value  = pygame.font.SysFont("monospace", 11)
        self._font_matrix = pygame.font.SysFont("monospace", 10)

    def select(self, node: SceneNode | None):
        """Establece el nodo cuyas matrices se mostrarán."""
        self.selected = node

    def draw(self):
        pygame.draw.rect(self.surface, BG_COLOR, self.rect)

        pygame.draw.line(
            self.surface,
            ACCENT,
            (self.rect.left, self.rect.top),
            (self.rect.left, self.rect.bottom),
            2
        )

        if self.selected is None:
            self._draw_text(
                "Sin nodo seleccionado",
                self.rect.left + 20,
                self.rect.top + 20,
                WARN_COLOR,
                self._font_label
            )
            return

        node = self.selected
        M = node.global_matrix

        # ==========================================================
        # EXTRACCIÓN ANALÍTICA
        # ==========================================================

        tx = M[0, 2]
        ty = M[1, 2]

        sx = np.linalg.norm(M[:2, 0])
        sy = np.linalg.norm(M[:2, 1])

        theta = np.degrees(np.arctan2(M[1, 0], M[0, 0]))

        T = np.array([
            [1, 0, tx],
            [0, 1, ty],
            [0, 0, 1]
        ])

        c = np.cos(np.radians(theta))
        s = np.sin(np.radians(theta))

        R = np.array([
            [c, -s, 0],
            [s,  c, 0],
            [0,  0, 1]
        ])

        S = np.array([
            [sx, 0, 0],
            [0, sy, 0],
            [0, 0, 1]
        ])

        # ==========================================================
        # MATRIZ INVERSA
        # ==========================================================

        try:
            M_inv = np.linalg.inv(M)
            V = np.round(np.dot(M, M_inv), 2)
        except np.linalg.LinAlgError:
            M_inv = None
            V = None
            #esta si es funcion de python, no es de nosotros pero sirve para verificar la inversa
            

        # ==========================================================
        # RENDER
        # ==========================================================

        x = self.rect.left + 14
        y = self.rect.top + 12

        y = self._section_title(
            f"NODO SELECCIONADO: {node.name}",
            x,
            y
        )

        # ==========================================================
        # MATRIZ GLOBAL
        # ==========================================================

        y = self._draw_separator(x, y)
        y = self._draw_label("MATRIZ GLOBAL (M)", x, y)

        y = self._draw_matrix(
            M,
            x + 10,
            y,
            MATRIX_COLOR
        )

        # ==========================================================
        # DESCOMPOSICIÓN
        # ==========================================================

        y = self._draw_separator(x, y)

        y = self._draw_text(
            "COMPOSICION ALGEBRAICA:  M = T * R * S",
            x,
            y,
            ACCENT,
            self._font_label
        )

        y = self._draw_label(
            "DESCOMPOSICION ANALITICA",
            x,
            y
        )

        # ---------------- T ----------------

        y = self._draw_label(
            "Traslacion (T)",
            x + 8,
            y
        )

        y = self._draw_matrix(
            T,
            x + 20,
            y,
            MATRIX_COLOR
        )

        y = self._draw_text(
            f"[X: {tx:.2f} , Y: {ty:.2f}]",
            x + 20,
            y,
            VALUE_COLOR,
            self._font_value
        )

        y += 4

        # ---------------- R ----------------

        small_font = pygame.font.SysFont("monospace", 10, bold=True)

        y = self._draw_text(
            "Rotacion (R)  [cos -sin 0 | sin cos 0 | 0 0 1]",
            x + 8,
            y,
            LABEL_COLOR,
            small_font
        )

        y = self._draw_matrix(
            R,
            x + 20,
            y,
            MATRIX_COLOR
        )

        y = self._draw_text(
            f"[Angulo: {theta:.2f}°]",
            x + 20,
            y,
            VALUE_COLOR,
            self._font_value
        )

        y += 4

        # ---------------- S ----------------

        y = self._draw_label(
            "Escala (S)",
            x + 8,
            y
        )

        y = self._draw_matrix(
            S,
            x + 20,
            y,
            MATRIX_COLOR
        )

        y = self._draw_text(
            f"[Escala X: {sx:.2f} , Escala Y: {sy:.2f}]",
            x + 20,
            y,
            VALUE_COLOR,
            self._font_value
        )

        # ==========================================================
        # MATRIZ INVERSA
        # ==========================================================

        y = self._draw_separator(x, y)

        y = self._draw_label(
            "MATRIZ INVERSA (M⁻¹)",
            x,
            y
        )

        if M_inv is None:
            y = self._draw_text(
                "Matriz singular",
                x + 20,
                y,
                WARN_COLOR,
                self._font_value
            )
        else:
            y = self._draw_matrix(
                M_inv,
                x + 10,
                y,
                (255, 220, 120)
            )

        # ==========================================================
        # VERIFICACIÓN
        # ==========================================================

        y = self._draw_separator(x, y)

        y = self._draw_label(
            "VERIFICACION   M · M⁻¹",
            x,
            y
        )

        if V is None:
            self._draw_text(
                "No existe inversa.",
                x + 20,
                y,
                WARN_COLOR,
                self._font_value
            )
        else:
            y = self._draw_matrix(
                V,
                x + 10,
                y,
                (120, 255, 120)
            )
            self._draw_text(
                "✓ Matriz Identidad",
                x + 20,
                y,
                (120, 255, 120),
                self._font_label
            )

    # ------------------------------------------------------------------ #
    #  Helpers de dibujado                                                #
    # ------------------------------------------------------------------ #

    def _draw_text(self, text, x, y, color, font) -> int:
        surf = font.render(text, True, color)
        self.surface.blit(surf, (x, y))
        return y + surf.get_height() + 2

    def _section_title(self, text, x, y) -> int:
        surf = self._font_title.render(text, True, TITLE_COLOR)
        self.surface.blit(surf, (x, y))
        pygame.draw.line(
            self.surface,
            ACCENT,
            (x, y + surf.get_height() + 1),
            (self.rect.right - 10, y + surf.get_height() + 1),
            1
        )
        return y + surf.get_height() + 6

    def _draw_label(self, text, x, y) -> int:
        return self._draw_text(text, x, y, LABEL_COLOR, self._font_label)

    def _draw_kv(self, key, value, x, y) -> int:
        line = f"  {key:<14}: {value}"
        return self._draw_text(line, x, y, VALUE_COLOR, self._font_value)

    def _draw_separator(self, x, y) -> int:
        pygame.draw.line(
            self.surface,
            SEP_COLOR,
            (x, y + 2),
            (self.rect.right - 10, y + 2),
            1
        )
        return y + 7

    def _draw_matrix(self, mat, x, y, color):
        """
        Dibuja una matriz 3x3 utilizando una fuente monoespaciada.
        """
        for fila in mat:
            texto = (
                f"[ "
                f"{fila[0]:7.2f} "
                f"{fila[1]:7.2f} "
                f"{fila[2]:7.2f} ]"
            )
            y = self._draw_text(
                texto,
                x,
                y,
                color,
                self._font_matrix
            )
        return y + 3