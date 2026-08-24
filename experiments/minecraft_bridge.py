#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
minecraft_bridge.py — Adaptador Mine flayer ↔ SGM Core.

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
import json, os, sys, time, math
import numpy as np
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

# Path
SGM = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SGM)
sys.path.insert(0, os.path.join(SGM, "experiments"))

from sgm_core import SGMAgentCore
from experiments.sgm_pulsiones import crear_arbitro_default
from experiments.minecraft_actions import NOMBRE, ACCIONES_MOVIMIENTO
from experiments.minecraft_perception import build_state
from experiments.sgm_lang import ID2TOKEN

# ---- Config
D = 128
N_NODOS = 64
RUTA_ESTADO = os.path.join(SGM, "experiments", "sgm_estado.npy")
AUTO_GUARDAR_S = 60.0
REENTRENAR_CADA = 200
CHUNK = 16  # place_bucket

# ---- Construir core
import random
_ag = SGMAgentCore(random.Random(42), D, N_NODOS)
# Grafo conectado (si no, PPR devuelve vacio y nunca se mueve)
_ag.set_edges({i: random.sample(range(N_NODOS), min(5, N_NODOS-1)) for i in range(N_NODOS)})
_ag.set_arbitro(crear_arbitro_default())
_ag.instinto_alimentacion = 8  # USE (boton derecho: comer/interactuar)

# Cargar estado persistido
if os.path.exists(RUTA_ESTADO):
    try:
        _ag.cargar(RUTA_ESTADO)
        n_place = len(getattr(_ag, 'place_cells', []))
        print(f"[bridge] Estado cargado. place_cells={n_place}")
    except Exception as e:
        print(f"[bridge] Error cargando estado: {e}")

_ultimo_guardado = time.time()
_pasos = 0

# ---- Utilidades de percepción (provisión de pulsiones)
def _target_a_entidad(pos, entidades, comida=False, peligro=False):
    """Calcula _target_dir/_target_dist a la entidad de interés más cercana."""
    tipos = []
    if comida: tipos += ['cow', 'pig', 'chicken', 'sheep', 'rabbit', 'apple']
    if peligro: tipos += ['zombie', 'skeleton', 'creeper', 'spider']
    cerca = [e for e in entidades if e.get('name') in tipos and e.get('dist', 99) < 15]
    if not cerca:
        return (0, 0, 0), 0
    e = min(cerca, key=lambda x: x['dist'])
    dx = 1 if e['x'] > pos[0] else (-1 if e['x'] < pos[0] else 0)
    dy = 1 if e['y'] > pos[1] else (-1 if e['y'] < pos[1] else 0)
    dz = 1 if e['z'] > pos[2] else (-1 if e['z'] < pos[2] else 0)
    return (dx, dy, dz), e['dist']


class Bridge(BaseHTTPRequestHandler):
    def _send(self, obj):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        # /estado sirve por GET (debug); /pose necesita POST (datos del mundo)
        u = urlparse(self.path)
        if u.path == "/estado":
            self._send({
                "nodos": len(_ag.omega),
                "aristas": sum(len(v) for v in _ag.edges.values()) // 2,
                "place_cells": len(getattr(_ag, 'place_cells', [])),
                "consolidadas": len(_ag.consolidadas),
                "historial_l2": len(_ag.historial_campos),
                "V_grafo": round(_ag.V_grafo, 3),
                "modo": _ag.modo,
                "meta": str(_ag.meta_recordada),
                "texto": _ag.generar_texto(),
            })
        else:
            self._send({"ok": True})

    def do_POST(self):
        global _ultimo_guardado, _pasos
        u = urlparse(self.path)
        try:
            length = int(self.headers.get('Content-Length', 0))
            data = json.loads(self.rfile.read(length)) if length else {}
        except Exception:
            data = {}
        
        try:
            if u.path == "/pose":
                # ---- Leer pose del bot
                pos = data.get('pos', [0, 64, 0])
                food = data.get('food', 20)
                health = data.get('health', 20)
                entidades = data.get('entidades', [])
                bloque = data.get('bloque', '')      # bloque en el cursor
                interactuable = data.get('interactuable', False)
                hora = data.get('hora', 0)

                # ---- Atributos de percepción del core
                _ag._posicion_actual = (pos[0], pos[1], pos[2])
                _ag._hambre_real = 1.0 - food / 20.0
                _ag._amenaza = 1.0 if any(e['name'] in ('zombie','skeleton','creeper','spider') for e in entidades) else 0.0

                # Objeto enfrente (para Interacción): bloque o entidad comestible
                hambre = _ag._hambre_real
                recursos = [e for e in entidades if e.get('name') in ('cow','pig','chicken','sheep','apple') and e.get('dist', 99) < 3]
                _ag._algo_enfrente = 8 if (hambre > 0.3 and recursos) else (4 if interactuable else 0)

                # ---- Pulsiones avanzadas (desde percepción)
                # Target: si hay hambre, ir a comida; si hay peligro, considerar huir
                target_dir, target_dist = _target_a_entidad(pos, entidades, comida=hambre > 0.3)
                if target_dir == (0,0,0) and _ag._amenaza > 0:
                    target_dir, target_dist = _target_a_entidad(pos, entidades, peligro=True)
                _ag._target_dir = target_dir
                _ag._target_dist = target_dist

                # Gradiente: recurso visible cerca (bloque o entidad de comida)
                hay_recurso = bool(recursos) or (bloque in ('grass_block','tall_grass','oak_leaves','wheat'))
                _ag._hay_gradiente = hay_recurso
                _ag._gradiente_dir = target_dir if hay_recurso else (0, 0, 0)
                _ag._config_grad = {'activo': hay_recurso, 'fuerza': 0.5}

                # Curiosidad/Exploración: incertidumbre por chunk visitado
                cx = int(pos[0]) // CHUNK; cz = int(pos[2]) // CHUNK
                clave = f"c{cx}_{cz}"
                visitado = getattr(_ag, '_chunks_visitados', {})
                if clave not in visitado:
                    visitado[clave] = 0
                visitado[clave] += 1
                _ag._chunks_visitados = visitado
                # Incertidumbre: cuanto menos visitado el chunk actual, mayor curiosidad
                n_vis = visitado.get(clave, 0)
                _ag.incertidumbre_acum = 1.0 / (1.0 + n_vis)  # 1.0 si nunca fui
                _ag._inc_dirs = {1: 0.5, 2: 0.5, 3: 0.5, 4: 0.5}
                _ag._config_curio = {'activo': True, 'fuerza': 0.4}

                # ---- state_semantic
                sv = build_state(
                    food, health,
                    peligro_cercano=_ag._amenaza,
                    comida_visible=bool(recursos),
                    bloque_interactuable=int(interactuable),
                    altura=pos[1], hora=hora,
                )

                # ---- STEP
                valid = list(range(17))
                accion = _ag.step(sv, valid, food=food, health=health)
                nombre = NOMBRE.get(accion, f"accion_{accion}")
                _pasos += 1

                # ---- Persistencia
                if time.time() - _ultimo_guardado > AUTO_GUARDAR_S:
                    _ag.guardar(RUTA_ESTADO)
                    _ultimo_guardado = time.time()
                    _ag.reconciliar()  # sueño/consolidación en reposo

                # ---- L2: reentrenar cada N pasos
                if _pasos % REENTRENAR_CADA == 0 and len(_ag.historial_campos) >= 10:
                    try:
                        _ag.procesar_l2(epochs=15)
                        print(f"[bridge] L2 reentrenado, texto: {_ag.generar_texto()}")
                    except Exception as e:
                        print(f"[bridge] L2 error: {e}")

                texto = _ag.generar_texto() if _pasos % 20 == 0 else ""

                self._send({
                    "accion": accion,
                    "nombre": nombre,
                    "texto": texto,
                    "modo": _ag.modo,
                    "V_grafo": round(_ag.V_grafo, 3),
                    "nodos": len(_ag.omega),
                    "place_cells": len(getattr(_ag, 'place_cells', [])),
                })

            elif u.path == "/estado":
                self._send({
                    "nodos": len(_ag.omega),
                    "aristas": sum(len(v) for v in _ag.edges.values()) // 2,
                    "place_cells": len(getattr(_ag, 'place_cells', [])),
                    "consolidadas": len(_ag.consolidadas),
                    "historial_l2": len(_ag.historial_campos),
                    "V_grafo": round(_ag.V_grafo, 3),
                    "modo": _ag.modo,
                    "meta": _ag.meta_recordada,
                    "texto": _ag.generar_texto(),
                })

            elif u.path == "/guardar":
                _ag.guardar(RUTA_ESTADO)
                self._send({"ok": True, "guardado": RUTA_ESTADO})

            else:
                self._send({"error": "ruta desconocida"})
        except Exception as e:
            import traceback; traceback.print_exc()
            self._send({"error": str(e)})

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    port = 8791
    print(f"[bridge] escuchando en :{port}")
    print(f"[bridge] instinto_alimentacion={_ag.instinto_alimentacion} (USE=8)")
    print(f"[bridge] core: nodos={len(_ag.omega)}, aristas={sum(len(v) for v in _ag.edges.values())//2}")
    HTTPServer(("127.0.0.1", port), Bridge).serve_forever()