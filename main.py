"""
PROYECTO GARRA — Version finalisisisisima
=========================================================
Ventana 1280×720:
  Simulador  800×720  izquierda   (coords matemáticas Y↑)
  Panel Mat  480×720  derecha

Controles
─────────
  ←  /  →       Traslación en X del brazo
  ↑  /  ↓       Escala del brazo (profundidad Z simulada)
  ESPACIO        Abrir / Cerrar pinzas
                   - Al CERRAR: intenta capturar caja si cumple criterios
                   - Al ABRIR:  suelta la caja capturada (si hay alguna)
  R              Iniciar secuencia de retorno a "Home" (con caja capturada)
  TAB            Cicla nodo seleccionado en el panel
  Click izq      Selecciona nodo más cercano
  D              Activa/desactiva ejes y etiquetas debug
  ESC            Salir

version 2 se regresa automatico a Home y suelta en "canasta"
─────────────────────────────────────────────────────
  Estado RETORNANDO:
    - Se activa con tecla R (solo si hay caja capturada Y pinzas cerradas).
    - Bloquea los controles de flechas del jugador.
    - LERP lineal (velocidad constante por frame) sobre brazo_tx y brazo_scale
      hacia BRAZO_INIT_X y BRAZO_INIT_SCALE respectivamente.
    - Al alcanzar Home (dentro de tolerancia), abre pinzas, suelta la caja
      (re-parenting al mundo con su posición global actual), y vuelve a IDLE.

Animacion de Caída Matricial con las cajitas
──────────────────────────────────────────────────────
  cajas_cayendo: list[SceneNode]
    - Al soltar la caja en Home, se añade a esta lista en lugar de quedar estática.
    - Cada frame, se reconstruye su M_local = T(tx, ty') · R(θ') · S(sx', sy')
      con los siguientes incrementos:
        · ty  -= 350 px/s   → cae hacia Y=0 (gravedad matemática)
        · θ   += 180 °/s    → rotación continua sobre su propio centro
        · sx  -= 0.25/s     → escala reduce en X (se "hunde" en la canasta)
        · sy  -= 0.25/s     → escala reduce en Y
    - Condición de destrucción: sx <= 0.0 O ty <= 0.0
      → se remueve del Mundo y de cajas_cayendo (para liberar memoria del Scene Graph).

  Carga de fondo (fondo.png):
    - Se busca "fondo.png" en assets/. Si no existe, el fondo es la cuadrícula
      de siempre (graceful degradation).
    - Se dibuja ANTES del Scene Graph para que quede detrás de todo.

Pivotes calibrados con el script de calibrar pivotessss:
  brazo.png     pivot_img = (414, 461)   — punto de dibujo: articulación brazo
  pinza_izq.png pivot_img = (622, 734)   — bisagra izq (Y↓ PNG)
  pinza_der.png pivot_img = (145, 734)   — bisagra der (Y↓ PNG)
  caja.png      pivot_img = (406, 411)   — centro de la caja

Traslaciones locales calibradas:
  PinzaIzq respecto al brazo: tx = -61,  ty = -364
  PinzaDer respecto al brazo: tx =  59,  ty = -364
"""

import sys
import os
import math
import numpy as np
import pygame

from math_engine import MathEngine
from scene_graph import WorldNode, SceneNode
from renderer    import Renderer, WORLD_W, WORLD_H
from math_panel  import MathPanel


# ─────────────────────────────────────────────────────────────────── #
#  Constantes                                                         #
# ─────────────────────────────────────────────────────────────────── #
WINDOW_W  = 1280
WINDOW_H  = 720
PANEL_W   = 480
FPS       = 60

# Velocidades de control
MOVE_SPEED  = 180.0    # px/s en X
SCALE_SPEED = 0.45     # factor/s para escala Z

# ── Escala de referencia del primer plano (cajas) ────────────────── #
ESCALA_FRENTE = 0.15            # escala base de las cajas — NO tocar porque ahora si quedo 

# Límites originales del brazo
BRAZO_X_MIN     = 60.0
BRAZO_X_MAX     = 740.0
BRAZO_SCALE_MIN = 0.20
BRAZO_SCALE_MAX = 0.625

# Estado inicial del brazo — "Home": fondo izquierdo
BRAZO_INIT_X     = BRAZO_X_MIN
BRAZO_INIT_Y     = 600.0
BRAZO_INIT_SCALE = BRAZO_SCALE_MIN

# Ángulos de pinzas
PINZA_ABIERTA_IZQ  =  0.0
PINZA_CERRADA_IZQ  =  28.0
PINZA_ABIERTA_DER  =  0.0
PINZA_CERRADA_DER  = -28.0

# ── OFFSET_PINZAS_Y (rev.5) ──────────────────────────────────────── #
OFFSET_PINZAS_Y_FACTOR = 724.0  # dist en px PNG: punta(790) − pivot_img.y(66)

# ── Fase 5: parámetros de captura ─────────────────────────────────── #
CAPTURE_DIST_MAX   = 50.0
CAPTURE_SCALE_TOL  = 0.05

CAJA_ANCHOR_TX = 0.0
CAJA_ANCHOR_TY = -364.0 - (OFFSET_PINZAS_Y_FACTOR * 0.5)  # = −364 − 362 = −726.0

# ── parámetros del retorno automático con r ────────────────────── #
RETURN_MOVE_SPEED  = 220.0   # px/s en X durante el retorno
RETURN_SCALE_SPEED = 0.55    # factor/s de escala durante el retorno

RETURN_X_TOL     = 2.0        # px
RETURN_SCALE_TOL = 0.005

# ── Secuencia de caída ──────────────────── #
# Velocidad de caída en Y (espacio matemático Y↑ → negativo = hacia abajo)
CAIDA_VEL_Y     = -350.0   # px/s — cae hacia Y=0 (suelo matemático)
# Velocidad de rotación continua mientras cae
CAIDA_VEL_ROT   =  180.0   # grados/s
# Tasa de reducción de escala (efecto de "hundirse" en la canasta)
CAIDA_VEL_SCALE =   -0.25  # 1/s  → en ~0.6 s pasa de 0.15 a 0.0

# ── Máquina de estados ────────────────────────────────────────────── #
STATE_IDLE       = "IDLE"
STATE_RETORNANDO = "RETORNANDO"

# Colores
BG_SIM   = (12, 14, 22)


# ─────────────────────────────────────────────────────────────────── #
#  Carga de sprites                                                   #
# ─────────────────────────────────────────────────────────────────── #

def load_sprites(asset_dir: str) -> dict:
    sprites: dict = {}
    files = {
        "brazo":      "brazo.png",
        "pinza_izq":  "pinza_izq.png",
        "pinza_der":  "pinza_der.png",
        "caja":       "caja.png",
    }
    for key, fname in files.items():
        path = os.path.join(asset_dir, fname)
        if os.path.exists(path):
            surf = pygame.image.load(path).convert_alpha()
            sprites[key] = surf
            print(f"  ✓  {fname}  ({surf.get_width()}×{surf.get_height()})")
        else:
            sprites[key] = None
            print(f"  ⚠  {fname} no encontrado — usando rect debug")
    return sprites


def load_background(asset_dir: str) -> pygame.Surface | None:
    """
    Carga fondo.png (800×720) desde assets/.
    Retorna None si el archivo no existe — la cuadrícula se usa como fallback.
    """
    path = os.path.join(asset_dir, "fondo.png")
    if os.path.exists(path):
        surf = pygame.image.load(path).convert()
        if surf.get_size() != (WORLD_W, WINDOW_H):
            surf = pygame.transform.scale(surf, (WORLD_W, WINDOW_H))
        print(f"  ✓  fondo.png cargado ({surf.get_width()}×{surf.get_height()})")
        return surf
    else:
        print("  ⚠  fondo.png no encontrado — usando cuadrícula de debug")
        return None


# ─────────────────────────────────────────────────────────────────── #
#  Construcción del Scene Graph                                       #
# ─────────────────────────────────────────────────────────────────── #

def build_scene(sprites: dict) -> tuple:
    world = WorldNode()

    # ── 1. Cajas — Un solo plano frontal ──────────────────────────── #
    CAJA_SCALE = ESCALA_FRENTE   # 0.15 — NO tocar

    _s_pinza_global  = 0.5 * BRAZO_SCALE_MAX
    _center_sprite   = 800.0 * _s_pinza_global / 2
    _ty_bisagra      = BRAZO_INIT_Y + (-364.0) * BRAZO_SCALE_MAX
    _screen_y_bisag  = WORLD_H - _ty_bisagra
    _offset_y_rend   = 66.0 * _s_pinza_global - _center_sprite
    _rot_center_y    = _screen_y_bisag - _offset_y_rend
    _punta_en_sprite = 790.0 * _s_pinza_global
    _screen_y_punta  = (_rot_center_y - _center_sprite) + _punta_en_sprite
    CAJA_Y           = WORLD_H - _screen_y_punta

    caja_cfg = [
        {"name": "Caja1", "tx": 200, "rot":  6},
        {"name": "Caja2", "tx": 400, "rot": -5},
        {"name": "Caja3", "tx": 600, "rot": 10},
    ]
    cajas: list[SceneNode] = []
    for cfg in caja_cfg:
        c = SceneNode(name=cfg["name"], pivot=(0, 0), color=(210, 160, 50), size=(80, 80))
        c.pivot_img = (406, 389)   # Y invertida: 800 - 411 = 389
        c.sprite    = sprites["caja"]
        c.set_translation(cfg["tx"], CAJA_Y)
        c.set_scale(CAJA_SCALE, CAJA_SCALE)
        c.set_rotation(cfg["rot"])
        world.add_child(c)
        cajas.append(c)

    # ── 2. Brazo y Pinzas ──────────────────────────────────────────── #
    brazo = SceneNode(name="Brazo", pivot=(0, 0), color=(70, 130, 200), size=(80, 180))
    brazo.pivot_img = (414, 339)   # Y invertida: 800 - 461 = 339
    brazo.sprite    = sprites["brazo"]
    brazo.set_translation(BRAZO_INIT_X, BRAZO_INIT_Y)
    brazo.set_scale(BRAZO_INIT_SCALE, BRAZO_INIT_SCALE)

    pinza_izq = SceneNode(name="PinzaIzq", pivot=(0, 0), color=(100, 180, 100), size=(50, 80))
    pinza_izq.pivot_img = (622, 66)   # Y invertida: 800 - 734 = 66
    pinza_izq.sprite    = sprites["pinza_izq"]
    pinza_izq.set_translation(-61, -364)
    pinza_izq.set_scale(0.5, 0.5)
    pinza_izq.set_rotation(PINZA_ABIERTA_IZQ)

    pinza_der = SceneNode(name="PinzaDer", pivot=(0, 0), color=(180, 100, 100), size=(50, 80))
    pinza_der.pivot_img = (145, 66)   # Y invertida: 800 - 734 = 66
    pinza_der.sprite    = sprites["pinza_der"]
    pinza_der.set_translation(59, -364)
    pinza_der.set_scale(0.5, 0.5)
    pinza_der.set_rotation(PINZA_ABIERTA_DER)

    brazo.add_child(pinza_izq)
    brazo.add_child(pinza_der)
    world.add_child(brazo)

    world.update()
    return world, brazo, pinza_izq, pinza_der, cajas


# ─────────────────────────────────────────────────────────────────── #
#  Fase 5 — Lógica de colisión y re-parenting                        #
# ─────────────────────────────────────────────────────────────────── #

def _get_global_position(node: SceneNode) -> np.ndarray:
    m = node.global_matrix
    return np.array([m[0, 2], m[1, 2]])


def _get_global_scale_x(node: SceneNode) -> float:
    m = node.global_matrix
    return float(np.linalg.norm(m[:2, 0]))


def _get_pinzas_tip(pinza_izq: SceneNode, pinza_der: SceneNode) -> np.ndarray:
    p_l = _get_global_position(pinza_izq)
    p_r = _get_global_position(pinza_der)
    mid = (p_l + p_r) / 2.0
    s_pinza = _get_global_scale_x(pinza_izq)
    tip_y_offset = OFFSET_PINZAS_Y_FACTOR * s_pinza
    return np.array([mid[0], mid[1] - tip_y_offset])


def intentar_captura(
    world: WorldNode,
    brazo: SceneNode,
    pinza_izq: SceneNode,
    pinza_der: SceneNode,
    cajas: list[SceneNode]
) -> SceneNode | None:
    world.update()

    pt      = _get_pinzas_tip(pinza_izq, pinza_der)
    s_brazo = _get_global_scale_x(brazo)

    rango_brazo = BRAZO_SCALE_MAX - BRAZO_SCALE_MIN
    if rango_brazo > 1e-6:
        t_brazo = (s_brazo - BRAZO_SCALE_MIN) / rango_brazo
    else:
        t_brazo = 1.0
    t_brazo = max(0.0, min(1.0, t_brazo))

    for caja in cajas:
        if caja.parent is not world:
            continue

        p_caja = _get_global_position(caja)
        s_caja = _get_global_scale_x(caja)

        dist = MathEngine.get_euclidean_distance(pt.tolist(), p_caja.tolist())
        if dist >= CAPTURE_DIST_MAX:
            continue

        t_caja = 1.0

        if abs(t_brazo - t_caja) >= CAPTURE_SCALE_TOL:
            continue

        if s_brazo > 1e-6:
            s_rel = s_caja / s_brazo
        else:
            s_rel = 1.0

        world.remove_child(caja)
        brazo.add_child(caja)

        caja.set_translation(CAJA_ANCHOR_TX, CAJA_ANCHOR_TY)
        caja.set_rotation(0.0)
        caja.set_scale(s_rel, s_rel)

        print(f"  [Fase5 rev.4] CAPTURA: {caja.name}  "
              f"dist={dist:.1f}  tip=({pt[0]:.1f},{pt[1]:.1f})  "
              f"t_brazo={t_brazo:.3f}  s_rel={s_rel:.4f}")
        return caja

    return None


def liberar_caja(
    world: WorldNode,
    brazo: SceneNode,
    caja_capturada: SceneNode
) -> None:
    """
    Suelta la caja y la devuelve al Mundo conservando su posición global actual.
    Usado tanto en ESPACIO (soltar manual) como al final del retorno automático.
    """
    m_global_actual = caja_capturada.global_matrix.copy()

    brazo.remove_child(caja_capturada)
    world.add_child(caja_capturada)

    tx  = float(m_global_actual[0, 2])
    ty  = float(m_global_actual[1, 2])
    sx  = float(np.linalg.norm(m_global_actual[:2, 0]))
    sy  = float(np.linalg.norm(m_global_actual[:2, 1]))
    ang = float(np.degrees(np.arctan2(m_global_actual[1, 0], m_global_actual[0, 0])))

    caja_capturada.set_translation(tx, ty)
    caja_capturada.set_scale(sx, sy)
    caja_capturada.set_rotation(ang)

    print(f"  [Fase5] LIBERACIÓN: {caja_capturada.name}  "
          f"pos=({tx:.1f}, {ty:.1f})  s=({sx:.4f}, {sy:.4f})  rot={ang:.2f}°")


# ─────────────────────────────────────────────────────────────────── #
#  Paso 2 — Retorno automático                                        #
# ─────────────────────────────────────────────────────────────────── #

def update_retorno(brazo_tx: float, brazo_scale: float, dt: float) -> tuple[float, float, bool]:
    """
    Avanza brazo_tx y brazo_scale un paso de LERP lineal hacia Home.
    Devuelve: (nuevo_tx, nueva_scale, llegó_a_home)
    """
    target_tx    = BRAZO_INIT_X
    target_scale = BRAZO_INIT_SCALE

    dx = target_tx - brazo_tx
    step_x = RETURN_MOVE_SPEED * dt
    if abs(dx) <= step_x:
        brazo_tx = target_tx
    else:
        brazo_tx += math.copysign(step_x, dx)

    ds = target_scale - brazo_scale
    step_s = RETURN_SCALE_SPEED * dt
    if abs(ds) <= step_s:
        brazo_scale = target_scale
    else:
        brazo_scale += math.copysign(step_s, ds)

    llegó = (
        abs(brazo_tx    - target_tx)    <= RETURN_X_TOL and
        abs(brazo_scale - target_scale) <= RETURN_SCALE_TOL
    )

    return brazo_tx, brazo_scale, llegó


# ─────────────────────────────────────────────────────────────────── #
#  Paso 3 — Secuencia de Caída Matricial (Drop Sequence)             #
# ─────────────────────────────────────────────────────────────────── #

def update_cajas_cayendo(
    world: WorldNode,
    cajas_cayendo: list[SceneNode],
    dt: float
) -> None:
    """
    Actualiza la animación de caída de todas las cajas en 'cajas_cayendo'.

    Por cada caja, extrae los componentes de su M_local actual y reconstruye
    la matriz incrementando ty, θ y reduciendo sx/sy, siguiendo estrictamente:

        M_local = T(tx, ty') · R(θ') · S(sx', sy')

    Las cajas que cumplan la condición de destrucción (sx ≤ 0 o ty ≤ 0) son
    removidas del Mundo y de la lista — liberando su nodo del Scene Graph.

    Parámetrosssssssss

    world         : WorldNode raíz del Scene Graph
    cajas_cayendo : lista mutable de SceneNode en animación de caída
    dt            : delta de tiempo en segundos del frame actual
    """
    # Iteramos en copia para poder modificar la lista original sin errores
    for caja in list(cajas_cayendo):

        # ── 1. Extraer componentes actuales de la M_local ───────────
        m = caja.local_matrix          # matriz 3×3 del nodo (espacio local)

        tx      = float(m[0, 2])       # traslación X — sin cambios horizontales
        ty      = float(m[1, 2])       # traslación Y — baja cada frame (caída)

        # Escala: norma euclidiana de los vectores-columna de la submatriz 2×2
        sx = float(np.linalg.norm(m[:2, 0]))   # escala en X
        sy = float(np.linalg.norm(m[:2, 1]))   # escala en Y

        # Ángulo de rotación actual (en grados) extraído de la primera columna
        ang_rad = math.atan2(float(m[1, 0]), float(m[0, 0]))
        ang_deg = math.degrees(ang_rad)

        # ── 2. Calcular nuevos valores incrementales ─────────────────
        # Gravedad: Y decrece (el objeto cae hacia el suelo matemático Y=0)
        new_ty  = ty  + (CAIDA_VEL_Y     * dt)

        # Rotación: gira continuamente sobre su propio pivote
        new_ang = ang_deg + (CAIDA_VEL_ROT   * dt)

        # Escala: se reduce simulando que "entra" en la canasta (perspectiva Z)
        new_sx  = max(0.0, sx + (CAIDA_VEL_SCALE * dt))
        new_sy  = max(0.0, sy + (CAIDA_VEL_SCALE * dt))

        # ── 3. Condición de destrucción ──────────────────────────────
        # La caja se considera "recogida" si se volvió invisible (escala ≈ 0)
        # o si cayó por debajo del suelo matemático que pusimos (ty ≤ 0).
        if new_sx <= 0.0 or new_ty <= 0.0:
            # Remover del Scene Graph y de la lista de animación
            if caja.parent is world:
                world.remove_child(caja)
            cajas_cayendo.remove(caja)
            print(f"  [Paso3] DESTRUIDA: {caja.name}  "
                  f"(sx={new_sx:.4f}  ty={new_ty:.1f}) — recolectada en canasta ✓")
            continue   # saltar al siguiente nodo

        # ── 4. Reconstruir M_local = T(tx, ty') · R(θ') · S(sx', sy') ──
        # Llamamos directamente a los setters del SceneNode para que el motor
        # matemático componga la matriz homogénea de forma explícita.
        caja.set_translation(tx, new_ty)
        caja.set_scale(new_sx, new_sy)
        caja.set_rotation(new_ang)


# ─────────────────────────────────────────────────────────────────── #
#  Selección por clic                                                 #
# ─────────────────────────────────────────────────────────────────── #

def pick_node(mouse_pos, nodes, renderer, radius=50):
    mx, my = mouse_pos
    best, best_dist = None, float("inf")
    for node in nodes:
        wp    = node.get_world_position()
        sx,sy = renderer.math_to_screen(wp[0], wp[1])
        d     = math.hypot(mx - sx, my - sy)
        if d < radius and d < best_dist:
            best_dist = d
            best      = node
    return best


# ─────────────────────────────────────────────────────────────────── #
#  Fondo y cuadrícula                                                 #
# ─────────────────────────────────────────────────────────────────── #

def draw_background(surface: pygame.Surface, renderer: "Renderer",
                    bg_surface: pygame.Surface | None):
    if bg_surface is not None:
        surface.blit(bg_surface, (0, 0))
    else:
        pygame.draw.rect(surface, BG_SIM, pygame.Rect(0, 0, WORLD_W, WINDOW_H))

        grid_c = (24, 29, 44)
        font   = pygame.font.SysFont("monospace", 9)
        lbl_c  = (45, 55, 82)

        for x in range(0, WORLD_W + 1, 100):
            sx, _ = renderer.math_to_screen(x, 0)
            pygame.draw.line(surface, grid_c, (sx, 0), (sx, WINDOW_H))
            surface.blit(font.render(str(x), True, lbl_c), (sx + 2, WINDOW_H - 16))

        for y in range(0, WORLD_H + 1, 100):
            _, sy = renderer.math_to_screen(0, y)
            pygame.draw.line(surface, grid_c, (0, sy), (WORLD_W, sy))
            surface.blit(font.render(str(y), True, lbl_c), (4, sy - 10))

        ax_c = (38, 50, 75)
        ox, oy = renderer.math_to_screen(0, 0)
        pygame.draw.line(surface, ax_c, (ox, 0),  (ox, WINDOW_H))
        pygame.draw.line(surface, ax_c, (0,  oy), (WORLD_W, oy))


# ─────────────────────────────────────────────────────────────────── #
#  HUD de controles                                                   #
# ─────────────────────────────────────────────────────────────────── #

def draw_hud(surface, selected, idx, total, pinzas_cerradas, debug,
             caja_capturada, estado_maquina: str, cajas_cayendo: list):
    font   = pygame.font.SysFont("monospace", 11)
    c      = (60, 85, 130)
    c_warn = (255, 200, 60)
    c_ret  = (100, 220, 255)
    c_drop = (180, 120, 255)   # color para indicar cajas en animación de caída

    estado_pinzas = "CERRADAS" if pinzas_cerradas else "ABIERTAS"
    dbg           = "ON" if debug else "OFF"

    lines = [
        (f"← →  Mover brazo en X",                        c),
        (f"↑ ↓  Profundidad (escala)",                    c),
        (f"SPC  Pinzas [{estado_pinzas}]",                c),
        (f"R    Retornar a Home",                         c),
        (f"TAB  Nodo [{idx+1}/{total}]: {selected.name if selected else '—'}", c),
        (f"D    Debug ejes [{dbg}]",                      c),
        (f"ESC  Salir",                                   c),
    ]

    if estado_maquina == STATE_RETORNANDO:
        lines.append((f"↩ RETORNANDO A HOME...", c_ret))
    elif caja_capturada is not None:
        lines.append((f"★ CAPTURADA: {caja_capturada.name}  [R] para entregar", c_warn))
    else:
        lines.append((f"○ Sin caja capturada", c))

    # Indicador del Paso 3: cajas en animación de caída
    if cajas_cayendo:
        nombres = ", ".join(cj.name for cj in cajas_cayendo)
        lines.append((f"↓ CAYENDO → canasta: {nombres}", c_drop))

    for i, (ln, color) in enumerate(lines):
        surface.blit(font.render(ln, True, color), (10, 10 + i * 14))


# ─────────────────────────────────────────────────────────────────── #
#  Bucle principal                                                    #
# ─────────────────────────────────────────────────────────────────── #

def main():
    pygame.init()
    pygame.display.set_caption(
        "Simulador Garra — Motor de Transformaciones Lineales [Paso 3]")

    screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
    clock  = pygame.time.Clock()

    asset_dir = os.path.join(os.path.dirname(__file__), "assets")
    if not os.path.isdir(asset_dir):
        asset_dir = os.path.dirname(__file__)

    print(f"\nBuscando sprites en: {asset_dir}")
    sprites    = load_sprites(asset_dir)
    bg_surface = load_background(asset_dir)

    panel_rect = pygame.Rect(WORLD_W, 0, PANEL_W, WINDOW_H)
    renderer   = Renderer(screen)
    panel      = MathPanel(screen, panel_rect)

    world, brazo, pinza_izq, pinza_der, cajas = build_scene(sprites)
    all_nodes  = [brazo, pinza_izq, pinza_der] + cajas

    selected_idx    = 0
    selected        = all_nodes[0]
    pinzas_cerradas = False
    debug_axes      = True

    caja_capturada: SceneNode | None = None

    # Esta lista es el corazón de la secuencia de como las cajitas caen (OJO AL PIOJOOO).
    # Cuando una caja llega a Home y se suelta, se añade aquí.
    # update_cajas_cayendo() la consume frame a frame hasta destruirla.
    cajas_cayendo: list[SceneNode] = []

    # ── Máquina de estados ──────────────────────────────────────────
    estado_maquina: str = STATE_IDLE

    panel.select(selected)

    brazo_tx    = BRAZO_INIT_X
    brazo_scale = BRAZO_INIT_SCALE

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0

        # ── Eventos ─────────────────────────────────────────────────
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

                elif event.key == pygame.K_TAB:
                    selected_idx = (selected_idx + 1) % len(all_nodes)
                    selected     = all_nodes[selected_idx]
                    panel.select(selected)

                # ── ESPACIO: abrir/cerrar pinzas (solo en IDLE) ─────
                elif event.key == pygame.K_SPACE and estado_maquina == STATE_IDLE:
                    pinzas_cerradas = not pinzas_cerradas

                    if pinzas_cerradas:
                        pinza_izq.set_scale(0.5, 0.5)
                        pinza_izq.set_rotation(PINZA_CERRADA_IZQ)
                        pinza_der.set_scale(0.5, 0.5)
                        pinza_der.set_rotation(PINZA_CERRADA_DER)

                        world.update()

                        if caja_capturada is None:
                            caja_capturada = intentar_captura(
                                world, brazo, pinza_izq, pinza_der, cajas
                            )

                    else:
                        pinza_izq.set_scale(0.5, 0.5)
                        pinza_izq.set_rotation(PINZA_ABIERTA_IZQ)
                        pinza_der.set_scale(0.5, 0.5)
                        pinza_der.set_rotation(PINZA_ABIERTA_DER)

                        if caja_capturada is not None:
                            world.update()
                            liberar_caja(world, brazo, caja_capturada)
                            caja_capturada = None

                # ── R: iniciar retorno a Home ────────────────────────
                elif event.key == pygame.K_r:
                    if estado_maquina == STATE_IDLE and caja_capturada is not None:
                        estado_maquina = STATE_RETORNANDO
                        print("  [Paso2] RETORNO iniciado → Home")

                elif event.key == pygame.K_d:
                    debug_axes = not debug_axes

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if event.pos[0] < WORLD_W:
                    picked = pick_node(event.pos, all_nodes, renderer)
                    if picked:
                        selected     = picked
                        selected_idx = all_nodes.index(picked)
                        panel.select(selected)

        # ── Update de movimiento ─────────────────────────────────────
        if estado_maquina == STATE_IDLE:
            keys = pygame.key.get_pressed()

            if keys[pygame.K_LEFT]:
                brazo_tx = max(BRAZO_X_MIN, brazo_tx - MOVE_SPEED * dt)

            if keys[pygame.K_RIGHT]:
                brazo_tx = min(BRAZO_X_MAX, brazo_tx + MOVE_SPEED * dt)

            if keys[pygame.K_UP]:
                brazo_scale = min(BRAZO_SCALE_MAX,
                                  brazo_scale + SCALE_SPEED * dt)

            if keys[pygame.K_DOWN]:
                brazo_scale = max(BRAZO_SCALE_MIN,
                                  brazo_scale - SCALE_SPEED * dt)

        elif estado_maquina == STATE_RETORNANDO:
            # ── Paso 2: Animación LERP hacia Home ───────────────────
            brazo_tx, brazo_scale, llegó = update_retorno(brazo_tx, brazo_scale, dt)

            if llegó:
                print("  [Paso2] Home alcanzado — soltando caja")

                # 1. Abrir pinzas
                pinzas_cerradas = False
                pinza_izq.set_scale(0.5, 0.5)
                pinza_izq.set_rotation(PINZA_ABIERTA_IZQ)
                pinza_der.set_scale(0.5, 0.5)
                pinza_der.set_rotation(PINZA_ABIERTA_DER)

                # 2. Actualizar matrices antes de leer posición global de la caja
                brazo.set_translation(brazo_tx, BRAZO_INIT_Y)
                brazo.set_scale(brazo_scale, brazo_scale)
                world.update()

                # 3. Suelta la caja: re-parenting al mundo con posición global actual
                if caja_capturada is not None:
                    liberar_caja(world, brazo, caja_capturada)

                    # 3. Encolar la caja en la animación de caída ──
                    # En lugar de quedar estática en el mundo, la caja entra
                    # en la Drop Sequence. update_cajas_cayendo() se encargará
                    # de animarla y destruirla frame a frame.
                    cajas_cayendo.append(caja_capturada)
                    print(f"  [Paso3] {caja_capturada.name} encolada en cajas_cayendo ↓")

                    caja_capturada = None

                # 4. Volver a IDLE
                estado_maquina = STATE_IDLE
                print("  [Paso2] Estado → IDLE")

        # animar cajas cayendo ────────────────────────────
        # Se ejecuta SIEMPRE (independiente del estado de la máquina)
        # para que las cajas ya soltadas continúen su animación
        # mientras el usuario mueve la garra hacia la siguiente.
        if cajas_cayendo:
            update_cajas_cayendo(world, cajas_cayendo, dt)

        # ── Aplicar transformaciones al brazo ────────────────────────
        brazo.set_translation(brazo_tx, BRAZO_INIT_Y)
        brazo.set_scale(brazo_scale, brazo_scale)

        world.update()

        # ── Renderizado ──────────────────────────────────────────────
        screen.fill((8, 10, 16))

        draw_background(screen, renderer, bg_surface)

        renderer.draw_scene(world,
                            draw_axes=debug_axes,
                            draw_labels=debug_axes)

        if selected:
            wp    = selected.get_world_position()
            sx,sy = renderer.math_to_screen(wp[0], wp[1])
            pygame.draw.circle(screen, (255, 220, 0), (sx, sy), 11, 2)

        if caja_capturada is not None:
            wp    = caja_capturada.get_world_position()
            sx,sy = renderer.math_to_screen(wp[0], wp[1])
            pygame.draw.circle(screen, (255, 100, 50), (sx, sy), 14, 2)

        draw_hud(screen, selected, selected_idx, len(all_nodes),
                 pinzas_cerradas, debug_axes, caja_capturada,
                 estado_maquina, cajas_cayendo)   # ← Paso 3: pasar lista

        pygame.draw.rect(screen, (28, 33, 52),
                         pygame.Rect(WORLD_W - 1, 0, 3, WINDOW_H))

        panel.draw()
        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()