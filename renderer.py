"""
 Renderizador 
===============================================
  1. Lee la matriz global de cada SceneNode.
  2. Aplicar la matriz de proyección (pasa de espacio matemático al espacio Pygame). Acuerdense de que haay que invertir el eje Y
  3. Dibujar el sprite PNG respetando el pivote de dibujo.

NO modifica ninguna matriz. NO contiene lógica de juego.

Conversión de coordenadas
─────────────────────────
  Espacio matemático : (0,0) esquina inferior-izquierda del simulador; Y↑
  Espacio Pygame     : (0,0) esquina superior-izquierda de la ventana;  Y↓

Matriz de proyección P (afín 2-D):
    px =  mx  + WORLD_OFFSET_X
    py = (WORLD_H − my) + WORLD_OFFSET_Y        ← inversión Y

Pipeline de dibujado de sprite
───────────────────────────────
Los sprites tienen 800×800 px con el dibujo centrado en su propio pivote
de IMAGEN (pivot_img), expresado en píxeles del PNG original (Y↓ Pygame).

Para dibujar correctamente:

  1. De la matriz global extraemos:   sx, sy (escala), θ (rotación)
  2. Escalamos el PNG: new_size = (800·sx, 800·sy)
  3. Rotamos en sentido Pygame: angle_pygame = +θ_matemático
     (la proyección ya invierte Y, así que el signo de la rotación
      se conserva tal cual al pasar por P)
  4. El pivote de imagen escalado queda en:
         pivot_img_scaled = (pivot_img_x · sx,  pivot_img_y · sy)
     Tras rotar, necesitamos saber dónde quedó ese punto dentro del
     rect rotado.  Usamos la fórmula analítica de rotación 2-D alrededor
     del centro del rect escalado, y lo restamos al blit_pos.
  5. blit_pos = pivot_screen − rotated_pivot_offset
"""

import math
import pygame
import numpy as np
from math_engine import MathEngine
from scene_graph import SceneNode


# ── Dimensiones de interfaz (sincronizadas con main.py) ──────────────── #
WINDOW_W       = 1280
WINDOW_H       = 720
WORLD_W        = 800
WORLD_H        = 720
WORLD_OFFSET_X = 0
WORLD_OFFSET_Y = 0


import pygame

import pygame
import math

class Renderer:
    def __init__(self, surface: pygame.Surface):
        self.surface = surface

    def math_to_screen(self, mx, my):
        # Convierte de coordenadas matemáticas a coordenadas de pantalla Pygame
        return mx + WORLD_OFFSET_X, (WORLD_H - my) + WORLD_OFFSET_Y

    def draw_scene(self, world_node, draw_axes=False, **kwargs):
        # Inicia el dibujado recursivo aceptando draw_axes y cualquier otro argumento extra por seguridad
        self._draw_subtree(world_node, draw_axes=draw_axes, **kwargs)

    def _draw_subtree(self, node, draw_axes=False, **kwargs):
        # 1. Dibuja el nodo actual
        self._draw_node(node, draw_axes=draw_axes, **kwargs)
        # 2. Dibuja a todos sus hijos respetando la jerarquía de matrices
        for child in node.children:
            self._draw_subtree(child, draw_axes=draw_axes, **kwargs)

    def _draw_node(self, node, draw_axes=False, **kwargs):
        # 1. Obtener los valores reales de la matriz global calculados en la Capa 1
        decomp = node.get_decomposed()
        tx = decomp["tx"]
        ty = decomp["ty"]
        sx = decomp["sx"]
        sy = decomp["sy"]
        angle = decomp["angle_deg"]

        # 2. Convertir posición matemática (Y↑) a pantalla Pygame (Y↓)
        screen_x = tx + WORLD_OFFSET_X
        screen_y = (WORLD_H - ty) + WORLD_OFFSET_Y

        # --- PIPELINE DE RENDERIZADO DE SPRITES ---
        if hasattr(node, 'sprite') and node.sprite is not None:
            orig_w, orig_h = node.sprite.get_size()
            
            # A. Escalar la imagen (max 1 para evitar escalas de 0 que congelan Pygame)
            scaled_w = max(1, int(orig_w * sx))
            scaled_h = max(1, int(orig_h * sy))
            scaled_img = pygame.transform.scale(node.sprite, (scaled_w, scaled_h))

            # B. Extraer y escalar la coordenada del pivote del PNG
            if hasattr(node, 'pivot_img'):
                px_img, py_img = node.pivot_img
            else:
                px_img, py_img = orig_w / 2, orig_h / 2

            scaled_px = px_img * sx
            scaled_py = py_img * sy

            # C. Calcular el vector desde el centro de la imagen hasta el pivote excéntrico
            center_x = scaled_w / 2
            center_y = scaled_h / 2
            offset = pygame.Vector2(scaled_px - center_x, scaled_py - center_y)

            # D. Rotar el vector de desfase de acuerdo a la orientación del nodo
            offset_rotated = offset.rotate(-angle)

            # E. Rotar la imagen físicamente en Pygame
            rotated_img = pygame.transform.rotate(scaled_img, angle)
            rot_rect = rotated_img.get_rect()

            # F. Posicionar la caja contenedora compensando el pivote rotado
            rot_rect.center = (screen_x - offset_rotated.x, screen_y - offset_rotated.y)

            # G. Transferir los píxeles a la pantalla
            self.surface.blit(rotated_img, rot_rect.topleft)

        # --- FALLBACK A RECTÁNGULOS (Si un nodo no tiene textura asignada) ---
        else:
            w, h = getattr(node, 'size', (20, 20))
            sw, sh = max(1, int(w * sx)), max(1, int(h * sy))
            rect = pygame.Rect(0, 0, sw, sh)
            rect.center = (int(screen_x), int(screen_y))
            
            surf = pygame.Surface((sw, sh), pygame.SRCALPHA)
            surf.fill(getattr(node, 'color', (255, 255, 255)))
            
            rotated_surf = pygame.transform.rotate(surf, angle)
            rot_rect = rotated_surf.get_rect(center=rect.center)
            self.surface.blit(rotated_surf, rot_rect.topleft)

        # --- SISTEMA DE DEPURACIÓN VISUAL DE EJES (Modo 'D' activado) ---
        if draw_axes:
            rad = math.radians(angle)
            
            # Determinar longitud de las líneas guía basada en la escala del objeto
            axis_len_x = max(30, 40 * sx)
            axis_len_y = max(30, 40 * sy)

            # Eje X Local del objeto (Representado en Rojo)
            end_x_x = screen_x + axis_len_x * math.cos(rad)
            end_x_y = screen_y - axis_len_x * math.sin(rad)  # Resta por inversión de eje Y de Pygame
            pygame.draw.line(self.surface, (255, 60, 60), (int(screen_x), int(screen_y)), (int(end_x_x), int(end_x_y)), 2)

            # Eje Y Local del objeto (Representado en Verde)
            end_y_x = screen_x + axis_len_y * math.cos(rad + math.pi / 2)
            end_y_y = screen_y - axis_len_y * math.sin(rad + math.pi / 2)
            pygame.draw.line(self.surface, (60, 255, 60), (int(screen_x), int(screen_y)), (int(end_y_x), int(end_y_y)), 2)

            # Nodo / Centro de Rotación exacto (Representado en Azul)
            pygame.draw.circle(self.surface, (60, 60, 255), (int(screen_x), int(screen_y)), 4)
# ─────────────────────────────────────────────────────────────────────── #
#  Utilidad: cabeza de flecha                                             #
# ─────────────────────────────────────────────────────────────────────── #

def _draw_arrowhead(surface, start, end, color, size=6):
    dx = end[0] - start[0];  dy = end[1] - start[1]
    ln = math.hypot(dx, dy)
    if ln < 1e-6:
        return
    ux, uy = dx / ln, dy / ln
    lx = end[0] - size * ux + size * 0.5 * uy
    ly = end[1] - size * uy - size * 0.5 * ux
    rx = end[0] - size * ux - size * 0.5 * uy
    ry = end[1] - size * uy + size * 0.5 * ux
    pygame.draw.polygon(surface, color,
                        [end, (int(lx), int(ly)), (int(rx), int(ry))])