#!/usr/bin/env python3
"""sgm_bridge.py — Adaptador Minecraft con core modularizado + persistencia."""
import json, random, sys, os, math, time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

SGM = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SGM)
sys.path.insert(0, os.path.join(SGM, "experiments"))

from sgm.core.sgm_core import SGMAgentCore
from experiments.sgm_pulsiones import crear_arbitro_default
from experiments.sgm_l2_system import L2Decoder, DecodeL2
from experiments.sgm_kuramoto import campo_interferencia

# LA MENTE: agente SGM con core modularizado
ag = SGMAgentCore(random.Random(42), 128, n_nodes=64, gamma=0.01)
ag.set_edges({i: random.sample(range(64), min(5, 63)) for i in range(64)})
ag.instinto_alimentacion = 5

# Arbitro de pulsiones
arbitro = crear_arbitro_default()
ag.set_arbitro(arbitro)

# L2 Decoder
l2 = L2Decoder(128)
l2.cargar(os.path.join(SGM, "experiments", "l2_projection.npz"))
decoder_l2 = DecodeL2(128)
decoder_l2.l2 = l2
ag.configurar_l2(l2)

# Persistencia: cargar estado si existe
RUTA_ESTADO = os.path.join(SGM, "experiments", "sgm_estado.npy")
if os.path.exists(RUTA_ESTADO):
    ag.cargar(RUTA_ESTADO)
    print(f"[sgm_bridge] Estado cargado desde {RUTA_ESTADO}")

# Auto-guardado cada 60 segundos
ultimo_guardado = time.time()

print(f"[sgm_bridge] SGM listo: {len(arbitro.pulsiones)} pulsiones, L2={l2.W.shape}")

ACCION_MC = {
    0: "noop", 1: "mover_norte", 2: "mover_sur", 3: "mover_oeste", 4: "mover_este",
    5: "interactuar", 6: "romper", 7: "recoger", 8: "colocar", 9: "craftear",
    10: "saludar", 11: "explorar", 12: "atacar", 13: "huir", 14: "saltar",
    15: "agacharse", 16: "expresarse",
}

class Puente(BaseHTTPRequestHandler):
    def _send(self, txt):
        body = txt.encode("utf-8") if isinstance(txt, str) else txt
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        global ultimo_guardado
        try:
            u = urlparse(self.path)
            q = parse_qs(u.query)
            
            if u.path == "/hablar":
                texto = q.get("texto", [""])[0]
                texto_lower = texto.lower().strip()
                
                sv = [0.0] * 18
                sv[2] = min(1.0, len([p for p in texto_lower.split() if p in ['hambre', 'comida', 'food']]) * 0.3)
                sv[3] = min(1.0, len([p for p in texto_lower.split() if p in ['peligro', 'zombie', 'enemigo']]) * 0.3)
                sv[4] = min(1.0, len([p for p in texto_lower.split() if p in ['arbol', 'madera', 'piedra', 'recurso']]) * 0.3)
                
                ag._hambre_real = sv[2]
                ag._amenaza = sv[3]
                ag._algo_enfrente = 1 if sv[4] > 0 else (2 if sv[3] > 0 else 0)
                
                valid_actions = list(range(17))
                a = ag.step(sv, valid_actions)
                accion_nombre = ACCION_MC.get(a, "noop")
                
                # Generar expresión usando L2
                zona = campo_interferencia(ag.omega, ag.phi, ag.phi[0] if ag.phi else 0.0, ag.vitalidad)
                texto_gen = decoder_l2.decode(zona, max_palabras=3)
                
                payload = {"texto": texto_gen if texto_gen != "..." else f"Entiendo: {texto_lower}"}
                if a != 0:
                    payload["ejecutar"] = {"accion": accion_nombre, "objeto": None}
                
                self._send(json.dumps(payload, ensure_ascii=False))
            
            elif u.path == "/estado":
                zona = campo_interferencia(ag.omega, ag.phi, ag.phi[0] if ag.phi else 0.0, ag.vitalidad)
                texto = decoder_l2.decode(zona, max_palabras=3)
                
                payload = {
                    "texto": texto,
                    "nodos": len(ag.omega),
                    "aristas": sum(len(v) for v in ag.edges.values()) // 2,
                    "place_cells": sum(1 for x in ag.es_place_cell if x),
                    "conn_type": len(ag.conn_type),
                    "V_grafo": round(ag.V_grafo, 3),
                    "modo": ag.modo,
                    "hambre": round(ag._hambre_real, 2),
                    "amenaza": round(ag._amenaza, 2),
                }
                self._send(json.dumps(payload, ensure_ascii=False))
            
            elif u.path == "/accion":
                x = float(q.get("x", ["0"])[0])
                y = float(q.get("y", ["0"])[0])
                z = float(q.get("z", ["0"])[0])
                food = float(q.get("food", ["20"])[0])
                health = float(q.get("health", ["20"])[0])
                hambre = max(0.0, 1.0 - food / 20.0)
                ent_near = q.get("entidades", "[]")[0] if q.get("entidades") else "[]"
                ent_near = json.loads(ent_near) if isinstance(ent_near, str) else ent_near
                peligro = 1.0 if any(e in ("zombie", "skeleton", "creeper", "spider") for e in ent_near) else 0.0
                recurso = 1.0 if any(e in ("tree", "oak_log", "wood", "cow", "pig", "chicken") for e in ent_near) else 0.0
                
                sv = [x/50.0, z/50.0, hambre, peligro, recurso, health/20.0, food/20.0] + [0.0]*11
                
                ag._hambre_real = hambre
                ag._amenaza = peligro
                ag._posicion_actual = (int(x), int(z))
                ag._algo_enfrente = 1 if recurso > 0 else (2 if peligro > 0 else 0)
                ag._hay_gradiente = recurso > 0 or peligro > 0
                ag._gradiente_dir = (1, 0) if recurso > 0 else (0, 0)
                ag._config_grad = {"activo": recurso > 0, "fuerza": recurso}
                ag._config_curio = {"activo": True, "fuerza": 0.4}
                ag._inc_dirs = {1: 1.0, 2: 0.5, 3: 0.5, 4: 0.5}
                
                valid_actions = list(range(17))
                a = ag.step(sv, valid_actions, food=food, health=health)
                accion = ACCION_MC.get(a, "noop")
                
                # Guardar en historial para L2
                zona = campo_interferencia(ag.omega, ag.phi, ag.phi[0] if ag.phi else 0.0, ag.vitalidad)
                ag.historial_campos.append(zona)
                ag.historial_acciones_l2.append(a)
                
                # Auto-guardar cada 60 segundos
                if time.time() - ultimo_guardado > 60:
                    ag.guardar(RUTA_ESTADO)
                    ultimo_guardado = time.time()
                
                self._send(json.dumps({
                    "accion": accion,
                    "indice": a,
                    "hambre": round(hambre, 2),
                    "amenaza": round(peligro, 2),
                    "V_grafo": round(ag.V_grafo, 3),
                    "modo": ag.modo,
                }))
            
            elif u.path == "/metacognicion":
                self._send(json.dumps({
                    "nodos": len(ag.omega),
                    "aristas": sum(len(v) for v in ag.edges.values()) // 2,
                    "place_cells": sum(1 for x in ag.es_place_cell if x),
                    "conn_type": len(ag.conn_type),
                    "V_grafo": round(ag.V_grafo, 3),
                    "modo": ag.modo,
                    "hambre": round(ag._hambre_real, 2),
                    "amenaza": round(ag._amenaza, 2),
                    "drive_noop": round(ag.drive_noop, 2),
                }))
            else:
                self._send(json.dumps({"ok": True}))
        except Exception as e:
            self._send(json.dumps({"error": str(e)}))

    def log_message(self, *a):
        pass

if __name__ == "__main__":
    port = 8790
    httpd = HTTPServer(("127.0.0.1", port), Puente)
    print(f"[sgm_bridge] escuchando en :{port}")
    httpd.serve_forever()