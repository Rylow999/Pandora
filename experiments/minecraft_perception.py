# -*- coding: utf-8 -*-
"""
minecraft_perception.py — Definición única del vector de percepción de Minecraft.

state_semantic es una lista de 18 floats. Esta es la fuente de verdad de qué
significa cada dimensión, para que el adaptador y el core hablen el mismo idioma.
"""
import math

# Dimensiones del state_semantic (18 total, las 7 primeras se usan)
PERCEPCION_DIMS = {
    0: "nivel_comida",          # 0.0 = vacío, 1.0 = lleno (bot.food/20)
    1: "salud",                 # 0.0 = muerto, 1.0 = full (bot.health/20)
    2: "peligro_cercano",       # 0.0 = seguro, 1.0 = zombie en la cara
    3: "comida_visible",        # 0.0 = nada, 1.0 = vaca/manzana enfrente
    4: "bloque_interactuable",  # 0.0 = aire, 1.0 = cofre/puerta/mesa
    5: "altura_relativa",       # -1.0 = bajo suelo, 0.0 = nivel, 1.0 = alto
    6: "hora_dia",              # 0.0 = noche, 0.5 = amanecer, 1.0 = mediodía
}
# Las dimensiones 7-17 son padding (0.0)

N = 18  # longitud total del state_semantic


def build_state(
    food, health,
    peligro_cercano=0.0, comida_visible=0.0, bloque_interactuable=0.0,
    altura=64.0, hora=0.0,
):
    """
    Construye el state_semantic (list de 18 floats) desde los datos del bot.

    Args:
        food: int 0-20 (bot.food)
        health: int 0-20 (bot.health)
        peligro_cercano: 0.0 o 1.0 (hay hostil a < N bloques)
        comida_visible: 0.0 o 1.0 (vaca/manzana/trigo a la vista)
        bloque_interactuable: 0.0 o 1.0 (cofre/mesa/puerta enfrente)
        altura: float, y del jugador (relativo al nivel del mar 64)
        hora: int 0-24000 (bot.time.timeOfDay)
    """
    sv = [0.0] * N
    sv[0] = max(0.0, min(1.0, food / 20.0))
    sv[1] = max(0.0, min(1.0, health / 20.0))
    sv[2] = 1.0 if peligro_cercano else 0.0
    sv[3] = 1.0 if comida_visible else 0.0
    sv[4] = 1.0 if bloque_interactuable else 0.0
    sv[5] = max(-1.0, min(1.0, (altura - 64.0) / 32.0))
    sv[6] = max(0.0, min(1.0, (hora % 24000) / 24000.0))
    return sv