#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
minecraft_bridge.py — Adaptador Mente (SGM core) ↔ Cuerpo (mineflayer-pathfinder).

REFACTOR: la navegacion fisica se delega a mineflayer-pathfinder (A*).
El SGM core YA NO genera acciones de movimiento (1-4); decide una META
de alto nivel ({type, x,y,z}), y el bot JS la convierte en setGoal().

Flujo por tick:
1. Bot JS POST /pose (posicion, food, health, entidades, bloque, meta_estado)
2. El bridge corre el core para decidir QUÉ hacer (comer/explorar/huir)
3. Bridge responde {goal: {...}} — la meta espacial a la que el cuerpo navega
4. Bot JS: si goal.type == 'goto' -> pathfinder.setGoal(GoalNear)
           si goal.type == 'interact' -> usar el bloque/entidad enfrente
5. Bot JS reporta feedback (goal_reached / stuck) via POST /feedback

Persistencia: auto-guarda cada 60s, carga al iniciar, reentrena L2.
"""
import json, os, sys, time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

# Path
SGM = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for p in (SGM, os.path.join(SGM, "experiments")):
    if p not in sys.path:
        sys.path.insert(0, p)

from sgm_core import SGMAgentCore
from experiments.sgm_pulsiones import crear_arbitro_default
from experiments.minecraft_actions import NOMBRE
from experiments.minecraft_perception import build_state

# ---- Config
D = 128
N_NODOS = 64
PUERTO = 8791
RUTA_ESTADO = os.path.join(SGM, "experiments", "sgm_estado.npy")
AUTO_GUARDAR_S = 60.0
REENTRENAR_CADA = 200
CHUNK = 16  # place_bucket de Minecraft
RANGO_NAV = 3      # rango de llegada a un goal
RANGO_COMER = 2.5  # llegar a <=2.5 bloques de la comida para interactuar
ALCANCE_EXPLORAR = 16  # distancia de exploracion (1 chunk)


# Tipos de entidad de interés
COMESTIBLES = ('cow', 'pig', 'chicken', 'sheep', 'rabbit', 'apple')
HOSTILES = ('zombie', 'skeleton', 'creeper', 'spider')


def crear_agente():
    """Construye un SGMAgentCore con grafo conectado y arbitro por defecto."""
    import random
    ag = SGMAgentCore(random.Random(42), D, N_NODOS)
    ag.set_edges({i: random.sample(range(N_NODOS), min(5, N_NODOS - 1)) for i in range(N_NODOS)})
    ag.set_arbitro(crear_arbitro_default())
    ag.instinto_alimentacion = 8
    return ag


def entidad_mas_cerca(pos, entidades, tipos, max_dist=25):
    """Entidad de los tipos mas cercana, o None."""
    cerca = [e for e in entidades if e.get('name') in tipos and e.get('dist', 99) <= max_dist]
    return min(cerca, key=lambda x: x['dist']) if cerca else None


def _decidir_tiene_comida(entidades):
    """True si hay alimento comestible a la vista (para prioridad de emergencia)."""
    return any(e.get('name') in COMESTIBLES for e in entidades)


# Core global del bridge
_ag = crear_agente()
if os.path.exists(RUTA_ESTADO):
    try:
        _ag.cargar(RUTA_ESTADO)
        print(f"[bridge] Estado cargado. place_cells={len(_ag.place_cells)}")
    except Exception as e:
        print(f"[bridge] Error cargando estado: {e}")
_ultimo_guardado = time.time()
_pasos = 0
_ultimas_metas = []   # diagnostico: ultimas metas decididas
_ultima_percep = {}   # diagnostico: percepcion del ultimo tick
_ultimo_feedback = {}  # estado del ultimo goal (goal_reached/stuck)
_meta_actual = None    # meta que se mantiene hasta completarse o fallar


def _decidir_meta(pos, entidades, hambre, amenaza, interactuable, bloque, tiene_comida_inv):
    """
    Decision de ALTO NIVEL del SGM: devuelve una meta {type, ...}.
    El cuerpo (pathfinder) ejecuta el desplazamiento.
    """
    # 1. PELIGRO: huir del hostil mas cercano (meta de escape)
    if amenaza > 0:
        hostil = entidad_mas_cerca(pos, entidades, HOSTILES, max_dist=15)
        if hostil:
            # punto opuesto al hostil a cierta distancia
            gx = pos[0] - (hostil['x'] - pos[0])
            gz = pos[2] - (hostil['z'] - pos[2])
            return {"type": "goto", "x": gx, "y": pos[1], "z": gz,
                    "range": RANGO_NAV, "razon": "huir"}

    # 2. HAMBRE: si el bot tiene comida en el inventario, comer de alli
    #    (accion instantanea, no perseguir animales). Solo ir a un animal
    #    si NO hay comida en el inventario.
    if hambre > 0.3:
        if _decidir_tiene_comida(entidades) and not tiene_comida_inv:
            comida = entidad_mas_cerca(pos, entidades, COMESTIBLES, max_dist=25)
            if comida:
                return {"type": "goto", "x": comida['x'], "y": comida['y'], "z": comida['z'],
                        "range": RANGO_COMER, "razon": "comer",
                        "interactuar_al_llegar": True}
        elif tiene_comida_inv:
            return {"type": "interact", "razon": "comer", "unico": True}

    # 3. INTERACTUABLE enfrente y con necesidad de usarlo (mesa, cofre, etc.)
    # Es una accion de UN SOLO USO: no persiste como meta navegable.
    if interactuable:
        return {"type": "interact", "razon": "usar_bloque", "unico": True}

    # 4. EXPLORACION: chunk vecino menos visitado (curiosidad)
    cx, cz = int(pos[0]) // CHUNK, int(pos[2]) // CHUNK
    visitado = getattr(_ag, '_chunks_visitados', {})
    vecinos = [(cx+1, cz), (cx-1, cz), (cx, cz+1), (cx, cz-1)]
    # el menos visitado
    menos = min(vecinos, key=lambda c: visitado.get(f"c{c[0]}_{c[1]}", 0))
    return {"type": "goto",
            "x": menos[0] * CHUNK + CHUNK//2, "y": pos[1], "z": menos[1] * CHUNK + CHUNK//2,
            "range": RANGO_NAV, "razon": "explorar"}


def _procesar_pose(data):
    """Aplica una pose del bot y decide la META que el cuerpo debe seguir."""
    global _ultimo_guardado, _pasos, _ultimas_metas, _ultima_percep, _ultimo_feedback
    pos = data.get('pos', [0, 64, 0])
    food = data.get('food', 20)
    health = data.get('health', 20)
    entidades = data.get('entidades', [])
    bloque = data.get('bloque', '')
    interactuable = data.get('interactuable', False)
    hora = data.get('hora', 0)
    meta_estado = data.get('meta_estado', '')  # goal_reached / stuck / None
    tiene_comida = data.get('tiene_comida', False)  # el bot tiene comida en inventario

    hambre = 1.0 - food / 20.0
    amenaza = 1.0 if any(e.get('name') in HOSTILES for e in entidades) else 0.0

    # ---- Estado corporal / amenaza en el core
    _ag._posicion_actual = (pos[0], pos[1], pos[2])
    _ag._hambre_real = hambre
    _ag._amenaza = amenaza
    recursos = [e for e in entidades if e.get('name') in COMESTIBLES and e.get('dist', 99) < 3]
    _ag._algo_enfrente = 8 if (hambre > 0.3 and recursos) else (4 if interactuable else 0)

    # ---- Curiosidad / exploracion (incertidumbre por chunk)
    cx, cz = int(pos[0]) // CHUNK, int(pos[2]) // CHUNK
    visitado = getattr(_ag, '_chunks_visitados', {})
    clave = f"c{cx}_{cz}"
    visitado[clave] = visitado.get(clave, 0) + 1
    _ag._chunks_visitados = visitado
    _ag.incertidumbre_acum = 1.0 / (1.0 + visitado[clave])
    _ag._inc_dirs = {}
    dirs = {1: (0, -1), 2: (0, 1), 3: (-1, 0), 4: (1, 0)}
    for acc, (dcx, dcz) in dirs.items():
        nv = visitado.get(f"c{cx+dcx}_{cz+dcz}", 0)
        _ag._inc_dirs[acc] = 1.0 / (1.0 + nv)
    estancado = visitado[clave] >= 3 and _ag.V_grafo < 0.2
    _ag._config_curio = {'activo': amenaza == 0, 'fuerza': 0.8 if estancado else 0.4}

    # ---- Correr el core (cerebro): produce la accion abstracta + estado
    sv = build_state(food, health, peligro_cercano=amenaza,
                     comida_visible=bool(recursos),
                     bloque_interactuable=int(interactuable),
                     altura=pos[1], hora=hora)
    accion_core = _ag.step(sv, list(range(17)), food=food, health=health)
    _pasos += 1

    # ---- DECIDIR LA META de alto nivel (cuerpo la navega)
    # Mantener la meta actual hasta que se complete (goal_reached), falle (stuck)
    # o haya una emergencia nueva (peligro/hambre aparecen). No recalcularla
    # cada tick, para que el pathfinder pueda llegar sin ser interrumpido.
    global _meta_actual
    if meta_estado == 'stuck':
        _ultimo_feedback = {'stuck': True, 'pos': pos}
        # marcar mucho visitado el chunk actual para forzar explorar otro
        _ag._chunks_visitados[clave] = visitado.get(clave, 0) + 5
        _meta_actual = None  # fallo -> decidir nueva
    elif meta_estado == 'goal_reached':
        _ultimo_feedback = {'goal_reached': True, 'pos': pos}
        _meta_actual = None  # cumplido -> decidir nueva
    else:
        _ultimo_feedback = {}

    # Emergencias superan la meta actual (siempre prioiritarias)
    emergencia = None
    if amenaza > 0 or (hambre > 0.3 and (_decidir_tiene_comida(entidades) or tiene_comida)):
        emergencia = _decidir_meta(pos, entidades, hambre, amenaza, interactuable, bloque, tiene_comida)

    if emergencia is not None:
        meta = emergencia
        # las metas 'unico' (interact) no persisten: se consumen en un tick
        _meta_actual = None if meta.get('unico') else meta
    elif _meta_actual is None:
        meta = _decidir_meta(pos, entidades, hambre, amenaza, interactuable, bloque, tiene_comida)
        _meta_actual = None if meta.get('unico') else meta
    else:
        meta = _meta_actual  # seguir con la meta en curso

    # Registrar la meta en el core para que el L2 aprenda estado->meta
    _ag.registrar_meta(meta.get('razon', 'explorar'))

    _ultimas_metas.append(meta['razon'])
    if len(_ultimas_metas) > 20:
        _ultimas_metas.pop(0)

    _ultima_percep = {
        "hambre": round(hambre, 2),
        "amenaza": round(amenaza, 2),
        "recursos": [r.get('name') for r in recursos],
        "meta": meta,
        "accion_core": accion_core,
    }

    # ---- Persistencia + sueño
    if time.time() - _ultimo_guardado > AUTO_GUARDAR_S:
        _ag.guardar(RUTA_ESTADO)
        _ultimo_guardado = time.time()
        _ag.reconciliar()

    # ---- L2 periodico
    if _pasos % REENTRENAR_CADA == 0 and len(_ag.historial_campos) >= 10:
        try:
            _ag.procesar_l2(epochs=15)
            print(f"[bridge] L2 reentrenado: {_ag.generar_texto()}")
        except Exception as e:
            print(f"[bridge] L2 error: {e}")

    return {
        "goal": meta,
        "texto": _ag.generar_texto() if _pasos % 20 == 0 else "",
        "modo": _ag.modo,
        "V_grafo": round(_ag.V_grafo, 3),
        "nodos": len(_ag.omega),
    }


def _estado():
    return {
        "nodos": len(_ag.omega),
        "aristas": sum(len(v) for v in _ag.edges.values()) // 2,
        "place_cells": len(getattr(_ag, 'place_cells', [])),
        "historial_l2": len(_ag.historial_campos),
        "V_grafo": round(_ag.V_grafo, 3),
        "modo": _ag.modo,
        "texto": _ag.generar_texto(),
        "posicion": str(_ag._posicion_actual),
        "ultimas_metas": list(_ultimas_metas),
        "percepcion": _ultima_percep,
        "feedback": _ultimo_feedback,
    }


class Bridge(BaseHTTPRequestHandler):
    def _send(self, obj):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urlparse(self.path)
        self._send(_estado() if u.path == "/estado" else {"ok": True})

    def do_POST(self):
        u = urlparse(self.path)
        try:
            length = int(self.headers.get('Content-Length', 0))
            data = json.loads(self.rfile.read(length)) if length else {}
        except Exception:
            data = {}
        try:
            if u.path == "/pose":
                self._send(_procesar_pose(data))
            elif u.path == "/guardar":
                _ag.guardar(RUTA_ESTADO)
                self._send({"ok": True, "guardado": RUTA_ESTADO})
            elif u.path == "/estado":
                self._send(_estado())
            else:
                self._send({"error": "ruta desconocida"})
        except Exception as e:
            import traceback; traceback.print_exc()
            self._send({"error": str(e)})

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    print(f"[bridge] MENTE-CUERPO escuchando en :{PUERTO}")
    print(f"[bridge] navegacion delegada a mineflayer-pathfinder (A*)")
    print(f"[bridge] core: nodos={len(_ag.omega)}")
    HTTPServer(("127.0.0.1", PUERTO), Bridge).serve_forever()