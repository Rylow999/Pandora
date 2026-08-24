# -*- coding: utf-8 -*-
"""
minecraft_actions.py — Mapeo de acciones de Minecraft → índices internos del SGM.
Fuente de verdad única. Tanto el core como el adaptador la usan.
"""

# Acciones básicas de movimiento + interacción
NOOP = 0
FORWARD = 1
BACK = 2
LEFT = 3
RIGHT = 4
JUMP = 5
SNEAK = 6
ATTACK = 7
USE = 8
CRAFT = 9
EQUIP = 10
MINE = 11
PLACE = 12
LOOK_UP = 13
LOOK_DOWN = 14
LOOK_LEFT = 15
LOOK_RIGHT = 16

# Grupos funcionales (usados por pulsiones)
ACCIONES_MOVIMIENTO = {FORWARD, BACK, LEFT, RIGHT, JUMP}
ACCIONES_INTERACCION = {ATTACK, USE, CRAFT, MINE, PLACE}
ACCIONES_VISTA = {LOOK_UP, LOOK_DOWN, LOOK_LEFT, LOOK_RIGHT}

# Nombres para debug y L2
NOMBRE = {
    NOOP: "quieto",
    FORWARD: "adelante",
    BACK: "atras",
    LEFT: "izquierda",
    RIGHT: "derecha",
    JUMP: "saltar",
    SNEAK: "agacharse",
    ATTACK: "atacar",
    USE: "usar",
    CRAFT: "craftear",
    EQUIP: "equipar",
    MINE: "minar",
    PLACE: "colocar",
    LOOK_UP: "mirar_arriba",
    LOOK_DOWN: "mirar_abajo",
    LOOK_LEFT: "mirar_izq",
    LOOK_RIGHT: "mirar_der",
}