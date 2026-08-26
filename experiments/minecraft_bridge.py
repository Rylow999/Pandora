#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
minecraft_bridge.py — Adaptador Mineflayer ↔ SGM Core.

Puente que conecta el bot de Minecraft (puente_minecraft_sgm.js) con el
SGMAgentCore. Corre como servidor HTTP en :8791. El bot JS lo llama cada tick.

Flujo por tick:
1. Bot JS POST /pose  (posicion, food, health, entidades, bloque en cursor)
2. El bridge arma state_semantic + atributos de pulsiones
3. Core.step() devuelve la accion (indice MC)
4. Bridge responde {accion, texto} y el bot ejecuta

Persistencia:
- Auto-guarda estado en experiments/sgm_estado.npy cada 60s
- Carga al iniciar si existe
- Reentrena L2 cada 200 pasos y guarda texto generado
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
CHUNK = 16  # place_bucket de Minecraft (coincide con sgm_core)

# Tipos de entidad de interés
COMESTIBLES = ('cow', 'pig', 'chicken', 'sheep', 'rabbit', 'apple')
HOSTILES = ('zombie', 'skeleton', 'creeper', 'spider')


def crear_agente():
    """Construye un SGMAgentCore con grafo conectado y arbitro por defecto."""
    import random
    ag = SGMAgentCore(random.Random(42), D, N_NODOS)
    # Grafo inicial conectado: sin esto PPR devuelve vacio y nunca se mueve
    ag.set_edges({i: random.sample(range(N_NODOS), min(5, N_NODOS - 1)) for i in range(N_NODOS)})
    ag.set_arbitro(crear_arbitro_default())
    ag.instinto_alimentacion = 8  # USE (boton derecho: comer/interactuar)
    return ag


def dir_a_entidad(pos, entidades, tipos):
    """Direccion unitaria y distancia a la entidad mas cercana de los tipos dados."""
    cerca = [e for e in entidades if e.get('name') in tipos and e.get('dist', 99) < 15]
    if not cerca:
        return (0, 0, 0), 0
    e = min(cerca, key=lambda x: x['dist'])
    dx = 1 if e['x'] > pos[0] else (-1 if e['x'] < pos[0] else 0)
    dy = 1 if e['y'] > pos[1] else (-1 if e['y'] < pos[1] else 0)
    dz = 1 if e['z'] > pos[2] else (-1 if e['z'] < pos[2] else 0)
    return (dx, dy, dz), e['dist']


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
_ultimas_acciones = []  # buffer de diagnostico: ultimas acciones decididas
_ultima_percep = {}      # diagnostico: percepcion del ultimo tick


def _procesar_pose(data):
    """Aplica una pose del bot al core y devuelve la accion decidida + info."""
    global _ultimo_guardado, _pasos, _ultimas_acciones, _ultima_percep
    pos = data.get('pos', [0, 64, 0])
    food = data.get('food', 20)
    health = data.get('health', 20)
    entidades = data.get('entidades', [])
    bloque = data.get('bloque', '')          # bloque en el cursor
    interactuable = data.get('interactuable', False)
    hora = data.get('hora', 0)

    hambre = 1.0 - food / 20.0

    # ---- Estado corporal / amenaza
    _ag._posicion_actual = (pos[0], pos[1], pos[2])
    _ag._hambre_real = hambre
    _ag._amenaza = 1.0 if any(e.get('name') in HOSTILES for e in entidades) else 0.0
    recursos = [e for e in entidades if e.get('name') in COMESTIBLES and e.get('dist', 99) < 3]
    _ag._algo_enfrente = 8 if (hambre > 0.3 and recursos) else (4 if interactuable else 0)

    # ---- Target: comida si hay hambre; HUIR (direccion opuesta) si hay peligro
    target_dir, target_dist = dir_a_entidad(pos, entidades, COMESTIBLES) if hambre > 0.3 else ((0, 0, 0), 0)
    if _ag._amenaza > 0:
        hdir, hdist = dir_a_entidad(pos, entidades, HOSTILES)
        target_dir = (-hdir[0], hdir[1], -hdir[2]) if hdir != (0, 0, 0) else (0, 0, 0)
        target_dist = hdist
    # ---- Girar al estancarse: si el bot no avanza (muro) pese a moverse,
    #      cambiar de direccion. Funciona AUNQUE target_dir sea (0,0,0) (caso
    #      'vagar sin objetivo'), porque el estancamiento = hay obstaculo.
    divs = ((-1, 0, 1), (1, 0, 1), (1, 0, -1), (-1, 0, -1), (0, 0, 1), (0, 0, -1),
            (1, 0, 0), (-1, 0, 0))
    pos_prev = getattr(_ag, '_pos_prev', None)
    _ag._pos_prev = (pos[0], pos[1], pos[2])
    giros = getattr(_ag, '_giros', 0)
    if pos_prev is not None:
        desplazo = abs(pos[0] - pos_prev[0]) + abs(pos[2] - pos_prev[2])
        if desplazo < 0.3:
            giros += 1
            if giros >= 4:  # 4 ticks sin avanzar => hay obstaculo, girar
                n = getattr(_ag, '_n_giro', 0)
                target_dir = divs[n % len(divs)]  # probar otra direccion
                _ag._n_giro = n + 1
                _ag._target_dir = target_dir
                giros = 0
        else:
            giros = 0
    _ag._giros = giros
    _ag._target_dir = target_dir
    _ag._target_dist = target_dist

    # ---- Gradiente: recurso visible cerca
    hay_recurso = bool(recursos) or bloque in ('grass_block', 'tall_grass', 'oak_leaves', 'wheat')
    _ag._hay_gradiente = hay_recurso
    _ag._gradiente_dir = target_dir if hay_recurso else (0, 0, 0)
    _ag._config_grad = {'activo': hay_recurso and _ag._amenaza == 0, 'fuerza': 0.5}

    # ---- Curiosidad: incertidumbre por chunk visitado
    cx, cz = int(pos[0]) // CHUNK, int(pos[2]) // CHUNK
    visitado = getattr(_ag, '_chunks_visitados', {})
    clave = f"c{cx}_{cz}"
    visitado[clave] = visitado.get(clave, 0) + 1
    _ag._chunks_visitados = visitado
    # Incertidumbre acumulada: inversa a cuantas veces visité este chunk
    _ag.incertidumbre_acum = 1.0 / (1.0 + visitado[clave])
    # Incertidumbre por direccion: mayor hacia chunk vecino menos visitado
    _ag._inc_dirs = {}
    vecinos = {
        1: (cx, cz - 1), 2: (cx, cz + 1), 3: (cx - 1, cz), 4: (cx + 1, cz),
    }
    for acc, (vx, vz) in vecinos.items():
        nv = visitado.get(f"c{vx}_{vz}", 0)
        _ag._inc_dirs[acc] = 1.0 / (1.0 + nv)
    # Curiosidad activa siempre que no haya peligro; se refuerza si el agente
    # esta empantanado (mismo chunk, homeostasis baja -> debe explorar)
    estancado = visitado[clave] >= 3 and _ag.V_grafo < 0.2
    _ag._config_curio = {'activo': _ag._amenaza == 0, 'fuerza': 0.8 if estancado else 0.4}

    # ---- state_semantic y STEP
    sv = build_state(food, health,
                     peligro_cercano=_ag._amenaza,
                     comida_visible=bool(recursos),
                     bloque_interactuable=int(interactuable),
                     altura=pos[1], hora=hora)
    accion = _ag.step(sv, list(range(17)), food=food, health=health)
    _pasos += 1
    _ultimas_acciones.append(accion)
    if len(_ultimas_acciones) > 20:
        _ultimas_acciones.pop(0)
    # diagnostico: guardar percepcion local de este tick (para /estado)
    _ultima_percep = {
        "hambre": round(_ag._hambre_real, 2),
        "algo_enfrente": _ag._algo_enfrente,
        "recursos": [r.get('name') for r in recursos],
        "target": _ag._target_dir,
        "estancado": _ultimas_acciones.count(_ultimas_acciones[-1]) if _ultimas_acciones else 0,
    }

    # ---- Persistencia periodica + sueño/consolidacion
    if time.time() - _ultimo_guardado > AUTO_GUARDAR_S:
        _ag.guardar(RUTA_ESTADO)
        _ultimo_guardado = time.time()
        _ag.reconciliar()

    # ---- Reentrenar L2 con datos acumulados
    if _pasos % REENTRENAR_CADA == 0 and len(_ag.historial_campos) >= 10:
        try:
            _ag.procesar_l2(epochs=15)
            print(f"[bridge] L2 reentrenado, texto: {_ag.generar_texto()}")
        except Exception as e:
            print(f"[bridge] L2 error: {e}")

    return {
        "accion": accion,
        "nombre": NOMBRE.get(accion, f"accion_{accion}"),
        "texto": _ag.generar_texto() if _pasos % 20 == 0 else "",
        "modo": _ag.modo,
        "V_grafo": round(_ag.V_grafo, 3),
        "nodos": len(_ag.omega),
        "place_cells": len(_ag.place_cells),
    }


def _estado():
    """Estado global del core (debug / observacion)."""
    return {
        "nodos": len(_ag.omega),
        "aristas": sum(len(v) for v in _ag.edges.values()) // 2,
        "place_cells": len(_ag.place_cells),
        "consolidadas": len(_ag.consolidadas),
        "historial_l2": len(_ag.historial_campos),
        "V_grafo": round(_ag.V_grafo, 3),
        "modo": _ag.modo,
        "meta": str(_ag.meta_recordada),
        "texto": _ag.generar_texto(),
        "posicion": str(_ag._posicion_actual),      # posicion percibida por el core
        "inc_dirs": _ag._inc_dirs,                   # incertidumbre por direccion
        "ultimas_acciones": list(_ultimas_acciones),  # diagnostico: ultimas acciones
        "percepcion": _ultima_percep,             # diagnostico: percepcion del tick
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
    print(f"[bridge] escuchando en :{PUERTO}")
    print(f"[bridge] instinto_alimentacion={_ag.instinto_alimentacion} (USE=8)")
    print(f"[bridge] core: nodos={len(_ag.omega)}, aristas={sum(len(v) for v in _ag.edges.values()) // 2}")
    HTTPServer(("127.0.0.1", PUERTO), Bridge).serve_forever()